from dotenv import load_dotenv

from hica import AgentConfig

load_dotenv()
import asyncio

from rich import print

from hica import Agent, ConversationMemoryStore, Thread
from hica.tools import MCPConnectionManager, ToolRegistry

# mcp_manager = MCPConnectionManager(Client("calculator_mcp_tools.py"))
registry = ToolRegistry()


async def main():
    config = AgentConfig(
        model="openai/gpt-4.1-mini",
        system_prompt=(
            "You are an autonomous agent. Reason carefully to select tools based on their name, description, and parameters. "
            "Analyze the user input, identify the required operation, and determine if clarification is needed."
        ),
    )
    metadata = {"userid": "1234", "role": "analyst"}
    mcp_config = {"mcpServers": {"grep": {"url": "https://mcp.grep.app"}}}
    conn = MCPConnectionManager(mcp_config)
    await conn.connect()
    await registry.load_mcp_tools(conn)
    agent = Agent(
        config=config,
        tool_registry=registry,
    )
    print(registry.mcp_tools)
    thread = Thread()
    store = ConversationMemoryStore(backend_type="file")
    thread.add_event(
        type="user_input", data="how to handle authentication in nextjs, use grep tool"
    )
    store.set(thread=thread)
    async for _ in agent.agent_loop(thread):
        pass
    store.set(thread=thread)

    await conn.disconnect()


asyncio.run(main())
