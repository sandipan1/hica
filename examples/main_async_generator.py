import asyncio
import time

from calculator_tools import registry as calculator_registry
from dotenv import load_dotenv
from rich import print

from hica import Agent, AgentConfig, ThreadStore
from hica.core import Event, Thread
from hica.logging import get_thread_logger


async def main():
    """
    This example demonstrates how to use the async generator `agent_loop`
    to stream and process agent events in real time, while also persisting
    the state at each step using ThreadStore.
    """
    config = AgentConfig(
        model="openai/gpt-4.1-mini",
        system_prompt=(
            "You are an autonomous agent. Reason carefully to select tools based on their name, description, and parameters. "
            "Analyze the user input, identify the required operation, and determine if clarification is needed."
        ),
    )

    agent = Agent(
        config=config,
        tool_registry=calculator_registry,
    )

    thread = Thread(
        events=[
            Event(
                type="user_input",
                data="Calculate 355 minus 3 and then divide the result by 2.",
            )
        ],
    )

    # --- Persistence with ThreadStore ---
    store = ThreadStore()
    thread_id = store.create(thread)

    # --- Thread-specific Logger ---
    logger = get_thread_logger(thread_id)
    logger.info("Starting new agent process", user_input=thread.events[0].data)
    # ---

    print(f"--- Starting Agent (Thread ID: {thread_id}) ---")
    start_time = time.time()
    last_event_count = 0

    # Use `async for` to iterate through the states yielded by the agent loop
    async for intermediate_thread in agent.agent_loop(thread):
        # Persist the latest state after each yield
        store.update(thread_id, intermediate_thread)
        logger.debug(
            "Intermediate state saved",
            event_count=len(intermediate_thread.events),
        )

        new_event_count = len(intermediate_thread.events)
        if new_event_count > last_event_count:
            # Print only the new events that have been added since the last yield
            for i in range(last_event_count, new_event_count):
                event = intermediate_thread.events[i]
                current_time = time.time() - start_time
                print(f"[{current_time:.2f}s] New Event: {event.type} -> {event.data}")
            last_event_count = new_event_count

    logger.info("Agent process finished.")
    print("--- Agent Finished ---")
    final_thread = store.get(thread_id)  # Retrieve final state from store
    print("\n--- Final Thread State ---")
    print(final_thread.model_dump_json(indent=2))


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
