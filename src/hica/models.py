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

    # Handle Pydantic Models first
    if hasattr(result, "model_dump"):
        return result.model_dump()

    # Handle lists recursively
    if isinstance(result, list):
        return [serialize_mcp_result(item) for item in result]

    # Handle FastMCP content types
    # from fastmcp.utilities.types import Image, Audio, File
    # Based on the reference code, we expect objects with specific structures

    # Handle Image/Audio content (dict with mime_type and data)
    if isinstance(result, dict) and "mime_type" in result and "data" in result:
        data_to_encode = result["data"]
        if isinstance(data_to_encode, str):
            # It might already be base64 encoded string, but let's assume it's raw string data
            data_to_encode = data_to_encode.encode("utf-8")
        if isinstance(data_to_encode, bytes):
            encoded_data = base64.b64encode(data_to_encode).decode("utf-8")
            return {"mime_type": result["mime_type"], "data": encoded_data}

    # Handle generic objects with .data attribute (like EmbeddedResource)
    if hasattr(result, "data"):
        data_to_encode = result.data
        if isinstance(data_to_encode, str):
            data_to_encode = data_to_encode.encode("utf-8")
        if isinstance(data_to_encode, bytes):
            return base64.b64encode(data_to_encode).decode("utf-8")
        return data_to_encode  # return as is if not bytes or string

    # Handle TextContent
    if hasattr(result, "text"):
        try:
            # Try to parse as JSON if it's a string representation of JSON
            return json.loads(result.text)
        except (json.JSONDecodeError, TypeError):
            # Otherwise, return the raw text
            return result.text

    # Handle primitive types
    if isinstance(result, (dict, str, float, int)):
        return result

    # Fallback for any other type
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
