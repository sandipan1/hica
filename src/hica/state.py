import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from .core import Event, Thread
from .logging import logger


class ThreadStore:
    def __init__(self, context_dir: str = "context"):
        self.threads: dict[str, Thread] = {}
        self.context_dir = Path(os.getenv("HICA_CONTEXT_DIR", context_dir))
        self.context_dir.mkdir(parents=True, exist_ok=True)
        logger.info("ThreadStore initialized", context_dir=str(self.context_dir))

    def create(self, thread: Thread) -> str:
        thread_id = str(uuid.uuid4())
        # Store the thread_id in the thread's metadata for resumability
        if not thread.metadata:
            thread.metadata = {}
        thread.metadata["thread_id"] = thread_id
        self.threads[thread_id] = thread
        self._save_to_file(thread_id, thread)
        logger.info("Thread created", thread_id=thread_id)
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
            # Ensure thread_id is in metadata (for backward compatibility)
            if not thread.metadata:
                thread.metadata = {}
            if "thread_id" not in thread.metadata:
                thread.metadata["thread_id"] = thread_id

            self.threads[thread_id] = thread
            logger.debug("Thread loaded from file", thread_id=thread_id)
        else:
            logger.warning("Thread not found", thread_id=thread_id)
        return thread

    def update(self, thread_id: str, thread: Thread):
        # Ensure thread_id is in metadata (for consistency)
        if not thread.metadata:
            thread.metadata = {}
        thread.metadata["thread_id"] = thread_id
        thread.metadata['awaiting_human_response'] = thread.awaiting_human_response()
        # Update in-memory']
        self.threads[thread_id] = thread
        self._save_to_file(thread_id, thread)
        logger.debug("Thread updated", thread_id=thread_id)

    def _save_to_file(self, thread_id: str, thread: Thread):
        """Save Thread to a JSON file."""
        file_path = self.context_dir / f"{thread_id}.json"
        try:
            with file_path.open("w") as f:
                f.write(thread.to_json())
            logger.debug(
                "Thread saved to file", thread_id=thread_id, file_path=str(file_path)
            )
        except Exception as e:
            logger.error(
                "Failed to save Thread to file", thread_id=thread_id, error=str(e)
            )
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
            logger.error(
                "Failed to load Thread from file", thread_id=thread_id, error=str(e)
            )
            return None

    # Convenience methods
    def create_from_message(
        self, message: str, metadata: Optional[Dict[str, Any]] = None
    ) -> tuple[str, Thread]:
        thread = Thread(
            events=[Event(type="user_input", data=message)], metadata=metadata or {}
        )
        thread_id = self.create(thread)
        return thread_id, thread
