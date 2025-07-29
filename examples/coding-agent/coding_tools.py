"""
Coding Tools for the Agent

Essential tools inspired by Gemini CLI, providing core file system operations,
text search, and shell execution capabilities for a coding agent.

Core tools based on Gemini CLI patterns:
- ReadFileTool: Read file contents (similar to Gemini's read-file tool)
- ListDirectoryTool: List directory contents (similar to Gemini's ls tool)
- GlobTool: Find files matching patterns (similar to Gemini's glob tool)
- GrepTool: Search for text patterns in files (similar to Gemini's grep tool)
- EditTool: Edit files with precise replacements (similar to Gemini's edit tool)
- ShellTool: Execute shell commands safely (similar to Gemini's shell tool)
- MemoryTool: Save information to long-term memory using HICA.md
"""

import os
import subprocess
import re
import ast
import shlex
import glob as glob_module
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from hica.tools import ToolRegistry, BaseTool
from hica.models import ToolResult
registry = ToolRegistry()

# Utility functions
def is_within_root(path: str, root: str) -> bool:
    """Check if a path is within the root directory (security check)."""
    try:
        path_resolved = Path(path).resolve()
        root_resolved = Path(root).resolve()
        return str(path_resolved).startswith(str(root_resolved))
    except Exception:
        return False

def validate_path_param(path: str) -> str:
    """Basic path validation."""
    if not path or not isinstance(path, str):
        raise ValueError("Path parameter must be a non-empty string")
    return path

# Default ignore patterns similar to Gemini CLI
DEFAULT_IGNORE_PATTERNS = [
    '**/node_modules/**',
    '**/.git/**',
    '**/__pycache__/**',
    '**/*.pyc',
    '**/.DS_Store',
    '**/venv/**',
    '**/.venv/**',
]


class MemoryTool(BaseTool):
    name = "memory_tool"
    description = "Save specific information or fact to long-term memory using HICA.md."

    MEMORY_SECTION_HEADER = '## HICA Added Memories'
    HICA_CONFIG_DIR = '.hica'
    DEFAULT_CONTEXT_FILENAME = 'HICA.md'

    def should_confirm(self, params: dict) -> bool:
        """Memory operations should be confirmed to prevent accidental data storage."""
        return True

    def get_confirmation_prompt(self, params: dict) -> str:
        """Return a human-readable confirmation prompt for memory operations."""
        fact = params.get('fact', 'unknown')
        return f"💾 Save to memory: '{fact[:100]}{'...' if len(fact) > 100 else ''}' - Confirm?"

    async def execute(self, fact: str) -> ToolResult:
        if not fact.strip():
            return ToolResult(llm_content="", display_content="Error: Fact is empty.", raw_result={"status": "error", "message": "Fact is empty."})

        try:
            # Use current working directory instead of home directory
            memory_file_path = Path.cwd() / self.HICA_CONFIG_DIR / self.DEFAULT_CONTEXT_FILENAME 
            memory_file_path.parent.mkdir(parents=True, exist_ok=True)

            content = ""
            if memory_file_path.exists():
                with open(memory_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

            header_index = content.find(self.MEMORY_SECTION_HEADER)
            separator = '\n\n' if content and not content.endswith('\n\n') else '\n'

            if header_index == -1:
                content += f"{separator}{self.MEMORY_SECTION_HEADER}\n- {fact.strip()}\n"
            else:
                start_of_section = header_index + len(self.MEMORY_SECTION_HEADER)
                end_of_section = content.find('\n## ', start_of_section)
                end_of_section = end_of_section if end_of_section != -1 else len(content)

                before_section = content[:start_of_section].rstrip()
                section_content = content[start_of_section:end_of_section].strip()
                after_section = content[end_of_section:].lstrip()

                section_content += f"\n- {fact.strip()}"
                content = f"{before_section}\n{section_content}\n{after_section}".strip() + '\n'

            with open(memory_file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return ToolResult(
                llm_content=f"I've saved the memory: \"{fact}\"",
                display_content=f"Memory saved: {fact}",
                raw_result={"status": "success", "message": f"Memory saved: {fact}"}
            )

        except Exception as e:
            return ToolResult(llm_content="", display_content=f"Error saving memory: {str(e)}", raw_result={"status": "error", "message": str(e)})


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read the contents of a file."

    async def execute(self, filepath: str) -> ToolResult:
        try:
            path = Path(filepath)
            if not path.exists():
                return ToolResult(llm_content='', display_content='', raw_result={"status": "error", "message": f"File not found: {filepath}"})

            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            result = {
                "status": "success",
                "content": content,
                "filepath": filepath,
                "size": len(content),
                "lines": len(content.splitlines()),
                "read_at": datetime.now().isoformat(),
            }
            return ToolResult(llm_content=content[:100], display_content=content[:200], raw_result=result)

        except UnicodeDecodeError:
            return ToolResult(llm_content='', display_content='', raw_result={"status": "error", "message": f"Cannot read {filepath}: Binary file or unsupported encoding"})
        except Exception as e:
            return ToolResult(llm_content='', display_content='', raw_result={"status": "error", "message": f"Error reading {filepath}: {str(e)}"})


class ShellTool(BaseTool):
    name = "shell"
    description = "Execute shell commands with safety checks and confirmation for dangerous operations."
    
    DANGEROUS_COMMANDS = [
        'rm -rf', 'del /s', 'format', 'mkfs', 'dd if=', 'sudo rm', 
        'chmod -R', 'chown -R', '> /dev/', 'curl | sh', 'wget | sh'
    ]
    
    def should_confirm(self, params: dict) -> bool:
        """Check if command requires confirmation."""
        command = params.get('command', '')
        return any(danger in command.lower() for danger in self.DANGEROUS_COMMANDS)
    
    def get_confirmation_prompt(self, params: dict) -> str:
        """Get confirmation prompt for dangerous commands."""
        command = params.get('command', '')
        return f"⚠️  Warning: Execute potentially dangerous command '{command}'?"
    
    async def execute(self, command: str, working_dir: str = ".", timeout: int = 30) -> ToolResult:
        try:
            # Execute the command
            result = subprocess.run(
                shlex.split(command) if not command.startswith('cd ') else command,
                shell=command.startswith('cd '),
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            raw_result = {
                "status": "success" if result.returncode == 0 else "failed",
                "command": command,
                "working_dir": working_dir,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "executed_at": datetime.now().isoformat(),
            }
            
            # Create appropriate display content
            display_parts = []
            if result.stdout:
                display_parts.append(f"stdout:\n{result.stdout}")
            if result.stderr:
                display_parts.append(f"stderr:\n{result.stderr}")
            if result.returncode != 0:
                display_parts.append(f"Exit code: {result.returncode}")
            
            display_content = "\n\n".join(display_parts) if display_parts else "Command executed successfully (no output)"
            llm_content = result.stdout[:500] if result.stdout else f"Command executed with exit code {result.returncode}"
            
            return ToolResult(
                llm_content=llm_content,
                display_content=display_content,
                raw_result=raw_result
            )
                
        except subprocess.TimeoutExpired:
            raw_result = {
                "status": "timeout",
                "message": f"Command timed out after {timeout} seconds: {command}"
            }
            return ToolResult(
                llm_content="Command timed out",
                display_content=f"❌ Command timed out after {timeout} seconds",
                raw_result=raw_result
            )
        except Exception as e:
            raw_result = {"status": "error", "message": f"Error executing command: {str(e)}"}
            return ToolResult(
                llm_content="Command failed",
                display_content=f"❌ Error: {str(e)}",
                raw_result=raw_result
            )


class WriteFileTool(BaseTool):
    name = "write_file_tool"
    description = "Write content to a file, creating directories if needed. Requires confirmation for safety."

    def should_confirm(self, params: dict) -> bool:
        """File write operations should be confirmed to prevent accidental overwrites."""
        return True

    def get_confirmation_prompt(self, params: dict) -> str:
        """Return a human-readable confirmation prompt for file write operations."""
        filepath = params.get('filepath', 'unknown')
        content = params.get('content', '')
        content_preview = content[:50] + '...' if len(content) > 50 else content
        file_exists = Path(filepath).exists()
        action = "Overwrite" if file_exists else "Create"
        return f"📝 {action} file '{filepath}' with content: '{content_preview}' - Confirm?"

    async def execute(self, filepath: str, content: str, create_dirs: bool = True) -> ToolResult:
        try:
            path = Path(filepath)
            
            if create_dirs:
                path.parent.mkdir(parents=True, exist_ok=True)
                
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            result = {
                "status": "success",
                "message": f"File written successfully: {filepath}",
                "filepath": filepath,
                "size": len(content),
                "lines": len(content.splitlines()),
                "created_at": datetime.now().isoformat(),
            }
            
            return ToolResult(
                llm_content=f"Successfully wrote {len(content)} characters to {filepath}",
                display_content=f"✅ File written: {filepath} ({len(content)} chars, {len(content.splitlines())} lines)",
                raw_result=result
            )
            
        except Exception as e:
            error_result = {"status": "error", "message": f"Error writing to {filepath}: {str(e)}"}
            return ToolResult(
                llm_content=f"Failed to write file: {str(e)}",
                display_content=f"❌ Error writing {filepath}: {str(e)}",
                raw_result=error_result
            )


class EditFileTool(BaseTool):
    name = "edit_file_tool"
    description = "Edit specific lines in a file by replacing content between start and end line numbers."

    def should_confirm(self, params: dict) -> bool:
        """File edit operations should be confirmed to prevent accidental changes."""
        return True

    def get_confirmation_prompt(self, params: dict) -> str:
        """Return a human-readable confirmation prompt for file edit operations."""
        filepath = params.get('filepath', 'unknown')
        start_line = params.get('start_line', 0)
        end_line = params.get('end_line', 0)
        new_content = params.get('new_content', '')
        content_preview = new_content[:50] + '...' if len(new_content) > 50 else new_content
        return f"✏️ Edit {filepath} lines {start_line}-{end_line} with: '{content_preview}' - Confirm?"

    async def execute(self, filepath: str, start_line: int, end_line: int, new_content: str) -> ToolResult:
        try:
            path = Path(filepath)
            if not path.exists():
                error_result = {"status": "error", "message": f"File not found: {filepath}"}
                return ToolResult(
                    llm_content="File not found",
                    display_content=f"❌ File not found: {filepath}",
                    raw_result=error_result
                )
                
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            total_lines = len(lines)
            start_idx = max(0, start_line - 1)
            end_idx = min(total_lines, end_line)
            
            # Preserve original content before and after the edit section
            before_section = lines[:start_idx]
            after_section = lines[end_idx:]
            
            # Ensure new content ends with newline if it doesn't already
            if new_content and not new_content.endswith('\n'):
                new_content += '\n'
                
            # Combine all sections
            new_lines = before_section + [new_content] + after_section
            
            with open(path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
                
            result = {
                "status": "success",
                "message": f"Edited lines {start_line}-{end_line} in {filepath}",
                "filepath": filepath,
                "lines_replaced": end_line - start_line + 1,
                "new_total_lines": len(new_lines),
                "edited_at": datetime.now().isoformat(),
            }
            
            return ToolResult(
                llm_content=f"Successfully edited {filepath} lines {start_line}-{end_line}",
                display_content=f"✅ Edited {filepath}: replaced {end_line - start_line + 1} lines",
                raw_result=result
            )
            
        except Exception as e:
            error_result = {"status": "error", "message": f"Error editing {filepath}: {str(e)}"}
            return ToolResult(
                llm_content=f"Failed to edit file: {str(e)}",
                display_content=f"❌ Error editing {filepath}: {str(e)}",
                raw_result=error_result
            )


# Register the tools
registry.add_tool(MemoryTool())
registry.add_tool(ReadFileTool())
registry.add_tool(ShellTool())
registry.add_tool(WriteFileTool())
registry.add_tool(EditFileTool())


@registry.tool()
def save_memory(fact: str) -> Dict[str, Any]:
    """Save a specific piece of information or fact to long-term memory in HICA.md."""
    try:
        if not fact.strip():
            return {"status": "error", "message": "Fact is empty."}

        MEMORY_SECTION_HEADER = '## HICA Added Memories'
        HICA_CONFIG_DIR = '.hica'
        DEFAULT_CONTEXT_FILENAME = 'HICA.md'
        
        memory_file_path = Path.cwd() / HICA_CONFIG_DIR / DEFAULT_CONTEXT_FILENAME 
        memory_file_path.parent.mkdir(parents=True, exist_ok=True)

        content = ""
        if memory_file_path.exists():
            with open(memory_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

        header_index = content.find(MEMORY_SECTION_HEADER)
        separator = '\n\n' if content and not content.endswith('\n\n') else '\n'

        if header_index == -1:
            content += f"{separator}{MEMORY_SECTION_HEADER}\n- {fact.strip()}\n"
        else:
            start_of_section = header_index + len(MEMORY_SECTION_HEADER)
            end_of_section = content.find('\n## ', start_of_section)
            end_of_section = end_of_section if end_of_section != -1 else len(content)

            before_section = content[:start_of_section].rstrip()
            section_content = content[start_of_section:end_of_section].strip()
            after_section = content[end_of_section:].lstrip()

            section_content += f"\n- {fact.strip()}"
            content = f"{before_section}\n{section_content}\n{after_section}".strip() + '\n'

        with open(memory_file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return {
            "status": "success",
            "message": f"Memory saved: {fact}",
            "fact": fact,
            "saved_at": datetime.now().isoformat(),
        }

    except Exception as e:
        return {"status": "error", "message": f"Error saving memory: {str(e)}"}


@registry.tool()
def write_file(filepath: str, content: str, create_dirs: bool = True) -> Dict[str, Any]:
    """Write content to a file, creating directories if needed."""
    try:
        path = Path(filepath)
        
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)
            
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return {
            "status": "success",
            "message": f"File written successfully: {filepath}",
            "filepath": filepath,
            "size": len(content),
            "lines": len(content.splitlines()),
            "created_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Error writing to {filepath}: {str(e)}"}


if __name__ == "__main__":
    import asyncio
    
    async def test_tools():
        """Test the enhanced tools"""
        print("Testing enhanced coding tools...")
        
        # Test memory tool
        result = await registry.execute_tool('save_memory', {'fact': 'User prefers .hica directory instead of .gemini'})
        print(f"Memory test: {result.raw_result['status']} - {result.raw_result.get('message', '')}")
        
        # Test file operations using registry
        result = await registry.execute_tool('write_file', {
            'filepath': 'test.py',
            'content': "print('Hello, World!')\n"
        })
        print(f"Write test: {result.raw_result['status']} - {result.raw_result.get('message', '')}")
        
        # Test the enhanced ReadFileTool
        result = await registry.execute_tool('read_file', {'filepath': 'test.py'})
        print(f"Enhanced read test: {result.raw_result['status']} - Content length: {result.raw_result.get('size', 0)}")
        
        # Test ShellTool with a safe command
        result = await registry.execute_tool('shell', {'command': 'echo "Hello from shell"'})
        print(f"Shell test: {result.raw_result['status']} - {result.llm_content}")
        
        print("\n✅ Core tools tested successfully!")

    # Run the async test
    asyncio.run(test_tools())
