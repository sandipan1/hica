"""
How to Run this Example
----------------------

1. Start a New Agent Thread:
   Run the script without arguments to start a new thread:
       python examples/human_in_loop/human_in_loop_example.py
   - The agent will process the initial input (e.g., "Add 5 and ...").
   - If the agent needs clarification, it will pause and print a message with the thread ID.

2. Resume a Thread with Clarification:
   If the agent requested clarification, you can resume the thread by running:
       python examples/human_in_loop/human_in_loop_example.py <thread_id>
   - Replace <thread_id> with the actual thread ID printed in the previous step.
   - You will be prompted to enter the missing input or clarification.
   - The agent will continue processing and print the final result.

Tip: You can repeat the resume step as many times as needed if the agent requests further clarifications.
"""

import asyncio
import sys

from hica.agent import Agent, AgentConfig
from hica.core import Event, Thread
from hica.memory import ConversationMemoryStore  , SQLConversationMemoryStore
from hica.tools import ToolRegistry
from hica.logging import get_thread_logger
from rich import print
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
    store = ConversationMemoryStore()  
    agent = Agent(config=config, tool_registry=registry)
    
    if len(sys.argv) > 1:
        # --- Resume mode: user provides thread_id as argument ---
        thread_id = sys.argv[1]
        print(f"\n=== Resuming thread {thread_id} ===")
        thread = store.get(thread_id)
        if not thread:
            print(f"Thread with id {thread_id} not found.")
            return
        logger = get_thread_logger(thread_id)

        if thread.awaiting_human_response():
            print("Agent requested clarification. Providing missing input...")
            # You can customize the clarification input here:
            clarification = input(f"Enter clarification for :{thread.events[-1].data}   > ")
            logger.info(
                         "Continuing existing thread from clarification request from user ...",
                        clarification,
                    )
            thread.append_event(Event(type="user_input", data=clarification))
            async for _ in agent.agent_loop(thread):
                pass
            store.set(thread_id, thread)
            # print(f"Thread events after resuming: {[e.type for e in thread.events]}")
            # print("Final result:", thread.events[-1].data)
            logger.info(
                "Thread completed",
                events=[e.dict() for e in thread.events],
            )
        else:
            print("No clarification needed. Final result:", thread.events[-1].data)
    else:
        # --- Start a new thread ---
        print("\n=== Step 1: Start a new thread ===")
        thread = Thread(events=[Event(type="user_input", data="how many types of cats are there")])
        thread_id = store.create(thread)  # <-- thread_id creation via memory store
        logger = get_thread_logger(thread_id)
        logger.info(f"Created new thread with id: {thread_id}")
        async for _ in agent.agent_loop(thread):
            pass
        store.set(thread_id, thread)
        logger.info(
        "Thread completed",
        events=[e.dict() for e in thread.events],
    )
        print(f"Thread events after first run: {[e.type for e in thread.events]}")
        print(f"To resume, run: python human_in_loop_example.py {thread_id}")


if __name__ == "__main__":
    asyncio.run(main())
