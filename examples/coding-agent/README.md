# Coding Agent Example

This example demonstrates a simple yet powerful coding agent built with HICA, inspired by the blog post ["How to Build an Agent"](https://ampcode.com/how-to-build-an-agent) by Thorsten Ball.

## Overview

The coding agent can:
- 📄 Read and write files
- 📂 List directory contents
- ⚡ Execute shell commands safely
- 🔍 Search for patterns in files
- 📊 Analyze file information
- 🏗️ Create project structures
- 🔧 Perform various coding tasks

## Features

### Core Philosophy
Just like in the blog post, this agent demonstrates that building a powerful coding assistant doesn't require complex architectures - it's **"an LLM, a loop, and enough tokens"** plus some well-designed tools.

### Tools Available

1. **File Operations**
   - `read_file()` - Read file contents
   - `write_file()` - Write content to files
   - `get_file_info()` - Get detailed file information

2. **Directory Operations**
   - `list_files()` - List directory contents
   - `create_directory()` - Create directories

3. **Search & Analysis**
   - `find_in_files()` - Search for patterns in files
   - Pattern matching with file type filtering

4. **Command Execution**
   - `run_command()` - Execute shell commands safely
   - Built-in safety checks for dangerous commands
   - Timeout protection

5. **Project Management**
   - `create_project_structure()` - Generate project scaffolding
   - Support for Python, JavaScript, and generic projects

### Key Design Principles

Following the blog post's approach:

1. **Simple but Powerful**: Each tool does one thing well
2. **Safety First**: Commands are checked for dangerous operations
3. **Rich Feedback**: Tools return both machine-readable and human-friendly content
4. **Autonomous Decision Making**: The agent decides which tools to use based on the user's request

## Setup

1. **Install Dependencies**
   ```bash
   pip install hica
   ```

2. **Set API Key**
   ```bash
   export OPENAI_API_KEY=your_key_here
   ```

3. **Run the Agent**
   ```bash
   cd examples/coding-agent
   python main.py
   ```

## Example Interactions

### File Operations
```
🧑‍💻 You: Create a Python script that prints hello world
🤖 Agent: I'll create a Python script for you...
   🔧 Using tool: write_file
✅ File written: hello.py (42 chars, 1 lines)
```

### Project Creation
```
🧑‍💻 You: Create a new Python project called "my-calculator"
🤖 Agent: I'll create a Python project structure for you...
   🔧 Using tool: create_project_structure
✅ Project created: my-calculator (python)
📁 Created 7 files
```

### Code Analysis
```
🧑‍💻 You: What's in the current directory?
🤖 Agent: Let me list the contents of the current directory...
   🔧 Using tool: list_files
📂 Directory: .
📁 coding_context/
📄 coding_tools.py (15234 bytes)
📄 main.py (4567 bytes)
📄 README.md (3456 bytes)
```

### Search Operations
```
🧑‍💻 You: Find all Python files that import 'os'
🤖 Agent: I'll search for Python files containing 'import os'...
   🔧 Using tool: find_in_files
🔍 Search results: 2 matches for import os in 3 files
main.py:8 import os
coding_tools.py:12 import os
```

## Architecture

The agent follows the simple but effective pattern from the blog post:

```python
# 1. The heartbeat loop
while True:
    user_input = get_user_input()
    thread.add_event("user_input", user_input)
    
    # 2. LLM decides what to do
    async for event in agent.agent_loop(thread):
        # 3. Tools are executed automatically
        # 4. Results feed back to the LLM
        pass
    
    # 5. Response is displayed
    display_response(thread)
```

## Tool Design

Each tool follows HICA's `ToolResult` pattern:

```python
@registry.tool()
def example_tool(parameter: str) -> ToolResult:
    try:
        # Do the work
        result = do_something(parameter)
        
        return ToolResult(
            llm_content="Clean data for the LLM",
            display_content="🎉 **Rich display** for humans"
        )
    except Exception as e:
        return ToolResult(
            llm_content=f"Error: {str(e)}",
            display_content=f"❌ **Error:** {str(e)}"
        )
```

## Safety Features

- **Command Safety**: Dangerous commands are blocked
- **File Safety**: Path validation and error handling
- **Timeout Protection**: Commands can't run indefinitely
- **Error Handling**: Graceful error recovery
- **Permission Checks**: Proper file permission handling

## Extensibility

Adding new tools is simple:

```python
@registry.tool()
def my_new_tool(param: str) -> ToolResult:
    """Description of what this tool does."""
    # Implementation here
    return ToolResult(llm_content="...", display_content="...")
```

## Inspiration

This example is directly inspired by the blog post ["How to Build an Agent"](https://ampcode.com/how-to-build-an-agent), which demonstrates that:

> "It's not that hard to build a fully functioning, code-editing agent... There isn't [a secret]. It's an LLM, a loop, and enough tokens."

The HICA framework makes this even easier by providing:
- Structured tool management
- Event-sourced conversation history
- Rich tool result handling
- Built-in safety and observability

## Next Steps

Try extending this agent with:
- Git integration tools
- Code formatting tools
- Testing and linting tools
- Docker container management
- Database interaction tools
- Web scraping capabilities

The possibilities are endless - just add more tools to the registry!
