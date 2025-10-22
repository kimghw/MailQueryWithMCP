"""
DCR OAuth 인증 미들웨어

모든 MCP 서버에서 공통으로 사용하는 Bearer 토큰 검증 미들웨어
"""

from starlette.responses import JSONResponse
from modules.dcr_oauth import DCRService
from infra.core.logger import get_logger

logger = get_logger(__name__)


async def verify_bearer_token_middleware(request, call_next=None):
    """
    Bearer 토큰 검증 미들웨어

    Returns:
        - None if authentication succeeds (token stored in request.state.azure_token)
        - JSONResponse with 401 if authentication fails
    """
    # Skip authentication for certain paths
    path = request.url.path

    # OAuth 엔드포인트와 메타데이터는 인증 제외
    excluded_paths = [
        "/.well-known/",
        "/oauth/",
        "/health",
        "/info",
        "/enrollment/callback"  # Enrollment 서비스의 OAuth 콜백만 제외
    ]

    if any(path.startswith(excluded) for excluded in excluded_paths):
        return None  # Skip authentication

    # OPTIONS 요청은 인증 제외
    if request.method == "OPTIONS":
        return None

    # Get Authorization header
    auth_header = request.headers.get("Authorization", "")

    # Check Bearer token
    if not auth_header.startswith("Bearer "):
        logger.warning(f"⚠️ Missing Bearer token for path: {path}")
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32001,
                    "message": "Authentication required. Please authenticate using OAuth 2.0"
                },
            },
            status_code=401,
            headers={
                "WWW-Authenticate": 'Bearer realm="MCP Server", error="invalid_token"',
                "Access-Control-Allow-Origin": "*",
            },
        )

    token = auth_header[7:]  # Remove "Bearer " prefix

    try:
        # Verify token using DCR service
        dcr_service = DCRService()
        token_data = dcr_service.verify_bearer_token(token)

        if token_data:
            # Store Azure token in request state for handlers to use
            request.state.azure_token = token_data["azure_access_token"]
            request.state.token_scope = token_data.get("scope", "")
            request.state.dcr_client_id = token_data.get("dcr_client_id", "")
            request.state.azure_object_id = token_data.get("azure_object_id", "")

            logger.info(f"✅ Authenticated DCR client: {token_data['dcr_client_id']} for {path}")
            return None  # Authentication successful
        else:
            logger.warning(f"⚠️ Invalid Bearer token for path: {path}")
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "error": {"code": -32001, "message": "Invalid authentication token"},
                },
                status_code=401,
                headers={
                    "WWW-Authenticate": 'Bearer realm="MCP Server", error="invalid_token"',
                    "Access-Control-Allow-Origin": "*",
                },
            )
    except Exception as e:
        logger.error(f"❌ Token verification failed: {str(e)}")
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "error": {"code": -32001, "message": f"Authentication error: {str(e)}"},
            },
            status_code=401,
            headers={
                "WWW-Authenticate": 'Bearer realm="MCP Server", error="invalid_token"',
                "Access-Control-Allow-Origin": "*",
            },
        )