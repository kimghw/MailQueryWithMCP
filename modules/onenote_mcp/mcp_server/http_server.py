"""HTTP Streaming-based MCP Server for OneNote

This server uses Starlette for MCP protocol implementation and FastAPI for OpenAPI documentation.
"""

import asyncio
import json
import secrets
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, Request as FastAPIRequest
from fastapi.responses import JSONResponse as FastAPIJSONResponse
from mcp.server import NotificationOptions, Server
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from infra.core.logger import get_logger
from modules.onenote_mcp.handlers import OneNoteHandlers
from modules.onenote_mcp.db_service import OneNoteDBService

logger = get_logger(__name__)


class HTTPStreamingOneNoteServer:
    """HTTP Streaming-based MCP Server for OneNote"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8003):
        self.host = host
        self.port = port

        # MCP Server
        self.mcp_server = Server("onenote-server")

        # Database
        self.db_service = OneNoteDBService()
        self.db_service.initialize_tables()

        # MCP Handlers
        self.handlers = OneNoteHandlers()

        # Active sessions
        self.sessions: Dict[str, Dict[str, Any]] = {}

        # Create Starlette app (actual MCP server)
        self.starlette_app = self._create_app()

        # Create FastAPI wrapper (for OpenAPI documentation)
        self.app = self._create_fastapi_wrapper()

        logger.info(f"🚀 HTTP Streaming OneNote Server initialized on port {port}")

    async def _handle_streaming_request(self, request: Request):
        """Handle MCP request - returns single JSON response"""
        # Common headers
        base_headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS, DELETE",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Mcp-Session-Id, MCP-Protocol-Version",
            "Access-Control-Expose-Headers": "Mcp-Session-Id",
        }

        # Bearer token authentication handled by unified_http_server middleware
        # request.state.azure_token is available if ENABLE_OAUTH_AUTH=true

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

            # Fix null fields to empty objects/lists for spec compliance
            caps_dict = caps.model_dump()
            if caps_dict.get("logging") is None:
                caps_dict["logging"] = {}
            if caps_dict.get("resources") is None:
                caps_dict["resources"] = {"listChanged": False}
            if caps_dict.get("tools") is None:
                caps_dict["tools"] = {"listChanged": True}
            if caps_dict.get("prompts") is None:
                caps_dict["prompts"] = {"listChanged": False}
            if caps_dict.get("completions") is None:
                caps_dict.pop("completions", None)

            self.sessions[session_id] = {
                "initialized": True,
                "capabilities": caps_dict,
            }

            # Use the protocol version requested by the client
            requested_version = params.get("protocolVersion", "2025-06-18")

            # Add session header
            headers = base_headers.copy()
            headers["Mcp-Session-Id"] = session_id
            headers["MCP-Protocol-Version"] = requested_version
            headers["Access-Control-Expose-Headers"] = "Mcp-Session-Id, MCP-Protocol-Version"

            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": requested_version,
                    "capabilities": caps_dict,
                    "serverInfo": {
                        "name": "onenote-server",
                        "title": "📝 OneNote MCP Server",
                        "version": "1.0.0",
                        "description": "MCP server for OneNote notebooks, sections, and pages management",
                    },
                    "instructions": "OneNote 노트북, 섹션, 페이지 조회 및 생성을 위한 MCP 서버입니다.",
                },
            }
            logger.info(f"📤 Sending initialize response")
            return JSONResponse(response, headers=headers)

        elif method == "tools/list":
            # List tools
            tools = await self.handlers.handle_list_tools()

            # Clean up tool data - remove null fields
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

            # Extract authenticated user_id from request.state (set by auth middleware)
            authenticated_user_id = getattr(request.state, "user_id", None)
            if authenticated_user_id:
                logger.info(f"  • Authenticated user_id: {authenticated_user_id}")

            try:
                results = await self.handlers.handle_call_tool(tool_name, tool_args, authenticated_user_id)

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
            # No prompts supported
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"prompts": []},
            }
            return JSONResponse(response, headers=base_headers)

        elif method == "resources/list":
            # No resources supported
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
                    "server": "onenote-server",
                    "version": "1.0.0",
                    "transport": "http-streaming",
                },
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Mcp-Session-Id, MCP-Protocol-Version",
                    "Access-Control-Expose-Headers": "Mcp-Session-Id",
                },
            )

        async def server_info(request):
            """Server information endpoint"""
            return JSONResponse(
                {
                    "name": "onenote-server",
                    "version": "1.0.0",
                    "protocol": "mcp",
                    "transport": "http-streaming",
                    "endpoints": {
                        "mcp": "/",
                        "health": "/health",
                        "info": "/info",
                    },
                }
            )

        # OPTIONS handler for CORS preflight
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

        async def mcp_discovery_handler(request):
            """MCP Server Discovery - /.well-known/mcp.json

            Note: OAuth is handled at the unified server level (root /.well-known/mcp.json)
            Individual MCP servers no longer expose OAuth endpoints to prevent
            Claude.ai from requesting separate authentication for each service.
            """
            return JSONResponse(
                {
                    "mcp_version": "1.0",
                    "name": "OneNote MCP Server",
                    "description": "OneNote notebooks, sections, and pages management service",
                    "version": "1.0.0",
                    "capabilities": {
                        "tools": True,
                        "resources": False,
                        "prompts": False
                    }
                },
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json",
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
                        "name": "onenote-server",
                        "version": "1.0.0",
                        "protocol": "mcp",
                        "transport": "http",
                        "endpoints": {"mcp": "/", "health": "/health", "info": "/info"},
                    },
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "GET, POST, OPTIONS, HEAD, DELETE",
                        "Access-Control-Allow-Headers": "Content-Type, Mcp-Session-Id, Authorization, MCP-Protocol-Version",
                        "Access-Control-Expose-Headers": "Mcp-Session-Id",
                    },
                )

        # Create routes
        routes = [
            # Root endpoint
            Route("/", endpoint=root_handler, methods=["GET", "POST", "HEAD"]),
            Route("/", endpoint=options_handler, methods=["OPTIONS"]),
            # MCP Discovery - REMOVED from Starlette (handled by FastAPI)
            # Health and info endpoints
            Route("/health", endpoint=health_check, methods=["GET"]),
            Route("/info", endpoint=server_info, methods=["GET"]),
            Route("/health", endpoint=options_handler, methods=["OPTIONS"]),
            Route("/info", endpoint=options_handler, methods=["OPTIONS"]),
        ]

        return Starlette(routes=routes)

    def _create_fastapi_wrapper(self):
        """Create FastAPI wrapper for OpenAPI documentation

        This wraps the Starlette MCP server with FastAPI to provide:
        - /docs - Swagger UI documentation
        - /redoc - ReDoc documentation
        - /openapi.json - OpenAPI schema

        The actual MCP protocol is still handled by Starlette.
        """
        from pydantic import BaseModel, Field

        # Create FastAPI app
        fastapi_app = FastAPI(
            title="📝 OneNote MCP Server",
            description="""
## OneNote MCP Server

MCP (Model Context Protocol) server for OneNote notebooks, sections, and pages management.

### Features
- 📓 Notebook listing and management
- 📑 Section creation and listing
- 📄 Page creation, reading, and updating
- 🔐 Integrated authentication support

### MCP Protocol
This server implements the MCP protocol (JSON-RPC 2.0).
All MCP requests should be sent to the root endpoint `/` as POST requests.

### Tools Available
1. **list_notebooks** - List user's OneNote notebooks
2. **create_section** - Create new section in a notebook
3. **list_sections** - List sections in a notebook
4. **list_pages** - List pages in a section
5. **get_page_content** - Get page content
6. **create_page** - Create new page
7. **update_page** - Update existing page
            """,
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
            openapi_url="/openapi.json",
        )

        # Pydantic models for documentation
        class MCPRequest(BaseModel):
            jsonrpc: str = Field("2.0", description="JSON-RPC version")
            method: str = Field(..., description="MCP method name (e.g., 'tools/list', 'tools/call')")
            params: Optional[Dict[str, Any]] = Field(default={}, description="Method parameters")
            id: Optional[int] = Field(None, description="Request ID for correlation")

            class Config:
                json_schema_extra = {
                    "examples": [
                        {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "tools/list",
                            "params": {}
                        }
                    ]
                }

        class MCPResponse(BaseModel):
            jsonrpc: str = Field("2.0", description="JSON-RPC version")
            result: Optional[Dict[str, Any]] = Field(None, description="Result data")
            error: Optional[Dict[str, Any]] = Field(None, description="Error information")
            id: Optional[int] = Field(None, description="Request ID for correlation")

        # Mount Starlette MCP app
        fastapi_app.mount("/mcp", self.starlette_app)

        # Add documentation endpoints
        @fastapi_app.post(
            "/",
            response_model=MCPResponse,
            summary="MCP Protocol Endpoint",
            description="""
Send MCP (Model Context Protocol) requests using JSON-RPC 2.0 format.

**Common Methods:**
- `initialize` - Initialize MCP session
- `tools/list` - List available tools
- `tools/call` - Call a specific tool
            """,
            tags=["MCP Protocol"],
        )
        async def mcp_endpoint(request: FastAPIRequest):
            """MCP Protocol endpoint - delegates to Starlette app"""
            from starlette.datastructures import Headers
            starlette_request = Request(request.scope, request.receive)
            response = await self._handle_streaming_request(starlette_request)
            return response

        @fastapi_app.get(
            "/.well-known/mcp.json",
            tags=["MCP Discovery"],
            summary="MCP Server Discovery",
            description="MCP discovery endpoint (OAuth handled at root level)"
        )
        async def mcp_discovery():
            """MCP Server Discovery - OAuth handled by unified server"""
            return {
                "mcp_version": "1.0",
                "name": "OneNote MCP Server",
                "description": "OneNote notebooks, sections, and pages management service",
                "version": "1.0.0",
                "capabilities": {
                    "tools": True,
                    "resources": False,
                    "prompts": False
                }
            }

        @fastapi_app.get(
            "/health",
            tags=["Health"],
            summary="Health Check",
            description="Check if the server is running and healthy"
        )
        async def health_check():
            return {"status": "healthy", "server": "onenote-mcp"}

        @fastapi_app.get(
            "/info",
            tags=["Info"],
            summary="Server Information",
            description="Get server information and capabilities"
        )
        async def server_info():
            return {
                "name": "onenote-mcp-server",
                "version": "1.0.0",
                "protocol": "mcp",
                "transport": "http",
                "tools_count": 7,
                "documentation": f"http://{self.host}:{self.port}/docs"
            }

        logger.info("📚 FastAPI wrapper created - OpenAPI available at /docs")
        return fastapi_app

    def run(self):
        """Run the HTTP streaming MCP server"""
        logger.info(f"🚀 Starting HTTP Streaming OneNote Server on http://{self.host}:{self.port}")
        logger.info(f"📝 MCP endpoint: http://{self.host}:{self.port}/")
        logger.info(f"📚 OpenAPI docs: http://{self.host}:{self.port}/docs")
        logger.info(f"💚 Health check: http://{self.host}:{self.port}/health")
        logger.info(f"ℹ️  Server info: http://{self.host}:{self.port}/info")

        # Run uvicorn with FastAPI app (which wraps Starlette)
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")


def main():
    """Main entry point"""
    server = HTTPStreamingOneNoteServer()
    server.run()


if __name__ == "__main__":
    main()
