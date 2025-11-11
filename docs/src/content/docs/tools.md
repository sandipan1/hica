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

@registry.tool()
class DeleteFileTool(BaseTool):
    name = \"delete_file\"
    description = \"Deletes a file\"

    def should_confirm(self, params: dict) -> bool:
        return True

    async def execute(self, path: str) -> ToolResult:
        # ... delete ...
        return ToolResult(
            llm_content=f\"Deleted {path}\",
            display_content=f\"✅ Deleted `{path}`\",
            raw_result={\"path\": path}\n+        )\n```\n\n## MCP tools\n\nRegister MCP tools alongside local tools so the agent can call either uniformly. Structured content from MCP responses is normalized into `ToolResult` for LLM and display use.\n*** End Patch```}"/>

