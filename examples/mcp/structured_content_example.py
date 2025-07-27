import asyncio

from rich import print

from hica import ToolRegistry
from hica.tools import MCPConnectionManager


async def main():
    """
    This example demonstrates how HICA handles structured content from an MCP server.
    """
    print(
        "[bold cyan]-- Demonstrating Structured Content Handling in HICA --[/bold cyan]"
    )

    # 1. Configure the MCP Connection Manager to run our new server

    conn = MCPConnectionManager("user_profile_mcp.py")

    # 2. Set up the HICA Agent and Tool Registry
    registry = ToolRegistry()
    # agent_config = AgentConfig(model="openai/gpt-4.1-mini")
    # agent = Agent(config=agent_config, tool_registry=registry)

    try:
        # 3. Connect to the MCP server and load the tools
        await conn.connect()
        await registry.load_mcp_tools(conn)
        print(
            f"[green]Successfully loaded tools from MCP server: {list(registry.mcp_tools.keys())}[/green]"
        )

        # 4. Execute the tool
        print("\n[yellow]Calling the 'get_user_profile' tool...[/yellow]")
        tool_result = await registry.execute_tool(
            name="get_user_profile", arguments={"user_id": 123}
        )

        # 5. Inspect the result to see the separation of content
        print("\n[bold cyan]-- Inspecting the ToolResult from HICA --[/bold cyan]")

        print("\n[bold]1. `llm_content` (for the Language Model):[/bold]")
        print(
            "[green]This is a clean, compact JSON string. Perfect for the LLM.[/green]"
        )
        print(tool_result.llm_content)

        print("\n[bold]2. `display_content` (for the User):[/bold]")
        print("[green]This is the human-readable text summary.[/green]")
        print(tool_result.display_content)

        print("\n[bold]3. `raw_result` (The original object from FastMCP):[/bold]")
        print(tool_result.raw_result)

    except Exception as e:
        print(f"[bold red]An error occurred: {e}[/bold red]")
    finally:
        # 6. Disconnect from the MCP server
        await conn.disconnect()
        print("\n[yellow]Disconnected from MCP server.[/yellow]")


if __name__ == "__main__":
    asyncio.run(main())
