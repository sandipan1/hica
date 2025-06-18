from typing import Dict, Generic, List, Literal, Optional, Type, TypeVar

from instructor import AsyncInstructor
from pydantic import BaseModel

from hica.core import Event, Thread
from hica.logging import logger
from hica.models import ClarificationRequest, DoneForNow, DynamicToolCall, FinalResponse
from hica.tools import ToolRegistry, create_model_from_tool_schema

T = TypeVar("T")


class AgentConfig(BaseModel):
    """Configuration for the autonomous agent."""

    model: str = "gpt-4o"
    system_prompt: str = (
        "You are an autonomous agent. Your primary goal is to fulfill the user's request. "
        "Carefully analyze the user's initial input and the results of any previous tool executions. "
        "Based on this, select the appropriate tool(s) from the available list. "
        "If the user's request has been fully addressed, respond with 'done'. "
        "If you require further input or clarification, respond with 'clarification'."
    )
    context_format: str = "json"


class Agent(Generic[T]):
    """An autonomous agent that processes user queries using tools and an LLM."""

    def __init__(
        self,
        client: AsyncInstructor,
        config: AgentConfig,
        tool_registry: Optional[ToolRegistry] = None,
        metadata: Optional[Dict[str, any]] = None,
    ):
        self.client = client
        self.config = config
        self.tool_registry = tool_registry or ToolRegistry()
        self.response_model: Type[BaseModel] = DynamicToolCall
        self.metadata = metadata or {}
        self._tool_metadata_cache: Optional[str] = None
        logger.info(
            "Agent initialized", config=config.model_dump(), metadata=self.metadata
        )

    def set_response_model(self, response_model: Type[BaseModel]) -> None:
        """Set the response model for LLM calls."""
        self.response_model = response_model
        logger.debug("Response model set", model=response_model.__name__)

    def _format_tool_metadata(self) -> str:
        """Format tool metadata for inclusion in LLM prompts."""
        if self._tool_metadata_cache is None:
            tools_str = ""
            for intent, tool_def in self.tool_registry.tool_definitions.items():
                tools_str += f"<tool> {tool_def.name} : {tool_def.description or 'No description'}</tool>\n"
            self._tool_metadata_cache = tools_str.rstrip()
        return self._tool_metadata_cache

    def _build_messages(
        self,
        thread: Thread[T],
        instruction: str,
        include_tools: bool = True,
        for_parameters: bool = False,
    ) -> List[Dict[str, str]]:
        """Build a list of messages from thread events for LLM calls."""
        messages = [{"role": "system", "content": self.config.system_prompt}]

        # Add tool metadata if requested
        if include_tools:
            tool_metadata = self._format_tool_metadata()
            if tool_metadata:
                messages[0]["content"] += f"\nAvailable tools:\n{tool_metadata}"

        # Add conversation history
        for event in thread.events:
            if event.type == "user_input":
                messages.append({"role": "user", "content": str(event.data)})
            elif event.type == "llm_response":
                if "intent" in event.data:
                    intent = event.data["intent"]
                    if intent in ["done", "clarification"]:
                        messages.append({"role": "assistant", "content": intent})
                    else:
                        tool_name = intent
                        tool_args = event.data.get("arguments", {})
                        messages.append(
                            {
                                "role": "assistant",
                                "content": f"Selected tool '{tool_name}' with parameters: {tool_args}",
                            }
                        )
                else:
                    messages.append({"role": "assistant", "content": str(event.data)})
            elif event.type == "tool_response":
                messages.append(
                    {"role": "user", "content": f"Tool execution result: {event.data}"}
                )

        # Add specific instruction
        if for_parameters:
            messages[0]["content"] += (
                "\nYou are an expert at extracting parameters for tools. "
                "Analyze the user's request and previous tool results to provide the correct parameters. "
                "Use numbers directly from the request or the most recent tool result if implied."
            )
        messages.append({"role": "user", "content": instruction})

        return messages

    async def _call_llm(
        self, messages: List[Dict[str, str]], response_model: Type[BaseModel]
    ) -> BaseModel:
        """Execute an LLM call with the given messages and response model."""
        logger.debug(
            "LLM call", messages=messages, response_model=response_model.__name__
        )
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                response_model=response_model,
                messages=messages,
                temperature=0.0,
            )
            thread_data = (
                response.model_dump()
                if hasattr(response, "model_dump")
                else str(response)
            )
            return response
        except Exception as e:
            logger.error("LLM call failed", error=str(e), messages=messages)
            raise ValueError(f"LLM call failed: {str(e)}")

    async def _select_tool(self, thread: Thread[T]) -> BaseModel:
        """Select the next tool or terminal state using the LLM."""
        valid_intents = tuple(self.tool_registry.tool_definitions.keys()) + (
            "done",
            "clarification",
        )
        ToolLiteral = Literal[valid_intents] if valid_intents else str

        class ToolSelection(BaseModel):
            intent: ToolLiteral

        instruction = (
            "Based on the conversation and tool results, select the next tool (intent), "
            "or respond with 'done' if the task is complete, or 'clarification' if more information is needed. "
            "Respond ONLY with the intent name, 'done', or 'clarification'."
        )
        messages = self._build_messages(thread, instruction)
        response = await self._call_llm(messages, ToolSelection)
        thread.append_event(Event(type="llm_response", data=response.model_dump()))
        logger.info("Tool selected", intent=response.intent)

        if response.intent == "done":
            return DoneForNow(message="Task completed by agent.")
        if response.intent == "clarification":
            return ClarificationRequest(message="Clarification needed from user.")
        return response

    async def _fill_parameters(self, thread: Thread[T], intent: str) -> DynamicToolCall:
        """Fill parameters for the selected tool using the LLM."""
        tool_def = self.tool_registry.tool_definitions.get(intent)
        if not tool_def:
            logger.error("Tool not found", intent=intent)
            raise ValueError(f"Tool {intent} not found")

        ToolParamsModel = create_model_from_tool_schema(tool_def)
        instruction = (
            f"You have selected the tool: {tool_def.name}.\n"
            f"Description: {tool_def.description}\n"
            f"Parameters schema:\n{tool_def.parameters_json_schema}\n"
            "Considering the full conversation history and the most recent tool execution result, "
            "provide ONLY the required parameters as per the schema above. "
            "If the user's request implies using a previous result, use that result as an input."
        )
        messages = self._build_messages(thread, instruction, for_parameters=True)
        param_response = await self._call_llm(messages, ToolParamsModel)

        arguments = {
            param_name: getattr(param_response, param_name)
            for param_name in tool_def.parameters_json_schema.get(
                "properties", {}
            ).keys()
            if hasattr(param_response, param_name)
        }
        tool_call = DynamicToolCall(intent=intent, arguments=arguments)
        thread.append_event(Event(type="llm_response", data=tool_call.model_dump()))
        logger.info("Tool parameters filled", intent=intent)
        return tool_call

    async def _generate_final_response(self, thread: Thread[T]) -> FinalResponse:
        """Generate a final response summarizing the results for the user."""
        instruction = (
            "Based on the conversation history and tool execution results, "
            "provide a clear and concise response to the user's original request. "
            "Summarize the key findings or results in a user-friendly way."
        )
        messages = self._build_messages(thread, instruction)

        class ResponseModel(BaseModel):
            message: str
            summary: Optional[str] = None

        response = await self._call_llm(messages, ResponseModel)

        # Collect all tool results
        tool_results = {}
        for event in thread.events:
            if event.type == "tool_response" or event.type == "user_input":
                tool_results[event.type] = event.data

        return FinalResponse(
            message=response.message, summary=response.summary, raw_results=tool_results
        )

    async def determine_next_step(self, thread: Thread[T]) -> T:
        """Determine the next step for the agent based on the thread state.

        This method orchestrates tool selection and parameter filling using two LLM calls:
        1. Selects a tool or terminal state (done/clarification).
        2. Fills parameters for the selected tool, if applicable.
        """
        if not thread.events:
            logger.warning("Thread has no events; initializing with empty user input")
            thread.append_event(Event(type="user_input", data=""))

        # Step 1: Select tool or terminal state
        selection = await self._select_tool(thread)

        # Step 2: Handle tool selection or return terminal state
        if isinstance(selection, (DoneForNow, ClarificationRequest)):
            return selection
        if isinstance(selection, DynamicToolCall):
            return selection

        # Step 3: Fill parameters for the selected tool
        return await self._fill_parameters(thread, selection.intent)

    async def agent_loop(self, thread: Thread[T]) -> Thread[T]:
        """Run the agent loop to process the thread until completion or clarification.

        The loop continues until a DoneForNow or ClarificationRequest is received,
        executing tools and updating the thread with events.
        """
        thread.metadata.update(self.metadata)
        thread_id = thread.metadata.get("thread_id", "unknown")
        logger.info(
            "Starting agent loop", thread_id=thread_id, metadata=thread.metadata
        )
        while True:
            next_step = await self.determine_next_step(thread)
            logger.debug(
                "Next step",
                thread_id=thread_id,
                step=next_step.model_dump()
                if hasattr(next_step, "model_dump")
                else str(next_step),
            )
            thread.append_event(
                Event(
                    type="tool_call",
                    data=next_step.model_dump()
                    if hasattr(next_step, "model_dump")
                    else {},
                )
            )

            if isinstance(next_step, DoneForNow):
                # Generate final response when task is done
                final_response = await self._generate_final_response(thread)
                thread.append_event(
                    Event(type="llm_response", data=final_response.model_dump())
                )
                logger.info("Final response generated", response=final_response.message)
                return thread
            elif isinstance(next_step, ClarificationRequest):
                logger.info(
                    "Agent loop exiting: clarification needed",
                    intent=next_step.intent,
                )
                return thread
            elif isinstance(next_step, DynamicToolCall):
                logger.debug("Executing tool call", intent=next_step.intent)
                result = await self.tool_registry.execute_tool(
                    next_step.intent, next_step.arguments
                )
                thread.append_event(Event(type="tool_response", data=result))
                logger.debug("Tool response recorded", result=result)
            else:
                logger.error(
                    "Unknown intent", intent=getattr(next_step, "intent", None)
                )
                raise ValueError(
                    f"Unknown intent: {getattr(next_step, 'intent', None)}"
                )
