"""
Dynamic Client Registration (DCR) OAuth Module

RFC 7591 준수 동적 클라이언트 등록 서비스
Claude Custom Connector 지원을 위한 OAuth 2.0 Authorization Server
"""

from .dcr_service import DCRService
from .auth_middleware import verify_bearer_token_middleware

__all__ = ["DCRService", "verify_bearer_token_middleware"]