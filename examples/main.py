import asyncio

from calculator_tools import registry as calculator_registry
from dotenv import load_dotenv

from hica import Agent, AgentConfig, ThreadStore
from hica.core import Event, Thread
from hica.logging import get_thread_logger

load_dotenv()


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
                data="Calculate 153 minus 3 and then divide the result ",
            )
        ],
    )
    store = ThreadStore()
    thread_id = store.create(thread)

    # Get thread-specific logger
    logger = get_thread_logger(thread_id, metadata)

    logger.info("Starting new thread", user_input=thread.events[0].data)
    updated_thread = await agent.agent_loop(thread)
    store.update(thread_id, updated_thread)

    logger.info(
        "Thread completed",
        events=[e.dict() for e in updated_thread.events],
    )


## Resume thread
async def resume_thread(thread_id: str):
    store = ThreadStore()
    thread = store.get(thread_id)
    if not thread:
        return
    logger = get_thread_logger(thread_id)
    # check of the last event was a clarification request
    if not thread.awaiting_human_response():
        return
    clarification_event = Event(
        type="user_input",
        data="divide by 2",
    )
    logger.info(
        "Continuing existing thread from clarification request from user ...",
        clarification_event.data,
    )
    config = AgentConfig(
        model="openai/gpt-4.1-mini",
        system_prompt=(
            "You are an autonomous agent. Reason carefully to select tools based on their name, description, and parameters. "
            "Analyze the user input, identify the required operation, and determine if clarification is needed."
        ),
        context_format="json",
    )
    thread.append_event(clarification_event)
    agent = Agent(config=config, tool_registry=calculator_registry)
    updated_thread = await agent.agent_loop(thread)
    store.update(thread_id, updated_thread)
    logger.info(
        "Thread completed",
        events=[e.dict() for e in updated_thread.events],
    )


if __name__ == "__main__":
    # asyncio.run(resume_thread(thread_id="dad58eee-2da8-4b3a-999d-5ffbca7bc8c7"))
    asyncio.run(main())
