"""Authentication module - OAuth 2.0 flow management"""

from ._auth_helpers import (
    auth_calculate_session_timeout,
    auth_create_session_expiry,
    auth_format_error_message,
    auth_generate_callback_error_html,
    auth_generate_callback_success_html,
    auth_generate_session_id,
    auth_generate_state_token,
    auth_log_session_activity,
    auth_mask_sensitive_data,
    auth_parse_callback_params,
    auth_sanitize_user_id,
    auth_validate_callback_url,
    auth_validate_token_info,
)
from .auth_orchestrator import AuthOrchestrator, get_auth_orchestrator
from .auth_schema import (
    AuthBulkRequest,
    AuthBulkResponse,
    AuthBulkStatus,
    AuthCallback,
    AuthCleanupRequest,
    AuthCleanupResponse,
    AuthSession,
    AuthStartRequest,
    AuthStartResponse,
    AuthState,
    AuthStatusResponse,
    TokenData,
)
from .auth_web_server import (
    AuthWebServer,
    AuthWebServerManager,
    get_auth_web_server_manager,
)

__all__ = [
    # Orchestrator
    "AuthOrchestrator",
    "get_auth_orchestrator",
    # Web Server
    "AuthWebServer",
    "AuthWebServerManager",
    "get_auth_web_server_manager",
    # Schema
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
    # Helpers
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
