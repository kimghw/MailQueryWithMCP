"""
Enrollment 모듈 - OAuth 2.0 인증 플로우 및 계정 관리 (통합)

OAuth 2.0 인증 플로우와 계정 관리를 통합한 모듈입니다.
infra 서비스들을 최대 활용하여 토큰 저장/갱신/상태확인을 수행합니다.

주요 기능:
- OAuth 플로우 조정 (인증 URL 생성 → 콜백 처리)
- 메모리 기반 세션 관리
- 계정 관리 (등록, 동기화, enrollment)
- MCP 서버 제공 (HTTP streaming)
- infra 서비스 연동
"""

# Auth submodule
from .auth import (
    AuthOrchestrator,
    get_auth_orchestrator,
    AuthWebServer,
    AuthWebServerManager,
    get_auth_web_server_manager,
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

# Account submodule
from .account import (
    AccountOrchestrator,
    AccountRepository,
    AccountSyncService,
    AccountResponse,
    AccountCreate,
    AccountUpdate,
    AccountSyncResult,
    AccountAuditLog,
    AccountListFilter,
    EnrollmentFileData,
    OAuthConfig,
    TokenInfo,
    AccountStatus,
    AuthType,
    AccountCryptoHelpers,
    AccountFileHelpers,
    AccountAuditHelpers,
)

# MCP Server
from .mcp_server import (
    AuthAccountHandlers,
    HTTPStreamingAuthServer,
)

__all__ = [
    # Auth - Orchestrator
    "AuthOrchestrator",
    "get_auth_orchestrator",
    # Auth - Web Server
    "AuthWebServer",
    "AuthWebServerManager",
    "get_auth_web_server_manager",
    # Auth - Schema
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
    # Auth - Helpers
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
    # Account - Orchestrator
    "AccountOrchestrator",
    # Account - Repository & Services
    "AccountRepository",
    "AccountSyncService",
    # Account - Schema
    "AccountResponse",
    "AccountCreate",
    "AccountUpdate",
    "AccountSyncResult",
    "AccountAuditLog",
    "AccountListFilter",
    "EnrollmentFileData",
    "OAuthConfig",
    "TokenInfo",
    "AccountStatus",
    "AuthType",
    # Account - Helpers
    "AccountCryptoHelpers",
    "AccountFileHelpers",
    "AccountAuditHelpers",
    # MCP Server
    "AuthAccountHandlers",
    "HTTPStreamingAuthServer",
]


# 편의를 위한 전역 인스턴스
auth_orchestrator = get_auth_orchestrator()
auth_web_server_manager = get_auth_web_server_manager()


def enrollment_module_info() -> dict:
    """Enrollment 모듈 정보를 반환합니다."""
    return {
        "module": "enrollment",
        "description": "OAuth 2.0 인증 플로우 및 계정 관리 통합 모듈",
        "version": "2.0.0",
        "structure": {
            "auth/": "OAuth 2.0 인증 플로우",
            "account/": "계정 관리 및 enrollment",
            "mcp_server/": "MCP 서버 (HTTP streaming)",
        },
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
            "계정 등록 및 동기화",
            "MCP 도구 제공",
            "콜백 웹서버",
            "infra 서비스 연동",
        ],
    }
