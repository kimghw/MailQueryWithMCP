"""HTTP Streaming-based MCP Server for Subscription Tracker"""

import asyncio
import json
import logging
import secrets
from typing import Any, Dict

import uvicorn
from mcp.server import NotificationOptions, Server
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from infra.core.logger import get_logger
from ..config import get_subscription_config
from .handlers import SubscriptionHandlers

logger = get_logger(__name__)


class HTTPStreamingSubscriptionServer:
    """HTTP Streaming-based MCP Server for Subscription Tracking"""

    def __init__(self, host: str = "127.0.0.1", port: int = 8003):
        self.host = host
        self.port = port

        # MCP Server
        self.mcp_server = Server("subscription-tracker-server")

        # Configuration
        self.config = get_subscription_config()

        # MCP Handlers
        self.handlers = SubscriptionHandlers()

        # Active sessions
        self.sessions: Dict[str, Dict[str, Any]] = {}

        # Create Starlette app
        self.app = self._create_app()

        logger.info(f"🚀 HTTP Streaming Subscription Tracker Server initialized on port {port}")

    async def _handle_streaming_request(self, request: Request):
        """Handle MCP request - returns single JSON response"""
        # Common headers
        base_headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Mcp-Session-Id",
            "Access-Control-Expose-Headers": "Mcp-Session-Id",
        }

        # Read and parse request
        try:
            body = await request.body()
            if not body:
                return JSONResponse(
                    {
                        "jsonrpc": "2.0",
                        "error": {"code": -32700, "message": "Empty request body"},
                    },
                    status_code=400,
                    headers=base_headers,
                )

            try:
                rpc_request = json.loads(body)
            except json.JSONDecodeError as e:
                return JSONResponse(
                    {
                        "jsonrpc": "2.0",
                        "error": {"code": -32700, "message": f"Parse error: {str(e)}"},
                    },
                    status_code=400,
                    headers=base_headers,
                )
        except Exception as e:
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                },
                status_code=500,
                headers=base_headers,
            )

        # Extract request details
        method = rpc_request.get("method")
        params = rpc_request.get("params", {}) or {}
        request_id = rpc_request.get("id")

        logger.info(f"📨 Received RPC request: {method} with id: {request_id}")

        # Handle notification (no id) - return 202 with no body
        if request_id is None:
            logger.info(f"📤 Handling notification: {method}")
            return Response(status_code=202, headers=base_headers)

        # Process based on method
        logger.info(f"📤 Processing method: {method} with params: {params}")

        if method == "initialize":
            # Initialize session
            session_id = secrets.token_urlsafe(24)
            caps = self.mcp_server.get_capabilities(
                notification_options=NotificationOptions(), experimental_capabilities={}
            )

            # Fix null fields
            caps_dict = caps.model_dump()
            if caps_dict.get("logging") is None:
                caps_dict["logging"] = {}
            if caps_dict.get("resources") is None:
                caps_dict["resources"] = {"listChanged": False}
            if caps_dict.get("tools") is None:
                caps_dict["tools"] = {"listChanged": False}
            if caps_dict.get("prompts") is None:
                caps_dict["prompts"] = {"listChanged": False}
            if caps_dict.get("completions") is None:
                caps_dict.pop("completions", None)

            self.sessions[session_id] = {
                "initialized": True,
                "capabilities": caps_dict
            }

            # Use the protocol version requested by the client
            requested_version = params.get("protocolVersion", "2025-06-18")

            # Add session header
            headers = base_headers.copy()
            headers["Mcp-Session-Id"] = session_id

            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": requested_version,
                    "capabilities": caps_dict,
                    "serverInfo": {
                        "name": "subscription-tracker-server",
                        "title": "💳 Subscription Tracker Server",
                        "version": "1.0.0",
                        "description": "MCP server for tracking subscription invoices and receipts",
                    },
                    "instructions": "구독 서비스 청구서/영수증을 자동으로 수집하고 Windows 폴더에 저장합니다.",
                },
            }
            logger.info(f"📤 Sending initialize response")
            return JSONResponse(response, headers=headers)

        elif method == "tools/list":
            # List tools
            tools = await self.handlers.handle_list_tools()

            # Clean up tool data
            tools_data = []
            for tool in tools:
                tool_dict = tool.model_dump()
                cleaned_tool = {}
                for key, value in tool_dict.items():
                    if value is not None:
                        cleaned_tool[key] = value
                tools_data.append(cleaned_tool)

            logger.info(f"📤 Returning {len(tools_data)} tools: {[t['name'] for t in tools_data]}")

            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": tools_data},
            }
            return JSONResponse(response, headers=base_headers)

        elif method == "tools/call":
            # Call tool
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            logger.info(f"🔧 [MCP Server] Received tools/call request")
            logger.info(f"  • Tool: {tool_name}")
            logger.info(f"  • Arguments: {json.dumps(tool_args, indent=2, ensure_ascii=False)}")

            try:
                results = await self.handlers.handle_call_tool(tool_name, tool_args)

                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"content": [content.model_dump() for content in results]},
                }
            except Exception as e:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32603, "message": str(e)},
                }

            return JSONResponse(response, headers=base_headers)

        elif method == "prompts/list":
            # List prompts
            prompts = await self.handlers.handle_list_prompts()

            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"prompts": [prompt.model_dump() for prompt in prompts]},
            }
            return JSONResponse(response, headers=base_headers)

        elif method == "resources/list":
            # Resources not supported
            response = {"jsonrpc": "2.0", "id": request_id, "result": {"resources": []}}
            return JSONResponse(response, headers=base_headers)

        else:
            # Unknown method
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
            return JSONResponse(response, status_code=404, headers=base_headers)

    def _create_app(self):
        """Create Starlette application"""

        async def health_check(request):
            """Health check endpoint"""
            return JSONResponse(
                {
                    "status": "healthy",
                    "server": "subscription-tracker-server",
                    "version": "1.0.0",
                    "transport": "http-streaming",
                    "monitored_senders": len(self.config.subscription_senders),
                    "save_path": str(self.config.save_path),
                },
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                },
            )

        async def server_info(request):
            """Server information endpoint"""
            return JSONResponse(
                {
                    "name": "subscription-tracker-server",
                    "version": "1.0.0",
                    "protocol": "mcp",
                    "transport": "http-streaming",
                    "endpoints": {
                        "streaming": "/stream",
                        "health": "/health",
                        "info": "/info",
                    },
                    "configuration": self.config.to_dict()
                }
            )

        # OPTIONS handler for CORS preflight
        async def options_handler(request):
            return Response(
                "",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Mcp-Session-Id",
                    "Access-Control-Expose-Headers": "Mcp-Session-Id",
                    "Access-Control-Max-Age": "3600",
                },
            )

        # Root endpoint handler
        async def root_handler(request):
            """Handle root endpoint requests"""
            if request.method == "POST":
                return await self._handle_streaming_request(request)
            else:
                return JSONResponse(
                    {
                        "name": "subscription-tracker-server",
                        "version": "1.0.0",
                        "protocol": "mcp",
                        "transport": "http",
                        "endpoints": {"mcp": "/", "health": "/health", "info": "/info"},
                    },
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                        "Access-Control-Allow-Headers": "Content-Type",
                    },
                )

        # Create routes
        routes = [
            Route("/", endpoint=root_handler, methods=["GET", "POST", "HEAD"]),
            Route("/", endpoint=options_handler, methods=["OPTIONS"]),
            Route("/health", endpoint=health_check, methods=["GET"]),
            Route("/info", endpoint=server_info, methods=["GET"]),
            Route("/stream", endpoint=self._handle_streaming_request, methods=["POST"]),
            Route("/stream", endpoint=options_handler, methods=["OPTIONS"]),
        ]

        return Starlette(routes=routes)

    def run(self):
        """Run the HTTP streaming MCP server"""
        logger.info(f"🚀 Starting HTTP Streaming Subscription Tracker Server on http://{self.host}:{self.port}")
        logger.info(f"📧 Streaming endpoint: http://{self.host}:{self.port}/stream")
        logger.info(f"💚 Health check: http://{self.host}:{self.port}/health")
        logger.info(f"ℹ️  Server info: http://{self.host}:{self.port}/info")
        logger.info(f"💾 Save path: {self.config.save_path}")

        # Run uvicorn
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")
