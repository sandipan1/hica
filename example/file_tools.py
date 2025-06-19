import base64
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict

from hica.tools import ToolRegistry

registry = ToolRegistry()


@registry.tool()
def create_file(filepath: str, content: str) -> Dict[str, str]:
    """Create a new file with the specified content."""
    try:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "status": "success",
            "message": f"File created successfully: {filepath}",
            "file_size": len(content),
            "created_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@registry.tool()
def read_file(filepath: str) -> Dict[str, str]:
    """Read and return the contents of a file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        return {
            "status": "success",
            "content": content,
            "file_size": len(content),
            "lines": len(content.splitlines()),
            "read_at": datetime.now().isoformat(),
        }
    except FileNotFoundError:
        return {"status": "error", "message": f"File not found: {filepath}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@registry.tool()
def analyze_text(filepath: str) -> Dict[str, any]:
    """Analyze text content of a file and return statistics."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.splitlines()
        words = re.findall(r"\b\w+\b", content.lower())

        # Count word frequency
        word_freq = {}
        for word in words:
            if len(word) > 2:  # Skip very short words
                word_freq[word] = word_freq.get(word, 0) + 1

        # Get top 10 most common words
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "status": "success",
            "file_path": filepath,
            "total_characters": len(content),
            "total_lines": len(lines),
            "total_words": len(words),
            "unique_words": len(set(words)),
            "average_line_length": len(content) / len(lines) if lines else 0,
            "top_words": dict(top_words),
            "analyzed_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@registry.tool()
def encrypt_file(filepath: str, password: str) -> Dict[str, str]:
    """Encrypt a file's content using a simple base64 + password hash method."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Create a simple encryption (for demo purposes)
        salt = hashlib.sha256(password.encode()).hexdigest()[:8]
        encrypted_content = base64.b64encode((content + salt).encode()).decode()

        # Save encrypted content
        encrypted_path = f"{filepath}.encrypted"
        with open(encrypted_path, "w") as f:
            f.write(encrypted_content)

        return {
            "status": "success",
            "message": f"File encrypted and saved as: {encrypted_path}",
            "original_size": len(content),
            "encrypted_size": len(encrypted_content),
            "encrypted_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@registry.tool()
def decrypt_file(filepath: str, password: str) -> Dict[str, str]:
    """Decrypt a previously encrypted file."""
    try:
        with open(filepath, "r") as f:
            encrypted_content = f.read()

        # Decrypt content
        decoded_content = base64.b64decode(encrypted_content).decode()
        salt = hashlib.sha256(password.encode()).hexdigest()[:8]
        original_content = decoded_content[: -len(salt)]

        # Save decrypted content
        decrypted_path = filepath.replace(".encrypted", ".decrypted")
        with open(decrypted_path, "w", encoding="utf-8") as f:
            f.write(original_content)

        return {
            "status": "success",
            "message": f"File decrypted and saved as: {decrypted_path}",
            "content_preview": original_content[:100] + "..."
            if len(original_content) > 100
            else original_content,
            "decrypted_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@registry.tool()
def find_files(directory: str, pattern: str = "*") -> Dict[str, any]:
    """Find files in a directory matching a pattern."""
    try:
        path = Path(directory)
        if not path.exists():
            return {"status": "error", "message": f"Directory not found: {directory}"}

        files = list(path.glob(pattern))
        file_info = []

        for file_path in files:
            if file_path.is_file():
                stat = file_path.stat()
                file_info.append(
                    {
                        "name": file_path.name,
                        "path": str(file_path),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "extension": file_path.suffix,
                    }
                )

        return {
            "status": "success",
            "directory": directory,
            "pattern": pattern,
            "files_found": len(file_info),
            "files": file_info,
            "searched_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@registry.tool()
def create_backup(filepath: str, backup_suffix: str = ".backup") -> Dict[str, str]:
    """Create a backup copy of a file with timestamp."""
    try:
        source_path = Path(filepath)
        if not source_path.exists():
            return {"status": "error", "message": f"File not found: {filepath}"}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = source_path.with_suffix(f"{backup_suffix}.{timestamp}")

        with open(source_path, "rb") as src, open(backup_path, "wb") as dst:
            dst.write(src.read())

        return {
            "status": "success",
            "message": f"Backup created: {backup_path}",
            "original_file": str(source_path),
            "backup_file": str(backup_path),
            "backup_size": backup_path.stat().st_size,
            "backed_up_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@registry.tool()
def transform_text(filepath: str, transformation: str) -> Dict[str, str]:
    """Apply text transformations to a file (uppercase, lowercase, reverse, etc.)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        if transformation.lower() == "uppercase":
            content = content.upper()
        elif transformation.lower() == "lowercase":
            content = content.lower()
        elif transformation.lower() == "reverse":
            content = content[::-1]
        elif transformation.lower() == "titlecase":
            content = content.title()
        elif transformation.lower() == "remove_spaces":
            content = re.sub(r"\s+", "", content)
        elif transformation.lower() == "word_count":
            words = re.findall(r"\b\w+\b", content)
            content = f"Word count: {len(words)}"
        else:
            return {
                "status": "error",
                "message": f"Unknown transformation: {transformation}",
            }

        # Save transformed content
        transformed_path = f"{filepath}.{transformation.lower()}"
        with open(transformed_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "status": "success",
            "message": f"Text transformed and saved as: {transformed_path}",
            "transformation": transformation,
            "original_size": len(original_content),
            "transformed_size": len(content),
            "transformed_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@registry.tool()
def create_json_report(filepath: str) -> Dict[str, any]:
    """Create a detailed JSON report about a file's properties and content."""
    try:
        path = Path(filepath)
        if not path.exists():
            return {"status": "error", "message": f"File not found: {filepath}"}

        stat = path.stat()

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.splitlines()
        words = re.findall(r"\b\w+\b", content.lower())

        report = {
            "file_info": {
                "name": path.name,
                "path": str(path),
                "extension": path.suffix,
                "size_bytes": stat.st_size,
                "size_kb": round(stat.st_size / 1024, 2),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
            },
            "content_analysis": {
                "total_characters": len(content),
                "total_lines": len(lines),
                "total_words": len(words),
                "unique_words": len(set(words)),
                "average_line_length": round(len(content) / len(lines), 2)
                if lines
                else 0,
                "empty_lines": len([line for line in lines if not line.strip()]),
                "non_empty_lines": len([line for line in lines if line.strip()]),
            },
            "generated_at": datetime.now().isoformat(),
        }

        # Save report
        report_path = f"{filepath}.report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return {
            "status": "success",
            "message": f"JSON report created: {report_path}",
            "report": report,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    print(find_files("./", ".txt"))
