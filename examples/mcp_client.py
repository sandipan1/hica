import ast
import asyncio

from fastmcp import Client
from rich import print

from hica.tools import ToolRegistry

config = {
    "mcpServers": {
        "sqlite": {
            "command": "uvx",
            "args": ["mcp-server-sqlite", "--db-path", "db.sqlite"],
        }
    }
}

registry = ToolRegistry()


@registry.tool()
def add(a: float, b: float) -> float:
    """Add two numbers."""


async def main():
    client = Client(config)
    async with client:
        await registry.load_mcp_tools(client)
        # print(registry.get_tool_definitions())
        tables_result = await registry.execute_tool("list_tables", {})
        print(tables_result)
        for content in tables_result:
            if hasattr(content, "text"):
                # Text content
                print(f"Text: {content.text}")
                tables = ast.literal_eval(content.text)
                print(tables)
            elif hasattr(content, "data"):
                # Binary content (images, files, etc.)
                print(f"Binary data: {len(content.data)} bytes")
                # You might save this to a file or process it further
            elif hasattr(content, "content"):
                # Generic content
                print(f"Content: {content.content}")


if __name__ == "__main__":
    asyncio.run(main())
