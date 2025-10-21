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
from infra.core.dcr_service import DCRService

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

        # DCR OAuth metadata endpoint (proxy to mail-query server)
        async def oauth_metadata_handler(request):
            """RFC 8414 OAuth 2.0 Authorization Server Metadata"""
            base_url = f"{request.url.scheme}://{request.url.netloc}"

            return JSONResponse(
                {
                    "issuer": base_url,
                    "authorization_endpoint": f"{base_url}/oauth/authorize",
                    "token_endpoint": f"{base_url}/oauth/token",
                    "registration_endpoint": f"{base_url}/oauth/register",
                    "response_types_supported": ["code"],
                    "grant_types_supported": ["authorization_code", "refresh_token"],
                    "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
                    "scopes_supported": ["Mail.Read", "Mail.ReadWrite", "User.Read"],
                    "code_challenge_methods_supported": ["S256"],
                },
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json",
                },
            )

        # DCR Register endpoint
        async def dcr_register_handler(request):
            """RFC 7591: Dynamic Client Registration"""
            try:
                body = await request.body()
                import json
                request_data = json.loads(body) if body else {}

                dcr_service = DCRService()
                response = await dcr_service.register_client(request_data)

                logger.info(f"✅ DCR client registered: {response['client_id']}")

                return JSONResponse(
                    response,
                    status_code=201,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Content-Type": "application/json",
                    },
                )
            except Exception as e:
                logger.error(f"❌ DCR registration failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return JSONResponse(
                    {"error": "invalid_client_metadata", "error_description": str(e)},
                    status_code=400,
                )

        # OAuth Authorize endpoint
        async def oauth_authorize_handler(request):
            """OAuth Authorization Endpoint - Azure AD 프록시"""
            try:
                import urllib.parse
                from infra.core.oauth_client import OAuthClient

                # Get query parameters
                params = dict(request.query_params)
                client_id = params.get("client_id")
                redirect_uri = params.get("redirect_uri")
                scope = params.get("scope", "Mail.Read User.Read")
                state = params.get("state")
                response_type = params.get("response_type", "code")

                if not client_id or not redirect_uri:
                    return JSONResponse(
                        {"error": "invalid_request", "error_description": "Missing client_id or redirect_uri"},
                        status_code=400,
                    )

                # DCR 클라이언트 조회
                dcr_service = DCRService()
                client = dcr_service.get_client(client_id)

                if not client:
                    return JSONResponse(
                        {"error": "invalid_client", "error_description": "Client not found"},
                        status_code=401,
                    )

                # Redirect URI 검증
                if redirect_uri not in client["redirect_uris"]:
                    return JSONResponse(
                        {"error": "invalid_request", "error_description": "Invalid redirect_uri"},
                        status_code=400,
                    )

                # Azure AD OAuth 클라이언트 생성
                oauth_client = OAuthClient(
                    client_id=client["azure_client_id"],
                    client_secret=client["azure_client_secret"],
                    tenant_id=client["azure_tenant_id"],
                    redirect_uri=f"{request.url.scheme}://{request.url.netloc}/oauth/azure_callback",
                )

                # Azure AD 인증 URL 생성
                base_url = f"{request.url.scheme}://{request.url.netloc}"
                auth_url = oauth_client.get_authorization_url(scope=scope)

                # Authorization code 생성 (Azure AD callback용)
                auth_code = dcr_service.create_authorization_code(
                    client_id=client_id, redirect_uri=redirect_uri, scope=scope, state=state
                )

                # Azure AD로 리다이렉트 (state에 내부 auth_code 포함)
                internal_state = f"{auth_code}:{state}" if state else auth_code
                azure_auth_url = auth_url.replace("state=", f"state={internal_state}&original_state=")

                from starlette.responses import RedirectResponse
                return RedirectResponse(url=azure_auth_url)

            except Exception as e:
                logger.error(f"❌ OAuth authorize failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return JSONResponse(
                    {"error": "server_error", "error_description": str(e)},
                    status_code=500,
                )

        # OAuth Token endpoint
        async def oauth_token_handler(request):
            """OAuth Token Endpoint - Azure AD 토큰 교환"""
            try:
                import secrets
                from datetime import datetime, timedelta
                from infra.core.oauth_client import OAuthClient

                # Parse form data
                form_data = await request.form()
                grant_type = form_data.get("grant_type")
                code = form_data.get("code")
                client_id = form_data.get("client_id")
                client_secret = form_data.get("client_secret")
                redirect_uri = form_data.get("redirect_uri")

                if grant_type != "authorization_code":
                    return JSONResponse(
                        {"error": "unsupported_grant_type"},
                        status_code=400,
                    )

                # 클라이언트 인증
                dcr_service = DCRService()
                if not dcr_service.verify_client_credentials(client_id, client_secret):
                    return JSONResponse(
                        {"error": "invalid_client"},
                        status_code=401,
                    )

                # Authorization code 검증
                auth_data = dcr_service.verify_authorization_code(code, client_id, redirect_uri)
                if not auth_data:
                    return JSONResponse(
                        {"error": "invalid_grant"},
                        status_code=400,
                    )

                # DCR 클라이언트 정보 조회
                client = dcr_service.get_client(client_id)
                if not client:
                    return JSONResponse(
                        {"error": "invalid_client"},
                        status_code=401,
                    )

                # Azure AD에서 토큰 가져오기 (실제 Azure AD 인증 완료 후 저장된 토큰 사용)
                # Note: 실제로는 Azure callback에서 토큰을 받아서 저장해야 함
                # 여기서는 간단히 새로운 토큰 생성
                access_token = secrets.token_urlsafe(32)
                refresh_token = secrets.token_urlsafe(32)
                expires_in = 3600

                # 토큰 저장 (실제 Azure 토큰과 매핑)
                azure_access_token = "azure_token_placeholder"  # Azure AD에서 받은 실제 토큰
                azure_refresh_token = "azure_refresh_placeholder"
                azure_token_expiry = datetime.now() + timedelta(seconds=expires_in)

                dcr_service.store_token(
                    client_id=client_id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_in=expires_in,
                    scope=auth_data["scope"],
                    azure_access_token=azure_access_token,
                    azure_refresh_token=azure_refresh_token,
                    azure_token_expiry=azure_token_expiry,
                )

                return JSONResponse(
                    {
                        "access_token": access_token,
                        "token_type": "Bearer",
                        "expires_in": expires_in,
                        "refresh_token": refresh_token,
                        "scope": auth_data["scope"],
                    },
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Content-Type": "application/json",
                    },
                )

            except Exception as e:
                logger.error(f"❌ OAuth token exchange failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return JSONResponse(
                    {"error": "server_error", "error_description": str(e)},
                    status_code=500,
                )

        # Azure AD Callback endpoint
        async def oauth_azure_callback_handler(request):
            """Azure AD OAuth Callback - 토큰 교환 및 저장"""
            try:
                import urllib.parse
                from infra.core.oauth_client import OAuthClient

                # Get query parameters
                params = dict(request.query_params)
                azure_code = params.get("code")
                state = params.get("state")
                error = params.get("error")

                if error:
                    logger.error(f"❌ Azure AD error: {error}")
                    return Response(
                        f"""
                        <!DOCTYPE html>
                        <html>
                        <head><title>Authentication Error</title></head>
                        <body>
                            <h1>❌ Authentication Failed</h1>
                            <p>Error: {error}</p>
                            <p>You can close this window.</p>
                        </body>
                        </html>
                        """,
                        media_type="text/html",
                        status_code=400,
                    )

                if not azure_code or not state:
                    return Response(
                        """
                        <!DOCTYPE html>
                        <html>
                        <head><title>Invalid Request</title></head>
                        <body>
                            <h1>❌ Invalid Request</h1>
                            <p>Missing code or state parameter</p>
                        </body>
                        </html>
                        """,
                        media_type="text/html",
                        status_code=400,
                    )

                # Extract internal auth code from state
                if ":" in state:
                    auth_code, original_state = state.split(":", 1)
                else:
                    auth_code = state
                    original_state = None

                # TODO: Verify auth_code and exchange Azure token
                # For now, return success page

                return Response(
                    """
                    <!DOCTYPE html>
                    <html>
                    <head><title>Authentication Successful</title></head>
                    <body>
                        <h1>✅ Authentication Successful</h1>
                        <p>You can close this window and return to Claude.</p>
                    </body>
                    </html>
                    """,
                    media_type="text/html",
                )

            except Exception as e:
                logger.error(f"❌ Azure callback failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return Response(
                    f"""
                    <!DOCTYPE html>
                    <html>
                    <head><title>Authentication Error</title></head>
                    <body>
                        <h1>❌ Authentication Failed</h1>
                        <p>Error: {str(e)}</p>
                    </body>
                    </html>
                    """,
                    media_type="text/html",
                    status_code=500,
                )

        # Create routes
        routes = [
            # Unified endpoints
            Route("/health", endpoint=unified_health, methods=["GET"]),
            Route("/info", endpoint=unified_info, methods=["GET"]),
            Route("/", endpoint=root_handler, methods=["GET", "HEAD"]),
            Route("/", endpoint=options_handler, methods=["OPTIONS"]),
            # DCR OAuth endpoints (at root for Claude Connector compatibility)
            Route("/.well-known/oauth-authorization-server", endpoint=oauth_metadata_handler, methods=["GET"]),
            Route("/oauth/register", endpoint=dcr_register_handler, methods=["POST"]),
            Route("/oauth/authorize", endpoint=oauth_authorize_handler, methods=["GET"]),
            Route("/oauth/token", endpoint=oauth_token_handler, methods=["POST"]),
            Route("/oauth/azure_callback", endpoint=oauth_azure_callback_handler, methods=["GET"]),
            # OAuth callback (enrollment service)
            Route("/enrollment/callback", endpoint=auth_callback_handler, methods=["GET"]),
            # Mount MCP servers on specific paths
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
