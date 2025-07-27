# Gemini CLI vs. HICA: A Detailed Comparison

This document provides a detailed comparison between the Gemini CLI Core and the HICA (Highly Customizable Agent) library, followed by suggestions for improving HICA based on the strengths of Gemini CLI.

### High-Level Summary

*   **Gemini CLI** is a specific, feature-rich **command-line application** designed for developers to interact with Gemini models. Its core provides the backend logic for that specific application, with features like hierarchical context files (`GEMINI.md`), chat history compression, and model fallback.
*   **HICA** is a more general-purpose **Python library/framework** for *building* AI agents. It is un-opinionated about the final application (it could be a CLI, a web app, or a backend service). Its core philosophy is built on observability, control, and composability, using an event-sourced architecture (`Thread`/`Event`) as its foundation.

The fundamental difference is **Application vs. Framework**. Gemini CLI is a product; HICA is a toolkit to build products.

---

### Key Differences Analyzed

| Feature | Gemini CLI Core | HICA (Highly Customizable Agent Library) | Analysis |
| :--- | :--- | :--- | :--- |
| **Core Philosophy** | A backend for a specific CLI tool. Provides features tailored to a command-line developer experience. | A general-purpose framework for building auditable, stateful, and controllable AI agents for any application. | Gemini is specialized. HICA is generalized. HICA's principles (control, observability) are its main selling point. |
| **Architecture** | `packages/core` acts as a backend service for `packages/cli`. Manages API calls, tool execution, and state for the CLI. | Event-sourced architecture. The `Thread` object contains a full history of `Event`s (user input, LLM calls, tool calls, etc.). This is the central design pattern. | HICA's architecture is more transparent and fundamentally designed for auditability and resumability. Every step is explicitly logged as a structured event. |
| **Context Management** | **Static & Hierarchical:** Uses `GEMINI.md` files found by searching up the directory tree. Content is modularized with an `@file.md` import syntax (`MemPort`). | **Dynamic & Stateful:** Context is primarily the conversation history within the `Thread`. It also supports injecting temporary, ad-hoc `context` strings into LLM calls without persisting them. | Gemini's approach is excellent for providing persistent, static instructions and documentation to the agent. HICA's approach excels at providing dynamic, conversational context. HICA lacks a built-in system for managing static, file-based context. |
| **Tooling** | Defines a `tools-api` for registering and using tools. The docs imply a set of built-in tools for the CLI. | **Unified Tool Registry:** A core feature. Seamlessly integrates local Python functions (sync/async) and remote tools via an `MCPConnectionManager`. Tool definitions are extracted automatically. | HICA has a more powerful, flexible, and extensible tooling system. The unification of local and remote (MCP) tools in a single registry is a significant advantage for building complex agents. |
| **State & Memory** | Manages conversation history with automatic compression and model fallback. The persistence mechanism is not detailed in the docs. | **Pluggable Memory Abstraction:** Provides a `MemoryStore` interface with `File`, `SQL`, and `Mongo` backends. `ConversationMemoryStore` is specialized for persisting `Thread` objects. | HICA's memory system is more explicit, production-ready, and customizable. The ability to choose a backend (file for development, DB for production) is a major strength. |
| **Workflow & Control** | Appears to be a standard request-response loop driven by the CLI user. | **Dual-Mode Operation:** Supports both a fully autonomous `agent_loop` and "programmable workflows" where developers can call `run_llm`, `select_tool`, `fill_parameters`, and `execute_tool` as individual building blocks. | HICA offers far greater control. The developer can choose full autonomy or build custom logic by orchestrating the agent's core functions. The first-class `clarification` event is a prime example of this control. |

---

### Suggestions for HICA's Improvement

HICA has a robust and flexible foundation. It could be enhanced by adopting some of the user-friendly, application-level features from Gemini CLI.

#### 1. Implement Hierarchical Static Context Management (Inspired by `GEMINI.md`)

HICA's `system_prompt` is currently a single string in `AgentConfig`. This is limiting for complex instructions.

**Suggestion:**
Create a "Context Loader" that searches for special files (e.g., `.hica.md` or `hica_prompt.md`) in the current directory and parent directories, up to the project root.

*   **Hierarchical Loading:** Concatenate the content from all found files to build the system prompt.
*   **`@file` Imports:** Implement a pre-processor, similar to Gemini's `MemPort`, that resolves `@./path/to/file.md` imports within these context files. This would allow users to modularize their prompts.
*   **Integration:** The `Agent` could be initialized with this context loader, which would dynamically build the system prompt.

This would give users a powerful way to manage agent instructions and context outside of their Python code, a significant advantage of the Gemini CLI.

#### 2. Enhance Chat History Management (Inspired by Gemini's Compression)

HICA has an LLM-based summarization feature (`summarize_thread_with_llm`), but it's triggered by event count. Gemini's approach is more dynamic.

**Suggestion:**
Make the history management more robust and configurable.

*   **Token-Based Trigger:** Instead of `max_events_before_summarization`, add a `max_context_tokens` threshold. Before calling the LLM, the agent would estimate the token count and trigger summarization if it exceeds the threshold.
*   **Configurable Strategies:** Allow users to choose a history management strategy in `AgentConfig`:
    *   `"truncate"`: The current simple approach.
    *   `"summarize"`: The current LLM-based approach.
    *   `"windowed"`: A simple sliding window of the last N events.

#### 3. Add a Model Fallback Mechanism

HICA's `AgentConfig` takes a single model. If an API call fails due to rate limiting or server errors, the entire workflow stops.

**Suggestion:**
Allow `AgentConfig` to accept a primary model and a list of fallback models.

```python
# In AgentConfig
class AgentConfig(BaseModel):
    model: str = "openai/gpt-4.1-mini"
    fallback_models: Optional[List[str]] = ["openai/gpt-4-flash"]
    # ...
```

The `_call_llm` method in `agent.py` could be updated with a retry loop. If the primary model fails with a specific, retriable error (e.g., 429 Too Many Requests, 5xx Server Error), it would automatically try the next model in the `fallback_models` list.

#### 4. Improve the Example CLI with a REPL

The current `run_cli` function in `src/hica/cli.py` is a one-shot execution. A more interactive CLI would better showcase HICA's stateful nature.

**Suggestion:**
Create an example of an interactive REPL (Read-Eval-Print Loop).

*   The CLI would start and load an `Agent`.
*   It would create a `Thread` and keep it in memory.
*   The user could have a multi-turn conversation, with each input being added as a `user_input` event to the *same thread*.
*   The `ConversationMemoryStore` would save the thread after each turn, demonstrating persistence.

This would provide a much better "out-of-the-box" experience and demonstrate how to build interactive chat applications with HICA.
