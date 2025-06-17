import unittest
from typing import Any, Dict

import pytest
from pydantic import BaseModel

from example.calculator_tools import registry as calculator_registry
from hica.tools import ToolRegistry


# Define a model for tool call arguments
class DynamicToolCall(BaseModel):
    intent: str
    arguments: Dict[str, Any]


class TestToolCall(unittest.IsolatedAsyncioTestCase):
    async def test_add_tool_call(self):
        """Test invoking the add tool via ToolRegistry."""
        # Create a tool call for add(3.0, 4.0)
        tool_call = DynamicToolCall(intent="add", arguments={"a": 3.0, "b": 4.0})

        # Execute the tool
        result = await calculator_registry.execute_tool(
            tool_call.intent, tool_call.arguments
        )
        print(result)
        # Verify the result
        self.assertEqual(result, 7.0, "Expected add(3.0, 4.0) to return 7.0")


@pytest.mark.asyncio
async def test_tool_registry_basic():
    registry = ToolRegistry()

    @registry.tool()
    def add(a: float, b: float) -> float:
        """Add two numbers."""
        return a + b

    @registry.tool()
    def multiply(a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b

    # Check tool registration
    assert "add" in registry.tools
    assert "multiply" in registry.tools

    # Check tool definitions
    add_def = registry.tool_definitions["add"]
    multiply_def = registry.tool_definitions["multiply"]
    assert add_def.name == "add"
    assert multiply_def.name == "multiply"
    assert add_def.parameters_json_schema["properties"].keys() == {"a", "b"}
    assert set(add_def.parameters_json_schema["required"]) == {"a", "b"}

    # Test execution
    result_add = await registry.execute_tool("add", {"a": 2, "b": 3})
    result_mul = await registry.execute_tool("multiply", {"a": 4, "b": 5})
    assert result_add == 5
    assert result_mul == 20


if __name__ == "__main__":
    unittest.main()
