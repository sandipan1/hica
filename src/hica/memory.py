"""
HICA Memory Abstraction
======================

This module provides a unified, pluggable memory abstraction for HICA agents.
It enables storing and retrieving arbitrary key-value data (such as prompts, configs, citations, or conversation history)
using a consistent interface, with support for multiple backends (in-memory, file, etc.).

Key Concepts:
-------------
- MemoryStore: Minimal interface for key-value memory (get, set, delete, all).
- InMemoryMemoryStore: Simple in-memory implementation for fast, ephemeral storage.
- FileMemoryStore: Stores all key-value pairs in a single JSON file (for general data, not for threads).
- ConversationMemoryStore: Specialized store for conversation history, storing each Thread as a separate JSON file in a directory.

Usage Examples:
---------------
# For general memory (e.g., prompt/config memory):
prompt_memory = InMemoryMemoryStore()
prompt_memory.set("citation_instructions", "Always cite your sources...")

# For conversation history:
conversation_store = ConversationMemoryStore(dir_path="context")
thread_id = "abc123"
conversation_store.set(thread_id, thread)
thread = conversation_store.get(thread_id)

Design Notes:
-------------
- ConversationMemoryStore is the recommended way to persist and retrieve conversation threads (replaces ThreadStore).
- All memory types can be used together in the agent for context injection and state management.
- This abstraction keeps HICA minimal, composable, and production-ready.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Generic, Optional, TypeVar

from pymongo import MongoClient

from hica.core import Thread

T = TypeVar("T")


class MemoryStore(Generic[T]):
    """Minimal key-value memory store interface."""

    def get(self, key: str) -> Optional[T]:
        raise NotImplementedError

    def set(self, key: str, value: T) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def all(self) -> Dict[str, T]:
        raise NotImplementedError


class InMemoryMemoryStore(MemoryStore[T]):
    def __init__(self):
        self._store: Dict[str, T] = {}

    def get(self, key: str) -> Optional[T]:
        return self._store.get(key)

    def set(self, key: str, value: T) -> None:
        self._store[key] = value

    def delete(self, key: str) -> None:
        if key in self._store:
            del self._store[key]

    def all(self) -> Dict[str, T]:
        return dict(self._store)


class FileMemoryStore(MemoryStore[T]):
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self._store = self._load()

    def _load(self) -> Dict[str, T]:
        if self.file_path.exists():
            with self.file_path.open("r") as f:
                return json.load(f)
        return {}

    def _save(self):
        with self.file_path.open("w") as f:
            json.dump(self._store, f)

    def get(self, key: str) -> Optional[T]:
        return self._store.get(key)

    def set(self, key: str, value: T) -> None:
        self._store[key] = value
        self._save()

    def delete(self, key: str) -> None:
        if key in self._store:
            del self._store[key]
            self._save()

    def all(self) -> Dict[str, T]:
        return dict(self._store)


class ConversationMemoryStore:
    """
    Unified conversation store supporting file-based, SQL-based, and MongoDB (NoSQL) storage.
    Specify backend_type as 'file', 'sql', or 'mongo'.
    For 'file', provide context_dir. For 'sql', provide db_path. For 'mongo', provide uri, db_name, and collection.
    """

    def __init__(
        self,
        backend_type: str = "file",
        context_dir: str = "context",
        db_path: str = "conversations.db",
        mongo_uri: str = "mongodb://localhost:27017",
        mongo_db: str = "hica",
        mongo_collection: str = "threads",
    ):
        self.backend_type = backend_type
        if backend_type == "file":
            self.dir_path = Path(context_dir)
            self.dir_path.mkdir(parents=True, exist_ok=True)
        elif backend_type == "sql":
            self.conn = sqlite3.connect(db_path)
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS threads (id TEXT PRIMARY KEY, data TEXT)"
            )
            self.conn.commit()
        elif backend_type == "mongo":
            self.mongo_store = MongoMemoryStore(
                uri=mongo_uri, db_name=mongo_db, collection=mongo_collection
            )
        else:
            raise ValueError("backend_type must be 'file', 'sql', or 'mongo'")

    def set(self, thread: Thread):
        if not thread.thread_id:
            raise ValueError("Thread must have a thread_id before storing.")
        if self.backend_type == "file":
            file_path = self.dir_path / f"{thread.thread_id}.json"
            with file_path.open("w") as f:
                f.write(thread.to_json())
        elif self.backend_type == "sql":
            data = thread.to_json()
            self.conn.execute(
                "REPLACE INTO threads (id, data) VALUES (?, ?)",
                (thread.thread_id, data),
            )
            self.conn.commit()
        elif self.backend_type == "mongo":
            self.mongo_store.set(thread.thread_id, thread)

    def get(self, thread_id: str) -> Optional[Thread]:
        if self.backend_type == "file":
            file_path = self.dir_path / f"{thread_id}.json"
            if not file_path.exists():
                return None
            with file_path.open("r") as f:
                return Thread.from_json(f.read())
        elif self.backend_type == "sql":
            cursor = self.conn.execute(
                "SELECT data FROM threads WHERE id = ?", (thread_id,)
            )
            row = cursor.fetchone()
            if row:
                return Thread.from_json(row[0])
            return None
        elif self.backend_type == "mongo":
            return self.mongo_store.get(thread_id)

    def delete(self, thread_id: str):
        if self.backend_type == "file":
            file_path = self.dir_path / f"{thread_id}.json"
            if file_path.exists():
                file_path.unlink()
        elif self.backend_type == "sql":
            self.conn.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
            self.conn.commit()
        elif self.backend_type == "mongo":
            self.mongo_store.delete(thread_id)

    def all(self) -> Dict[str, Thread]:
        if self.backend_type == "file":
            result = {}
            for file in self.dir_path.glob("*.json"):
                with file.open("r") as f:
                    result[file.stem] = Thread.from_json(f.read())
            return result
        elif self.backend_type == "sql":
            cursor = self.conn.execute("SELECT id, data FROM threads")
            return {row[0]: Thread.from_json(row[1]) for row in cursor.fetchall()}
        elif self.backend_type == "mongo":
            return self.mongo_store.all()


class SQLMemoryStore(MemoryStore[T]):
    def __init__(self, db_path: str = "memory.db", table: str = "kv_store"):
        self.conn = sqlite3.connect(db_path)
        self.table = table
        self.conn.execute(
            f"CREATE TABLE IF NOT EXISTS {self.table} (key TEXT PRIMARY KEY, value TEXT)"
        )
        self.conn.commit()

    def get(self, key: str) -> Optional[T]:
        cursor = self.conn.execute(
            f"SELECT value FROM {self.table} WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None

    def set(self, key: str, value: T) -> None:
        value_json = json.dumps(value)
        self.conn.execute(
            f"REPLACE INTO {self.table} (key, value) VALUES (?, ?)", (key, value_json)
        )
        self.conn.commit()

    def delete(self, key: str) -> None:
        self.conn.execute(f"DELETE FROM {self.table} WHERE key = ?", (key,))
        self.conn.commit()

    def all(self) -> Dict[str, T]:
        cursor = self.conn.execute(f"SELECT key, value FROM {self.table}")
        return {row[0]: json.loads(row[1]) for row in cursor.fetchall()}


class PromptStore:
    """
    Simple prompt/template store with dynamic variable filling.
    You can use any MemoryStore backend (in-memory, file, etc.).
    By default, uses a file-based memory store ('prompts.json').
    """

    def __init__(
        self,
        backend: Optional[MemoryStore[str]] = None,
        file_path: str = "prompts.json",
    ):
        if backend is not None:
            self.backend = backend
        else:
            self.backend = FileMemoryStore(file_path=file_path)

    def set(self, key: str, template: str) -> None:
        self.backend.set(key, template)

    def get(self, key: str, **kwargs) -> str:
        template = self.backend.get(key)
        if template is None:
            raise KeyError(f"Prompt '{key}' not found.")
        return template.format(**kwargs)

    def delete(self, key: str) -> None:
        self.backend.delete(key)

    def all(self) -> Dict[str, str]:
        return self.backend.all()


class MongoMemoryStore(MemoryStore[T]):
    def __init__(
        self, uri="mongodb://localhost:27017", db_name="hica", collection="threads"
    ):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection]

    def get(self, key: str) -> Optional[T]:
        doc = self.collection.find_one({"thread_id": key})
        if doc:
            return Thread(**doc)  # or T(**doc) if generic
        return None

    def set(self, key: str, value: T) -> None:
        self.collection.replace_one({"thread_id": key}, value.model_dump(), upsert=True)

    def delete(self, key: str) -> None:
        self.collection.delete_one({"thread_id": key})

    def all(self) -> Dict[str, T]:
        return {doc["thread_id"]: Thread(**doc) for doc in self.collection.find()}
