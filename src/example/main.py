import asyncio

import instructor
from dotenv import load_dotenv
from openai import AsyncOpenAI

from example.calculator_tools import registry as calculator_registry
from hica import Agent, AgentConfig, ThreadStore
from hica.core import Event, Thread
from hica.logging import get_thread_logger

load_dotenv()


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

    metadata = {"userid": "1234", "role": "analyst"}

    agent = Agent(
        client=client,
        config=config,
        tool_registry=calculator_registry,
        metadata=metadata,
    )

    # Create thread with metadata
    thread = Thread(
        events=[
            Event(
                type="user_input",
                data="Calculate 153 minus 3 and then divide the result with 5",
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


if __name__ == "__main__":
    asyncio.run(main())

## TODO think about resumability
## TODO think about viewing it online - thread execution and observability are independent
## you can beg LLM to take an action but you can also control how it operates with different conditions
## Human approval can be done in a lot of differernt ways -
##    1. LLM sampling or elicilation
##    2. between tool selection and tool calling
##    3. between tool parameter generation and tool execution
##    4. between tool response and next step
## TODO think about seperation of Agent and thread.
## TODO version history is not needed - remove
## TODO multiple threads for multiple agents.
