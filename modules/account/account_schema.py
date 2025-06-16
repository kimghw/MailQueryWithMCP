"""
Account 모듈의 데이터 스키마 정의

Pydantic 모델을 사용하여 계정 관련 데이터 구조와 검증 규칙을 정의합니다.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, validator, model_validator


class AccountStatus(str, Enum):
    """계정 상태 열거형"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LOCKED = "LOCKED"
    REAUTH_REQUIRED = "REAUTH_REQUIRED"


class AuthType(str, Enum):
    """인증 타입 열거형"""
    AUTHORIZATION_CODE_FLOW = "Authorization Code Flow"
    DEVICE_CODE_FLOW = "Device Code Flow"
    CLIENT_CREDENTIALS = "Client Credentials"


class OAuthConfig(BaseModel):
    """OAuth 설정 정보"""
    client_id: str = Field(..., min_length=1, description="Azure AD 클라이언트 ID")
    client_secret: str = Field(..., min_length=1, description="Azure AD 클라이언트 시크릿")
    tenant_id: str = Field(..., min_length=1, description="Azure AD 테넌트 ID")
    redirect_uri: str = Field(..., description="OAuth 리다이렉트 URI")
    auth_type: AuthType = Field(default=AuthType.AUTHORIZATION_CODE_FLOW, description="인증 타입")
    delegated_permissions: List[str] = Field(default_factory=list, description="위임된 권한 목록")

    @validator('client_id', 'tenant_id')
    def validate_azure_ids(cls, v):
        """Azure ID 형식 검증 (GUID 형식)"""
        if len(v) != 36 or v.count('-') != 4:
            raise ValueError(f"잘못된 Azure ID 형식: {v}")
        return v

    @validator('redirect_uri')
    def validate_redirect_uri(cls, v):
        """리다이렉트 URI 형식 검증"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("redirect_uri는 http:// 또는 https://로 시작해야 합니다")
        return v

    @validator('delegated_permissions')
    def validate_permissions(cls, v):
        """권한 목록 검증"""
        valid_permissions = {
            'User.Read', 'User.ReadWrite', 'Mail.Read', 'Mail.ReadWrite', 
            'Mail.Send', 'offline_access', 'Calendars.Read', 'Calendars.ReadWrite'
        }
        for permission in v:
            if permission not in valid_permissions:
                raise ValueError(f"지원하지 않는 권한: {permission}")
        return v


class EnrollmentFileData(BaseModel):
    """Enrollment 파일에서 읽은 데이터"""
    account_email: EmailStr = Field(..., description="계정 이메일")
    account_name: str = Field(..., min_length=1, description="계정 이름")
    oauth_config: OAuthConfig = Field(..., description="OAuth 설정")
    file_path: str = Field(..., description="파일 경로")
    file_hash: str = Field(..., description="파일 해시")

    @validator('account_name')
    def validate_account_name(cls, v):
        """계정 이름 검증"""
        if len(v.strip()) == 0:
            raise ValueError("계정 이름은 공백일 수 없습니다")
        return v.strip()


class AccountCreate(BaseModel):
    """계정 생성 요청 데이터"""
    user_id: str = Field(..., min_length=1, description="사용자 ID")
    user_name: str = Field(..., min_length=1, description="사용자 이름")
    email: EmailStr = Field(..., description="이메일 주소")
    enrollment_file_path: str = Field(..., description="등록 파일 경로")
    enrollment_file_hash: str = Field(..., description="등록 파일 해시")
    oauth_client_id: str = Field(..., description="OAuth 클라이언트 ID")
    oauth_client_secret: str = Field(..., description="OAuth 클라이언트 시크릿 (암호화됨)")
    oauth_tenant_id: str = Field(..., description="OAuth 테넌트 ID")
    oauth_redirect_uri: str = Field(..., description="OAuth 리다이렉트 URI")
    auth_type: AuthType = Field(default=AuthType.AUTHORIZATION_CODE_FLOW, description="인증 타입")
    delegated_permissions: List[str] = Field(default_factory=list, description="위임된 권한")
    status: AccountStatus = Field(default=AccountStatus.ACTIVE, description="계정 상태")

    @validator('user_id')
    def validate_user_id(cls, v):
        """사용자 ID 검증 (영문, 숫자, 일부 특수문자만 허용)"""
        import re
        if not re.match(r'^[a-zA-Z0-9._-]+$', v):
            raise ValueError("user_id는 영문, 숫자, '.', '_', '-'만 포함할 수 있습니다")
        return v


class AccountUpdate(BaseModel):
    """계정 업데이트 요청 데이터"""
    user_name: Optional[str] = Field(None, min_length=1, description="사용자 이름")
    status: Optional[AccountStatus] = Field(None, description="계정 상태")
    enrollment_file_path: Optional[str] = Field(None, description="등록 파일 경로")
    enrollment_file_hash: Optional[str] = Field(None, description="등록 파일 해시")
    oauth_client_secret: Optional[str] = Field(None, description="OAuth 클라이언트 시크릿 (암호화됨)")
    oauth_redirect_uri: Optional[str] = Field(None, description="OAuth 리다이렉트 URI")
    delegated_permissions: Optional[List[str]] = Field(None, description="위임된 권한")
    access_token: Optional[str] = Field(None, description="액세스 토큰")
    refresh_token: Optional[str] = Field(None, description="리프레시 토큰")
    token_expiry: Optional[datetime] = Field(None, description="토큰 만료 시간")
    last_sync_time: Optional[datetime] = Field(None, description="마지막 동기화 시간")


class AccountResponse(BaseModel):
    """계정 응답 데이터"""
    id: int = Field(..., description="계정 ID")
    user_id: str = Field(..., description="사용자 ID")
    user_name: str = Field(..., description="사용자 이름")
    email: EmailStr = Field(..., description="이메일 주소")
    status: AccountStatus = Field(..., description="계정 상태")
    enrollment_file_path: str = Field(..., description="등록 파일 경로")
    enrollment_file_hash: str = Field(..., description="등록 파일 해시")
    oauth_client_id: str = Field(..., description="OAuth 클라이언트 ID")
    oauth_tenant_id: str = Field(..., description="OAuth 테넌트 ID")
    oauth_redirect_uri: str = Field(..., description="OAuth 리다이렉트 URI")
    auth_type: AuthType = Field(..., description="인증 타입")
    delegated_permissions: List[str] = Field(..., description="위임된 권한")
    has_valid_token: bool = Field(..., description="유효한 토큰 보유 여부")
    token_expiry: Optional[datetime] = Field(None, description="토큰 만료 시간")
    last_sync_time: Optional[datetime] = Field(None, description="마지막 동기화 시간")
    is_active: bool = Field(..., description="활성화 여부")
    created_at: datetime = Field(..., description="생성 시간")
    updated_at: datetime = Field(..., description="수정 시간")

    @validator('has_valid_token', pre=True)
    def validate_token_validity(cls, v, values):
        """토큰 유효성 검증"""
        if 'token_expiry' in values and values['token_expiry']:
            return values['token_expiry'] > datetime.utcnow()
        return False


class AccountAuditLog(BaseModel):
    """계정 감사 로그"""
    id: Optional[int] = Field(None, description="로그 ID")
    account_id: int = Field(..., description="계정 ID")
    action: str = Field(..., description="수행된 액션")
    old_values: Optional[Dict[str, Any]] = Field(None, description="이전 값들")
    new_values: Optional[Dict[str, Any]] = Field(None, description="새로운 값들")
    changed_by: str = Field(..., description="변경 수행자")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="변경 시간")


class AccountSyncResult(BaseModel):
    """계정 동기화 결과"""
    total_files: int = Field(..., description="처리된 총 파일 수")
    created_accounts: int = Field(..., description="생성된 계정 수")
    updated_accounts: int = Field(..., description="업데이트된 계정 수")
    deactivated_accounts: int = Field(..., description="비활성화된 계정 수")
    errors: List[str] = Field(default_factory=list, description="발생한 오류 목록")
    sync_time: datetime = Field(default_factory=datetime.utcnow, description="동기화 시간")


class AccountListFilter(BaseModel):
    """계정 목록 필터링 옵션"""
    status: Optional[AccountStatus] = Field(None, description="상태별 필터")
    email_pattern: Optional[str] = Field(None, description="이메일 패턴 검색")
    name_pattern: Optional[str] = Field(None, description="이름 패턴 검색")
    has_valid_token: Optional[bool] = Field(None, description="유효한 토큰 보유 여부")
    tenant_id: Optional[str] = Field(None, description="테넌트 ID별 필터")
    limit: int = Field(default=50, ge=1, le=1000, description="조회 제한 수")
    offset: int = Field(default=0, ge=0, description="조회 시작 위치")


class TokenInfo(BaseModel):
    """토큰 정보"""
    access_token: Optional[str] = Field(None, description="액세스 토큰")
    refresh_token: Optional[str] = Field(None, description="리프레시 토큰")
    token_expiry: Optional[datetime] = Field(None, description="토큰 만료 시간")
    is_valid: bool = Field(default=False, description="토큰 유효성")

    @model_validator(mode='before')
    @classmethod
    def validate_token_consistency(cls, values):
        """토큰 일관성 검증"""
        access_token = values.get('access_token')
        token_expiry = values.get('token_expiry')
        
        if access_token and not token_expiry:
            raise ValueError("access_token이 있는 경우 token_expiry도 설정되어야 합니다")
        
        if token_expiry and token_expiry <= datetime.utcnow():
            values['is_valid'] = False
        elif access_token and token_expiry:
            values['is_valid'] = True
            
        return values
