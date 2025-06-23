import asyncio

from hica.agent import Agent, AgentConfig
from hica.core import Event, Thread
from hica.state import ThreadStore
from hica.tools import ToolRegistry

# 1. Define a simple tool for demonstration
registry = ToolRegistry()


@registry.tool()
def add(a: int, b: int) -> int:
    "Add two numbers."
    return a + b


@registry.tool()
def subtract(a: int, b: int) -> int:
    "Subtract two numbers."
    return a - b


# 2. Agent configuration
config = AgentConfig(model="openai/gpt-4.1-mini")


async def main():
    # --- Step 1: Start a new thread with ambiguous input ---
    print("\n=== Step 1: Start a new thread ===")
    thread = Thread(events=[Event(type="user_input", data="Add 5 and ...")])
    store = ThreadStore()
    thread_id = store.create(thread)
    agent = Agent(config=config, tool_registry=registry)

    # Run the agent loop (may result in a clarification request)
    async for _ in agent.agent_loop(thread):
        pass
    store.update(thread_id, thread)
    print(f"Thread events after first run: {[e.type for e in thread.events]}")

    # --- Step 2: Resume if clarification was requested ---
    print("\n=== Step 2: Resume after clarification ===")
    thread = store.get(thread_id)
    if thread and thread.awaiting_human_response():
        print("Agent requested clarification. Providing missing input...")
        thread.append_event(Event(type="user_input", data="add 5 and 7"))
        async for _ in agent.agent_loop(thread):
            pass
        store.update(thread_id, thread)
        print(f"Thread events after resuming: {[e.type for e in thread.events]}")
        print("Final result:", thread.events[-1].data)
    else:
        print("No clarification needed. Final result:", thread.events[-1].data)


if __name__ == "__main__":
    asyncio.run(main())
