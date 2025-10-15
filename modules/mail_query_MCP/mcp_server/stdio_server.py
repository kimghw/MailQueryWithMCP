"""STDIO server implementation for MCP"""

import asyncio
import logging
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server

from .handlers import MCPHandlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_stdio_server():
    """Run the MCP server in STDIO mode"""
    logger.info("Starting MCP server in STDIO mode...")

    # Create MCP server
    server = Server("mail-query-mcp")

    # Create handlers
    handlers = MCPHandlers()

    # Register handlers
    @server.list_tools()
    async def list_tools():
        return await handlers.handle_list_tools()

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        result = await handlers.handle_call_tool(name, arguments)
        return result

    @server.list_prompts()
    async def list_prompts():
        return await handlers.handle_list_prompts()

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict):
        return await handlers.handle_get_prompt(name, arguments)

    # Run the server with STDIO transport
    logger.info("STDIO server running. Waiting for input...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main():
    """Main entry point for STDIO server"""
    try:
        asyncio.run(run_stdio_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()