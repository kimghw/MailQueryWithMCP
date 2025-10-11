"""Authentication module for MCP server

Supports multiple authentication methods:
- API Key authentication
- JWT Bearer token
- OAuth 2.0 with external providers
"""

from .api_key_auth import AuthMiddleware
from .jwt_auth import JWTAuth

# OAuth2Auth requires python-jose, imported lazily
def get_oauth2_auth():
    """Lazy import OAuth2Auth to avoid dependency issues"""
    try:
        from .oauth2_auth import OAuth2Auth
        return OAuth2Auth
    except ImportError as e:
        raise ImportError(
            "OAuth2Auth requires 'python-jose[cryptography]' package. "
            "Install with: pip install python-jose[cryptography]"
        ) from e

__all__ = ["AuthMiddleware", "JWTAuth", "get_oauth2_auth"]
