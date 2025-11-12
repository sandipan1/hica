---
title: Quickstart
---

This guide gets you productive fast with HICA using the patterns in `src/hica` and the README.

## 1) Create an agent and a registry

```python
from hica.agent import Agent, AgentConfig
from hica.tools import ToolRegistry

registry = ToolRegistry()
config = AgentConfig(
        model="openai/gpt-4.1-mini",
        system_prompt=(
            "You are an autonomous agent. Reason carefully to select tools based on their name, description, and parameters. "
            "Analyze the user input, identify the required operation, and determine if clarification is needed."
            "Ask for clarification if Delete file operation is required"
        ),
    )
agent = Agent(config, tool_registry=registry)
```

## 2) Add tools

```python
from hica.tools import BaseTool, ToolResult

@registry.tool()
class DeleteFileTool(BaseTool):
    name = "delete_file"
    description = "Deletes a file from the filesystem. This action is permanent."

    async def execute(self, path: str) -> ToolResult:
        # ... delete logic ...
        return ToolResult(
            llm_content=f"File deleted: {path}",
            display_content=f"✅ File Deleted: `{path}`",
            raw_result={"path": path, "status": "deleted"},
        )
@registry.tool()
def add(a:int, b:int):
    """ Add 2 integer numbers """
    return a+b

```
## 3)  Define Thread, memory store and logging
```python

thread = Thread()

#  Create a file-based MemoryStore to store the thread
store = ConversationMemoryStore(backend_type="file", context_dir="context")
# Create a logger to track the thread
logger = get_thread_logger(thread.thread_id)


```


## 4) Run the agent loop

```python
from hica.core import Thread, Event

thread.add_event(type="user_input", data="Please delete /tmp/demo.txt")

logger.info("Starting new thread", user_input=thread.events[0].data)


async for _ in agent.agent_loop(thread):
    pass

store.set(thread)


logger.info(
        "Thread completed",
        events=[e.dict() for e in thread.events],
    )

```

If a tool needs confirmation, the loop yields a `clarification` event and pauses until you append a new `user_input` event and resume.


Set `HICA_LOG_LEVEL` (INFO, DEBUG, etc.). For console output, set `HICA_CONSOLE=1`. Logs are also written under `logs/thread_<id>.log`.


Checkout more examples in `examples/`
