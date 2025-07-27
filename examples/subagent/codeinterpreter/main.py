import asyncio
import json

from tools import CodeInterpreterTool

from hica import Agent, AgentConfig, Thread, ToolRegistry
from hica.memory import ConversationMemoryStore


async def main():
    # The conversation memory store
    memory = ConversationMemoryStore(context_dir="examples/subagent/codeinterpreter/context")

    # The main thread for the primary agent
    main_thread = Thread()
    main_thread.add_event(
        type="user_input",
        data="Please generate the SHA256 hash for the string 'hica-subagent-test-string-12345'.Then calculate square root of 32",
    )
    memory.set(main_thread)

    # The main agent's tool registry
    main_tool_registry = ToolRegistry()

    # Instantiate and register the new BaseTool
    code_interpreter_tool = CodeInterpreterTool(memory=memory)
    main_tool_registry.add_tool(code_interpreter_tool)

    # Configure and initialize the main agent
    main_agent_config = AgentConfig(
        model="openai/gpt-4.1-mini",
        system_prompt="You are a helpful assistant. You can delegate complex code-related tasks to a specialized code interpreter agent.",
    )
    main_agent = Agent(config=main_agent_config, tool_registry=main_tool_registry)

    print("--- Starting Main Agent Loop ---")

    # Run the main agent loop
    async for thread_state in main_agent.agent_loop(thread=main_thread):
        memory.set(thread_state)  # Save state after each step
        last_event = thread_state.events[-1]
        print(
            f"Event: {last_event.type}, Step: {last_event.step}, Data: {last_event.data}"
        )
        print("-" * 20)

    print("\n--- Main Agent Loop Finished ---")
    final_response = main_thread.events[-1].data
    print("\nFinal Response from Main Agent:")
    print(final_response)

    # --- Verification ---
    print("\n--- Verifying Thread Linkage in Memory ---")
    # Retrieve the main thread from memory
    retrieved_main_thread = memory.get(main_thread.thread_id)

    # Find the tool_call event to get the sub-agent's thread ID
    sub_agent_thread_id = None
    for event in retrieved_main_thread.events:
        if (
            event.type == "tool_response"
            and isinstance(event.data, dict)
            and "response" in event.data
            and isinstance(event.data["response"], dict)
            and "raw_result" in event.data["response"]
            and isinstance(event.data["response"]["raw_result"], dict)
            and "sub_agent_thread_id" in event.data["response"]["raw_result"]
        ):
            sub_agent_thread_id = event.data["response"]["raw_result"][
                "sub_agent_thread_id"
            ]
            break

    if sub_agent_thread_id:
        print(
            f"Main thread ({main_thread.thread_id}) is linked to sub-agent thread ({sub_agent_thread_id})"
        )
        retrieved_sub_agent_thread = memory.get(sub_agent_thread_id)
        print("\n--- Main Thread ---")
        print(json.dumps(retrieved_main_thread.model_dump(), indent=2))
        print("\n--- Sub-Agent Thread ---")
        print(json.dumps(retrieved_sub_agent_thread.model_dump(), indent=2))
    else:
        print(
            "Could not find a linked sub-agent thread in the main thread's tool_response event."
        )


if __name__ == "__main__":
    asyncio.run(main())
