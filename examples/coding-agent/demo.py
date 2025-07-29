"""
Demo script for the Coding Agent

This script demonstrates the coding agent's capabilities in a non-interactive way,
perfect for testing and showcasing features.
"""

import asyncio
import os
from pathlib import Path

from coding_tools import registry as coding_registry

from hica import Agent, AgentConfig, Thread
from hica.memory import ConversationMemoryStore


async def run_demo_task(agent, store, task_description, user_input):
    """Run a single demonstration task."""
    print(f"\n{'='*60}")
    print(f"🎯 Task: {task_description}")
    print(f"💬 Input: {user_input}")
    print("="*60)
    
    # Create a new thread for this task
    thread = Thread()
    thread.add_event(type="user_input", data=user_input)
    
    # Run the agent
    print("🤖 Agent working...")
    async for event in agent.agent_loop(thread):
        # Show tool usage in real-time
        if hasattr(event, 'type'):
            if event.type == "tool_call":
                tool_name = event.data.get('tool_name', 'unknown')
                print(f"   🔧 Using tool: {tool_name}")
    
    # Save and display result
    store.set(thread)
    
    # Find the final response
    final_events = [e for e in thread.events if e.type == "agent_response"]
    if final_events:
        final_response = final_events[-1].data
        print(f"✅ Result: {final_response}")
    
    return thread


async def main():
    """Run the complete demo."""
    print("🚀 HICA Coding Agent Demo")
    print("Inspired by 'How to Build an Agent' blog post")
    print("https://ampcode.com/how-to-build-an-agent")
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Please set OPENAI_API_KEY environment variable")
        print("   export OPENAI_API_KEY=your_key_here")
        return
    
    # Set up the agent
    config = AgentConfig(
        model="openai/gpt-4.1-mini",
        system_prompt=(
            "You are a helpful coding agent. You can read, write, and modify files, "
            "execute shell commands, and help with programming tasks. "
            "Be concise but informative in your responses. "
            "Always use the appropriate tools for each task."
        ),
        temperature=0.1,
    )
    
    agent = Agent(config=config, tool_registry=coding_registry)
    
    # Set up storage
    context_dir = Path("demo_context")
    context_dir.mkdir(exist_ok=True)
    store = ConversationMemoryStore(backend_type="file", context_dir=str(context_dir))
    
    # Demo tasks
    demo_tasks = [
        (
            "Create a simple Python script",
            "Create a Python script called 'hello.py' that prints 'Hello from HICA Agent!'"
        ),
        (
            "List directory contents",
            "Show me what files are in the current directory"
        ),
        (
            "Read the created file",
            "Show me the contents of hello.py"
        ),
        (
            "Create a project structure",
            "Create a new Python project called 'demo-project' with basic structure"
        ),
        (
            "Search for Python files",
            "Find all Python files in the current directory and show their basic info"
        ),
        (
            "Execute a safe command",
            "Run 'python hello.py' to test our script"
        ),
        (
            "Create a more complex file",
            "Create a Python calculator script with functions for add, subtract, multiply, and divide"
        ),
        (
            "Search within files",
            "Search for the word 'def' in all Python files to find function definitions"
        )
    ]
    
    # Run all demo tasks
    threads = []
    for task_description, user_input in demo_tasks:
        try:
            thread = await run_demo_task(agent, store, task_description, user_input)
            threads.append(thread)
            await asyncio.sleep(1)  # Brief pause between tasks
        except Exception as e:
            print(f"❌ Error in task '{task_description}': {e}")
            continue
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 Demo Summary")
    print("="*60)
    print(f"✅ Completed {len(threads)} tasks successfully")
    print(f"📁 All conversation threads saved to: {context_dir}")
    print("🎉 Demo finished!")
    
    # Show created files
    print("\n📂 Files created during demo:")
    current_dir = Path(".")
    for item in current_dir.iterdir():
        if item.is_file() and item.name.endswith(('.py', '.txt', '.md')):
            print(f"   📄 {item.name}")
        elif item.is_dir() and item.name.startswith('demo'):
            print(f"   📁 {item.name}/")
            # Show contents of demo directories
            for subitem in item.rglob('*'):
                if subitem.is_file():
                    rel_path = subitem.relative_to(item)
                    print(f"      📄 {rel_path}")


if __name__ == "__main__":
    asyncio.run(main())
