# Highly customizable Agent Library (HICA)

Move beyond agent frameworks to build production-ready AI systems.
HICA gives you complete control over your AI agents' Thought , Action and Observation. This simplicity in-practice looks like a having complete control over prompts, context windows, tool execution, and control flow. Many existing libraries trade convenience over control for reliability—build agents that work in production.

## 🎯 Why HICA?

Most agent frameworks are black boxes that work great for demos but fail in production or lock you in with certain vendors. You can't debug decisions, modify prompts, or handle edge cases , change your stack at will when you don't control the fundamentals.

HICA is built on four core principles:

- **Control Your Prompts** - Own every instruction your agent receives
- **Manage Context Windows** - Engineer context for maximum efficiency and reliability  
- **Simplify Tools & Workflows** - Everything is a structured tool call that includes MCP 
- **Own Control Flow** - Build custom execution patterns that fit your use case
- **Observability & tool** - Build you are own observability flow by integrating with existing OpenTelemetry workflows or building your own

## Agentic Workflow
Agents work in a continuous cycle of: thinking (Thought) → acting (Act) and observing (Observe).

**Thought**: The LLM part of the Agent decides what the next step should be.
**Action**: The agent takes an action, by calling the tools with the associated arguments.
**Observation**: The model reflects on the response from the tool.

These three components Thought-Action-Observation work in a continuous loop. When we are building an Agent , it might fail in one of these 3 steps .
As long as we control each component of this loop , we can build Agents systematically and reliably.



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


### src/main.py
```python
import asyncio
from instructor import AsyncInstructor
from openai import AsyncOpenAI
from hica.agent import Agent, AgentConfig
from hica.core import Thread, Event
from hica.state import ThreadStore
from example.calculator_tool import registry as calculator_registry
import structlog

logger = structlog.get_logger()

async def main():
    client = AsyncInstructor.from_openai(AsyncOpenAI())
    config = AgentConfig()
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