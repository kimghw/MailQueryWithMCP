#!/usr/bin/env python3
"""Local Development - HTTP MCP Server

Entry point for running the MCP server in HTTP mode for local development.
This is the local development version for testing and debugging.
"""

import sys
import os
import argparse
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.mail_query_without_db.mcp_server.http_server import HTTPStreamingMailAttachmentServer
from infra.core.logger import get_logger

logger = get_logger(__name__)


def main():
    """Main entry point for local HTTP MCP server"""
    parser = argparse.ArgumentParser(description="Local Development - MCP HTTP Server for Mail Query")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT") or os.getenv("PORT") or "8002"),
        help="Port for HTTP server (default: 8002, or MCP_PORT/PORT env var)"
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_HOST") or "127.0.0.1",
        help="Host for HTTP server (default: 127.0.0.1 for local dev, use 0.0.0.0 for external access)"
    )

    args = parser.parse_args()

    logger.info("🚀 Starting LOCAL HTTP MCP Mail Attachment Server")
    logger.info(f"📁 Project root: {PROJECT_ROOT}")
    logger.info(f"🌐 Server will listen on {args.host}:{args.port}")

    # Create and run server
    server = HTTPStreamingMailAttachmentServer(host=args.host, port=args.port)
    server.run()


if __name__ == "__main__":
    main()
