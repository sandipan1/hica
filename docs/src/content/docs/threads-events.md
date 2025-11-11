---
title: Threads & Events
---

A `Thread` holds an append-only list of events. This acts as a durable audit log and working memory.

### Common event types

- `user_input`: end-user message or instruction.
- `llm_response`: the agent’s model output for routing or parameter filling.
- `tool_call`: intent plus arguments selected by the agent.
- `clarification`: agent requests confirmation or missing info and pauses.
- `tool_response`: result returned by a tool.
- `final_response`: the agent’s final answer.

### Pause and resume

When a tool needs confirmation, the agent stores `pending_confirmation` in thread context and emits a `clarification`. Append a new `user_input` and resume the `agent_loop` to continue.

### Context helpers

`thread.set_context(key, value)`, `thread.get_context(key)`, `thread.remove_context(key)` let you stash ephemeral state (like pending confirmations).


