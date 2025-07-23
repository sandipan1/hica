from typing import AsyncGenerator, Dict, Generic, List, Optional, Type, TypeVar

import instructor
from pydantic import BaseModel, Field, model_validator

from hica.core import Thread
from hica.logging import logger
from hica.memory import MemoryStore
from hica.models import (
    ClarificationRequest,
    DoneForNow,
    DynamicToolCall,
    FinalResponse,
    serialize_mcp_result,
)
from hica.tools import ToolRegistry, create_model_from_tool_schema

T = TypeVar("T")


class AgentConfig(BaseModel):
    """Configuration for the autonomous agent."""

    model: str = "openai/gpt-4.1-mini"
    system_prompt: str = (
        "You are an autonomous agent. Your primary goal is to fulfill the user's request. "
        "Carefully analyze the user's initial input and the results of any previous tool executions. "
        "Based on this, select the appropriate tool(s) from the available list. "
        "If the user's request has been fully addressed, respond with 'done'. "
        "If you require further input or clarification, respond with 'clarification'."
    )
    max_events_before_summarization: Optional[int] = 20


class Agent(Generic[T]):
    """An autonomous agent that processes user queries using tools and an LLM."""

    def __init__(
        self,
        config: AgentConfig,
        tool_registry: Optional[ToolRegistry] = None,
        metadata: Optional[Dict[str, any]] = None,
        memories: Optional[Dict[str, MemoryStore]] = None,
    ):
        self.config = config
        self.tool_registry = tool_registry or ToolRegistry()
        self.response_model: Type[BaseModel] = DynamicToolCall
        self.metadata = metadata or {}
        self._tool_metadata_cache: Optional[str] = None
        self.memories = memories or {}
        logger.info(
            "Agent initialized", config=config.model_dump(), metadata=self.metadata
        )
        self.client = instructor.from_provider(self.config.model, async_client=True)

    def set_response_model(self, response_model: Type[BaseModel]) -> None:
        """Set the response model for LLM calls."""
        self.response_model = response_model
        logger.debug("Response model set", model=response_model.__name__)

    def _format_tool_metadata(self) -> str:
        """Format tool metadata for inclusion in LLM prompts."""
        if self._tool_metadata_cache is None:
            tools_str = ""
            for intent, tool_def in self.tool_registry.all_tool_defs.items():
                tools_str += f"<tool> {tool_def.name} : {tool_def.description or 'No description'}</tool>\n"
            self._tool_metadata_cache = tools_str.rstrip()
        return self._tool_metadata_cache

    def _build_messages(
        self,
        prompt: str,
        thread: Optional[Thread] = None,
        context: Optional[str] = None,
        **kwargs,
    ) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": self.config.system_prompt}]

        # Add tool metadata
        tool_metadata = self._format_tool_metadata()
        if tool_metadata:
            messages[0]["content"] += f"\nAvailable tools:\n{tool_metadata}"

        # Add context if provided
        if context:
            messages[0]["content"] += f"\n\nContext:\n{context}"

        # Add conversation history if provided
        if thread:
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
                        messages.append(
                            {"role": "assistant", "content": str(event.data)}
                        )
                elif event.type == "tool_response":
                    messages.append(
                        {
                            "role": "user",
                            "content": f"Tool execution result: {event.data}",
                        }
                    )

        # Add the user prompt
        messages.append({"role": "user", "content": prompt})
        return messages

    async def _call_llm(
        self, messages: List[Dict[str, str]], response_model: Type[BaseModel]
    ) -> BaseModel:
        """Execute an LLM call with the given messages and response model."""
        logger.info(
            "LLM call", messages=messages, response_model=response_model.__name__
        )
        try:
            response = await self.client.chat.completions.create(
                response_model=response_model,
                messages=messages,
                temperature=0.0,
            )
            return response
        except Exception as e:
            logger.error("LLM call failed", error=str(e), messages=messages)
            raise ValueError(f"LLM call failed: {str(e)}")

    async def summarize_thread_with_llm(self, thread: Thread[T], keep_last_n: int = 5):
        """
        Summarizes the thread's events using an LLM, replacing older events with a summary.
        """
        
        class ContextSummary(BaseModel):
            summary: str = Field(..., description="A concise summary of the key facts, decisions, and outcomes from the conversation history.")

        summarization_prompt = "Summarize the key facts, decisions, and outcomes from the provided conversation history. Focus on information that will be relevant for future steps."
        
        # We pass the thread to run_llm, but we will handle adding the event manually.
        response = await self.run_llm(
            prompt=summarization_prompt,
            thread=thread,
            response_model=ContextSummary,
            add_event=False 
        )

        # Create a summary event
        summary_event = {
            "type": "context_summary",
            "data": response.summary
        }

        # Keep the last N events and prepend the summary
        recent_events = thread.events[-keep_last_n:]
        thread.events = [summary_event] + recent_events
        logger.info("Thread has been summarized with LLM.", new_event_count=len(thread.events))


    async def select_tool(
        self,
        tools: List[str] = None,
        thread: Optional[Thread[T]] = None,
        context: Optional[str] = None,
        add_event=True,
    ) -> BaseModel:
        """Select the next tool or terminal state using the LLM."""

        # print(tuple(self.tool_registry.all_tool_defs.keys()))
        valid_intents = (
            list(self.tool_registry.all_tool_defs.keys()) if not tools else list(tools)
        )
        valid_intents += ["done", "clarification"]

        # ToolLiteral = Literal[valid_intents] if valid_intents else str

        class ToolSelection(BaseModel):
            intent: str = Field(
                ...,
                description="The tool to use. Must be one of: "
                + ", ".join(valid_intents),
            )
            reason: str

            @model_validator(mode="after")
            def check_intent(self) -> "ToolSelection":
                if self.intent not in valid_intents:
                    raise ValueError(
                        f"Invalid tool selected: {self.intent}. Must be one of: {valid_intents}"
                    )
                return self

        instruction = (
            "IMPORTANT: Only call tools when they are absolutely necessary. If the USER's task is general or you already know the answer, respond without calling tools. NEVER make redundant tool calls as these are very expensive."
            "IMPORTANT: If you state that you will use a tool, immediately call that tool as your next action."
            "Based on the conversation and tool results, select the next tool (intent), "
            "When a tool name is explicitly mentioned in the context, use that tool"
            "or respond with 'done' if the task is complete, or 'clarification' if more information is needed. "
            "Respond ONLY with the intent name, 'done', or 'clarification'."
        )

        # Use run_llm with response model
        response = await self.run_llm(
            instruction,
            thread=thread,
            context=context,
            response_model=ToolSelection,
            add_event=False,
        )
        if add_event and thread:
            thread.add_event(
                type="llm_response",
                step="ToolSeclection",
                data={
                    "intent": response.intent,
                    "reason": response.reason,
                },
            )
        print(type(response), "---------")
        logger.info("Tool selected", intent=response.intent)

        if response.intent == "done":
            return DoneForNow(message="Task completed by agent.")
        if response.intent == "clarification":
            return ClarificationRequest(
                message=f"Clarification needed for : {response.reason}"
            )
        return response

    async def fill_parameters(
        self,
        intent: str,
        thread: Optional[Thread[T]] = None,
        add_event: bool = True,
        context: Optional[str] = None,
    ) -> Dict[str, any]:
        """
        Fill parameters for a tool using LLM generation.
        Similar to run_llm abstraction - simple input/output with optional logging.
        """
        tool_def = self.tool_registry.all_tool_defs.get(intent)
        if not tool_def:
            logger.error("Tool not found", intent=intent)
            raise ValueError(f"Tool {intent} not found")

        ToolParamsModel = create_model_from_tool_schema(tool_def)
        instruction = (
            f"You have selected the tool: {tool_def.name}.\n"
            f"Description: {tool_def.description}\n"
            f"Parameters schema:\n{tool_def.parameters_json_schema}\n"
            "Considering the full conversation history and the most recent tool execution result, "
            "provide ONLY the required parameters as per the schema above."
        )

        # Use run_llm with response model
        param_response = await self.run_llm(
            instruction,
            thread=thread,
            context=context,
            response_model=ToolParamsModel,
            add_event=False,
        )

        arguments = {
            param_name: getattr(param_response, param_name)
            for param_name in tool_def.parameters_json_schema.get(
                "properties", {}
            ).keys()
            if hasattr(param_response, param_name)
        }

        if add_event and thread is not None:
            thread.add_event(
                type="llm_response",
                data={"intent": intent, "arguments": arguments},
                step="llm_parameters",
            )

        logger.info("Tool parameters filled", intent=intent)
        return arguments

    async def _generate_final_response(self, thread: Thread[T]) -> FinalResponse:
        """Generate a final response summarizing the results for the user."""
        instruction = (
            "Based on the conversation history and tool execution results, "
            "provide a clear and concise response to the user's original request. "
            "Summarize the key findings or results in a user-friendly way."
        )
        response = await self.run_llm(
            instruction,
            thread=thread,
            response_model=FinalResponse,
            add_event=False,  # Don't add 'llm_response' event
        )
        # Collect all tool results
        tool_results = {}
        for event in thread.events:
            if event.type == "tool_response" or event.type == "user_input":
                tool_results[event.type] = event.data

        final_response = FinalResponse(
            message=response.message, summary=response.summary, raw_results=tool_results
        )

        # Add a 'final_response' event to the thread
        thread.add_event(
            type="llm_response",
            data=final_response.model_dump(exclude_none=True),
            step="final_reponse",
        )

        return final_response

    async def agent_loop(
        self, thread: Thread[T], context: Optional[str] = None
    ) -> AsyncGenerator[Thread, None]:
        """
        Run the agent loop to process the thread until completion or clarification.

        The loop continues until a DoneForNow or ClarificationRequest is received,
        executing tools and updating the thread with events. This is an async generator
        that yields the thread state after each significant step.
        """
        logger.info(
            "Starting agent loop",
            thread_id=thread.thread_id,
        )
        
        if self.config.max_events_before_summarization and len(thread.events) > self.config.max_events_before_summarization:
            await self.summarize_thread_with_llm(thread)

        yield thread  # Yield initial state

        while True:
            # Step 1: Select tool or terminal state
            selection = await self.select_tool(
                tools=None, thread=thread, context=context
            )
            print(selection)
            logger.info("Selected tool : ", selection)
            yield thread  # Yield after tool selection

            # Step 2: Handle terminal states
            if isinstance(selection, DoneForNow):
                final_response = await self._generate_final_response(thread)
                logger.info("Final response generated", response=final_response.message)
                yield thread
                return  # End of loop

            if isinstance(selection, ClarificationRequest):
                logger.info("Agent loop exiting: clarification needed")
                yield thread
                return  # End of loop

            # Step 3: Fill parameters for the selected tool
            arguments = await self.fill_parameters(selection.intent, thread)
            yield thread  # Yield after params are filled and tool_call is formulated

            # Step 4: Execute the tool
            logger.debug("Executing tool call", intent=selection.intent)
            result = await self.execute_tool(
                selection.intent, arguments, thread=thread, add_event=True
            )
            yield thread  # Yield after tool execution

    async def run_llm(
        self,
        prompt: str,
        thread: Optional[Thread] = None,
        context: Optional[str] = None,
        max_thread_events: Optional[int] = None,
        response_model: Optional[Type[BaseModel]] = None,
        add_event: bool = True,
        step=None,
        **kwargs,
    ) -> BaseModel:
        # Apply pruning if specified
        if max_thread_events and thread:
            thread.events = thread.events[-max_thread_events:]

        messages = self._build_messages(prompt, thread, context, **kwargs)
        logger.info(
            "LLM call",
            messages=messages,
            response_model=response_model.__name__ if response_model else "text",
        )
        try:
            # Use provided response_model or default
            class Response(BaseModel):
                response: str

            model_to_use = response_model or Response
            response = await self._call_llm(messages, model_to_use)

            if thread is not None and add_event:
                if step != None:
                    thread.add_event(
                        type="llm_response",
                        data=response.model_dump(exclude_none=True),
                        step=step,
                    )
                else:
                    thread.add_event(
                        type="llm_response", data=response.model_dump(exclude_none=True)
                    )

            # Return the response
            return response
        except Exception as e:
            logger.error("LLM call failed", error=str(e), messages=messages)
            raise ValueError(f"LLM call failed: {str(e)}")

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, any],
        thread: Optional[Thread[T]] = None,
        add_event: bool = True,
    ) -> any:
        """
        Execute a single tool with optional thread logging.
        Simple input/output abstraction similar to run_llm.
        """
        try:
            # Log tool call event if requested
            if add_event and thread is not None:
                thread.add_event(
                    type="tool_call", data={"intent": tool_name, "arguments": arguments}
                )

            # Execute tool using existing registry
            result = await self.tool_registry.execute_tool(tool_name, arguments)
            result = serialize_mcp_result(result)

            # Log tool response event if requested
            if add_event and thread is not None:
                thread.add_event(
                    type="tool_response",
                    data={"response": result, "source": "ToolRegistry"},
                )

            logger.info("Tool execution completed", tool=tool_name)
            return result

        except Exception as e:
            logger.error("Tool execution failed", tool=tool_name, error=str(e))
            raise