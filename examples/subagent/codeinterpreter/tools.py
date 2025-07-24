import asyncio
from typing import Dict, Any

from hica import Agent, AgentConfig, Thread, ToolRegistry
from hica.memory import ConversationMemoryStore


def execute_python(code: str) -> Dict[str, Any]:
    """
    Executes a string of Python code in an isolated scope and returns the output.
    """
    try:
        from io import StringIO
        import sys

        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        exec(code, {})

        sys.stdout = old_stdout
        output = captured_output.getvalue()
        return {"status": "success", "stdout": output}
    except Exception as e:
        return {"status": "error", "error": str(e)}


class CodeGenerationAgent(Agent):
    """A specialized agent for generating Python code."""

    def __init__(self, **kwargs):
        config = AgentConfig(
            model="openai/gpt-4.1-mini",
            system_prompt=(
                "You are a Python code generation expert. Your only task is to write a Python script "
                "that performs the requested task. Output *only* the raw Python code. "
                "Do not add explanations, markdown, or any other text."
            ),
        )
        tool_registry = ToolRegistry()
        super().__init__(config=config, tool_registry=tool_registry, **kwargs)


class CodeInterpreterTool:
    """A tool that delegates a task to a sub-agent and executes the code it generates."""

    def __init__(self, main_agent_thread: Thread, memory: ConversationMemoryStore):
        self.main_agent_thread = main_agent_thread
        self.memory = memory

    async def run_code_interpreter(self, task_description: str) -> Dict[str, Any]:
        """
        Delegates a task to a CodeGenerationAgent and executes the returned code.
        """
        sub_agent = CodeGenerationAgent()
        sub_agent_thread = Thread()
        self.memory.set(sub_agent_thread)

        self.main_agent_thread.add_event(
            type="tool_call",
            data={
                "intent": "run_code_interpreter",
                "arguments": {"task_description": task_description},
                "sub_agent_thread_id": sub_agent_thread.thread_id,
            },
        )
        self.memory.set(self.main_agent_thread)

        prompt = f"Your task is to write a Python script that does the following: {task_description}"
        sub_agent_thread.add_event(type="user_input", data=prompt)
        self.memory.set(sub_agent_thread)

        # Direct LLM call, bypassing the agent loop
        from pydantic import BaseModel

        class CodeResponse(BaseModel):
            code: str

        messages = [{"role": "system", "content": sub_agent.config.system_prompt}, {"role": "user", "content": prompt}]
        
        response = await sub_agent.client.chat.completions.create(
            messages=messages,
            response_model=CodeResponse,
            temperature=0.0,
        )
        generated_code = response.code
        
        sub_agent_thread.add_event(type="llm_response", data={"generated_code": generated_code})
        self.memory.set(sub_agent_thread)

        if not generated_code:
            return {"status": "error", "error": "Sub-agent did not generate any code."}

        execution_result = execute_python(generated_code)

        return {
            "response": execution_result,
            "sub_agent_thread_id": sub_agent_thread.thread_id,
        }


def get_codeinterpreter_tool(
    thread: Thread, memory: ConversationMemoryStore
) -> CodeInterpreterTool:
    """Factory function to create a CodeInterpreterTool instance."""
    return CodeInterpreterTool(thread, memory)
