
# Highly customizable Agent Library (HICA)

Move beyond agent frameworks to build production-ready AI systems.
HICA gives you complete control over your AI agents' Thought , Action and Observation. This simplicity in-practice looks like a having complete control over prompts, context windows, tool execution, and control flow. Many existing libraries trade convenience over control for reliability—build agents that work in production.
> ## TLDR: Give you visibility and control into every part of you Agent through Stateful Conversations, Human-in-the-Loop by Design, Structured Logging
## 🎯 Why HICA?

Most agent frameworks are black boxes that work great for demos but fail in production or lock you in with certain vendors. You can't debug decisions, modify prompts, or handle edge cases , change your stack at will when you don't control the fundamentals.

HICA is built on four core principles:

- **Control Your Prompts** - Own every instruction your agent receives
- **Manage Context Windows** - Engineer context for maximum efficiency and reliability  
- **Simplify Tools & Workflows by Atomization** - Everything is a `Event` that includes user input, LLM call, tool call
- **Own Control Flow** - Build custom execution patterns that fit your use case
- **Observability & tool** - Build you are own observability flow by integrating with existing OpenTelemetry workflows or building your own

## Agentic Workflow
Agents work in a continuous cycle of: thinking (Thought) → acting (Act) and observing (Observe).

**Thought**: The LLM part of the Agent decides what the next step should be.
**Action**: The agent takes an action, by calling the tools with the associated arguments.
**Observation**: The model reflects on the response from the tool.

These three components Thought-Action-Observation work in a continuous loop. When we are building an Agent , it might fail in one of these 3 steps .
As long as we control each component of this loop , we can build Agents systematically and reliably.

## 

A generalized Python library for building 12-factor compliant agents, designed to handle tool execution, human interactions, and state management with a modular and extensible architecture.

## Features
- **Tool Support**: Register and execute custom tools (e.g., calculator operations).
- **Human Interaction**: Handle clarification requests and approvals via CLI or HTTP.
- **Thread Management**: Maintain conversation state with JSON or XML serialization.
- **Customizable Prompts**: Configure LLM prompts with reasoning steps.
- **HTTP API**: Expose agent functionality via FastAPI endpoints.
- **State Management**: In-memory thread store, extensible to databases.
- **Structured Logging**: Comprehensive logging with `structlog` for debugging and monitoring.
- **Statelessness**: Externalized state management for scalability.

# Usage
**Example: Running an Agent with Calculator Tool**
### Set Environment variables in .env 
`OPENAI_API_KEY="your-api-key"`


Run the Example:
The main.py script processes a query ("Calculate 3 plus 4") using the add tool from calculator_tool.py:


### src/main.py
```python
import asyncio
import instructor
from openai import AsyncOpenAI
from hica.agent import Agent, AgentConfig
from hica.core import Thread, Event
from hica.state import ThreadStore
from example.calculator_tool import registry as calculator_registry
import structlog

logger = structlog.get_logger()

async def main():
    client = instructor.from_openai(AsyncOpenAI())
    config = AgentConfig(
        model="gpt-4.1-mini",
        system_prompt=(
            "You are an autonomous agent. Reason carefully to select tools based on their name, description, and parameters. "
            "Analyze the user input, identify the required operation, and determine if clarification is needed."
        ),
        context_format="json",
    )
    agent = Agent(
        client=client,
        config=config,
        tool_registry=calculator_registry,
        metadata={"userid": "1234", "role": "analyst"}
    )
    thread = Thread(events=[Event(type="user_input", data="Calculate 3 plus 4")])
    store = ThreadStore()
    thread_id = store.create(thread)
    updated_thread = await agent.agent_loop(thread)
    store.update(thread_id, updated_thread)
    logger.info("Thread state", thread_id=thread_id, events=[e.model_dump() for e in updated_thread.events])

if __name__ == "__main__":
    asyncio.run(main())
```
Run the script:
`python main.py`



### Event Output (in context/<thread_id>.json):
```json
{
  "events": [
    {"type": "user_input", "data": "Calculate 3 plus 4", "timestamp": "..."},
    {"type": "llm_response", "data": {"intent": "add"}, "timestamp": "..."},
    {"type": "llm_response", "data": {"intent": "add", "arguments": {"a": 3.0, "b": 4.0}}, "timestamp": "..."},
    {"type": "tool_call", "data": {"intent": "add", "arguments": {"a": 3.0, "b": 4.0}}, "timestamp": "..."},
    {"type": "tool_response", "data": 7.0, "timestamp": "..."},
    {"type": "llm_response", "data": {"intent": "done"}, "timestamp": "..."},
    {"type": "tool_call", "data": {"intent": "done", "message": "Task completed by agent."}, "timestamp": "..."}
  ],
  "metadata": {"userid": "1234", "role": "analyst"},
  "version": 2
}

```

### 🚀  MCP (Model Context Protocol) Tool Integration
HICA now supports seamless integration with FastMCP and other MCP-compatible tool servers.
You can register and invoke both local Python tools and remote MCP tools in a unified agent workflow.

**Key Benefits**
- Unified Tool Registry: Register local and remote (MCP) tools together.
- Dynamic Tool Loading: Load tool definitions from any MCP server at runtime.
- LLM-Orchestrated Tool Use: The agent can reason about and call both local and MCP tools in the same workflow.
- Robust Serialization: All tool results (including complex MCP content types) are normalized for logging, storage, and downstream use.

### Register MCP tools and run the Agent 
```python
# MCP server config
registry = ToolRegistry()
mcp_config = {
    "mcpServers": {
        "sqlite": {
            "command": "uvx",
            "args": ["mcp-server-sqlite", "--db-path", "db.sqlite"],
        }
    }
}
 # Optionally, register local tools as well
@registry.tool()
def add(a: int, b: int) -> int:
    return a + b

mcp_manager = MCPConnectionManager(mcp_config)


async def main():
    await conn.connect()
    await registry.load_mcp_tools(mcp_manager)
    agent = Agent(
        client=...,  # your LLM client
        config=AgentConfig(
            model="gpt-4.1-mini",
            system_prompt="You are an autonomous agent. Reason carefully to select tools based on their name, description, and parameters.",
            context_format="json",
        ),
        tool_registry=registry,
        metadata={"userid": "1234", "role": "analyst"}
    )
    thread = Thread(events=[Event(type="user_input", data="List all tables in the database")])
    store = ThreadStore()
    thread_id = store.create(thread)
    updated_thread = await agent.agent_loop(thread)
    store.update(thread_id, updated_thread)
    print("Thread state:", [e.model_dump() for e in updated_thread.events])

    await mcp_manager.close()

if __name__ == "__main__":
    asyncio.run(main())
```
Check out the complete example on `/example/main_mcp_tool.py`

## 🤝 Contributing

We welcome contributions from the community! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to report issues, submit pull requests, and get involved.


Feel free to email me if you have questions or suggestions: