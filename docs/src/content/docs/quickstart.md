---
title: Quickstart
---

This guide gets you productive fast with HICA using the patterns in `src/hica` and the README.

## 1) Create an agent and a registry

```python
from hica.agent import Agent, AgentConfig
from hica.tools import ToolRegistry

registry = ToolRegistry()
agent = Agent(AgentConfig(model=\"gpt-4o-mini\"), tool_registry=registry)
```

## 2) Add tools

```python
from hica.tools import BaseTool, ToolResult

@registry.tool()
class DeleteFileTool(BaseTool):
    name = \"delete_file\"
    description = \"Deletes a file from the filesystem. This action is permanent.\"

    def should_confirm(self, params: dict) -> bool:
        return True  # Require confirmation

    async def execute(self, path: str) -> ToolResult:
        # ... delete logic ...
        return ToolResult(
            llm_content=f\"File deleted: {path}\",
            display_content=f\"✅ File Deleted: `{path}`\",
            raw_result={\"path\": path, \"status\": \"deleted\"},
        )
```

## 3) Run the agent loop

```python
from hica.core import Thread, Event

thread = Thread()
thread.add_event(type=\"user_input\", data=\"Please delete /tmp/demo.txt\")

async for _ in agent.agent_loop(thread):
    pass
```

If a tool needs confirmation, the loop yields a `clarification` event and pauses until you append a new `user_input` event and resume.

## 4) Logging

Set `HICA_LOG_LEVEL` (INFO, DEBUG, etc.). For console output, set `HICA_CONSOLE=1`. Logs are also written under `logs/thread_<id>.log`.

## 5) Deploy docs

The documentation site lives in `docs/` (Astro Starlight). For Vercel, this repo includes `vercel.json` that builds `docs/` automatically.


