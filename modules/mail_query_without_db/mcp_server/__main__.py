"""Main entry point for MCP server

Supports both HTTP and STDIO modes through command-line arguments
"""

import sys
import asyncio
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    """Main entry point with mode selection"""
    parser = argparse.ArgumentParser(description="MCP Server for Mail Query")
    parser.add_argument(
        "--mode",
        choices=["http", "stdio"],
        default="http",
        help="Server mode: http (default) or stdio"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port for HTTP server (default: 3000)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for HTTP server (default: 0.0.0.0)"
    )

    args = parser.parse_args()

    if args.mode == "stdio":
        # Run STDIO server
        from .stdio_server import run_stdio_server
        asyncio.run(run_stdio_server())
    else:
        # Run HTTP server
        from .server import MailAttachmentMCPServer

        server = MailAttachmentMCPServer()
        server.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()