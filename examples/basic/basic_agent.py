import asyncio

from examples.basic.calculator_tools import registry as calculator_registry
from hica import Agent, AgentConfig, ThreadStore
from hica.core import Event, Thread
from hica.logging import get_thread_logger


async def main():
    config = AgentConfig(
        model="openai/gpt-4.1-mini",
        system_prompt=(
            "You are an autonomous agent. Reason carefully to select tools based on their name, description, and parameters. "
            "Analyze the user input, identify the required operation, and determine if clarification is needed."
        ),
        context_format="json",
    )

    metadata = {"userid": "1234", "role": "analyst"}

    agent = Agent(
        config=config,
        tool_registry=calculator_registry,
        metadata=metadata,
    )

    # Create thread with metadata
    thread = Thread(
        events=[
            Event(
                type="user_input",
                data="Calculate 153 minus 3 and then divide the result with.. ",
            )
        ],
    )
    store = ThreadStore()
    thread_id = store.create(thread)

    # Get thread-specific logger
    logger = get_thread_logger(thread_id, metadata)

    logger.info("Starting new thread", user_input=thread.events[0].data)
    # We loop through the generator to run it to completion.
    # The `thread` object itself is updated, so we don't need to capture the yielded values.
    async for _ in agent.agent_loop(thread):
        pass
    store.update(thread_id, thread)

    logger.info(
        "Thread completed",
        events=[e.dict() for e in thread.events],
    )


if __name__ == "__main__":
    asyncio.run(main())
