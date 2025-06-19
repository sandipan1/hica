import base64
import json
from typing import Any, Dict, Optional

from pydantic import BaseModel


def serialize_mcp_result(result: Any) -> dict | str | float | int | list | None:
    """
    Serializes the output of an MCP tool call into a format suitable for storage in an Event.

    This function is used to normalize and convert the various possible return types from FastMCP tool calls
    (including custom content types like TextContent, EmbeddedResource, images, audio, files, lists, and Pydantic models)
    into standard Python types (dict, str, float, int, list, or None) that are compatible with Pydantic models and JSON serialization.

    It is typically called before storing the result of a tool call in the `data` field of an Event, ensuring that
    all Event data is serializable, consistent, and easy to consume downstream.

    Args:
        result: The raw result returned by an MCP tool call. This may be a FastMCP content object, a list, a dict,
                a Pydantic model, a primitive, or None.

    Returns:
        A value of type dict, str, float, int, list, or None, suitable for storage in Event.data.
        - TextContent: returns the parsed JSON if possible, else the text string.
        - EmbeddedResource, BlobResourceContents, File: returns base64-encoded string or dict with mime_type.
        - ImageContent, AudioContent: returns dict with mime_type and base64-encoded data.
        - Pydantic BaseModel: returns the model as a dict.
        - list: recursively serializes each item.
        - dict, str, float, int: returned as-is.
        - None: returns None.
        - Any other type: returns its string representation.
    """
    if result is None:
        return None
    if isinstance(result, list):
        return [serialize_mcp_result(item) for item in result]
    if hasattr(result, "text"):
        try:
            return json.loads(result.text)
        except Exception:
            return result.text
    if hasattr(result, "data"):
        # If it has a mime_type, treat as image/audio/file
        if hasattr(result, "mime_type"):
            return {
                "mime_type": getattr(result, "mime_type", None),
                "data": base64.b64encode(result.data).decode("utf-8"),
            }
        return base64.b64encode(result.data).decode("utf-8")
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, (dict, str, float, int)):
        return result
    return str(result)


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
    data: dict | str | float | int | list | None  # Accepts list and None

    # @computed_field
    # @property
    # def serialized_data(self) -> dict | str | float | int | list | None:
    #     """
    #     For tool_response events, returns the serialized/normalized data.
    #     For other event types, returns data as-is.
    #     """
    #     if self.type == "tool_response":
    #         return serialize_mcp_result(self.data)
    #     return self.data


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
