"""
Auth 모듈 - OAuth 2.0 인증 플로우 관리

OAuth 2.0 인증 플로우를 조정하고 메모리 세션을 관리하는 경량화된 모듈입니다.
infra 서비스들을 최대 활용하여 토큰 저장/갱신/상태확인을 수행합니다.

주요 기능:
- OAuth 플로우 조정 (인증 URL 생성 → 콜백 처리)
- 메모리 기반 세션 관리
- 일괄 인증 처리
- infra 서비스 연동
"""

from .auth_orchestrator import AuthOrchestrator, get_auth_orchestrator
from .auth_web_server import (
    AuthWebServer,
    AuthWebServerManager,
    get_auth_web_server_manager,
)
from .auth_schema import (
    AuthState,
    AuthSession,
    AuthCallback,
    TokenData,
    AuthStartRequest,
    AuthStartResponse,
    AuthStatusResponse,
    AuthBulkRequest,
    AuthBulkResponse,
    AuthBulkStatus,
    AuthCleanupRequest,
    AuthCleanupResponse,
)
from ._auth_helpers import (
    auth_generate_session_id,
    auth_generate_state_token,
    auth_validate_callback_url,
    auth_parse_callback_params,
    auth_sanitize_user_id,
    auth_create_session_expiry,
    auth_format_error_message,
    auth_validate_token_info,
    auth_mask_sensitive_data,
    auth_calculate_session_timeout,
    auth_generate_callback_success_html,
    auth_generate_callback_error_html,
    auth_log_session_activity,
)

__all__ = [
    # 메인 컴포넌트
    "AuthOrchestrator",
    "get_auth_orchestrator",
    "AuthWebServer",
    "AuthWebServerManager",
    "get_auth_web_server_manager",
    # 스키마
    "AuthState",
    "AuthSession",
    "AuthCallback",
    "TokenData",
    "AuthStartRequest",
    "AuthStartResponse",
    "AuthStatusResponse",
    "AuthBulkRequest",
    "AuthBulkResponse",
    "AuthBulkStatus",
    "AuthCleanupRequest",
    "AuthCleanupResponse",
    # 헬퍼 함수
    "auth_generate_session_id",
    "auth_generate_state_token",
    "auth_validate_callback_url",
    "auth_parse_callback_params",
    "auth_sanitize_user_id",
    "auth_create_session_expiry",
    "auth_format_error_message",
    "auth_validate_token_info",
    "auth_mask_sensitive_data",
    "auth_calculate_session_timeout",
    "auth_generate_callback_success_html",
    "auth_generate_callback_error_html",
    "auth_log_session_activity",
]


# 편의를 위한 전역 인스턴스
auth_orchestrator = get_auth_orchestrator()
auth_web_server_manager = get_auth_web_server_manager()


def auth_module_info() -> dict:
    """Auth 모듈 정보를 반환합니다."""
    return {
        "module": "auth",
        "description": "OAuth 2.0 인증 플로우 관리 모듈",
        "version": "1.0.0",
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
            "infra 서비스 연동",
        ],
    }
