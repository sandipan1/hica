from fastmcp import FastMCP

mcp = FastMCP("calculator")


@mcp.tool()
def square(x: float) -> float:
    """Square a number."""
    return x * x


@mcp.tool()
def cube(x: float) -> float:
    """Cube a number."""
    return x * x * x


if __name__ == "__main__":
    mcp.run()
