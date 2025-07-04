"""
Mail Query 모듈 스키마 정의
Pydantic v2 기반 데이터 모델
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class MailQueryFilters(BaseModel):
    """메일 필터 조건"""

    date_from: Optional[datetime] = Field(None, description="시작 날짜")
    date_to: Optional[datetime] = Field(None, description="종료 날짜")
    sender_address: Optional[str] = Field(None, description="발신자 이메일")
    subject_contains: Optional[str] = Field(None, description="제목 포함 텍스트")
    is_read: Optional[bool] = Field(None, description="읽음 상태")
    has_attachments: Optional[bool] = Field(None, description="첨부파일 여부")
    importance: Optional[str] = Field(None, description="중요도")

    @field_validator("importance")
    @classmethod
    def validate_importance(cls, v):
        if v and v not in ["low", "normal", "high"]:
            raise ValueError("importance는 'low', 'normal', 'high' 중 하나여야 합니다")
        return v

    @field_validator("date_from", "date_to")
    @classmethod
    def validate_dates(cls, v):
        if v:
            # timezone-aware datetime과 비교하기 위해 현재 시간도 UTC로 설정
            now = datetime.now(timezone.utc)

            # 입력값이 timezone-naive인 경우 UTC로 가정
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)

            if v > now:
                raise ValueError("미래 날짜는 설정할 수 없습니다")
        return v


class PaginationOptions(BaseModel):
    """페이징 옵션"""

    top: int = Field(default=50, ge=1, le=1000, description="한 번에 가져올 메일 수")
    skip: int = Field(default=0, ge=0, description="건너뛸 메일 수")
    max_pages: int = Field(default=10, ge=1, le=50, description="최대 페이지 수")


class MailQueryRequest(BaseModel):
    """메일 조회 요청"""

    user_id: str = Field(..., description="사용자 ID")
    filters: Optional[MailQueryFilters] = Field(None, description="필터 조건")
    pagination: Optional[PaginationOptions] = Field(None, description="페이징 옵션")
    select_fields: Optional[List[str]] = Field(None, description="선택할 필드")

    @field_validator("select_fields")
    @classmethod
    def validate_select_fields(cls, v):
        if v:
            allowed_fields = {
                "id",
                "subject",
                "sender",
                "from",
                "toRecipients",
                "receivedDateTime",
                "bodyPreview",
                "body",
                "isRead",
                "hasAttachments",
                "importance",
                "webLink",
            }
            invalid_fields = set(v) - allowed_fields
            if invalid_fields:
                raise ValueError(f"허용되지 않은 필드: {invalid_fields}")
        return v


# # 실제 넘어 가는 값
class GraphMailItem(BaseModel):
    """Graph API 메일 아이템"""

    id: str = Field(..., description="메일 ID")
    subject: Optional[str] = Field(None, description="제목")
    sender: Optional[Dict[str, Any]] = Field(None, description="발신자 정보")
    from_address: Optional[Dict[str, Any]] = Field(
        None, alias="from", description="From 필드"
    )
    to_recipients: List[Dict[str, Any]] = Field(
        default_factory=list, description="수신자 목록"
    )
    received_date_time: datetime = Field(..., description="수신 시간")
    body_preview: Optional[str] = Field(None, description="본문 미리보기")
    body: Optional[Dict[str, Any]] = Field(None, description="본문 전체")
    is_read: bool = Field(default=False, description="읽음 상태")
    has_attachments: bool = Field(default=False, description="첨부파일 여부")
    importance: str = Field(default="normal", description="중요도")
    web_link: Optional[str] = Field(None, description="웹 링크")

    class Config:
        populate_by_name = True


# mail_query 출력
class MailQueryResponse(BaseModel):
    """메일 조회 응답"""

    user_id: str = Field(..., description="사용자 ID")
    total_fetched: int = Field(..., description="조회된 메일 수")
    messages: List[GraphMailItem] = Field(..., description="메일 목록")
    has_more: bool = Field(..., description="추가 데이터 여부")
    next_link: Optional[str] = Field(None, description="다음 페이지 링크")
    execution_time_ms: int = Field(..., description="실행 시간(밀리초)")
    query_info: Dict[str, Any] = Field(..., description="쿼리 정보")


class MailQueryLog(BaseModel):
    """메일 조회 로그"""

    user_id: str = Field(..., description="사용자 ID")
    query_type: str = Field(default="mail_query", description="쿼리 타입")
    odata_filter: Optional[str] = Field(None, description="OData 필터")
    select_fields: Optional[str] = Field(None, description="선택 필드")
    top: int = Field(..., description="페이지 크기")
    skip: int = Field(..., description="건너뛴 수")
    result_count: int = Field(..., description="결과 수")
    execution_time_ms: int = Field(..., description="실행 시간")
    has_error: bool = Field(default=False, description="오류 여부")
    error_message: Optional[str] = Field(None, description="오류 메시지")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="생성 시간"
    )


class MailboxInfo(BaseModel):
    """메일박스 정보"""

    display_name: Optional[str] = Field(None, description="표시 이름")
    user_principal_name: Optional[str] = Field(None, description="사용자 주체 이름")
    automatic_replies_setting: Optional[Dict[str, Any]] = Field(
        None, description="자동 회신 설정"
    )
    archive_folder: Optional[str] = Field(None, description="보관 폴더")
    time_zone: Optional[str] = Field(None, description="시간대")
    language: Optional[Dict[str, Any]] = Field(None, description="언어 설정")


class GraphAPIError(BaseModel):
    """Graph API 오류 정보"""

    code: str = Field(..., description="오류 코드")
    message: str = Field(..., description="오류 메시지")
    inner_error: Optional[Dict[str, Any]] = Field(None, description="내부 오류 정보")
    status_code: int = Field(..., description="HTTP 상태 코드")
    api_endpoint: str = Field(..., description="API 엔드포인트")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="오류 발생 시간"
    )
