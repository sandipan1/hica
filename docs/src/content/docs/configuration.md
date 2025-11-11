---
title: Configuration
---

Configure the agent via `AgentConfig` and environment variables.

## AgentConfig

```python
from hica.agent import Agent, AgentConfig
from hica.tools import ToolRegistry

agent = Agent(AgentConfig(model=\"gpt-4o-mini\", temperature=1), tool_registry=ToolRegistry())
```

## Environment

- `HICA_LOG_LEVEL` — global log level (e.g., `INFO`, `DEBUG`)\n- `HICA_CONSOLE` — if set to `1/true/yes/on`, enable console logging\n\nCredentials for your LLM provider (e.g., `OPENAI_API_KEY`) should be set per provider requirements.\n*** End Patch  ?>"} />

