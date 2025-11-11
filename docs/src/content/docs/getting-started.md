---
title: Getting Started
---

HICA (Highly Customizable Agent Library) helps you build transparent, human-in-the-loop agents with explicit tool usage, event-sourced history, and unified local/MCP tools.

## Install

```bash
pip install hica
```
To include examples, use
```bash
pip install hica[all]
```
## Minimum example

```python
from hica.agent import Agent, AgentConfig
from hica.tools import ToolRegistry

registry = ToolRegistry()

@registry.tool()
def echo(text: str) -> str:
    return text

agent = Agent(AgentConfig(model="gpt-4o-mini"), tool_registry=registry)

# Run a one-off LLM call
resp = await agent.run_llm("Say hello")
print(resp)
```

## Next steps

- Read the Quickstart for a guided setup.
- Learn the Architecture to understand threads, events, and the agent loop.
- Explore Tools and MCP Integration to add capabilities.
