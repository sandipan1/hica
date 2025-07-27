from typing import Any, Dict

from pydantic import BaseModel

from hica import Agent, AgentConfig, Thread
from hica.memory import ConversationMemoryStore
from hica.models import ToolResult
from hica.tools import BaseTool


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
        super().__init__(config=config, **kwargs)


class CodeInterpreterTool(BaseTool):
    """A tool that delegates a task to a sub-agent and executes the code it generates."""

    name = "run_code_interpreter"
    description = (
        "Delegates a task to a CodeGenerationAgent and executes the returned code."
    )

    def __init__(self, memory: ConversationMemoryStore):
        self.memory = memory

    async def execute(self, task_description: str) -> ToolResult:
        """
        Delegates a task to a CodeGenerationAgent and executes the returned code.
        """
        sub_agent = CodeGenerationAgent()
        sub_agent_thread = Thread(metadata={"parent_task": task_description})
        self.memory.set(sub_agent_thread)

        prompt = f"Your task is to write a Python script that does the following: {task_description}"
        sub_agent_thread.add_event(type="user_input", data=prompt)
        self.memory.set(sub_agent_thread)

        # Direct LLM call, bypassing the agent loop
        class CodeResponse(BaseModel):
            code: str

        messages = [
            {"role": "system", "content": sub_agent.config.system_prompt},
            {"role": "user", "content": prompt},
        ]

        response = await sub_agent.client.chat.completions.create(
            messages=messages,
            response_model=CodeResponse,
            temperature=0.0,
        )
        generated_code = response.code

        sub_agent_thread.add_event(
            type="llm_response", data={"generated_code": generated_code}
        )
        self.memory.set(sub_agent_thread)

        if not generated_code:
            execution_result = {
                "status": "error",
                "error": "Sub-agent did not generate any code.",
            }
        else:
            execution_result = execute_python(generated_code)

        sub_agent_thread.add_event(type="tool_response", data=execution_result)
        self.memory.set(sub_agent_thread)

        llm_summary = f"Code execution finished with status: {execution_result.get('status')}. Output: {execution_result.get('stdout', 'N/A')}"
        display_output = f"""### Code Interpreter Result
**Status:** {execution_result.get('status')}
**Output:**
```
{execution_result.get('stdout', execution_result.get('error', 'No output'))}
```
"""

        return ToolResult(
            llm_content=llm_summary,
            display_content=display_output,
            raw_result=execution_result,
        )

