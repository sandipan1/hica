import asyncio
import inspect
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from pydantic import BaseModel, Field, create_model
from pydantic_ai.tools import ToolDefinition

from hica.logging import logger


def create_model_from_tool_schema(tool_def: ToolDefinition) -> Type[BaseModel]:
    """Dynamically create a Pydantic model from a tool's parameter schema."""
    model_name = tool_def.name.replace(" ", "_")
    field_definitions = {}
    for param, schema in tool_def.parameters_json_schema.get("properties", {}).items():
        # Use type annotation from schema if possible, else default to Any
        annotation = Any
        if schema.get("type") == "integer":
            annotation = int
        elif schema.get("type") == "number":
            annotation = float
        elif schema.get("type") == "string":
            annotation = str
        elif schema.get("type") == "boolean":
            annotation = bool
        elif schema.get("type") == "array":
            annotation = list
        elif schema.get("type") == "object":
            annotation = dict
        field_definitions[param] = (annotation, ...)
    # Use BaseModel instead of BaseToolModel to avoid field conflicts
    return create_model(model_name, __base__=BaseModel, **field_definitions)


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


from fastmcp import Client


class MCPConnectionManager:
    def __init__(self, server_path_or_url):
        self.client = Client(server_path_or_url)

    async def connect(self):
        """Establish connection to the MCP server"""
        if not self.client.is_connected():
            await self.client.__aenter__()

    async def disconnect(self):
        """Close connection to the MCP server"""
        if self.client.is_connected():
            await self.client.__aexit__(None, None, None)

    async def call_tool(self, name, arguments=None):
        """Call a tool on the MCP server"""
        if not self.client.is_connected():
            raise RuntimeError("Not connected. Call connect() first.")
        return await self.client.call_tool(name, arguments)

    async def list_tools(self):
        """List all available tools on the MCP server"""
        if not self.client.is_connected():
            raise RuntimeError("Not connected. Call connect() first.")
        return await self.client.list_tools()

    async def list_resources(self):
        """List all available resources on the MCP server"""
        if not self.client.is_connected():
            raise RuntimeError("Not connected. Call connect() first.")
        return await self.client.list_resources()

    async def read_resource(self, uri):
        """Read a resource from the MCP server"""
        if not self.client.is_connected():
            raise RuntimeError("Not connected. Call connect() first.")
        return await self.client.read_resource(uri)

    async def ping(self):
        """Ping the MCP server to verify connectivity"""
        if not self.client.is_connected():
            raise RuntimeError("Not connected. Call connect() first.")
        return await self.client.ping()

    def is_connected(self):
        """Check if currently connected to the server"""
        return self.client.is_connected()


class ToolRegistry:
    def __init__(self):
        self.local_tools: Dict[str, Callable] = {}
        self.local_tool_defs: Dict[str, ToolDefinition] = {}
        self.mcp_tools: Dict[str, Tuple[MCPConnectionManager, ToolDefinition]] = {}
        self.all_tool_defs: Dict[str, ToolDefinition] = {}

    def _register_local_tool(self, func: Callable, intent: Optional[str] = None):
        """A private helper to register a local Python function as a tool."""
        tool_intent = intent or func.__name__
        if tool_intent in self.local_tools:
            logger.warning(f"Tool '{tool_intent}' is already registered. Overwriting.")

        signature = inspect.signature(func)
        properties = {}
        required = []

        type_map = {
            int: "integer",
            float: "number",
            str: "string",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        for param_name, param in signature.parameters.items():
            param_type = param.annotation
            json_type = "string"  # Default if type is not recognized
            if param_type in type_map:
                json_type = type_map[param_type]

            param_schema = {"type": json_type}
            if param.default != inspect.Parameter.empty:
                param_schema["default"] = param.default
            else:
                required.append(param_name)

            properties[param_name] = param_schema

        tool_def = ToolDefinition(
            name=func.__name__,
            description=func.__doc__ or "",
            parameters_json_schema={
                "type": "object",
                "properties": properties,
                "required": required,
            },
        )
        self.local_tools[tool_intent] = func
        self.local_tool_defs[tool_intent] = tool_def
        self.all_tool_defs[tool_intent] = tool_def
        logger.info(f"Registered local tool: {tool_intent}")

    def tool(self, intent: Optional[str] = None):
        """A decorator to register a Python function as a tool."""

        def decorator(func: Callable):
            self._register_local_tool(func, intent)
            return func

        return decorator

    def add_tool(self, func: Callable, intent: Optional[str] = None):
        """Programmatically adds a local Python function as a tool."""
        self._register_local_tool(func, intent)

    def remove_tool(self, name: str):
        """Removes a tool (local or MCP) from the registry by its name."""
        if name in self.local_tools:
            del self.local_tools[name]
            del self.local_tool_defs[name]
            del self.all_tool_defs[name]
            logger.info(f"Removed local tool: {name}")
        elif name in self.mcp_tools:
            del self.mcp_tools[name]
            del self.all_tool_defs[name]
            logger.info(f"Removed MCP tool: {name}")
        else:
            logger.warning(f"Attempted to remove tool '{name}' which was not found.")

    async def load_mcp_tools(self, mcp_manager: "MCPConnectionManager"):
        """Fetch tool definitions from an MCP server and register them."""
        tools = await mcp_manager.list_tools()
        for tool in tools:
            tool_def = ToolDefinition(
                name=tool.name,
                description=tool.description,
                parameters_json_schema=tool.inputSchema,
            )
            self.mcp_tools[tool.name] = (mcp_manager, tool_def)
            self.all_tool_defs[tool.name] = tool_def

    def get_tool_definitions(self):
        """Return all tool definitions (local + MCP)."""
        return self.all_tool_defs

    async def execute_tool(self, name: str, arguments: dict) -> Any:
        if name in self.local_tools:
            logger.info(
                f"Executing LOCAL tool: {name}",
                extra={"tool_type": "local", "arguments": arguments},
            )
            func = self.local_tools[name]
            if asyncio.iscoroutinefunction(func):
                return await func(**arguments)
            else:
                return func(**arguments)
        elif name in self.mcp_tools:
            logger.info(
                f"Executing MCP tool: {name}",
                extra={"tool_type": "mcp", "arguments": arguments},
            )
            mcp_manager, _ = self.mcp_tools[name]
            return await mcp_manager.call_tool(name, arguments)
        else:
            logger.error(f"Tool {name} not found in registry.")
            raise ValueError(f"Tool {name} not found")
