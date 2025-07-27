import asyncio
import inspect
import json
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

from fastmcp import Client
from pydantic import BaseModel, Field, create_model
from pydantic_ai.tools import ToolDefinition

from hica.logging import logger
from hica.models import ToolResult, serialize_mcp_result


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


class BaseTool:
    """Base class for all tools. Ensures a consistent interface for execution and metadata."""

    name: str
    description: str

    def get_confirmation_prompt(self, params: dict) -> str:
        """Return a human-readable description of what this tool will do with these params."""
        return f"Execute {self.name} with parameters: {params}?"

    def should_confirm(self, params: dict) -> bool:
        """Return True if this tool execution requires user confirmation."""
        return False

    async def execute(self, **kwargs) -> ToolResult:
        """The core execution logic of the tool. Must return a ToolResult."""
        raise NotImplementedError


def _create_wrapper_tool(func: Callable) -> BaseTool:
    """Dynamically creates a BaseTool subclass that wraps a simple function."""

    class FunctionToolWrapper(BaseTool):
        def __init__(self, wrapped_func: Callable):
            self._wrapped_func = wrapped_func
            self.name = wrapped_func.__name__
            self.description = wrapped_func.__doc__ or ""

        async def execute(self, **kwargs) -> ToolResult:
            # Execute the original function (sync or async)
            if asyncio.iscoroutinefunction(self._wrapped_func):
                raw_result = await self._wrapped_func(**kwargs)
            else:
                raw_result = self._wrapped_func(**kwargs)

            # Wrap the simple result in a ToolResult object
            str_result = str(raw_result)
            return ToolResult(
                llm_content=str_result,
                display_content=str_result,
                raw_result=raw_result,
            )

    return FunctionToolWrapper(func)


class MCPConnectionManager:
    def __init__(self, server_path_or_url):
        self.client = Client(server_path_or_url)

    async def __aenter__(self):
        """Establish connection to the MCP server with context manager"""
        if not self.client.is_connected():
            await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type=None, exc_value=None, traceback=None):
        """Close connection to the MCP server with context manager"""
        if self.client.is_connected():
            await self.client.__aexit__(exc_type, exc_value, traceback)

    async def connect(self):
        """Establish connection to the MCP server"""
        await self.__aenter__()

    async def disconnect(self):
        """Close connection to the MCP server"""
        await self.__aexit__(None, None, None)

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


class ToolRegistry:
    def __init__(self):
        self.local_tools: Dict[str, BaseTool] = {}
        self.local_tool_defs: Dict[str, ToolDefinition] = {}
        self.mcp_tools: Dict[str, Tuple[MCPConnectionManager, ToolDefinition]] = {}
        self.all_tool_defs: Dict[str, ToolDefinition] = {}

    def _register_local_tool(
        self, tool: Union[Callable, BaseTool], intent: Optional[str] = None
    ):
        """A private helper to register a local Python function or a BaseTool instance."""
        if callable(tool) and not isinstance(tool, BaseTool):
            tool_instance = _create_wrapper_tool(tool)
        elif isinstance(tool, BaseTool):
            tool_instance = tool
        else:
            raise TypeError("Tool must be a callable or an instance of BaseTool")

        tool_intent = intent or tool_instance.name
        description = tool_instance.description
        func_to_inspect = tool_instance.execute
        name = tool_instance.name

        if tool_intent in self.local_tools:
            logger.warning(f"Tool '{tool_intent}' is already registered. Overwriting.")

        signature = inspect.signature(func_to_inspect)
        params_to_process = list(signature.parameters.values())
        if params_to_process and params_to_process[0].name == "self":
            params_to_process.pop(0)

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

        for param in params_to_process:
            param_type = param.annotation
            json_type = "string"
            if param_type in type_map:
                json_type = type_map[param_type]

            param_schema = {"type": json_type}
            if param.default != inspect.Parameter.empty:
                param_schema["default"] = param.default
            else:
                required.append(param.name)

            properties[param.name] = param_schema

        tool_def = ToolDefinition(
            name=name,
            description=description,
            parameters_json_schema={
                "type": "object",
                "properties": properties,
                "required": required,
            },
        )

        self.local_tools[tool_intent] = tool_instance
        self.local_tool_defs[tool_intent] = tool_def
        self.all_tool_defs[tool_intent] = tool_def
        logger.info(f"Registered local tool: {tool_intent}")

    def tool(self, intent: Optional[str] = None):
        """A decorator to register a Python function or a BaseTool subclass as a tool."""

        def decorator(tool_item: Union[Callable, Type[BaseTool]]):
            if inspect.isclass(tool_item) and issubclass(tool_item, BaseTool):
                # Instantiate if it's a class
                self.add_tool(tool_item(), intent)
            elif callable(tool_item):
                # Handle function
                self.add_tool(tool_item, intent)
            else:
                raise TypeError(
                    "The @tool decorator can only be used on functions or BaseTool subclasses."
                )
            return tool_item

        return decorator

    def add_tool(self, tool: Union[Callable, BaseTool], intent: Optional[str] = None):
        """Programmatically adds a local Python function or a BaseTool instance as a tool."""
        self._register_local_tool(tool, intent)

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
            tool = self.local_tools[name]
            return await tool.execute(**arguments)
        elif name in self.mcp_tools:
            logger.info(
                f"Executing MCP tool: {name}",
                extra={"tool_type": "mcp", "arguments": arguments},
            )
            mcp_manager, _ = self.mcp_tools[name]
            # MCP tools might not return a ToolResult, so we wrap it for consistency
            raw_result = await mcp_manager.call_tool(name, arguments)

            llm_content_str = ""
            display_content_str = ""

            # Check if the result is a ToolResult-like object with structured content
            if hasattr(raw_result, "structured_content") and raw_result.structured_content is not None:
                # For the LLM, use the clean, structured data, serialized to a compact JSON string
                llm_content_str = json.dumps(serialize_mcp_result(raw_result.structured_content))
            
            # For display, use the traditional content if available
            if hasattr(raw_result, "content") and raw_result.content:
                # Assuming content is a list of content blocks like TextContent
                display_parts = []
                for item in raw_result.content:
                    if hasattr(item, "text"):
                        display_parts.append(item.text)
                display_content_str = " ".join(display_parts)

            # Fallback for both if the above checks fail, maintaining old behavior
            if not llm_content_str:
                llm_content_str = str(serialize_mcp_result(raw_result))
            if not display_content_str:
                display_content_str = llm_content_str

            return ToolResult(
                llm_content=llm_content_str,
                display_content=display_content_str,
                raw_result=raw_result,
            )
        else:
            logger.error(f"Tool {name} not found in registry.")
            raise ValueError(f"Tool {name} not found")


