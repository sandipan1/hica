# from examples.basic.calculator_tools import registry as calculator_registry
import asyncio
import random
import string
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel, field_validator

from hica import Agent, AgentConfig, ConversationMemoryStore
from hica.core import Thread
from hica.logging import get_thread_logger
from hica.tools import ToolRegistry

load_dotenv()
registry = ToolRegistry()


@registry.tool()
def search_paper(query: str):
    """search for papers in science database for the given query and outputs papers with links and summary"""
    random_part = "".join(random.choices(string.ascii_letters + string.digits, k=20))
    return f"{query}_{random_part}"


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
        tool_registry=registry,
        metadata=metadata,
    )
    thread = Thread()
    logger = get_thread_logger(thread_id=thread.thread_id)
    store = ConversationMemoryStore(backend_type="file", context_dir="context")
    thread.add_event(
        type="user_input",
        data="generate 3 queries to search on a scientific journal data for relation between cancer and fut2 gene",
    )
    logger.info("added user input")

    class Query(BaseModel):
        queries: List[str]

        @field_validator("queries")
        def validate(cls, value):
            if len(value) != 3:
                raise ValueError("queries must have exactly 3 items")
            return value

    response = await agent.run_llm(
        "answer the user input", thread=thread, response_model=Query
    )
    store.set(thread=thread)
    logger.info("generated 3 queries from the user query ")

    ## use generate parameters for tools calls / user should give it
    ## tools are called sequentially.
    for query in response.queries:
        thread.add_event(
            type="parameters",
            data={"intent": "search_paper", "arguments": {"query": query}},
        )

        res = await agent.execute_tool("search_paper", {"query": query}, thread=thread)

        logger.info(f"tool reponse for query : {query} ", res)
    store.set(thread=thread)


asyncio.run(main())
