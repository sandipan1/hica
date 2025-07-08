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

### 2. Run an Agent

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
    store = ThreadStore()
    thread_id = store.create(thread)
    # Iterate through the async generator to run the agent loop to completion
    async for _ in agent.agent_loop(thread):
        pass
    store.update(thread_id, thread)
    print("Events:", [e.model_dump() for e in thread.events])

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Inspect State

All conversation state is saved as JSON in the `context/` directory. You can resume or audit any thread at any time.

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


mcp_manager = MCPConnectionManager("http://localhost:8000")  # or MCP server config

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
## 🧩 Observable and Stateful by Design

HICA provides robust state management through its `Thread` and `ThreadStore` system:

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

The `ThreadStore` provides production-grade state persistence:
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

HICA makes it seamless and robust to use both local Python functions and remote MCP tools:

- **Unified Tool Registration:**
  - Register local tools with a simple decorator or method. HICA extracts tool properties (name, description, parameters) from the function signature and docstring.
  - Register MCP tools automatically by fetching their schemas from the MCP server using the `MCPConnectionManager`.
  - All tools (local and remote) are available in a single registry for the agent to use, with no code changes needed as your toolset evolves.

- **MCPConnectionManager:**
  - Handles connecting to MCP servers, fetching available tools, and executing remote tool calls.
  - Makes it easy to add or remove remote tools at runtime, and keeps your agent in sync with remote tool definitions.

- **Parameter Validation & Type Safety:**
  - Every tool call (local or MCP) is validated against a Pydantic model generated from the tool's schema.
  - This ensures all arguments are type-checked before execution, reducing runtime errors and making debugging easier.

- **Automatic Tool Execution Handling:**
  - HICA automatically determines whether to execute a tool locally or via MCP, based on the registry.
  - Both sync and async local functions are supported.

**Example:**
```python
from hica.tools import ToolRegistry, MCPConnectionManager

registry = ToolRegistry()
##local tool
@registry.tool()
def add(a: int, b: int) -> int:
    "Add two numbers"
    return a + b

## mcp server
config = {
    "mcpServers": {
        "sqlite": {
            "command": "uvx",
            "args": ["mcp-server-sqlite", "--db-path", "db.sqlite"],
        }
    }
}
conn = MCPConnectionManager(config)
# ... connect and load MCP tools ...
async def setup():
    await conn.connect()
    await registry.load_mcp_tools(mcp_manager)
    print(registry.get_tool_definitions())
    await conn.disconnect()
asyncio.run(setup())
# Now both local and remote tools are available to the agent!
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


## 🧪 Testing

Run all tests with:

```bash
pytest
```

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
