"""STDIO server implementation for MCP"""

import asyncio
import logging
from pathlib import Path

from mcp import StdioServer

from .handlers import setup_mcp_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_stdio_server():
    """Run the MCP server in STDIO mode"""
    logger.info("Starting MCP server in STDIO mode...")

    # Create and configure server
    server = StdioServer("mail-query-mcp")

    # Setup handlers
    setup_mcp_server(server)

    # Run the server
    async with server:
        logger.info("STDIO server running. Waiting for input...")
        await server.serve()


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