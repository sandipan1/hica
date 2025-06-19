import ast
import asyncio

from fastmcp import Client
from rich import print

from hica.tools import ToolRegistry

# MCP server config
config = {
    "mcpServers": {
        "sqlite": {
            "command": "uvx",
            "args": ["mcp-server-sqlite", "--db-path", "db.sqlite"],
        }
    }
}
client = Client(config)
registry = ToolRegistry()


# Local tool for formatting summaries
@registry.tool()
def summarize_schema(table: str, schema: dict) -> str:
    """Format a summary of a table's schema."""
    columns = ", ".join(f"{col}: {typ}" for col, typ in schema.items())
    return f"Table '{table}' has columns: {columns}"


async def main():
    async with client:
        # Load MCP tools from the MCP server
        await registry.load_mcp_tools(client)

        # # Step 1: Create a table named 'animals' (MCP tool)
        # if "create_table" in registry.get_tool_definitions():
        #     create_table_sql = (
        #         "CREATE TABLE IF NOT EXISTS animals ("
        #         "name TEXT, species TEXT, age INTEGER)"
        #     )
        #     result_create = await registry.execute_tool(
        #         "create_table", {"query": create_table_sql}
        #     )
        #     print(f"Result of MCP tool 'create_table': {result_create}")
        # else:
        #     print("MCP tool 'create_table' not found in registry.")

        # Step 2: List all tables (MCP tool)
        tables_result = await registry.execute_tool("list_tables", {})
        if hasattr(tables_result[0], "text"):
            tables = ast.literal_eval(tables_result[0].text)

            print(f"Tables found: {tables}")
            print(type(tables))
        else:
            print("No tables found")

        # Step 3: For each table, describe its schema (MCP tool)
        summaries = []
        for table_info in tables:
            if isinstance(table_info, dict):
                table = table_info.get("name")
            else:
                table = table_info
            print(table)

            schema_result = await registry.execute_tool(
                "describe_table", {"table_name": table}
            )
            print(schema_result)
            # schema = (
            #     schema_result.get("schema", {})
            #     if isinstance(schema_result, dict)
            #     else schema_result
            # )
            # # Step 4: Summarize schema (local tool)
            # summary = await registry.execute_tool(
            #     "summarize_schema", {"table": table, "schema": schema}
            # )
            # summaries.append(summary)

        # Step 5: Present the summaries
        # print("\nSummary of all tables:")
        # for s in summaries:
        #     print("-", s)


if __name__ == "__main__":
    asyncio.run(main())
