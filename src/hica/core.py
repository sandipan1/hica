import json
import xml.etree.ElementTree as ET
from typing import Any, Dict, Generic, List, TypeVar

from pydantic import BaseModel

from .logging import logger
from .models import Event

T = TypeVar("T")


class Thread(BaseModel, Generic[T]):
    events: List[Event] = []
    metadata: Dict[str, Any] = {}

    def serialize_for_llm(self, format: str = "json") -> str:
        """Serialize thread for LLM consumption, excluding redundant events."""
        context_summary = (
            f"Thread Context: {json.dumps(self.metadata)}\n\n" if self.metadata else ""
        )

        # Filter out llm_prompt events and only include relevant events
        relevant_events = []
        for event in self.events:
            if event.type not in ["llm_prompt"]:  # Exclude llm_prompt events
                relevant_events.append(event)

        events_str = (
            "\n".join(self.serialize_one_event(event) for event in relevant_events)
            if format == "xml"
            else json.dumps([event.dict() for event in relevant_events], indent=2)
        )
        return f"{context_summary}{events_str}"

    def serialize_one_event(self, event: Event) -> str:
        root = ET.Element(
            event.data.get("intent", event.type)
            if isinstance(event.data, dict)
            else event.type
        )
        if isinstance(event.data, (str, float, int)):
            root.text = str(event.data)
        elif isinstance(event.data, dict):
            for key, value in event.data.items():
                if key != "intent":
                    child = ET.SubElement(root, key)
                    child.text = str(value)
        return ET.tostring(root, encoding="unicode", method="xml")

    def awaiting_human_response(self) -> bool:
        if not self.events:
            return False
        last_event = self.events[-1]
        return (
            isinstance(last_event.data, dict)
            and last_event.data.get("intent") == "clarification"
        )

    def awaiting_human_approval(self) -> bool:
        if not self.events:
            return False
        last_event = self.events[-1]
        return isinstance(last_event.data, dict) and last_event.data.get(
            "requires_approval", False
        )

    def set_context(self, key: str, value: Any) -> None:
        """Set a context value in the thread's metadata."""
        self.metadata[key] = value
        logger.debug("Context updated", key=key, value=value)

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value from the thread's metadata."""
        return self.metadata.get(key, default)

    def append_event(self, event: Event) -> None:
        self.events.append(event)
        logger.debug("Event appended", event_type=event.type)

    async def summarize_context(self, max_events: int = 10) -> None:
        if len(self.events) <= max_events:
            return
        recent_events = self.events[-max_events:]
        summary_event = Event(
            type="context_summary",
            data="Summary of earlier interactions: user initiated conversation, performed calculations.",
        )
        self.events = [summary_event] + recent_events
        logger.info(
            "Context summarized",
            remaining_events=len(self.events),
        )

    def validate(self) -> bool:
        if not self.events:
            logger.warning("Thread has no events")
            return False
        for event in self.events:
            if not isinstance(event, Event):
                logger.error("Invalid event type", event=event)
                return False
            if not event.type or event.data is None:
                logger.error("Invalid event structure", event=event.dict())
                return False
        logger.debug("Context validated", event_count=len(self.events))
        return True

    def to_json(self) -> str:
        """Serialize Thread to JSON string."""
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "Thread":
        """Deserialize Thread from JSON string."""
        try:
            data = json.loads(json_str)
            return cls(**data)
        except json.JSONDecodeError as e:
            logger.error("Failed to deserialize Thread from JSON", error=str(e))
            raise ValueError(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error("Unexpected error deserializing Thread", error=str(e))
            raise
