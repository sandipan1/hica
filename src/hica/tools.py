import asyncio
import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from pydantic import BaseModel, Field, computed_field, create_model, validate_arguments
from pydantic_ai.tools import ToolDefinition


def create_model_from_tool_schema(tool_def: ToolDefinition) -> Type[BaseModel]:
    """Create a Pydantic model from a tool definition's parameters JSON schema."""
    schema = tool_def.parameters_json_schema
    model_name = f"{tool_def.name}"

    properties = schema.get("properties", {})
    required = schema.get("required", [])

    field_definitions: Dict[str, Tuple[Type, Field]] = {}
    for field_name, field_schema in properties.items():
        field_type = _get_python_type_from_schema(field_schema)
        is_required = field_name in required

        description = field_schema.get("description", "")

        if is_required:
            field_definitions[field_name] = (field_type, Field(description=description))
        else:
            field_definitions[field_name] = (
                Optional[field_type],
                Field(None, description=description),
            )

    # Create a base class with the computed fields
    class BaseToolModel(BaseModel):
        @computed_field
        def name(self) -> str:
            return tool_def.name

        @computed_field
        def description(self) -> str:
            return tool_def.description

    # Create the final model by inheriting from the base class
    return create_model(model_name, __base__=BaseToolModel, **field_definitions)


def _get_python_type_from_schema(schema: Dict[str, Any]) -> type:
    """Convert JSON schema type to Python type."""
    schema_type = schema.get("type")

    if schema_type == "string":
        return str
    elif schema_type == "integer":
        return int
    elif schema_type == "number":
        return float
    elif schema_type == "boolean":
        return bool
    elif schema_type == "array":
        items = schema.get("items", {})
        item_type = _get_python_type_from_schema(items)
        return List[item_type]
    elif schema_type == "object":
        if "properties" in schema:
            # This is a nested object with defined properties
            nested_model = create_model_from_nested_schema(schema)
            return nested_model
        else:
            # This is a generic object
            return Dict[str, Any]
    else:
        return Any


def create_model_from_nested_schema(schema: Dict[str, Any]) -> type[BaseModel]:
    """Create a Pydantic model from a nested object schema."""
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    field_definitions = {}
    for field_name, field_schema in properties.items():
        field_type = _get_python_type_from_schema(field_schema)
        is_required = field_name in required

        description = field_schema.get("description", "")

        if is_required:
            field_definitions[field_name] = (field_type, Field(description=description))
        else:
            field_definitions[field_name] = (
                Optional[field_type],
                Field(None, description=description),
            )

    return create_model("NestedModel", **field_definitions)


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_definitions: Dict[str, ToolDefinition] = {}

    def tool(self, intent: Optional[str] = None):
        def decorator(func: Callable):
            tool_intent = intent or func.__name__
            signature = inspect.signature(func)
            properties = {}
            required = []
            for param_name, param in signature.parameters.items():
                param_type = (
                    param.annotation.__name__
                    if param.annotation != inspect.Parameter.empty
                    else "string"
                )
                param_schema = {"type": param_type}
                if param.default != inspect.Parameter.empty:
                    param_schema["default"] = param.default
                properties[param_name] = param_schema
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)
            tool_def = ToolDefinition(
                name=func.__name__,
                description=func.__doc__ or None,
                parameters_json_schema={
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            )
            self.tool_definitions[tool_intent] = tool_def

            @validate_arguments
            @functools.wraps(func)
            async def wrapper(**kwargs):
                if asyncio.iscoroutinefunction(func):
                    return await func(**kwargs)
                else:
                    return func(**kwargs)

            self.tools[tool_intent] = wrapper
            return func

        return decorator

    async def execute_tool(self, intent: str, arguments: dict) -> Any:
        if intent not in self.tools:
            raise ValueError(f"No tool registered for intent: {intent}")
        tool_func = self.tools[intent]
        return await tool_func(**arguments)
