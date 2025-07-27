import asyncio

from dotenv import load_dotenv

load_dotenv()

from tools import FileManipulationTool

from hica import Agent, AgentConfig, Thread, ToolRegistry
from hica.memory import ConversationMemoryStore


async def main():
    """
    An example of a multi-step file manipulation task using a bash sub-agent.
    """
    # The conversation memory store
    memory = ConversationMemoryStore(
        backend_type="file", context_dir="examples/subagent/filemanipulation/context"
    )

    # The main thread for the primary agent
    main_thread = Thread()
    main_thread.add_event(
        type="user_input",
        data="Create a directory named work_dir, and then create a file inside it named 'new.txt' with the content 'This is a test anabelle' .List content of that dir",
    )
    memory.set(main_thread)

    # The main agent's tool registry
    main_tool_registry = ToolRegistry()

    # Instantiate and register the new BaseTool
    subagent_tool = FileManipulationTool(memory=memory)
    main_tool_registry.add_tool(subagent_tool)

    # Configure and initialize the main agent
    main_agent_config = AgentConfig(
        model="openai/gpt-4.1-mini",
        system_prompt="You are a helpful assistant. You delegate bash command tasks to a specialized sub-agent.",
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


if __name__ == "__main__":
    asyncio.run(main())

