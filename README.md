<div align="center">

# HICA: Highly Customizable Agent Library


<strong>Build AI agents you can trust, trace, and control—every step, every decision. </strong>

[![PyPI](https://img.shields.io/pypi/v/hica)](https://pypi.org/project/hica/)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

</div>

---

## 🚀 What is HICA?

**HICA** is a design principle put together in a framework for building customisable, deterministic AI agents. Unlike most frameworks, HICA gives you full control and visibility over every step of your agent's reasoning, tool use, and state. It's designed for developers who want to:

- **Debug and audit** every decision an agent makes
- **MCP as first class citizen** - Use any tool that you like - MCP tools or local
- **Human-in-loop clarifications** - native to the workflow for trustablity of your workflows
- **Customize prompts, context, and workflows** for maximum control
- **Persist and resume conversations** with full event history
- **Build for reliability, not just demos**


![Agent Loop](./excalidraw-animate.svg)


---

## 🧠 How HICA Works

HICA agents operate in a **Thought → Action → Observation** loop:

1. **Thought:** The LLM decides what to do next (call a tool, ask for clarification, or finish).
2. **Action:** The agent executes a tool (local or remote) or asks the user for input.
3. **Observation:** The agent records the result and reasons about the next step.

All steps are recorded as `Event` objects in a `Thread`, which can be saved, resumed, and audited.

---
![agent workflow](./agent-workflow.png) 


## 🌟 Core Principles

- **Total Control:** Own every prompt, tool call, and context window.
- **Structured Tool Output:** Tools return both human-readable content for display and clean, structured JSON for the LLM, ensuring reliable and efficient context.
- **Action History & Transparent State:** Every action (user input, LLM call, tool call, tool response, clarification request) is recorded as an `Event` in a persistent `Thread`, providing a complete, auditable history for traceability and LLM planning.
- **Observability:** Structured logging and stateful conversations for full transparency.
- **Composable Tools:** Register both local Python functions and remote MCP tools in a unified registry.
- **Human-in-the-Loop:** Agents can request clarifications or approvals at any step.
- **Stateful by Design:** State is externalized—persisted outside the agent process (e.g., in a database or file system)—for scalability and reliability.
- **Real-Time Event Streaming:** Each event is yielded instantly for immediate logging, UI updates, or client streaming—enabling real-time observability.

---

## 📦 Installation

```bash
pip install hica
# or for all optional dependencies (examples, tests)
pip install 'hica[all]'
```

Requires Python 3.12+.

---

## 🏁 Quick Start

### 1. Register a Tool

```python
from hica.tools import ToolRegistry

registry = ToolRegistry()

@registry.tool()
def add(a: int, b: int) -> int:
    "Add two numbers"
    return a + b
```

### 2. Run an Agent (Autonomous agent_loop)

```python
import asyncio
from hica.agent import Agent, AgentConfig
from hica.core import Thread, Event
from hica.memory import ConversationMemoryStore

async def main():
    agent = Agent(
        config=AgentConfig(model="openai/gpt-4.1-mini"),
        tool_registry=registry,
        metadata={"userid": "1234", "role": "developer"}
    )
    thread = Thread(events=[Event(type="user_input", data="What is 3 + 4?")])
    store = ConversationMemoryStore(backend_type="file", context_dir="context")
    # Run the agent loop to completion (autonomous mode)
    async for _ in agent.agent_loop(thread):
        pass
    store.set(thread)
    print("Events:", [e.model_dump() for e in thread.events])

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Inspect State

All conversation state is saved as JSON in the `context/` directory (or in your chosen backend). You can resume or audit any thread at any time.

---

## 🛠️ Stepwise Parameter Handling and Event Logging

HICA supports both autonomous and stepwise workflows. For stepwise workflows, you can use `fill_parameters` to have the LLM generate tool parameters, which logs an event of type `'llm_parameters'`:

```python
params = await agent.fill_parameters("add", thread=thread)
result = await agent.execute_tool("add", params, thread=thread)
```

If you already have parameters (e.g., from LLM output), call `execute_tool` directly:

```python
for query in response.queries:
    result = await agent.execute_tool("search_paper", {"query": query}, thread=thread)
```

---

## 🗄️ MongoDB Conversation Store

HICA supports storing conversation threads in MongoDB for scalable, production-ready persistence.

```python
from hica.memory import ConversationMemoryStore

store = ConversationMemoryStore(
    backend_type="mongo",
    mongo_uri="mongodb://localhost:27017",
    mongo_db="hica_test",
    mongo_collection="threads"
)

# Create and store a thread
thread = Thread()
thread.add_event(type="user_input", data="Hello, MongoDB!")
store.set(thread)

# Retrieve the thread
retrieved = store.get(thread.thread_id)
print(retrieved)
```

---

## 🔌 Integrate Remote (MCP) Tools

HICA supports [Model Context Protocol (MCP)](https://github.com/jlowin/fastmcp) for remote tool execution.

```python
from hica.tools import ToolRegistry, MCPConnectionManager

registry = ToolRegistry()
## Add locals tools 
@registry.tool()
def add(a: int, b: int) -> int:
    "Add two numbers"
    return a + b


mcp_manager = MCPConnectionManager("http://localhost:8000/mcp")  # or MCP server config

async def setup():
    await mcp_manager.connect()
    await registry.load_mcp_tools(mcp_manager)
    # Now both local and remote tools are available to the agent!
    # ..run agent_loop and save thread
    await mcp_manager.disconnect()

asyncio.run(setup())
```

See [`examples/main_mcp_tool.py`](examples/main_mcp_tool.py) for a full example.

---

## 🛠️ Examples

- [examples/basic/basic_agent.py](examples/basic/basic_agent.py): Basic calculator agent
- [examples/mcp/mcp_agent.py](examples/mcp/mcp_agent.py): Using MCP tools
- [examples/basic/file_tools.py](examples/basic/file_tools.py): File manipulation tools
- [examples/web_app/streamlit_app.py](examples/web_app/streamlit_app.py): Interactive web UI
- [examples/web_app/polling_streamlit_app.py](examples/web_app/polling_streamlit_app.py): Streamlit UI with manual polling
- [examples/async/async_agent_loop.py](examples/async/async_agent_loop.py): Async agent loop with real-time event streaming
- [examples/human_in_loop/human_in_loop_example.py](examples/human_in_loop/human_in_loop_example.py): Human-in-the-loop agent example

---
## 🤖 Flexible, Programmable Workflows

HICA supports both fully autonomous agent loops and **stepwise, programmable workflows**. This means you can:
- Call the LLM for structured output using `run_llm` (e.g., generate a list of queries or tasks).
- Use `fill_parameters` to have the LLM generate tool parameters (with event logging as `llm_parameters`).
- Call any tool directly with `execute_tool`.
- Chain these steps in your own code, with custom logic, error handling, and aggregation.

This gives you **fine-grained control** over the agent's reasoning and tool use, enabling workflows such as:
- Generating a list of search queries, then calling a tool for each query.
- Aggregating and processing results as you wish.
- Passing large context (documents, histories) to the LLM and using the output to drive further tool calls.

**Example: Flexible Orchestration with Tools**

```python
# LLM generates a list of queries
class QueryList(BaseModel):
    queries: List[str]

response = await agent.run_llm(
    "Generate 3 search queries for ...", thread=thread, response_model=QueryList
)
for query in response.queries:
    result = await agent.execute_tool("search_paper", {"query": query}, thread=thread)
    # process result as needed
```

**Example: Large Context LLM Handling**

```python
# Pass a large document/context to the LLM, then use the output
response = await agent.run_llm(
    prompt="Summarize the main findings", thread=thread, context=large_context
)
print("LLM response (large context only):", response)
```
## the large context is not added to the thread

See [examples/basic/workflow.py](examples/basic/workflow.py) and [examples/basic/large_context_only.py](examples/basic/large_context_only.py) for full examples.

---
## 🧠 Unified Memory Management

HICA provides a **unified memory abstraction** for all your agent’s needs—not just conversation state, but also prompts, configs, citations, and arbitrary key-value data.

You can use:
- **ConversationMemoryStore** for conversation threads (with file, SQL, or MongoDB backends)
- **PromptStore** for prompt templates (with any backend)
- **InMemoryMemoryStore** for fast, ephemeral data
- **FileMemoryStore** for persistent key-value data in a JSON file
- **SQLMemoryStore** for structured, queryable storage
- **MongoMemoryStore** for scalable, NoSQL storage

All memory types share a minimal, composable interface (`get`, `set`, `delete`, `all`).

**Example: Using Different Memory Types**

```python
from hica.memory import (
    ConversationMemoryStore, PromptStore, InMemoryMemoryStore, FileMemoryStore, SQLMemoryStore, MongoMemoryStore
)

# Conversation history (file, SQL, or MongoDB)
conversation_store = ConversationMemoryStore(backend_type="file", context_dir="context")
# Prompt templates (file-based by default)
prompt_store = PromptStore()
# Fast ephemeral memory
fast_mem = InMemoryMemoryStore()
# Persistent key-value memory
file_mem = FileMemoryStore("mydata.json")
# SQL-based memory
sql_mem = SQLMemoryStore(db_path="memory.db")
# MongoDB-based memory
mongo_mem = MongoMemoryStore(uri="mongodb://localhost:27017", db_name="hica", collection="kv")
```

You can mix and match these memory types for different parts of your agent’s workflow.

---

## 🧩 Observable and Stateful by Design

HICA provides robust state management through its `Thread` and `ConversationMemoryStore` system:

### Thread: The Core State Container

Each conversation is managed through a `Thread` that:
- Maintains an ordered list of `Event` objects representing every interaction
- Stores metadata for workflow context and user-defined data
- Provides intelligent state checks like `awaiting_human_response()`
- Supports context summarization for long-running conversations

```python
thread = Thread(
    events=[Event(type="user_input", data="What is 2+2?")],
    metadata={"user_id": "123", "session": "calc-01"}
)
# Check if waiting for user
if thread.awaiting_human_response():
    # Handle user interaction
```

### Persistent State Management

The `ConversationMemoryStore` provides production-grade state persistence:
- **File-based/DB-based Storage**: Each thread is automatically saved as JSON in a configurable context directory
- **In-memory Caching**: Active threads are cached for performance while maintaining persistence
- **Resumable Sessions**: Threads can be retrieved and resumed by ID at any time
- **Metadata Tracking**: Thread metadata (like human interaction state) is automatically maintained

```python
store = ThreadStore(context_dir="context")
# Create and persist a new thread
thread_id = store.create_from_message(
    "Calculate 2+2",
    metadata={"user": "alice"}
)
# Resume an existing thread
thread = store.get(thread_id)
```

### Event-Sourced Architecture

Every action in HICA is recorded as an `Event` in the thread's history:
- **Complete Traceability**: LLM calls, tool executions, user inputs, and clarifications are all recorded
- **Structured Logging**: Events include type, data, and timestamps for debugging and auditing
- **LLM Context Management**: Events are intelligently filtered and formatted for LLM consumption
- **State Recovery**: The full conversation state can be reconstructed from the event history

```python
# Events are automatically logged
thread.append_event(Event(
    type="tool_response",
    data={"result": 4}
))

# Serialize for LLM consumption
context = thread.serialize_for_llm(format="json")
```

This architecture enables:
- **Reliable Recovery**: Conversations can be paused, saved, and resumed without loss of context
- **Audit Trails**: Every decision and action is recorded for compliance and debugging
- **Flexible Workflows**: Build complex interactions with full state awareness
- **Production Scalability**: Threads can be stored in any backend (file system, database, cloud storage)

---

## 🧑‍💻 Human-in-the-Loop: Clarification Requests & Resumability

HICA natively supports **human-in-the-loop** workflows by treating clarification requests as first-class events in the conversation history. When the agent determines that more information is needed to proceed, it emits a `clarification` event. This event is recorded in the thread, pausing the agent's autonomous workflow and allowing for human intervention.

### How it Works

- **Clarification Event:** If the agent cannot proceed (e.g., missing information or ambiguous instruction), it appends a `clarification` event to the thread.
- **Pause and Resume:** The agent loop yields control, allowing a human to inspect the conversation state and provide the necessary input.
- **Resumability:** You can resume the thread at any time by appending a new `user_input` event and restarting the agent loop. The agent will continue from where it left off, with full context.

### Example: Handling Clarification and Resuming

```python
# resume with new input if clarification was requested
thread = store.get(thread_id)
if thread and thread.awaiting_human_response():
    # Human provides missing info
    thread.append_event(Event(type="user_input", data="yes continue"))
    async for _ in agent.agent_loop(thread):
        pass
    store.update(thread_id, thread)
```

This design ensures:
- **Trust and Safety:** The agent never hallucinates missing information; it explicitly asks for clarification.
- **Full Auditability:** All human interventions are logged as events.
- **Seamless Resumption:** Workflows can be paused and resumed at any time, even across processes or after a system restart.

HICA's event-sourced architecture makes it easy to build reliable, auditable, and human-friendly agent workflows.

---

## 🧩 Elegant Tool Creation & Unified Tool Management

HICA provides a robust and flexible tooling architecture that supports both simple functions and advanced, class-based tools.

- **Simple, Decorator-Based Tools:** For straightforward, stateless tools, you can use the simple `@registry.tool()` decorator on a Python function. HICA automatically infers the name, description, and parameters.

- **Advanced, Class-Based Tools (`BaseTool`):** For complex, stateful tools that require more control, you can inherit from `hica.tools.BaseTool`. This allows you to:
  - Implement custom logic for pre-execution safety checks (`should_confirm`).
  - Provide dynamic, user-friendly descriptions of the tool's actions.
  - Manage complex state or dependencies within the tool's own class structure.

- **Structured Tool Results (`ToolResult`):** All tools in HICA return a `ToolResult` object, which separates the clean, machine-readable data for the LLM (`llm_content`) from the rich, human-readable output for the user (`display_content`). This is a core feature that improves reliability and user experience.

- **Unified MCP & Local Tools:** HICA seamlessly integrates local Python tools and remote MCP tools into a single registry. The agent can use any tool without needing to know where it's located, and HICA automatically handles parsing the structured content from MCP responses.

**Example: Advanced `BaseTool`**
```python
from hica.tools import BaseTool, ToolResult

@registry.tool()
class DeleteFileTool(BaseTool):
    name = "delete_file"
    description = "Deletes a file from the filesystem. This action is permanent."

    def should_confirm(self, params: dict) -> bool:
        return True # Always ask the user for confirmation

    async def execute(self, path: str) -> ToolResult:
        # ... logic to delete the file ...
        return ToolResult(
            llm_content=f"The file at {path} was deleted.",
            display_content=f"✅ **File Deleted:** `{path}`"
        )
```

---


## 🛠️ Customizability

HICA's agent architecture is designed for maximum flexibility and composability: gives you **complete control** over the agent's reasoning, tool usage, and user interaction, to tailor every aspect of the agent's workflow to your needs.

### Decoupled Tool Routing and Parameter Generation

 HICA separates the process of **tool selection** (routing) from **parameter generation** and **tool execution**. The agent first determines which tool (or terminal state) to invoke, then—if a tool is selected—generates the required parameters in a dedicated step, and finally executes the tool. This modular approach allows you to:

- **Customize or override any step**: You can plug in your own logic for tool selection, parameter filling, or tool execution.
- **Integrate with any LLM or model provider**: The agent's LLM calls are abstracted via `AgentConfig`, so you can use OpenAI, Azure, local models, or any async-compatible provider.

### Clarification Requests as First-Class Events

If the agent determines that more information is needed, it emits a **ClarificationRequest** event. This is not just a return value—it's a logged event in the thread's event-sourced history. You have full control over how to handle clarifications:

- **LLM-driven clarifications**: Let the agent's LLM prompt the user for more information automatically.
- **Custom workflows**: Intercept clarification events and design your own user interaction or fallback logic.

### Event-Sourced, Observable Workflows

Every action—LLM call, tool call, user input, clarification, or final response—is recorded as a sequential event in the thread. This enables:

- **Full traceability and auditability** of the agent's reasoning and actions.
- **Custom workflow orchestration**: You can pause, resume, or branch workflows at any event, or inject your own events as needed.

### Metadata and Extensibility

- **Flexible metadata storage**: You can attach arbitrary metadata to the agent, the thread, or individual events, enabling advanced use cases like workflow tracking, analytics, or custom state management.
- **Pluggable model providers**: Simply set the `model` in `AgentConfig` to use any supported LLM backend.

---

## 🛠️ Design Note: Optional Thread and Context

HICA’s agent APIs (e.g., `run_llm`, `fill_parameters`, `select_tool`) accept both `thread` and `context` as optional parameters:

- **thread (Optional):**
  - If provided, the LLM receives the full event history for context, and new events are appended to the thread (unless `add_event=False`).
  - If omitted, the LLM operates statelessly—no history is used or recorded. This is useful for testing, isolated calls, or stateless inference.

- **context (Optional):**
  - If provided, this external context (e.g., a document, search results, or memory) is injected into the LLM prompt for that call only.
  - It is not persisted in the thread, allowing you to provide temporary or external information without affecting the conversation history.

**This design enables both:**
- **Stateful, auditable workflows** (with thread)
- **Stateless, ad-hoc LLM calls** (without thread)
- **Flexible context injection** for advanced reasoning

**Example: Stateless LLM Call for Testing**

```python
response = await agent.run_llm(
    prompt="What is the capital of France?",
    # No thread, no context: pure LLM call
)
print(response)
```

**Example: Context-Augmented LLM Call**

```python
response = await agent.run_llm(
    prompt="Summarize the following document.",
    context=large_document,
    # Optionally, with or without thread
)
```

---

## 🧪 Testing

Run all tests with:

```bash
pytest
```

- Includes tests in `tests` dir

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

HICA is licensed under the [Apache 2.0 License](LICENSE).

---

## 💡 Why Choose HICA?

- **Production-Ready:** Designed for reliability, auditability, and extensibility.
- **Unified Tooling:** Mix and match local Python and remote MCP tools.
- **Transparent:** Every step is logged and persisted for debugging and compliance.
- **Human-in-the-Loop:** Agents can pause for user input or approval at any time.
- **Open Source:** Community-driven and vendor-neutral.

---
