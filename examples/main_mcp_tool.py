import asyncio

import instructor
from dotenv import load_dotenv
from openai import AsyncOpenAI

from hica import Agent, AgentConfig, ThreadStore
from hica.core import Event, Thread
from hica.logging import get_thread_logger

load_dotenv()

from hica.tools import MCPConnectionManager, ToolRegistry

# mcp_manager = MCPConnectionManager(Client("calculator_mcp_tools.py"))
registry = ToolRegistry()


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
    # Usage

    mcp_config = {
        "mcpServers": {
            "sqlite": {
                "command": "uvx",
                "args": [
                    "mcp-server-sqlite",
                    "--db-path",
                    "/Users/sandipan/projects/AI/hica/example/db.sqlite",
                ],
            }
        }
    }

    conn = MCPConnectionManager(mcp_config)

    await conn.connect()
    await registry.load_mcp_tools(conn)

    agent = Agent(
        client=client,
        config=config,
        tool_registry=registry,
        metadata=metadata,
    )

    # Create thread with metadata
    thread = Thread(
        events=[
            Event(
                type="user_input",
                data="create a table called stocks with column stock_price, name, symbol, and date. List all the table in the database.If you find the animals table, give me description for it",
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
    await conn.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
