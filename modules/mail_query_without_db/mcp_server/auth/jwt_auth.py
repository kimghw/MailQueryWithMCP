"""JWT-based authentication for MCP server

Simple JWT authentication without full OAuth 2.0 flow.
Generate tokens manually or via a simple endpoint.
"""

import os
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
from starlette.requests import Request
from starlette.responses import JSONResponse

class JWTAuth:
    """JWT Bearer token authentication"""

    def __init__(self):
        # JWT secret from environment
        self.secret = os.getenv("JWT_SECRET")
        self.algorithm = "HS256"
        self.enabled = bool(self.secret)

    def create_token(self, user_id: str, expires_hours: int = 24) -> str:
        """Create a JWT token for a user"""
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(hours=expires_hours),
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def verify_request(self, request: Request) -> Optional[JSONResponse]:
        """Verify request has valid JWT token"""
        if not self.enabled:
            return None

        # Skip auth for health/info
        if request.url.path in ["/health", "/info"]:
            return None

        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32001,
                        "message": "Missing Bearer token. Use: Authorization: Bearer <token>"
                    }
                },
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"}
            )

        token = auth_header.replace("Bearer ", "")
        payload = self.verify_token(token)

        if not payload:
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32002,
                        "message": "Invalid or expired token"
                    }
                },
                status_code=403
            )

        # Store user info in request state for later use
        request.state.user_id = payload.get("user_id")
        return None


# Helper function to generate tokens
def generate_token(user_id: str):
    """Generate a token for manual distribution"""
    auth = JWTAuth()
    if not auth.enabled:
        print("Error: JWT_SECRET not set")
        return None

    token = auth.create_token(user_id)
    print(f"Token for {user_id}:")
    print(token)
    return token


if __name__ == "__main__":
    # Example: python -m modules.mail_query_without_db.mcp_server.jwt_auth
    import sys
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
        generate_token(user_id)
    else:
        print("Usage: python jwt_auth.py <user_id>")
