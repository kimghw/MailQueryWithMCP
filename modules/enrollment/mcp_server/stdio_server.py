"""STDIO server implementation for MCP

This module provides a reusable function to run the MCP server in STDIO mode.
For standalone execution, use: modules/enrollment/entrypoints/run_stdio.py
"""

from mcp.server import Server
from mcp.server.stdio import stdio_server

from .handlers import AuthAccountHandlers


async def run_stdio_server():
    """
    Run the MCP server in STDIO mode (library function)

    This is a reusable function that can be called from entrypoints.
    Does NOT include initialization, logging setup, or error handling.
    Caller is responsible for those.

    Returns:
        None - runs indefinitely until interrupted
    """
    # Create MCP server
    server = Server("auth-account-server")
    handlers = AuthAccountHandlers()

    # Register handlers
    @server.list_tools()
    async def list_tools():
        return await handlers.handle_list_tools()

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        return await handlers.handle_call_tool(name, arguments)

    @server.list_prompts()
    async def list_prompts():
        return await handlers.handle_list_prompts()

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict):
        return await handlers.handle_get_prompt(name, arguments)

    # Run the server with STDIO transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )
