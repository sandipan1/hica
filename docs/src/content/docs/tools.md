---
title: Tools
---

Tools add capabilities to an agent. HICA supports:

- Simple function tools via `@registry.tool()`
- Advanced class-based tools by extending `BaseTool`
- Remote MCP tools via a unified registry

## Function tool

```python
from hica.tools import ToolRegistry
registry = ToolRegistry()

@registry.tool()
def echo(text: str) -> str:
    return text
```

## BaseTool

```python
from hica.tools import BaseTool, ToolResult
from pathlib import Path

@registry.tool()
class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Reads a file from disk"

    async def execute(self, path: str) -> ToolResult:
        try:
            content = Path(path).read_text()
            return ToolResult(
                llm_content=content,
                display_content=f"📄 Read `{path}`",
                raw_result={"path": path,  "content ": content}
            )
        except FileNotFoundError:
            return ToolResult(
                llm_content=f"Error: File not found: {path}",
                display_content=f"❌ Error: File `{path}` not found"
            )
```\n\n## MCP tools\n\nRegister MCP tools alongside local tools so the agent can call either uniformly. Structured content from MCP responses is normalized into `ToolResult` for LLM and display use.\n*** End Patch```}"/>

