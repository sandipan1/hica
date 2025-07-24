# Sub-Agent Thread Management Architecture

This document outlines the architectural approach for managing and tracing tasks delegated from a main agent to one or more sub-agents.

## 1. Guiding Principles

The architecture is founded on three core principles:

- **Traceability:** Every task must be fully traceable from the main agent to a sub-agent and back. It should be straightforward to identify all sub-agent threads spawned by a given main thread.
- **Atomicity:** Each agent interaction, or "turn," is treated as a transaction. The state of any given thread must be saved consistently in the memory store to ensure data integrity.
- **Scalability:** The design must be robust enough to support multiple sub-agents being called from a single main thread. It also accommodates nested hierarchies, where a sub-agent can delegate tasks to other sub-agents.

---

## 2. Proposed Architecture: Linking Threads via Events

To ensure a robust and traceable link between agents, the sub-agent's `thread_id` is embedded directly into the event on the main thread that triggers its execution.

### 2.1. Central `ConversationMemoryStore`

A single `ConversationMemoryStore` instance serves as the centralized, authoritative source of truth for all agent threads within the system.

### 2.2. The "Foreign Key": `sub_agent_thread_id`

When the main agent invokes a sub-agent tool, the `SubAgentTool` orchestrates the linkage:

1.  A new `Thread` object is instantiated for the sub-agent.
2.  This new sub-agent thread is immediately saved to the `ConversationMemoryStore`.
3.  A `tool_call` event is created and added to the *main thread*. The `data` payload of this event contains the standard `intent` and `arguments`, along with a `sub_agent_thread_id` key.

This event-based linkage is superior to using the main thread's top-level `metadata` because it directly associates the sub-agent with the specific task it was invoked for. This ensures that even if a main thread calls multiple sub-agents, each invocation remains uniquely traceable.

---

## 3. Interaction and Storage Flow

The following diagram illustrates the step-by-step flow of how threads are created, linked, and stored.

```
+---------------------------+         +--------------------------+        +-----------------------------+
| Main Agent                |         | SubAgentTool             |        | ConversationMemoryStore     |
+---------------------------+         +--------------------------+        +-----------------------------+
           |                                  |                                 |
           | 1. Decides to delegate           |                                 |
           | (selects a sub-agent tool)       |                                 |
           |--------------------------------->|                                 |
           |                                  | 2. Create Sub-Agent Thread      |
           |                                  |    (sub_thread_id = 'xyz')      |
           |                                  |-------------------------------->| 3. memory.set(sub_thread)
           |                                  |                                 | (Save empty sub-thread)
           |                                  | 4. Add event to *main thread*:  |
           |                                  |    event.type = 'tool_call'     |
           |                                  |    event.data = {               |
           |                                  |      'intent': '...',           |
           |                                  |      'sub_agent_thread_id': 'xyz'|
           |                                  |    }                            |
           |<---------------------------------|                                 |
           |                                  |                                 |
           | 5. Main agent loop saves         |                                 |
           |    its updated state.            |                                 |
           |------------------------------------------------------------------>| 6. memory.set(main_thread)
           |                                  |                                 |
           |                                  | 7. Sub-agent runs its loop,     |
           |                                  |    updating its own thread.     |
           |                                  |-------------------------------->| 8. memory.set(sub_thread)
           |                                  |    (repeatedly)                 |
           |                                  |                                 |
           |                                  | 9. Sub-agent finishes, returns  |
           |                                  |    result to main agent.        |
           |<---------------------------------|                                 |
           |                                  |                                 |
           | 10. Main agent adds              |                                 |
           |     'tool_response' event.       |                                 |
           |------------------------------------------------------------------>| 11. memory.set(main_thread)
           |                                  |                                 |
```

---

## 4. Implementation Plan

The following outlines the concrete implementation steps:

### 4.1. Sub-Agent Tool Implementation

- The sub-agent tool method will orchestrate the process.
- It will accept the `memory` store as an argument.
- **Steps 2 & 3:** It will create a `Thread()` for the sub-agent and immediately persist it by calling `memory.set(sub_agent_thread)`.
- **Step 4:** It will add a `tool_call` event to the main thread via `self.main_agent_thread.add_event()`. The event's `data` will include the `intent`, `arguments`, and the crucial `sub_agent_thread_id`.
- **Steps 7 & 8:** As the sub-agent executes its loop, the tool will call `memory.set(sub_agent_thread)` after each step to persist its state.

### 4.2. Main Agent Implementation

- Instantiate the `ConversationMemoryStore` at the application's start.
- Pass the `memory` instance when creating the sub-agent tool.
- Within the main agent's loop, call `memory.set(thread_state)` after each iteration to save the main thread's progress.
- After the loop completes, implement verification logic to:
    - Fetch the final main thread from the store.
    - Find the `tool_call` event and extract the `sub_agent_thread_id`.
    - Use the ID to fetch the completed sub-agent thread.
    - Print both threads to confirm the successful linkage and storage.