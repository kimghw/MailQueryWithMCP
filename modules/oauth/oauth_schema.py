"""
OAuth Pydantic 모델
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class OAuthState(str, Enum):
    """OAuth 인증 흐름의 상태를 나타내는 열거형"""

    PENDING = "pending"
    CALLBACK_RECEIVED = "callback_received"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class OAuthConfig(BaseModel):
    """OAuth 설정"""

    client_id: str
    client_secret: str
    redirect_uri: str
    scope: str = "https://graph.microsoft.com/.default"
    authority: str = "https://login.microsoftonline.com/common"


class OAuthTokens(BaseModel):
    """OAuth 토큰"""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int
    scope: Optional[str] = None


class OAuthSession(BaseModel):
    """OAuth 세션 정보를 담는 모델"""

    session_id: str
    user_id: str
    state: str
    status: OAuthState = OAuthState.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    auth_url: Optional[str] = None
    error_message: Optional[str] = None
    tokens: Optional[OAuthTokens] = None

    def is_expired(self) -> bool:
        """세션 만료 여부 확인"""
        return datetime.utcnow() > self.expires_at

    def is_pending(self) -> bool:
        """인증이 아직 진행 중인지 확인"""
        return self.status in [OAuthState.PENDING, OAuthState.CALLBACK_RECEIVED]


class OAuthStartRequest(BaseModel):
    """인증 시작 요청"""

    user_id: str


class OAuthStartResponse(BaseModel):
    """인증 시작 응답"""

    session_id: str
    user_id: str
    auth_url: str
    expires_at: datetime
    status: OAuthState


class OAuthStatusResponse(BaseModel):
    """세션 상태 조회 응답"""

    session_id: str
    user_id: str
    status: OAuthState
    message: str
    created_at: datetime
    expires_at: datetime
    error_message: Optional[str] = None
    is_completed: bool


class OAuthBulkStatus(BaseModel):
    """일괄 인증의 개별 사용자 상태"""

    user_id: str
    status: str  # "AUTHENTICATION_REQUIRED", "COMPLETED", "FAILED"
    session_id: Optional[str] = None
    auth_url: Optional[str] = None
    error: Optional[str] = None


class OAuthBulkRequest(BaseModel):
    """일괄 인증 요청"""

    user_ids: List[str]


class OAuthBulkResponse(BaseModel):
    """일괄 인증 응답"""

    results: List[OAuthBulkStatus]


class OAuthCleanupRequest(BaseModel):
    """세션 정리 요청"""

    expire_threshold_minutes: int = 60
    force_cleanup: bool = False


class OAuthCleanupResponse(BaseModel):
    """세션 정리 응답"""

    cleaned_sessions: int
    active_sessions: int
    total_sessions_before: int


class OAuthCallback(BaseModel):
    """OAuth 콜백 데이터"""

    code: str
    state: str
    session_state: Optional[str] = None  # For Microsoft Entra ID
    error: Optional[str] = None
    error_description: Optional[str] = None
