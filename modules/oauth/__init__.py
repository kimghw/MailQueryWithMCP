"""
OAuth 모듈 - OAuth 2.0 인증 플로우 관리

OAuth 2.0 인증 플로우를 조정하고, 세션을 관리하며, 콜백 웹서버를 운영합니다.
"""

from .oauth_orchestrator import OAuthOrchestrator, get_oauth_orchestrator
from .oauth_schema import (
    OAuthBulkRequest,
    OAuthBulkResponse,
    OAuthBulkStatus,
    OAuthCallback,
    OAuthCleanupRequest,
    OAuthCleanupResponse,
    OAuthSession,
    OAuthStartRequest,
    OAuthStartResponse,
    OAuthState,
    OAuthStatusResponse,
    OAuthTokens,
)
from .oauth_session_manager import OAuthSessionManager, get_oauth_session_manager
from .oauth_web_server import (
    OAuthWebServer,
    OAuthWebServerManager,
    get_auth_web_server_manager,
)

__all__ = [
    # 메인 컴포넌트
    "OAuthOrchestrator",
    "get_oauth_orchestrator",
    "OAuthSessionManager",
    "get_oauth_session_manager",
    "OAuthWebServer",
    "OAuthWebServerManager",
    "get_auth_web_server_manager",
    # 스키마
    "OAuthState",
    "OAuthSession",
    "OAuthCallback",
    "OAuthTokens",
    "OAuthStartRequest",
    "OAuthStartResponse",
    "OAuthStatusResponse",
    "OAuthBulkRequest",
    "OAuthBulkResponse",
    "OAuthBulkStatus",
    "OAuthCleanupRequest",
    "OAuthCleanupResponse",
]

# 편의를 위한 전역 인스턴스
oauth_orchestrator = get_oauth_orchestrator()
oauth_session_manager = get_oauth_session_manager()
oauth_web_server_manager = get_auth_web_server_manager()


def oauth_module_info() -> dict:
    """OAuth 모듈 정보를 반환합니다."""
    return {
        "module": "oauth",
        "description": "OAuth 2.0 인증 플로우 관리 모듈",
        "version": "3.0.0",
        "dependencies": [
            "infra.core.token_service",
            "infra.core.oauth_client",
            "infra.core.database",
            "infra.core.logger",
            "infra.core.config",
        ],
        "features": [
            "OAuth 플로우 조정",
            "메모리 세션 관리",
            "일괄 인증 처리",
            "콜백 웹서버",
            "서비스 계층 분리",
        ],
        "architecture": {
            "orchestrator": "인증 플로우 조정",
            "session_manager": "세션 라이프사이클 관리",
            "services": "개별 도메인 로직 처리 (세션, OAuth, 계정, 콜백)",
            "utilities": "검증, 파싱 등 공통 기능",
            "web_server": "HTTP 콜백 엔드포인트",
        },
    }
