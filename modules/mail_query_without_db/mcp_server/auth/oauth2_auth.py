"""OAuth 2.0 authentication using external provider

Supports Auth0, Clerk, Supabase, or any OAuth 2.0 provider.
Validates JWT tokens issued by the provider.
"""

import os
import requests
from typing import Optional, Dict
from jose import jwt, JWTError
from starlette.requests import Request
from starlette.responses import JSONResponse

class OAuth2Auth:
    """OAuth 2.0 authentication with external provider"""

    def __init__(self):
        # OAuth provider configuration
        self.issuer = os.getenv("OAUTH_ISSUER")  # e.g., https://your-tenant.auth0.com/
        self.audience = os.getenv("OAUTH_AUDIENCE")  # Your API identifier

        self.enabled = bool(self.issuer and self.audience)
        self._jwks = None

    def _get_jwks(self) -> Dict:
        """Fetch JSON Web Key Set from provider"""
        if self._jwks:
            return self._jwks

        jwks_url = f"{self.issuer}.well-known/jwks.json"
        response = requests.get(jwks_url)
        self._jwks = response.json()
        return self._jwks

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token from OAuth provider"""
        try:
            # Get signing key
            jwks = self._get_jwks()

            # Decode and verify
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
            )
            return payload
        except JWTError as e:
            print(f"JWT verification failed: {e}")
            return None

    def verify_request(self, request: Request) -> Optional[JSONResponse]:
        """Verify request has valid OAuth token"""
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
                        "message": "Missing Bearer token"
                    }
                },
                status_code=401,
                headers={"WWW-Authenticate": f'Bearer realm="{self.audience}"'}
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

        # Store user info in request state
        request.state.user_id = payload.get("sub")
        request.state.scopes = payload.get("scope", "").split()
        return None


# Configuration examples for different providers:

"""
# Auth0
OAUTH_ISSUER=https://your-tenant.auth0.com/
OAUTH_AUDIENCE=https://mail-query-api

# Clerk
OAUTH_ISSUER=https://your-app.clerk.accounts.dev/
OAUTH_AUDIENCE=https://mail-query-api

# Supabase
OAUTH_ISSUER=https://your-project.supabase.co/auth/v1/
OAUTH_AUDIENCE=authenticated

# Google Identity Platform
OAUTH_ISSUER=https://accounts.google.com
OAUTH_AUDIENCE=your-client-id.apps.googleusercontent.com
"""
