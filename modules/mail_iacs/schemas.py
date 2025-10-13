"""
IACS 모듈 데이터 스키마
Pydantic v2 기반 데이터 모델
"""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, EmailStr


# ============================================================================
# DB 모델
# ============================================================================

class PanelChairDB(BaseModel):
    """DB 패널 의장 정보"""
    id: Optional[int] = None
    chair_address: EmailStr
    panel_name: str
    kr_panel_member: EmailStr
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DefaultValueDB(BaseModel):
    """DB 기본값 정보"""
    id: Optional[int] = None
    panel_name: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ============================================================================
# MCP Tool 입력 스키마
# ============================================================================

class InsertInfoRequest(BaseModel):
    """패널 정보 삽입 요청"""
    chair_address: EmailStr = Field(..., description="의장 이메일 주소")
    panel_name: str = Field(..., description="패널 이름 (예: sdtp)")
    kr_panel_member: EmailStr = Field(..., description="한국 패널 멤버 이메일 주소")

    @field_validator("panel_name")
    @classmethod
    def validate_panel_name(cls, v):
        if not v or not v.strip():
            raise ValueError("panel_name은 비어있을 수 없습니다")
        return v.strip().lower()


class SearchAgendaRequest(BaseModel):
    """아젠다 검색 요청"""
    start_date: Optional[datetime] = Field(
        None,
        description="시작 날짜 (기본값: now)"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="종료 날짜 (기본값: 3개월 전)"
    )
    mail_type: Literal["agenda"] = Field(
        "agenda",
        description="메일 타입 (의장이 보낸 아젠다)"
    )
    content_field: List[str] = Field(
        default=["subject"],
        description="조회할 필드 (subject, body, attachments)"
    )
    agenda_code: Optional[str] = Field(
        None,
        description="아젠다 코드 키워드 (옵션)"
    )
    panel_name: Optional[str] = Field(
        None,
        description="패널 이름 (옵션, DB에서 조회)"
    )

    @field_validator("content_field")
    @classmethod
    def validate_content_field(cls, v):
        allowed = {"subject", "body", "attachments", "id", "from", "receivedDateTime"}
        for field in v:
            if field not in allowed:
                raise ValueError(f"허용되지 않은 필드: {field}")
        # id는 항상 포함
        if "id" not in v:
            v.append("id")
        return v


class SearchResponsesRequest(BaseModel):
    """응답 메일 검색 요청"""
    mail_type: Literal["responses"] = Field(
        "responses",
        description="메일 타입 (멤버들의 응답)"
    )
    content_field: List[str] = Field(
        default=["subject"],
        description="조회할 필드 (subject, body, attachments)"
    )
    agenda_code: str = Field(
        ...,
        description="아젠다 코드 키워드 (필수, 제목 검색)"
    )
    send_address: Optional[List[EmailStr]] = Field(
        None,
        description="발신자 주소 리스트 (옵션)"
    )

    @field_validator("content_field")
    @classmethod
    def validate_content_field(cls, v):
        allowed = {"subject", "body", "attachments", "id", "from", "receivedDateTime"}
        for field in v:
            if field not in allowed:
                raise ValueError(f"허용되지 않은 필드: {field}")
        if "id" not in v:
            v.append("id")
        return v

    @field_validator("agenda_code")
    @classmethod
    def validate_agenda_code(cls, v):
        if not v or len(v.strip()) < 7:
            raise ValueError("agenda_code는 최소 7자 이상이어야 합니다")
        return v.strip()


class InsertDefaultValueRequest(BaseModel):
    """기본값 삽입 요청"""
    panel_name: str = Field(..., description="기본 패널 이름")

    @field_validator("panel_name")
    @classmethod
    def validate_panel_name(cls, v):
        if not v or not v.strip():
            raise ValueError("panel_name은 비어있을 수 없습니다")
        return v.strip().lower()


# ============================================================================
# MCP Tool 출력 스키마
# ============================================================================

class InsertInfoResponse(BaseModel):
    """패널 정보 삽입 응답"""
    success: bool
    message: str
    panel_name: str
    chair_address: str
    kr_panel_member: str


class SearchAgendaResponse(BaseModel):
    """아젠다 검색 응답"""
    success: bool
    message: str
    total_count: int
    panel_name: Optional[str] = None
    chair_address: Optional[str] = None
    kr_panel_member: Optional[str] = None
    mails: List[dict]  # GraphMailItem 리스트


class SearchResponsesResponse(BaseModel):
    """응답 메일 검색 응답"""
    success: bool
    message: str
    total_count: int
    agenda_code: str
    mails: List[dict]  # GraphMailItem 리스트


class InsertDefaultValueResponse(BaseModel):
    """기본값 삽입 응답"""
    success: bool
    message: str
    panel_name: str


# ============================================================================
# 유틸리티 함수
# ============================================================================

def get_default_start_date() -> datetime:
    """기본 시작 날짜 (현재)"""
    return datetime.now()


def get_default_end_date() -> datetime:
    """기본 종료 날짜 (3개월 전)"""
    from datetime import timedelta
    return datetime.now() - timedelta(days=90)
