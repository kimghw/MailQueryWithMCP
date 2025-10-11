"""Authentication module for MCP server

Supports multiple authentication methods:
- API Key authentication
- JWT Bearer token
- OAuth 2.0 with external providers
"""

from .api_key_auth import AuthMiddleware
from .jwt_auth import JWTAuth
from .oauth2_auth import OAuth2Auth

__all__ = ["AuthMiddleware", "JWTAuth", "OAuth2Auth"]
