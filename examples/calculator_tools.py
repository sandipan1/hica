from hica.tools import ToolRegistry

registry = ToolRegistry()


@registry.tool()
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


@registry.tool()
def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b


@registry.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


@registry.tool()
def divide(a: float, b: float) -> float:
    """Divide a by b."""
    if b == 0:
        raise ValueError("Division by zero")
    return a / b
