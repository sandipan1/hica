from typing import Any, Dict, Optional

from pydantic import BaseModel


class DoneForNow(BaseModel):
    """Indicates the agent has completed its task or reached a stopping point."""

    intent: str = "done"
    message: Optional[str] = None


class ClarificationRequest(BaseModel):
    """Indicates the agent needs user clarification to proceed."""

    intent: str = "clarification"
    message: Optional[str] = None


class Event(BaseModel):
    type: str
    data: dict | str | float | int


class DynamicToolCall(BaseModel):
    """Represents a tool call with intent and arguments."""

    intent: str
    arguments: Dict[str, Any] = {}
    message: Optional[str] = None


class FinalResponse(BaseModel):
    """Represents the final response from the LLM to the user."""

    intent: str = "final_response"
    message: str
    summary: Optional[str] = None
    raw_results: Optional[Dict[str, Any]] = None
