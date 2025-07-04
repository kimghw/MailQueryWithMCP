"""
Email Dashboard 모듈의 데이터 스키마 정의

이벤트 데이터, 데이터베이스 모델, 응답 모델을 포함합니다.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# =============================================================================
# 이벤트 관련 스키마
# =============================================================================


class AgendaInfo(BaseModel):
    """아젠다 정보 추출 결과"""

    full_pattern: Optional[str] = None
    panel_name: Optional[str] = None
    year: Optional[str] = None
    round_no: Optional[str] = None
    round_version: Optional[str] = None
    organization_code: Optional[str] = None
    sequence: Optional[str] = None
    reply_version: Optional[str] = None


class TokenUsage(BaseModel):
    """토큰 사용량"""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ExtractionResult(BaseModel):
    """이메일 키워드 추출 결과"""

    summary: str
    deadline: Optional[str] = None
    has_deadline: bool = False
    mail_type: str  # REQUEST, RESPONSE, NOTIFICATION, COMPLETED, OTHER
    decision_status: str  # created, comment, consolidated, review, decision
    keywords: List[str]
    sender_type: str  # CHAIR, MEMBER
    sender_organization: Optional[str] = None
    send_time: str
    agenda_no: Optional[str] = None
    agenda_info: AgendaInfo
    token_usage: TokenUsage


class ExtractionMetadata(BaseModel):
    """추출 메타데이터"""

    success: bool
    extraction_time_ms: int
    model_used: str
    token_usage: TokenUsage


class EmailDashboardEventData(BaseModel):
    """이메일 대시보드 이벤트 데이터"""

    mail_id: str
    extraction_result: ExtractionResult
    extraction_metadata: ExtractionMetadata
    processing_timestamp: str


class EmailDashboardEvent(BaseModel):
    """이메일 대시보드 이벤트"""

    event_type: str
    event_id: str
    occurred_at: str
    source: str
    version: str
    correlation_id: str
    data: EmailDashboardEventData


# =============================================================================
# 데이터베이스 모델 스키마
# =============================================================================


class EmailAgendaChair(BaseModel):
    """의장 발송 아젠다 정보"""

    panel_id: str
    agenda_no: str
    round_no: Optional[str] = None
    agenda_sequence: Optional[int] = None
    send_time: datetime
    deadline: Optional[datetime] = None
    mail_type: str
    decision_status: str = "created"
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EmailAgendaMemberResponse(BaseModel):
    """멤버 기관 응답 내용"""

    agenda_no: str
    ABS: Optional[str] = None
    BV: Optional[str] = None
    CCS: Optional[str] = None
    CRS: Optional[str] = None
    DNV: Optional[str] = None
    IRS: Optional[str] = None
    KR: Optional[str] = None
    NK: Optional[str] = None
    PRS: Optional[str] = None
    RINA: Optional[str] = None
    IL: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EmailAgendaMemberResponseTime(BaseModel):
    """멤버 기관 응답 시간"""

    agenda_no: str
    ABS: Optional[datetime] = None
    BV: Optional[datetime] = None
    CCS: Optional[datetime] = None
    CRS: Optional[datetime] = None
    DNV: Optional[datetime] = None
    IRS: Optional[datetime] = None
    KR: Optional[datetime] = None
    NK: Optional[datetime] = None
    PRS: Optional[datetime] = None
    RINA: Optional[datetime] = None
    IL: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =============================================================================
# 조회/대시보드 응답 스키마
# =============================================================================


class OrganizationResponse(BaseModel):
    """기관별 응답 현황"""

    organization: str
    response_content: Optional[str] = None
    response_time: Optional[datetime] = None
    has_responded: bool = False


class AgendaDetail(BaseModel):
    """아젠다 상세 정보"""

    agenda_no: str
    panel_id: str
    round_no: Optional[str] = None
    agenda_sequence: Optional[int] = None
    send_time: datetime
    deadline: Optional[datetime] = None
    mail_type: str
    decision_status: str
    summary: Optional[str] = None
    responses: List[OrganizationResponse] = []
    response_count: int = 0
    total_organizations: int = 11


class AgendaStatusSummary(BaseModel):
    """아젠다 상태 요약"""

    agenda_no: str
    panel_id: str
    decision_status: str
    response_rate: float  # 응답률 (0.0 ~ 1.0)
    days_until_deadline: Optional[int] = None
    is_overdue: bool = False


class OrganizationStats(BaseModel):
    """기관별 통계"""

    organization: str
    total_agendas: int
    responded_agendas: int
    response_rate: float
    avg_response_time_hours: Optional[float] = None


class DashboardStats(BaseModel):
    """대시보드 전체 통계"""

    total_agendas: int
    pending_agendas: int
    completed_agendas: int
    overdue_agendas: int
    today_deadline_agendas: int
    overall_response_rate: float
    organization_stats: List[OrganizationStats] = []


class TimelineEvent(BaseModel):
    """아젠다 타임라인 이벤트"""

    timestamp: datetime
    event_type: str  # "sent", "response_received", "deadline"
    organization: Optional[str] = None
    description: str


class AgendaTimeline(BaseModel):
    """아젠다 타임라인"""

    agenda_no: str
    events: List[TimelineEvent] = []


# =============================================================================
# 검색/필터 요청 스키마
# =============================================================================


class AgendaSearchFilter(BaseModel):
    """아젠다 검색 필터"""

    panel_id: Optional[str] = None
    round_no: Optional[str] = None
    decision_status: Optional[str] = None
    mail_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    deadline_start: Optional[datetime] = None
    deadline_end: Optional[datetime] = None
    has_deadline: Optional[bool] = None
    organization: Optional[str] = None  # 특정 기관이 응답한 아젠다만
    response_status: Optional[str] = None  # "responded", "not_responded"


class DashboardRequest(BaseModel):
    """대시보드 요청"""

    date_range_days: int = 30  # 최근 며칠간의 데이터
    include_organization_stats: bool = True
    include_overdue: bool = True


# =============================================================================
# 상수 정의
# =============================================================================

# 조직/기관 코드 목록
ORGANIZATIONS = [
    "ABS",
    "BV",
    "CCS",
    "CRS",
    "DNV",
    "IRS",
    "KR",
    "NK",
    "PRS",
    "RINA",
    "IL",
]

# 메일 타입
MAIL_TYPES = ["REQUEST", "RESPONSE", "NOTIFICATION", "COMPLETED", "OTHER"]

# 결정 상태
DECISION_STATUSES = ["created", "comment", "consolidated", "review", "decision"]

# 발신자 타입
SENDER_TYPES = ["CHAIR", "MEMBER"]
