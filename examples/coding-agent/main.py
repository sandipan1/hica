"""
Coding Agent Example - Inspired by "How to Build an Agent" blog post

This example demonstrates a simple yet powerful coding agent built with HICA that can:
- Read and write files
- List directory contents  
- Execute shell commands
- Edit code files
- Create new projects

Based on the blog post at https://ampcode.com/how-to-build-an-agent
"""

import asyncio
import os
from pathlib import Path

from coding_tools import registry as coding_registry

from hica import Agent, AgentConfig, Thread
from hica.logging import get_thread_logger
from hica.memory import ConversationMemoryStore


async def main():
    """Main function to run the coding agent."""
    
    # Ensure we have the required API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Please set OPENAI_API_KEY environment variable")
        print("   export OPENAI_API_KEY=your_key_here")
        return
    
    # Configure the agent
    config = AgentConfig(
        model="openai/gpt-4.1-mini",
        system_prompt=(
            "You are a helpful coding agent. You can read, write, and modify files, "
            "execute shell commands, and help with programming tasks. "
            "\n\n"
            "When working with files:\n"
            "- Always read a file before editing it to understand its current state\n"
            "- Be careful with file operations and explain what you're doing\n"
            "- Use appropriate tools for each task (read_file, write_file, list_files, etc.)\n"
            "\n"
            "When executing commands:\n"
            "- Explain what commands you're running and why\n"
            "- Be cautious with destructive operations\n"
            "- Always check if files exist before trying to read them\n"
            "\n"
            "You should be autonomous but ask for clarification when:\n"
            "- The user's request is ambiguous\n"
            "- You need to perform potentially destructive operations\n"
            "- You need additional information to complete a task"
        ),
        temperature=0.1,  # Lower temperature for more consistent code generation
    )

    # Create agent with coding tools
    agent = Agent(
        config=config,
        tool_registry=coding_registry,
    )

    # Set up conversation storage
    context_dir = Path("coding_context")
    context_dir.mkdir(exist_ok=True)
    store = ConversationMemoryStore(backend_type="file", context_dir=str(context_dir))

    print("🤖 Coding Agent Ready!")
    print("=" * 50)
    print("I can help you with:")
    print("• Reading and writing files")
    print("• Listing directory contents")
    print("• Executing shell commands")
    print("• Creating and editing code")
    print("• Setting up new projects")
    print("=" * 50)
    print("Type 'quit' or 'exit' to stop the agent")
    print()

    # Initialize a single thread for the entire session
    thread = Thread()

    while True:
        try:
            # Get user input
            user_input = input("🧑‍💻 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
                
            if not user_input:
                continue

            # Process the user input in a loop to handle clarifications
            while True:
                # Add user input to the existing thread
                thread.add_event(type="user_input", data=user_input)
                
                # Get thread-specific logger
                logger = get_thread_logger(thread.thread_id, {"user": "coding_session"})
                logger.info("Processing request", user_input=user_input)

                print(f"🤖 Agent: Working on your request...")
                
                # Run the agent loop
                async for event in agent.agent_loop(thread):
                    # Real-time event streaming
                    if hasattr(event, 'type'):
                        if event.type == "tool_call":
                            tool_name = event.data.get('tool_name', 'unknown')
                            print(f"   🔧 Using tool: {tool_name}")

                # Check if the agent needs clarification by examining the last event
                last_event = thread.events[-1] if thread.events else None
                if last_event and last_event.type == "agent_response":
                    final_response = last_event.data
                    
                    # Check if it's a clarification request
                    if isinstance(final_response, dict) and final_response.get('intent') == 'clarification':
                        clarification_message = final_response.get('message', 'Need clarification')
                        print(f"❓ Agent needs clarification: {clarification_message}")
                        
                        # Get clarification from user
                        user_input = input("🧑‍💻 You: ").strip()
                        if not user_input:
                            print("No clarification provided, moving to next request.")
                            break
                        # Continue the while loop to process the clarification
                        continue
                    else:
                        # Regular response - display it and break the clarification loop
                        if isinstance(final_response, dict):
                            message = final_response.get('message', str(final_response))
                        else:
                            message = str(final_response)
                        print(f"🤖 Agent: {message}")
                        break
                else:
                    # No valid response found
                    print("🤖 Agent: Task completed.")
                    break
            
            # Save the thread after processing is complete
            store.set(thread)
            
            print()  # Add spacing between interactions
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            continue


if __name__ == "__main__":
    asyncio.run(main())
