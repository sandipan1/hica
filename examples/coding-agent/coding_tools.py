"""
Coding Tools for the Agent

This module provides essential tools for a coding agent, inspired by the blog post
"How to Build an Agent" (https://ampcode.com/how-to-build-an-agent).

Tools include:
- File operations (read, write, list)
- Directory operations
- Shell command execution
- Code editing and analysis
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from hica.tools import ToolRegistry

registry = ToolRegistry()


@registry.tool()
def read_file(filepath: str) -> Dict[str, Any]:
    """Read the contents of a file."""
    try:
        path = Path(filepath)
        if not path.exists():
            return {"status": "error", "message": f"File not found: {filepath}"}
            
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return {
            "status": "success",
            "content": content,
            "filepath": filepath,
            "size": len(content),
            "lines": len(content.splitlines()),
            "read_at": datetime.now().isoformat(),
        }
        
    except UnicodeDecodeError:
        return {"status": "error", "message": f"Cannot read {filepath}: Binary file or unsupported encoding"}
    except Exception as e:
        return {"status": "error", "message": f"Error reading {filepath}: {str(e)}"}


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


@registry.tool()
def list_files(directory: str = ".", pattern: str = "*", show_hidden: bool = False) -> Dict[str, Any]:
    """List files and directories in the specified directory."""
    try:
        path = Path(directory)
        if not path.exists():
            return {"status": "error", "message": f"Directory not found: {directory}"}
            
        if not path.is_dir():
            return {"status": "error", "message": f"Path is not a directory: {directory}"}
            
        # Get all items matching the pattern
        items = list(path.glob(pattern))
        
        # Filter hidden files if not requested
        if not show_hidden:
            items = [item for item in items if not item.name.startswith('.')]
            
        # Sort items: directories first, then files
        items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
        
        # Prepare the listing
        file_list = []
        
        for item in items:
            if item.is_dir():
                file_list.append({
                    "name": item.name,
                    "type": "directory",
                    "path": str(item)
                })
            else:
                size = item.stat().st_size
                file_list.append({
                    "name": item.name,
                    "type": "file",
                    "path": str(item),
                    "size": size
                })
        
        return {
            "status": "success",
            "directory": directory,
            "pattern": pattern,
            "files": file_list,
            "count": len(file_list),
            "listed_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Error listing directory {directory}: {str(e)}"}


@registry.tool()
def run_command(command: str, working_dir: str = ".", timeout: int = 30) -> Dict[str, Any]:
    """Execute a shell command and return the output."""
    try:
        # Security check - prevent potentially dangerous commands
        dangerous_commands = ['rm -rf', 'del /s', 'format', 'mkfs', 'dd if=']
        if any(danger in command.lower() for danger in dangerous_commands):
            return {
                "status": "blocked",
                "message": f"Command blocked for safety: {command}"
            }
            
        # Execute the command
        result = subprocess.run(
            command,
            shell=True,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return {
            "status": "success" if result.returncode == 0 else "failed",
            "command": command,
            "working_dir": working_dir,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "executed_at": datetime.now().isoformat(),
        }
            
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "message": f"Command timed out after {timeout} seconds: {command}"
        }
    except Exception as e:
        return {"status": "error", "message": f"Error executing command: {str(e)}"}


@registry.tool()
def create_directory(directory: str) -> Dict[str, Any]:
    """Create a directory and any necessary parent directories."""
    try:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        
        return {
            "status": "success", 
            "message": f"Directory created: {directory}",
            "directory": directory,
            "created_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Error creating directory {directory}: {str(e)}"}


@registry.tool()
def find_in_files(pattern: str, directory: str = ".", file_pattern: str = "*.py") -> Dict[str, Any]:
    """Search for a pattern in files within a directory."""
    try:
        path = Path(directory)
        if not path.exists():
            return {"status": "error", "message": f"Directory not found: {directory}"}
            
        matches = []
        files_searched = 0
        
        # Search in files
        for file_path in path.glob(f"**/{file_pattern}"):
            if file_path.is_file():
                files_searched += 1
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            if pattern in line:
                                matches.append({
                                    'file': str(file_path),
                                    'line': line_num,
                                    'content': line.strip()
                                })
                except (UnicodeDecodeError, PermissionError):
                    continue  # Skip binary files or files we can't read
                    
        return {
            "status": "success",
            "pattern": pattern,
            "directory": directory,
            "file_pattern": file_pattern,
            "matches": matches,
            "match_count": len(matches),
            "files_searched": files_searched,
            "searched_at": datetime.now().isoformat(),
        }
            
    except Exception as e:
        return {"status": "error", "message": f"Error searching for pattern: {str(e)}"}


@registry.tool()
def get_file_info(filepath: str) -> Dict[str, Any]:
    """Get detailed information about a file or directory."""
    try:
        path = Path(filepath)
        if not path.exists():
            return {"status": "error", "message": f"Path not found: {filepath}"}
            
        stat = path.stat()
        
        info = {
            'name': path.name,
            'path': str(path),
            'type': 'directory' if path.is_dir() else 'file',
            'size': stat.st_size,
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'permissions': oct(stat.st_mode)[-3:],
        }
        
        if path.is_file():
            info['extension'] = path.suffix
            # Try to count lines for text files
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = sum(1 for _ in f)
                info['lines'] = lines
            except (UnicodeDecodeError, PermissionError):
                info['lines'] = 'N/A (binary file)'
                
        return {
            "status": "success",
            "info": info,
            "analyzed_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Error getting file info for {filepath}: {str(e)}"}


@registry.tool()
def create_project_structure(project_name: str, project_type: str = "python") -> Dict[str, Any]:
    """Create a basic project structure for different types of projects."""
    try:
        project_path = Path(project_name)
        
        if project_path.exists():
            return {
                "status": "error",
                "message": f"Project directory already exists: {project_name}"
            }
            
        project_path.mkdir(parents=True)
        
        files_created = []
        
        if project_type.lower() == "python":
            # Create Python project structure
            (project_path / "src").mkdir()
            (project_path / "tests").mkdir()
            (project_path / "docs").mkdir()
            
            # Create basic files
            files = {
                "README.md": f"# {project_name}\n\nA Python project.\n",
                "requirements.txt": "# Add your dependencies here\n",
                ".gitignore": "__pycache__/\n*.pyc\n.env\nvenv/\n.venv/\n",
                "src/__init__.py": "",
                "src/main.py": f'"""\nMain module for {project_name}\n"""\n\ndef main():\n    print("Hello from {project_name}!")\n\nif __name__ == "__main__":\n    main()\n',
                "tests/__init__.py": "",
                "tests/test_main.py": f'"""\nTests for {project_name}\n"""\n\nimport pytest\nfrom src.main import main\n\ndef test_main():\n    # Add your tests here\n    pass\n'
            }
            
        elif project_type.lower() == "javascript":
            # Create JavaScript/Node.js project structure
            (project_path / "src").mkdir()
            (project_path / "tests").mkdir()
            
            files = {
                "README.md": f"# {project_name}\n\nA JavaScript project.\n",
                "package.json": f'{{\n  "name": "{project_name}",\n  "version": "1.0.0",\n  "description": "",\n  "main": "src/index.js",\n  "scripts": {{\n    "start": "node src/index.js",\n    "test": "jest"\n  }},\n  "keywords": [],\n  "author": "",\n  "license": "ISC"\n}}',
                ".gitignore": "node_modules/\n.env\n*.log\n",
                "src/index.js": f'// Main file for {project_name}\nconsole.log("Hello from {project_name}!");\n',
                "tests/index.test.js": f'// Tests for {project_name}\ntest("example test", () => {{\n  expect(true).toBe(true);\n}});\n'
            }
            
        else:
            # Generic project structure
            files = {
                "README.md": f"# {project_name}\n\nA {project_type} project.\n",
                ".gitignore": "# Add ignore patterns here\n",
            }
            
        # Create all files
        for filename, content in files.items():
            file_path = project_path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            files_created.append(str(file_path))
            
        return {
            "status": "success",
            "message": f"Created {project_type} project '{project_name}' with {len(files_created)} files",
            "project_name": project_name,
            "project_type": project_type,
            "files_created": files_created,
            "file_count": len(files_created),
            "created_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error creating project {project_name}: {str(e)}"
        }


if __name__ == "__main__":
    # Test the tools
    print("Testing coding tools...")
    
    # Test file operations
    result = write_file("test.py", "print('Hello, World!')\n")
    print(f"Write test: {result['status']} - {result.get('message', '')}")
    
    result = read_file("test.py")
    print(f"Read test: {result['status']} - Content length: {result.get('size', 0)}")
    
    result = list_files(".")
    print(f"List test: {result['status']} - Found {result.get('count', 0)} items")
