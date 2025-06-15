"""
Auth 모듈의 OAuth 관련 Pydantic 스키마

OAuth 2.0 인증 플로우에서 사용되는 데이터 모델들을 정의합니다.
메모리 세션 관리와 인증 상태 관리를 위한 스키마를 포함합니다.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field, validator


class AuthState(str, Enum):
    """OAuth 인증 상태"""
    PENDING = "PENDING"           # 인증 URL 생성됨, 사용자 인증 대기 중
    CALLBACK_RECEIVED = "CALLBACK_RECEIVED"  # 콜백 수신됨, 토큰 교환 진행 중
    COMPLETED = "COMPLETED"       # 토큰 교환 완료
    FAILED = "FAILED"            # 인증 실패
    EXPIRED = "EXPIRED"          # 세션 만료


class AuthSession(BaseModel):
    """OAuth 인증 세션 (메모리 기반)"""
    session_id: str = Field(..., description="세션 고유 ID")
    user_id: str = Field(..., description="사용자 ID")
    state: str = Field(..., description="CSRF 방지용 상태값")
    auth_url: str = Field(..., description="생성된 인증 URL")
    status: AuthState = Field(default=AuthState.PENDING, description="인증 상태")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="세션 생성 시간")
    expires_at: datetime = Field(..., description="세션 만료 시간")
    error_message: Optional[str] = Field(None, description="오류 메시지")
    callback_received_at: Optional[datetime] = Field(None, description="콜백 수신 시간")
    token_info: Optional[Dict[str, Any]] = Field(None, description="토큰 정보")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @validator('expires_at', pre=True, always=True)
    def set_expiry_time(cls, v, values):
        """세션 만료 시간 설정 (기본 10분)"""
        if v is None:
            created_at = values.get('created_at', datetime.utcnow())
            return created_at + timedelta(minutes=10)
        return v

    def is_expired(self) -> bool:
        """세션 만료 여부 확인"""
        return datetime.utcnow() > self.expires_at

    def is_pending(self) -> bool:
        """인증 대기 상태 확인"""
        return self.status == AuthState.PENDING and not self.is_expired()


class AuthCallback(BaseModel):
    """OAuth 콜백 데이터"""
    code: str = Field(..., description="인증 코드")
    state: str = Field(..., description="상태값")
    session_state: Optional[str] = Field(None, description="세션 상태")
    error: Optional[str] = Field(None, description="오류 코드")
    error_description: Optional[str] = Field(None, description="오류 설명")

    def has_error(self) -> bool:
        """오류 여부 확인"""
        return self.error is not None


class TokenData(BaseModel):
    """토큰 데이터"""
    access_token: str = Field(..., description="액세스 토큰")
    refresh_token: str = Field(..., description="리프레시 토큰") 
    expires_in: int = Field(..., description="만료 시간(초)")
    scope: str = Field(..., description="권한 범위")
    token_type: str = Field(default="Bearer", description="토큰 타입")
    expiry_time: Optional[datetime] = Field(None, description="만료 시점")


class AuthStartRequest(BaseModel):
    """인증 시작 요청"""
    user_id: str = Field(..., description="사용자 ID")
    redirect_after_auth: Optional[str] = Field(None, description="인증 후 리다이렉트 URL")


class AuthStartResponse(BaseModel):
    """인증 시작 응답"""
    session_id: str = Field(..., description="세션 ID")
    auth_url: str = Field(..., description="인증 URL")
    state: str = Field(..., description="상태값")
    expires_at: datetime = Field(..., description="세션 만료 시간")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AuthStatusResponse(BaseModel):
    """인증 상태 응답"""
    session_id: str = Field(..., description="세션 ID")
    user_id: str = Field(..., description="사용자 ID")
    status: AuthState = Field(..., description="인증 상태")
    message: str = Field(..., description="상태 메시지")
    created_at: datetime = Field(..., description="세션 생성 시간")
    expires_at: datetime = Field(..., description="세션 만료 시간")
    error_message: Optional[str] = Field(None, description="오류 메시지")
    is_completed: bool = Field(..., description="인증 완료 여부")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AuthBulkRequest(BaseModel):
    """일괄 인증 요청"""
    user_ids: List[str] = Field(..., description="사용자 ID 목록")
    max_concurrent: int = Field(default=3, description="최대 동시 인증 수")
    timeout_minutes: int = Field(default=10, description="각 인증의 타임아웃(분)")


class AuthBulkStatus(BaseModel):
    """일괄 인증 상태"""
    user_id: str = Field(..., description="사용자 ID")
    session_id: Optional[str] = Field(None, description="세션 ID")
    status: AuthState = Field(..., description="인증 상태")
    auth_url: Optional[str] = Field(None, description="인증 URL")
    error_message: Optional[str] = Field(None, description="오류 메시지")


class AuthBulkResponse(BaseModel):
    """일괄 인증 응답"""
    total_users: int = Field(..., description="총 사용자 수")
    pending_count: int = Field(..., description="대기 중인 사용자 수")
    completed_count: int = Field(..., description="완료된 사용자 수")
    failed_count: int = Field(..., description="실패한 사용자 수")
    user_statuses: List[AuthBulkStatus] = Field(..., description="사용자별 상태")


class AuthCleanupRequest(BaseModel):
    """세션 정리 요청"""
    expire_threshold_minutes: int = Field(default=60, description="만료 기준 시간(분)")
    force_cleanup: bool = Field(default=False, description="강제 정리 여부")


class AuthCleanupResponse(BaseModel):
    """세션 정리 응답"""
    cleaned_sessions: int = Field(..., description="정리된 세션 수")
    active_sessions: int = Field(..., description="활성 세션 수")
    total_sessions_before: int = Field(..., description="정리 전 총 세션 수")
