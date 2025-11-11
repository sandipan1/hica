---
title: MCP Integration
---

HICA treats [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) as a first-class citizen, allowing you to seamlessly integrate remote MCP tools alongside local Python tools in a unified registry. The agent can use any tool without needing to know its location.

## Why MCP in HICA?

- **Unified Tool Interface**: Mix local Python functions and remote MCP tools in a single registry
- **Structured Content Handling**: Automatic parsing of MCP responses into clean `ToolResult` objects
- **Separation of Concerns**: Distinct content for LLMs (`llm_content`) and humans (`display_content`)
- **Standard Protocol**: Leverage existing MCP servers from the ecosystem

## Quick Start

### 1. Connect to an MCP Server

```python
from hica.tools import ToolRegistry, MCPConnectionManager

registry = ToolRegistry()

# Configure MCP connection
mcp_config = {
    "mcpServers": {
        "sqlite": {
            "command": "uvx",
            "args": ["mcp-server-sqlite", "--db-path", "db.sqlite"]
        }
    }
}

conn = MCPConnectionManager(mcp_config)
await conn.connect()

# Load all tools from the MCP server
await registry.load_mcp_tools(conn)
```

### 2. Use MCP Tools in Your Agent

```python
from hica.agent import Agent, AgentConfig
from hica.core import Thread, Event

agent = Agent(
    config=AgentConfig(model="gpt-4o-mini"),
    tool_registry=registry
)

thread = Thread(
    events=[Event(
        type="user_input",
        data="List all tables in the database"
    )]
)

# Agent can now use both local and MCP tools
async for _ in agent.agent_loop(thread):
    pass

await conn.disconnect()
```

## MCP Connection Options

HICA supports multiple ways to connect to MCP servers:

### Option 1: Configuration Dictionary

```python
mcp_config = {
    "mcpServers": {
        "sqlite": {
            "command": "uvx",
            "args": ["mcp-server-sqlite", "--db-path", "/path/to/db.sqlite"]
        },
        "calculator": {
            "command": "python",
            "args": ["calculator_mcp_tools.py"]
        }
    }
}

conn = MCPConnectionManager(mcp_config)
```

### Option 2: Direct Script Path (FastMCP)

```python
# Connect to a local FastMCP server script
conn = MCPConnectionManager("user_profile_mcp.py")
```

## Structured Content Example

HICA automatically handles structured content from MCP servers, providing clean separation between LLM-optimized and human-readable content.

### MCP Server with Structured Output

```python
# user_profile_mcp.py
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP("user_profile_server")

class UserProfile(BaseModel):
    """A user's profile."""
    name: str
    email: str
    user_id: int
    status: str

@mcp.tool
def get_user_profile(user_id: int) -> UserProfile:
    """Retrieves a user's profile from the database."""
    return UserProfile(
        name="Alice",
        email="alice@example.com",
        user_id=user_id,
        status="active"
    )

if __name__ == "__main__":
    mcp.run()
```

### Using the Structured Content

```python
# Execute the MCP tool
tool_result = await registry.execute_tool(
    name="get_user_profile",
    arguments={"user_id": 123}
)

# llm_content: Clean JSON for the LLM
print(tool_result.llm_content)
# '{"name": "Alice", "email": "alice@example.com", "user_id": 123, "status": "active"}'

# display_content: Human-readable summary
print(tool_result.display_content)
# "User Profile: Alice (alice@example.com) - Status: active"

# raw_result: Original MCP response object
print(tool_result.raw_result)
```

## Mixing Local and MCP Tools

One of HICA's key strengths is the ability to seamlessly combine local Python tools with remote MCP tools:

```python
from hica.tools import ToolRegistry, MCPConnectionManager

registry = ToolRegistry()

# Define local tools
@registry.tool()
def summarize_schema(table: str, columns: list[str]) -> str:
    """Format a summary of a table's schema."""
    cols = ", ".join(columns)
    return f"Table '{table}' has columns: {cols}"

# Load MCP tools
conn = MCPConnectionManager({
    "mcpServers": {
        "sqlite": {
            "command": "uvx",
            "args": ["mcp-server-sqlite", "--db-path", "db.sqlite"]
        }
    }
})

await conn.connect()
await registry.load_mcp_tools(conn)

# Now the agent can use both:
# - list_tables (MCP tool from sqlite server)
# - describe_table (MCP tool from sqlite server)
# - summarize_schema (local Python tool)
```

## Complete Example

Here's a complete example using an MCP SQLite server with an agent:

```python
import asyncio
from hica import Agent, AgentConfig
from hica.core import Thread, Event
from hica.tools import ToolRegistry, MCPConnectionManager

async def main():
    # Setup MCP connection
    mcp_config = {
        "mcpServers": {
            "sqlite": {
                "command": "uvx",
                "args": ["mcp-server-sqlite", "--db-path", "db.sqlite"]
            }
        }
    }

    conn = MCPConnectionManager(mcp_config)
    await conn.connect()

    # Setup registry and load tools
    registry = ToolRegistry()
    await registry.load_mcp_tools(conn)

    # Create agent
    agent = Agent(
        config=AgentConfig(
            model="gpt-4o-mini",
            system_prompt=(
                "You are a database assistant. Help users explore "
                "and query SQLite databases using available tools."
            )
        ),
        tool_registry=registry
    )

    # Create and run thread
    thread = Thread(
        events=[Event(
            type="user_input",
            data="Create a table called stocks with columns: stock_price, name, symbol, date. Then list all tables."
        )]
    )

    async for _ in agent.agent_loop(thread):
        pass

    # Cleanup
    await conn.disconnect()

    # View results
    for event in thread.events:
        print(f"{event.type}: {event.data}")

if __name__ == "__main__":
    asyncio.run(main())
```

## How It Works

### Tool Loading

When you call `registry.load_mcp_tools(conn)`, HICA:

1. Queries the MCP server for available tools
2. Extracts tool name, description, and parameter schema
3. Registers each tool in the unified registry
4. Creates proxy functions that handle MCP communication

### Structured Content Parsing

When an MCP tool returns structured content (like Pydantic models), HICA automatically:

1. **Extracts the raw data** for the `llm_content` field (as clean JSON)
2. **Generates a human-readable summary** for `display_content`
3. **Preserves the original response** in `raw_result` for debugging

This ensures:
- LLMs receive clean, compact JSON for efficient processing
- Users see formatted, readable output
- Full transparency with access to raw responses

## Best Practices

### 1. Clear Tool Descriptions

MCP tool descriptions are used during agent routing and parameter filling. Make them specific:

```python
@mcp.tool
def search_papers(query: str, limit: int = 10) -> list[dict]:
    """
    Search academic papers by keyword query.
    Returns paper titles, authors, and abstracts.
    Limited to the specified number of results.
    """
    # implementation
```

### 2. Use Standard MCP Servers

Leverage existing MCP servers from the ecosystem:
- `mcp-server-sqlite`: SQLite database operations
- `mcp-server-fetch`: Web content fetching
- `mcp-server-filesystem`: File system operations
- [More in the MCP Registry](https://github.com/modelcontextprotocol/servers)

### 3. Combine with Local Tools

Use local tools for:
- Formatting and presentation logic
- Business rules and validation
- Data aggregation and transformation

Use MCP tools for:
- External service integration
- Reusable capabilities
- Shared infrastructure

### 4. Connection Management

Always disconnect from MCP servers when done:

```python
try:
    await conn.connect()
    await registry.load_mcp_tools(conn)
    # ... use tools ...
finally:
    await conn.disconnect()
```

Or use async context managers if supported:

```python
async with MCPConnectionManager(config) as conn:
    await registry.load_mcp_tools(conn)
    # ... use tools ...
```

## Examples

See the [`examples/mcp/`](https://github.com/yourusername/hica/tree/main/examples/mcp) directory for complete examples:

- [mcp_agent.py](https://github.com/yourusername/hica/blob/main/examples/mcp/mcp_agent.py): Full agent with SQLite MCP server
- [structured_content_example.py](https://github.com/yourusername/hica/blob/main/examples/mcp/structured_content_example.py): Demonstrates structured content handling
- [calculator_mcp_tools.py](https://github.com/yourusername/hica/blob/main/examples/mcp/calculator_mcp_tools.py): Simple FastMCP calculator server
- [user_profile_mcp.py](https://github.com/yourusername/hica/blob/main/examples/mcp/user_profile_mcp.py): FastMCP server with Pydantic models

## Troubleshooting

### Tools Not Loading

If `load_mcp_tools()` doesn't find your tools:
- Verify the MCP server is running and accessible
- Check the command and args in your config
- Ensure the MCP server implements the protocol correctly

### Structured Content Not Parsing

If structured content isn't being parsed:
- Ensure your MCP server is using FastMCP or equivalent
- Verify the tool returns Pydantic models or similar structured types
- Check HICA logs for parsing errors

### Connection Issues

If you can't connect to the MCP server:
- Test the command manually: `uvx mcp-server-sqlite --db-path db.sqlite`
- Check file paths are absolute and accessible
- Verify required dependencies are installed (`uvx`, `fastmcp`, etc.)

