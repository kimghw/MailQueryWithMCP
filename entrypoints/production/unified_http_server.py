#!/usr/bin/env python3
"""Unified MCP HTTP Server

Single HTTP server instance serving multiple MCP servers on different paths:
- /mail-query/* - Mail Query MCP Server
- /enrollment/* - Enrollment MCP Server
- /onenote/* - OneNote MCP Server
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env file
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment variables from {env_file}")

from modules.mail_query_MCP.mcp_server.http_server import HTTPStreamingMailAttachmentServer
from modules.enrollment.mcp_server.http_server import HTTPStreamingAuthServer
from modules.onenote_mcp.mcp_server.http_server import HTTPStreamingOneNoteServer
from modules.enrollment.auth import get_auth_orchestrator
from modules.enrollment.auth.auth_web_server import AuthWebServer
from infra.core.logger import get_logger

logger = get_logger(__name__)


class UnifiedMCPServer:
    """Unified HTTP server hosting multiple MCP servers on different paths"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        self.host = host
        self.port = port

        logger.info("🚀 Initializing Unified MCP Server")

        # Initialize individual MCP servers (don't run them, just get their apps)
        logger.info("📧 Initializing Mail Query MCP Server...")
        self.mail_query_server = HTTPStreamingMailAttachmentServer(host=host, port=port)

        logger.info("🔐 Initializing Enrollment MCP Server...")
        self.enrollment_server = HTTPStreamingAuthServer(host=host, port=port)

        logger.info("📝 Initializing OneNote MCP Server...")
        self.onenote_server = HTTPStreamingOneNoteServer(host=host, port=port)

        # Initialize Auth Web Server for OAuth callback handling
        logger.info("🔐 Initializing Auth Web Server for OAuth callbacks...")
        self.auth_web_server = AuthWebServer()
        # Set session store from auth orchestrator
        orchestrator = get_auth_orchestrator()
        self.auth_web_server.set_session_store(orchestrator.auth_sessions)

        # Create unified Starlette app
        self.app = self._create_unified_app()

        logger.info("✅ Unified MCP Server initialized")

    def _create_unified_app(self):
        """Create unified Starlette application with multiple MCP servers"""

        # Health check endpoint
        async def unified_health(request):
            return JSONResponse(
                {
                    "status": "healthy",
                    "server": "unified-mcp-server",
                    "version": "1.0.0",
                    "services": {
                        "mail-query": "running",
                        "enrollment": "running",
                        "onenote": "running",
                    },
                    "endpoints": {
                        "mail-query": "/mail-query/",
                        "enrollment": "/enrollment/",
                        "onenote": "/onenote/",
                    },
                },
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Mcp-Session-Id, MCP-Protocol-Version",
                },
            )

        # Server info endpoint
        async def unified_info(request):
            return JSONResponse(
                {
                    "name": "unified-mcp-server",
                    "version": "1.0.0",
                    "protocol": "mcp",
                    "transport": "http",
                    "services": [
                        {
                            "name": "mail-query-server",
                            "path": "/mail-query",
                            "description": "Email and attachment management",
                        },
                        {
                            "name": "enrollment-server",
                            "path": "/enrollment",
                            "description": "Account registration and authentication",
                        },
                        {
                            "name": "onenote-server",
                            "path": "/onenote",
                            "description": "OneNote notebooks, sections, and pages management",
                        },
                    ],
                    "endpoints": {
                        "health": "/health",
                        "info": "/info",
                    },
                }
            )

        # Root endpoint
        async def root_handler(request):
            return JSONResponse(
                {
                    "name": "unified-mcp-server",
                    "version": "1.0.0",
                    "message": "Unified MCP Server - Multiple MCP services on different paths",
                    "services": {
                        "mail-query": "/mail-query/",
                        "enrollment": "/enrollment/",
                        "onenote": "/onenote/",
                    },
                    "endpoints": {
                        "health": "/health",
                        "info": "/info",
                    },
                },
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                },
            )

        # OPTIONS handler for CORS
        async def options_handler(request):
            return Response(
                "",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS, DELETE",
                    "Access-Control-Allow-Headers": "Content-Type, Mcp-Session-Id, Authorization, MCP-Protocol-Version",
                    "Access-Control-Expose-Headers": "Mcp-Session-Id",
                    "Access-Control-Max-Age": "3600",
                },
            )

        # OAuth callback handler
        async def auth_callback_handler(request):
            """Handle OAuth callback from Microsoft"""
            import asyncio
            try:
                # Get query parameters
                params = dict(request.query_params)

                # Run synchronous callback in executor to avoid event loop conflicts
                loop = asyncio.get_running_loop()
                html_response = await loop.run_in_executor(
                    None,
                    self.auth_web_server._process_callback,
                    params
                )

                return Response(
                    html_response,
                    media_type="text/html",
                    headers={
                        "Access-Control-Allow-Origin": "*",
                    }
                )
            except Exception as e:
                logger.error(f"OAuth callback failed: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                error_html = f"""
                <!DOCTYPE html>
                <html>
                <head><title>Authentication Error</title></head>
                <body>
                    <h1>❌ Authentication Failed</h1>
                    <p>Error: {str(e)}</p>
                    <p>You can close this window.</p>
                </body>
                </html>
                """
                return Response(
                    error_html,
                    media_type="text/html",
                    status_code=500
                )

        # Create routes
        routes = [
            # Root endpoints
            Route("/", endpoint=root_handler, methods=["GET"]),
            Route("/", endpoint=options_handler, methods=["OPTIONS"]),
            Route("/health", endpoint=unified_health, methods=["GET"]),
            Route("/info", endpoint=unified_info, methods=["GET"]),
            # OAuth callback (enrollment service)
            Route("/enrollment/callback", endpoint=auth_callback_handler, methods=["GET"]),
            # Mount MCP servers on different paths
            Mount("/mail-query", app=self.mail_query_server.app),
            Mount("/enrollment", app=self.enrollment_server.app),
            Mount("/onenote", app=self.onenote_server.app),
        ]

        return Starlette(routes=routes)

    def run(self):
        """Run the unified HTTP server"""
        logger.info("=" * 80)
        logger.info(f"🚀 Starting Unified MCP Server on http://{self.host}:{self.port}")
        logger.info("=" * 80)
        logger.info(f"📧 Mail Query MCP: http://{self.host}:{self.port}/mail-query/")
        logger.info(f"🔐 Enrollment MCP: http://{self.host}:{self.port}/enrollment/")
        logger.info(f"📝 OneNote MCP: http://{self.host}:{self.port}/onenote/")
        logger.info("-" * 80)
        logger.info(f"💚 Health check: http://{self.host}:{self.port}/health")
        logger.info(f"ℹ️  Server info: http://{self.host}:{self.port}/info")
        logger.info("=" * 80)

        # Run uvicorn
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")


def main():
    """Main entry point for unified HTTP MCP server"""
    parser = argparse.ArgumentParser(description="Unified MCP HTTP Server")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT") or os.getenv("PORT") or "8000"),
        help="Port for HTTP server (default: 8000, or MCP_PORT/PORT env var)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_HOST") or "0.0.0.0",
        help="Host for HTTP server (default: 0.0.0.0, or MCP_HOST env var)",
    )

    args = parser.parse_args()

    logger.info("🚀 Starting Unified MCP HTTP Server")
    logger.info(f"📁 Project root: {PROJECT_ROOT}")
    logger.info(f"🌐 Server will listen on {args.host}:{args.port}")

    # Create and run unified server
    server = UnifiedMCPServer(host=args.host, port=args.port)
    server.run()


if __name__ == "__main__":
    main()
