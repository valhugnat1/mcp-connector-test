from typing import Sequence
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from mcp.shared.exceptions import McpError

from pydantic import BaseModel


class MathTools(str):
    ADD = "add"
    SUBTRACT = "subtract"


class MathResult(BaseModel):
    operation: str
    result: float
    details: str


class MathServer:
    def add(self, a: float, b: float) -> MathResult:
        """Add two numbers together"""
        result = a + b
        return MathResult(
            operation="addition",
            result=result,
            details=f"{a} + {b} = {result}"
        )

    def subtract(self, a: float, b: float) -> MathResult:
        """Subtract second number from first"""
        result = a - b
        return MathResult(
            operation="subtraction",
            result=result,
            details=f"{a} - {b} = {result}"
        )


async def serve() -> None:
    server = Server("mcp-math")
    math_server = MathServer()

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available math tools."""
        return [
            Tool(
                name=MathTools.ADD,
                description="Add two numbers together",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "a": {
                            "type": "number",
                            "description": "First number",
                        },
                        "b": {
                            "type": "number",
                            "description": "Second number",
                        }
                    },
                    "required": ["a", "b"],
                },
            ),
            Tool(
                name=MathTools.SUBTRACT,
                description="Subtract second number from first",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "a": {
                            "type": "number",
                            "description": "First number (minuend)",
                        },
                        "b": {
                            "type": "number",
                            "description": "Second number (subtrahend)",
                        }
                    },
                    "required": ["a", "b"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool calls for math operations."""
        try:
            match name:
                case MathTools.ADD:
                    if not all(k in arguments for k in ["a", "b"]):
                        raise ValueError("Missing required arguments: a and b")

                    result = math_server.add(float(arguments["a"]), float(arguments["b"]))

                case MathTools.SUBTRACT:
                    if not all(k in arguments for k in ["a", "b"]):
                        raise ValueError("Missing required arguments: a and b")

                    result = math_server.subtract(float(arguments["a"]), float(arguments["b"]))
                    
                case _:
                    raise ValueError(f"Unknown tool: {name}")

            return [
                TextContent(type="text", text=json.dumps(result.model_dump(), indent=2))
            ]

        except Exception as e:
            raise McpError(f"Error processing math operation: {str(e)}")

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)


if __name__ == "__main__":
    import asyncio
    asyncio.run(serve())