"""HTTP Streaming-based MCP Server for Mail Attachments"""

import asyncio
import json
import logging
import secrets
from typing import Any, Dict

import uvicorn
from mcp.server import NotificationOptions, Server
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from infra.core.auth_logger import get_auth_logger
from infra.core.database import get_database_manager
from infra.core.logger import get_logger
from .handlers import MCPHandlers

logger = get_logger(__name__)
auth_logger = get_auth_logger()


class HTTPStreamingMailAttachmentServer:
    """HTTP Streaming-based MCP Server for Mail Attachments"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8002):
        self.host = host
        self.port = port

        # MCP Server
        self.mcp_server = Server("mail-attachment-server")

        # Database
        self.db = get_database_manager()

        # Initialize database connection and check authentication
        self._initialize_and_check_auth()

        # MCP Handlers
        self.handlers = MCPHandlers()

        # Active sessions
        self.sessions: Dict[str, Dict[str, Any]] = {}

        # Create Starlette app
        self.app = self._create_app()

        logger.info(f"🚀 HTTP Streaming Mail Attachment Server initialized on port {port}")
    
    def _initialize_and_check_auth(self):
        """Initialize database connection and check authentication status"""
        logger.info("🔍 Initializing database and checking authentication...")
        
        try:
            # Force database connection initialization
            query = "SELECT COUNT(*) FROM accounts WHERE is_active = 1"
            result = self.db.fetch_one(query)
            active_accounts = result[0] if result else 0
            
            logger.info(f"✅ Database connection successful")
            logger.info(f"📊 Active accounts found: {active_accounts}")
            
            # Check authentication status for all active accounts
            if active_accounts > 0:
                auth_query = """
                SELECT user_id, 
                       CASE 
                           WHEN access_token IS NOT NULL AND token_expiry > datetime('now') THEN 'VALID'
                           WHEN refresh_token IS NOT NULL THEN 'REFRESH_NEEDED'
                           ELSE 'EXPIRED'
                       END as auth_status
                FROM accounts 
                WHERE is_active = 1
                ORDER BY user_id
                """
                auth_results = self.db.fetch_all(auth_query)
                
                logger.info("🔐 Authentication status:")
                
                # Count by status
                valid_count = sum(1 for row in auth_results if row[1] == "VALID")
                refresh_count = sum(1 for row in auth_results if row[1] == "REFRESH_NEEDED")
                expired_count = sum(1 for row in auth_results if row[1] == "EXPIRED")
                
                for row in auth_results:
                    user_id, status = row
                    status_emoji = "✅" if status == "VALID" else "⚠️" if status == "REFRESH_NEEDED" else "❌"
                    logger.info(f"   {status_emoji} {user_id}: {status}")
                    auth_logger.log_authentication(user_id, status, "server startup check")
                
                # Log batch check summary
                auth_logger.log_batch_auth_check(
                    active_accounts, valid_count, refresh_count, expired_count
                )
            else:
                logger.warning("⚠️ No active accounts found in database")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize database or check auth: {str(e)}")
            raise
    
    async def _send_list_changed_notifications(self, request: Request):
        """Send list changed notifications after initialization"""
        # Wait a bit to ensure client is ready
        await asyncio.sleep(0.1)
        
        # Note: In a real implementation, we would need to track the client's SSE connection
        # For now, we'll just log that we would send these
        logger.info("📤 Would send notifications/tools/list_changed")
        logger.info("📤 Would send notifications/prompts/list_changed")
        logger.info("📤 Would send notifications/resources/list_changed")
    
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
            
            # If this is the initialized notification, send list changed notifications
            if method == "notifications/initialized":
                # Send tools list changed notification after a short delay
                asyncio.create_task(self._send_list_changed_notifications(request))
            
            return Response(status_code=202, headers=base_headers)
        
        # Process based on method
        logger.info(f"📤 Processing method: {method} with params: {params}")
        
        if method == "initialize":
            # Initialize session with standard Mcp-Session-Id
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
            # Fix tools and prompts to show they are available
            if caps_dict.get("tools") is None:
                caps_dict["tools"] = {"listChanged": True}
            if caps_dict.get("prompts") is None:
                caps_dict["prompts"] = {"listChanged": True}
            # Remove completions field if it's null (not supported by this server)
            if caps_dict.get("completions") is None:
                caps_dict.pop("completions", None)
            
            self.sessions[session_id] = {
                "initialized": True, 
                "capabilities": caps_dict,
                "query_count": 0,  # 쿼리 횟수 추적
                "last_query_params": {}  # 마지막 쿼리 파라미터 저장
            }
            
            # Use the protocol version requested by the client
            requested_version = params.get("protocolVersion", "2025-06-18")
            
            # Add session header and ensure it's exposed
            headers = base_headers.copy()
            headers["Mcp-Session-Id"] = session_id
            headers["MCP-Protocol-Version"] = requested_version
            headers["Access-Control-Expose-Headers"] = "Mcp-Session-Id, MCP-Protocol-Version"
            
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": requested_version,
                    # Use fixed capabilities (with logging as empty object)
                    "capabilities": caps_dict,
                    "serverInfo": {
                        "name": "mail-attachment-server",
                        "title": "📧 Mail Attachment Server",
                        "version": "2.0.0",
                        "description": "MCP server for email attachment handling",
                    },
                    "instructions": "이메일과 첨부파일을 조회하고 텍스트로 변환하는 MCP 서버입니다.",
                },
            }
            logger.info(f"📤 Sending initialize response: {json.dumps(response, indent=2)}")
            return JSONResponse(response, headers=headers)
        
        elif method == "tools/list":
            # List tools
            tools = await self.handlers.handle_list_tools()
            
            # Clean up tool data - remove null fields
            tools_data = []
            for tool in tools:
                tool_dict = tool.model_dump()
                # Remove null fields as per spec
                cleaned_tool = {}
                for key, value in tool_dict.items():
                    if value is not None:
                        cleaned_tool[key] = value
                tools_data.append(cleaned_tool)
            
            # Debug: Log the actual tool data being sent
            logger.info(f"📤 Tool data details: {json.dumps(tools_data, indent=2)}")
            
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
            # Resources not supported, return empty list
            response = {"jsonrpc": "2.0", "id": request_id, "result": {"resources": []}}
            return JSONResponse(response, headers=base_headers)
        
        elif method == "prompts/get":
            # Get prompt
            prompt_name = params.get("name")
            prompt_args = params.get("arguments", {})
            
            try:
                prompt_msg = await self.handlers.handle_get_prompt(prompt_name, prompt_args)
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"messages": [prompt_msg.model_dump()]},
                }
            except Exception as e:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32603, "message": str(e)},
                }
            
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
                    "server": "mail-attachment-server",
                    "version": "2.0.0",
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
                    "name": "mail-attachment-server",
                    "version": "2.0.0",
                    "protocol": "mcp",
                    "transport": "http-streaming",
                    "endpoints": {
                        "streaming": "/stream",
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
        
        # Root endpoint handler
        async def root_handler(request):
            """Handle root endpoint requests"""
            if request.method == "POST":
                # For POST requests, handle as MCP request
                return await self._handle_streaming_request(request)
            else:
                # For GET/HEAD requests, return server info
                return JSONResponse(
                    {
                        "name": "mail-attachment-server",
                        "version": "2.0.0",
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
        
        # Register endpoint - for client registration
        async def register_handler(request):
            """Handle client registration"""
            return JSONResponse(
                {
                    "success": True,
                    "message": "No registration required - this is an open server",
                    "endpoint": "/stream",
                },
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                },
            )
        
        # OAuth discovery endpoints - indicate no auth required
        async def oauth_authorization_server(request):
            """OAuth authorization server metadata - returns empty to indicate no auth"""
            # Return 404 to indicate OAuth is not supported
            return JSONResponse(
                {"error": "OAuth not supported - this server does not require authentication"},
                status_code=404,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json",
                },
            )
        
        async def oauth_protected_resource(request):
            """OAuth protected resource metadata - returns empty to indicate no auth"""
            # Return 404 to indicate this resource is not OAuth protected
            return JSONResponse(
                {"error": "This resource does not require authentication"},
                status_code=404,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json",
                },
            )
        
        # Create routes
        routes = [
            # Root endpoint
            Route("/", endpoint=root_handler, methods=["GET", "POST", "HEAD"]),
            Route("/", endpoint=options_handler, methods=["OPTIONS"]),
            # MCP endpoint (alias for root)
            Route("/mcp", endpoint=self._handle_streaming_request, methods=["POST"]),
            Route("/mcp", endpoint=options_handler, methods=["OPTIONS"]),
            # Register endpoint
            Route("/register", endpoint=register_handler, methods=["POST"]),
            Route("/register", endpoint=options_handler, methods=["OPTIONS"]),
            # Health and info endpoints
            Route("/health", endpoint=health_check, methods=["GET"]),
            Route("/info", endpoint=server_info, methods=["GET"]),
            # Streaming endpoints (both /stream and /steam for compatibility)
            Route("/stream", endpoint=self._handle_streaming_request, methods=["POST"]),
            Route("/steam", endpoint=self._handle_streaming_request, methods=["POST", "GET", "HEAD"]),
            Route("/stream", endpoint=options_handler, methods=["OPTIONS"]),
            Route("/steam", endpoint=options_handler, methods=["OPTIONS"]),
            Route("/health", endpoint=options_handler, methods=["OPTIONS"]),
            Route("/info", endpoint=options_handler, methods=["OPTIONS"]),
            # OAuth discovery endpoints
            Route("/.well-known/oauth-authorization-server", endpoint=oauth_authorization_server, methods=["GET"]),
            Route("/.well-known/oauth-protected-resource", endpoint=oauth_protected_resource, methods=["GET"]),
            Route("/.well-known/oauth-authorization-server/stream", endpoint=oauth_authorization_server, methods=["GET"]),
            Route("/.well-known/oauth-protected-resource/stream", endpoint=oauth_protected_resource, methods=["GET"]),
            Route("/.well-known/oauth-authorization-server/steam", endpoint=oauth_authorization_server, methods=["GET"]),
            Route("/.well-known/oauth-protected-resource/steam", endpoint=oauth_protected_resource, methods=["GET"]),
        ]
        
        return Starlette(routes=routes)
    
    def run(self):
        """Run the HTTP streaming MCP server"""
        logger.info(f"🚀 Starting HTTP Streaming Mail Attachment Server on http://{self.host}:{self.port}")
        logger.info(f"📧 Streaming endpoint: http://{self.host}:{self.port}/stream")
        logger.info(f"💚 Health check: http://{self.host}:{self.port}/health")
        logger.info(f"ℹ️  Server info: http://{self.host}:{self.port}/info")
        
        # Run uvicorn
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")