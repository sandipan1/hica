import uuid
from typing import Optional, List
from .core import Thread
from .logging import logger
from pathlib import Path
import os
import json

class ThreadStore:
    def __init__(self, context_dir: str = "context"):
        self.threads: dict[str, Thread] = {}
        self.versions: dict[str, List[Thread]] = {}
        self.context_dir = Path(os.getenv("HICA_CONTEXT_DIR", context_dir))
        self.context_dir.mkdir(parents=True, exist_ok=True)
        logger.info("ThreadStore initialized", context_dir=str(self.context_dir))

    def create(self, thread: Thread) -> str:
        thread_id = str(uuid.uuid4())
        self.threads[thread_id] = thread
        self.versions[thread_id] = [thread.copy(deep=True)]
        self._save_to_file(thread_id, thread)
        logger.info("Thread created", thread_id=thread_id, version=thread.version)
        return thread_id

    def get(self, thread_id: str) -> Optional[Thread]:
        # Check in-memory cache first
        thread = self.threads.get(thread_id)
        if thread:
            logger.debug("Thread retrieved from cache", thread_id=thread_id)
            return thread
        # Load from file if not in cache
        thread = self._load_from_file(thread_id)
        if thread:
            self.threads[thread_id] = thread
            self.versions[thread_id] = [thread.copy(deep=True)]
            logger.debug("Thread loaded from file", thread_id=thread_id)
        else:
            logger.warning("Thread not found", thread_id=thread_id)
        return thread

    def update(self, thread_id: str, thread: Thread):
        self.threads[thread_id] = thread
        self.versions[thread_id].append(thread.copy(deep=True))
        self._save_to_file(thread_id, thread)
        logger.debug("Thread updated", thread_id=thread_id, version=thread.version)

    def get_version(self, thread_id: str, version: int) -> Optional[Thread]:
        if thread_id in self.versions:
            for t in self.versions[thread_id]:
                if t.version == version:
                    logger.debug("Thread version retrieved", thread_id=thread_id, version=version)
                    return t
        logger.warning("Thread version not found", thread_id=thread_id, version=version)
        return None

    def _save_to_file(self, thread_id: str, thread: Thread):
        """Save Thread to a JSON file."""
        file_path = self.context_dir / f"{thread_id}.json"
        try:
            with file_path.open("w") as f:
                f.write(thread.to_json())
            logger.debug("Thread saved to file", thread_id=thread_id, file_path=str(file_path))
        except Exception as e:
            logger.error("Failed to save Thread to file", thread_id=thread_id, error=str(e))
            raise

    def _load_from_file(self, thread_id: str) -> Optional[Thread]:
        """Load Thread from a JSON file."""
        file_path = self.context_dir / f"{thread_id}.json"
        if not file_path.exists():
            return None
        try:
            with file_path.open("r") as f:
                json_str = f.read()
            thread = Thread.from_json(json_str)
            return thread
        except Exception as e:
            logger.error("Failed to load Thread from file", thread_id=thread_id, error=str(e))
            return None