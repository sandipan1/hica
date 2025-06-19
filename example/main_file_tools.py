import asyncio

import instructor
from openai import AsyncOpenAI

from example.file_tools import registry as file_registry
from hica.agent import Agent, AgentConfig
from hica.core import Event, Thread
from hica.logging import get_thread_logger
from hica.state import ThreadStore


async def main():
    client = instructor.from_openai(AsyncOpenAI())
    config = AgentConfig(
        model="gpt-4o-mini",
        system_prompt=(
            "You are a powerful file manipulation agent. You can create, read, analyze, encrypt, decrypt, "
            "and transform files. You can also find files, create backups, and generate detailed reports. "
            "Always be careful with file operations and provide clear feedback about what you're doing. "
            "When working with files, make sure to handle errors gracefully and inform the user about the results."
            "<example> query: find all pdf files - tool: find_files, parameters: ('./', '*.pdf')</example> "
        ),
        context_format="json",
    )
    agent = Agent(
        client=client,
        config=config,
        tool_registry=file_registry,
        metadata={"userid": "demo_user", "role": "file_manager"},
    )

    # Example: Create a file and then analyze it
    thread = Thread(
        events=[
            Event(
                type="user_input",
                data="Find all .txt files in the current directory",
            )
        ]
    )

    store = ThreadStore()
    thread_id = store.create(thread)
    # Get thread-specific logger
    logger = get_thread_logger(thread_id)

    logger.info("Starting new thread", user_input=thread.events[0].data)
    updated_thread = await agent.agent_loop(thread)
    store.update(thread_id, updated_thread)

    logger.info(
        "File operations completed",
        thread_id=thread_id,
        events=[e.model_dump() for e in updated_thread.events],
    )


if __name__ == "__main__":
    asyncio.run(main())
