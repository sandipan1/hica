---
title: Architecture
---

HICA is designed around a transparent, event-sourced workflow with three pillars:

- Agent: orchestrates LLM calls, tool selection, parameter filling, and execution.
- Tools: local Python tools and remote MCP tools with a unified `ToolRegistry`.
- Thread: append-only event log capturing every step for auditability and resumability.

## Agent flow

1. Select intent (a tool name, `done`, or `clarification`).
2. Fill parameters for the selected tool.
3. Execute the tool and add a `tool_response` event.
4. Repeat until `done`.

## Thread and events

Each interaction is recorded as an event:

- `user_input`, `llm_response`, `tool_call`, `tool_response`, `clarification`, `final_response`

This enables pause/resume, reproducibility, and full observability of the agent’s decisions.

## Tool results

Tools return:

```python
ToolResult(
  llm_content: str,
  display_content: str,
  raw_result: Any,
)
```

This separates machine-optimized content for the LLM from human-friendly output.


