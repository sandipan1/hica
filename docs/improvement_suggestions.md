# HICA Improvement Suggestions: Tooling Architecture

After a critical analysis of the Gemini CLI Tools API documentation and comparison with HICA's current tooling implementation, this document outlines suggestions for improving HICA's tooling architecture.

HICA's approach is elegant and Pythonic, but it prioritizes developer simplicity, whereas the Gemini CLI's tooling is more mature and architected for robust, user-facing applications. HICA could be significantly improved by adopting some of Gemini CLI's more sophisticated concepts.

---

### Critical Analysis: HICA vs. Gemini CLI Tooling

The core philosophical difference is this:
*   **HICA's tooling** is designed as a lightweight, programmatic wrapper around Python functions. It's developer-centric.
*   **Gemini CLI's tooling** is designed as a complete system for safe, interactive, and extensible tool use in a user-facing application. It's application-centric.

Here is a breakdown of the key differences and missing features in HICA:

#### 1. Tool Definition: Simplicity vs. Richness
*   **HICA:** A tool is just a Python function. Its name, description (docstring), and parameters (type hints) are automatically inferred. This is simple and elegant for the developer.
*   **Gemini CLI:** A tool is a structured class (`BaseTool`) with a rich contract: `name`, `displayName`, `description`, `parameterSchema`, and methods for validation, confirmation, and execution.
*   **Critique:** HICA's simplicity is also a limitation. It lacks the metadata needed for a polished user experience, such as a user-friendly `displayName` or the ability to generate a pre-execution summary.

#### 2. Tool Output: A Single Value vs. Separated Concerns
*   **HICA:** A tool returns a single Python object. The `agent` then takes this raw output and includes it in a `tool_response` event. This same data is used for both the LLM's context and for any potential display to the user.
*   **Gemini CLI:** A tool returns a `ToolResult` object, which makes a critical distinction between `llmContent` (a factual, concise string for the model) and `returnDisplay` (a rich, user-friendly string or object for the CLI).
*   **Critique:** This is the most significant architectural advantage of the Gemini CLI's approach. **HICA is missing this separation of concerns.** Forcing one return value to serve two masters (the LLM and the user) is problematic. A verbose, user-friendly output can pollute the LLM's context window with unnecessary tokens, while a terse, LLM-friendly output provides a poor user experience.

#### 3. Execution Flow: Agent-Driven vs. Tool-Driven Safety
*   **HICA:** The `Agent` controls the entire flow (`select_tool` -> `fill_parameters` -> `execute_tool`). Any safety checks (like asking for confirmation) must be implemented *outside* the tool, within the application's orchestration logic.
*   **Gemini CLI:** The tool itself has a say in its execution. The `shouldConfirmExecute()` method allows a tool to flag itself as potentially dangerous, forcing a confirmation step. This is a powerful, decentralized safety mechanism.
*   **Critique:** HICA lacks built-in, tool-level safety hooks. A developer could easily register a tool like `delete_file` without realizing they also need to build a separate confirmation workflow in their application code. Gemini's approach is safer by design.

#### 4. Dynamic Discovery: Limited vs. Highly Extensible
*   **HICA:** Can discover tools from an MCP server at runtime. However, it has no built-in mechanism for discovering local tools from a configuration file or a command. New local tools must be added programmatically via the `@tool` decorator or `add_tool` method.
*   **Gemini CLI:** Features `toolDiscoveryCommand` and `mcpServerCommand`. This allows a project to expose custom tools to the Gemini CLI without modifying the CLI's source code. It's a highly extensible, plug-in-like architecture.
*   **Critique:** HICA is less flexible for integration into larger systems where tools might be defined in a non-Python context. The Gemini CLI's discovery mechanism allows it to be a more general-purpose assistant for any project that can describe its tools in JSON.

---

### Simplification & Improvement Suggestions for HICA

HICA can adopt the best parts of the Gemini Tools API without losing its Pythonic feel.

#### Suggestion 1: Introduce a Richer `ToolResult` Object

This is the most important change. Instead of returning a raw value, tools should return a structured object.

**Proposed Implementation:**
Create a `ToolResult` model in `hica/models.py` and encourage its use.

```python
# in hica/models.py
from pydantic import BaseModel, Field
from typing import Any, Union

class ToolResult(BaseModel):
    """The structured result of a tool execution."""
    llm_content: str = Field(..., description="The concise, factual content to be sent to the LLM.")
    display_content: Any = Field(..., description="The rich content to be displayed to the user.")
    raw_result: Any = Field(None, description="The original raw result from the tool function.")

# The agent's execute_tool would then be updated to handle this
# and store the components in the 'tool_response' event.
```

This would allow HICA to manage context for the LLM and the user separately and effectively.

#### Suggestion 2: Introduce an Optional `BaseTool` Class with Safety Hooks

To add Gemini-like safety and UX features without breaking the simple decorator for basic tools, HICA can introduce an optional base class for more advanced tools.

**Proposed Implementation:**
Create a `BaseTool` class that advanced tools can inherit from.

```python
# in hica/tools.py

class BaseTool:
    """Optional base class for tools that need advanced features like pre-execution confirmation."""
    
    # These would be implemented by the developer for their specific tool
    def get_description(self, params: dict) -> str:
        """Return a human-readable description of what this tool will do with these params."""
        return f"Executing {self.__class__.__name__} with the provided parameters."

    def should_confirm(self, params: dict) -> bool:
        """Return True if this tool execution requires user confirmation."""
        return False

    def execute(self, **kwargs) -> ToolResult:
        """The core execution logic of the tool."""
        raise NotImplementedError
```

The `ToolRegistry` and `Agent` would be updated to check if a registered tool is an instance of `BaseTool` and, if so, call these hooks during the execution flow.

#### Suggestion 3: Simplify and Unify Tool Definition

The current system of inferring everything from a function can be brittle. Combining the decorator with the optional `BaseTool` provides a clearer, more robust path.

**Before (Current HICA):**
```python
@registry.tool()
def delete_file(path: str):
    """Deletes a file. DANGEROUS!"""
    # ... logic ...
    return f"Deleted {path}"
```

**After (Proposed HICA):**
```python
from hica.tools import BaseTool, ToolResult

# The decorator now just handles registration
@registry.tool()
class DeleteFileTool(BaseTool):
    
    def should_confirm(self, params: dict) -> bool:
        return True # Always ask for confirmation

    def get_description(self, params: dict) -> str:
        return f"You are about to permanently delete the file at: {params.get('path')}"

    def execute(self, path: str) -> ToolResult:
        # ... logic to delete file ...
        return ToolResult(
            llm_content=f"Action: The file at '{path}' was successfully deleted.",
            display_content=f"✅ File deleted: `{path}`"
        )
```
This approach is more explicit, safer, and produces better output, while simple, read-only functions can still use the decorator on its own.

---
### Case Study: Simplifying Subagent Tools

The subagent examples highlight the exact point where HICA's current simple, function-based tooling shows its limitations and where the proposed Gemini-inspired architecture would provide significant benefits.

#### Analysis: Simple Tools vs. Complex Subagent Tools

1.  **The Simple Case (`calculator_tools.py`):**
    *   The calculator tools are perfect examples of HICA's current strength. They are stateless, pure functions. The `@registry.tool()` decorator is incredibly elegant here, inferring everything with zero boilerplate.

2.  **The Complex Case (`subagent/.../tools.py`):**
    *   The subagent tools are the complete opposite. They are complex, stateful orchestrators that require dependencies like `main_agent_thread` and `memory`.
    *   To manage this, the current implementation uses a class (`CodeInterpreterTool`) and registers an *instance method* as the tool. This feels like a workaround.
    *   **Crucially, the tool's internal logic is messy.** It manually adds events back to the parent thread (`self.main_agent_thread.add_event(...)`). A tool should be self-contained and should not have to know about the internal state of the agent that is calling it.

The subagent pattern exposes the architectural limitations of HICA's current tooling. It works, but it's not clean.

#### How the Proposed Architecture Simplifies Subagents

The proposed changes (introducing an optional `BaseTool` class and a `ToolResult` return object) are designed precisely to clean up complex cases like this, without adding complexity to the simple cases.

**What would change for `calculator_tools.py`?**

**Absolutely nothing.** The new architecture would be opt-in for advanced use cases, ensuring backward compatibility and keeping simple tools simple.

**Refactoring the Subagent with `BaseTool`:**

The new approach provides a formal structure for class-based tools, improving encapsulation and clarity.

**Current Approach (Simplified):**
```python
# tools.py
class CodeInterpreterTool:
    def __init__(self, main_agent_thread, memory):
        self.main_agent_thread = main_agent_thread # <--- Problem: Tight coupling
        self.memory = memory

    async def run_code_interpreter(self, task_description: str):
        # ... logic to create subagent, subthread ...
        # Manually add event to parent thread to link them
        self.main_agent_thread.add_event(...) # <--- Problem: Tool modifies caller's state
        # ... run subagent, get result ...
        return {"response": execution_result, ...} # <--- Problem: Ambiguous dictionary return

# main.py
subagent_tool = get_codeinterpreter_tool(main_thread, memory)
main_tool_registry.add_tool(subagent_tool.run_code_interpreter)
```

**Proposed `BaseTool` Approach:**
```python
# in examples/subagent/codeinterpreter/tools.py
from hica.tools import BaseTool
from hica.models import ToolResult

# The decorator now registers a class that inherits from BaseTool
@registry.tool()
class CodeInterpreterTool(BaseTool):
    name = "run_code_interpreter"
    description = "Delegates a task to a CodeGenerationAgent and executes the code."
    
    def __init__(self, memory: ConversationMemoryStore):
        self.memory = memory

    async def execute(self, task_description: str) -> ToolResult:
        # 1. Create and manage the sub-agent and its thread internally.
        sub_agent = CodeGenerationAgent()
        sub_agent_thread = Thread(metadata={"parent_task": task_description})
        self.memory.set(sub_agent_thread)

        # 2. Run the sub-agent logic and get the result.
        execution_result = # ... (logic to call LLM, get code, execute it) ...
        
        # 3. Return a structured, unambiguous ToolResult.
        llm_summary = f"Code execution finished with status: {execution_result.get('status')}"
        display_output = f"### Code Interpreter Result\n**Status:** {execution_result.get('status')}\n**Output:**\n```\n{execution_result.get('stdout')}\n```"

        return ToolResult(
            llm_content=llm_summary,
            display_content=display_output,
            raw_result=execution_result
        )

# in main.py
# The tool is now instantiated and registered cleanly.
code_tool = CodeInterpreterTool(memory=memory)
main_tool_registry.add_tool(code_tool)
```

#### Summary of Benefits:

1.  **Better Encapsulation:** The entire subagent workflow is now fully contained within the `CodeInterpreterTool` class.
2.  **Decoupling:** The tool no longer needs a reference to the `main_agent_thread`. It is a self-contained unit that receives a task and returns a result.
3.  **Clearer Interfaces:** By returning a `ToolResult`, the tool provides unambiguous, structured output, separating the concise summary for the LLM from the rich output for the user.
4.  **Architectural Consistency:** Complex, class-based tools now have a formal, consistent structure (`BaseTool`), making the framework more robust and easier to reason about.
