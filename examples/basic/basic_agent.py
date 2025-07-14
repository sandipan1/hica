import asyncio

from calculator_tools import registry as calculator_registry

from hica import Agent, AgentConfig, Thread
from hica.logging import get_thread_logger
from hica.memory import ConversationMemoryStore


async def main():
    config = AgentConfig(
        model="openai/gpt-4.1-mini",
        system_prompt=(
            "You are an autonomous agent. Reason carefully to select tools based on their name, description, and parameters. "
            "Analyze the user input, identify the required operation, and determine if clarification is needed."
        ),
    )

    metadata = {
        "userid": "1234",
        "role": "analyst",
        "agent_config": config.model_dump(),
    }

    agent = Agent(
        config=config,
        tool_registry=calculator_registry,
    )
    # prompt_store = PromptStore(file_path="prompts.json")
    # # prompt_store.set("citation", "Cite using {style} style for {date}")
    # print(prompt_store.get("citation", style="APA", date="2025"))

    thread = Thread(metadata=metadata)  ## Create a new thread
    thread.add_event(type="user_input", data="what is 2 times 4 ")
    # Create a file-based MemoryStore to store the thread
    store = ConversationMemoryStore(backend_type="file", context_dir="context")
    store.set(thread)

    # Get thread-specific logger
    logger = get_thread_logger(thread.thread_id, metadata)

    logger.info("Starting new thread", user_input=thread.events[0].data)
    # We loop through the generator to run it to completion.
    # The `thread` object itself is updated, so we don't need to capture the yielded values.
    async for _ in agent.agent_loop(thread):
        pass
    store.set(thread)

    logger.info(
        "Thread completed",
        events=[e.dict() for e in thread.events],
    )


if __name__ == "__main__":
    asyncio.run(main())
