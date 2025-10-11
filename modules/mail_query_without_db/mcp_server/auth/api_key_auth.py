"""Authentication middleware for MCP server"""

import os
from starlette.requests import Request
from starlette.responses import JSONResponse
from typing import Optional

class AuthMiddleware:
    """API Key authentication middleware"""

    def __init__(self):
        # API keys from environment variable (comma-separated)
        api_keys_str = os.getenv("API_KEYS", "")
        self.api_keys = set(k.strip() for k in api_keys_str.split(",") if k.strip())

        # If no API keys configured, authentication is disabled
        self.enabled = len(self.api_keys) > 0

    def verify_request(self, request: Request) -> Optional[JSONResponse]:
        """
        Verify request has valid API key
        Returns None if valid, JSONResponse with error if invalid
        """
        # Skip auth if not enabled
        if not self.enabled:
            return None

        # Skip auth for health check and info endpoints
        if request.url.path in ["/health", "/info"]:
            return None

        # Get API key from header or query parameter
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")

        if not api_key:
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32001,
                        "message": "Missing API key. Provide X-API-Key header or api_key query parameter."
                    }
                },
                status_code=401,
                headers={
                    "WWW-Authenticate": "ApiKey",
                    "Access-Control-Allow-Origin": "*",
                }
            )

        if api_key not in self.api_keys:
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32002,
                        "message": "Invalid API key"
                    }
                },
                status_code=403,
                headers={"Access-Control-Allow-Origin": "*"}
            )

        return None
