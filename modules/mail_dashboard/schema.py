# modules/mail_dashboard/schema.py
"""
Email Dashboard 스키마 정의 - 새로운 이벤트 구조 대응
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# =============================================================================
# 이벤트 스키마 (새로운 구조)
# =============================================================================


class EventInfo(BaseModel):
    """email.received 이벤트의 event_info 구조"""

    sentDateTime: str
    hasAttachments: bool
    subject: str
    webLink: str
    body: str
    sender: str
    sender_address: str
    agenda_code: Optional[str] = None
    agenda_base: Optional[str] = None
    agenda_base_version: Optional[str] = None
    agenda_panel: Optional[str] = None
    agenda_year: Optional[str] = None
    agenda_number: Optional[str] = None
    agenda_version: Optional[str] = None
    response_org: Optional[str] = None
    response_version: Optional[str] = None
    sent_time: str
    sender_type: str
    sender_organization: Optional[str] = None
    parsing_method: str
    keywords: List[str]
    deadline: Optional[str] = None
    has_deadline: bool
    mail_type: str
    decision_status: str


class EmailReceivedEvent(BaseModel):
    """email.received 이벤트 전체 구조"""

    event_type: str
    event_id: str
    mail_id: str
    occurred_at: str
    event_info: EventInfo


# =============================================================================
# 데이터베이스 모델 스키마
# =============================================================================


class AgendaAll(BaseModel):
    """agenda_all 테이블 - 모든 이벤트 로그"""

    id: Optional[int] = None
    event_id: str
    agenda_code: str
    sender_type: str
    sender_organization: Optional[str] = None
    sent_time: datetime
    mail_type: Optional[str] = None
    decision_status: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    keywords: Optional[List[str]] = None
    response_org: Optional[str] = None
    response_version: Optional[str] = None
    deadline: Optional[datetime] = None
    has_deadline: bool = False
    sender: Optional[str] = None
    sender_address: Optional[str] = None
    agenda_panel: Optional[str] = None
    agenda_year: Optional[str] = None
    agenda_number: Optional[str] = None
    agenda_base: Optional[str] = None
    agenda_version: Optional[str] = None
    agenda_base_version: Optional[str] = None
    parsing_method: Optional[str] = None
    hasAttachments: bool = False
    sentDateTime: Optional[str] = None
    webLink: Optional[str] = None
    created_at: Optional[datetime] = None


class AgendaChair(BaseModel):
    """agenda_chair 테이블 - 의장 발송 의제"""

    agenda_base_version: str  # PK
    agenda_code: str
    sender_type: str = "CHAIR"
    sender_organization: str
    sent_time: datetime
    mail_type: str = "REQUEST"
    decision_status: str = "created"
    subject: str
    body: Optional[str] = None
    keywords: Optional[List[str]] = None
    deadline: Optional[datetime] = None
    has_deadline: bool = False
    sender: Optional[str] = None
    sender_address: Optional[str] = None
    agenda_panel: str
    agenda_year: str
    agenda_number: str
    agenda_version: Optional[str] = None
    parsing_method: Optional[str] = None
    hasAttachments: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AgendaResponsesContent(BaseModel):
    """agenda_responses_content 테이블 - 기관별 응답 내용"""

    agenda_base_version: str  # PK
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
    TL: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AgendaResponsesReceivedTime(BaseModel):
    """agenda_responses_receivedtime 테이블 - 기관별 응답 시간"""

    agenda_base_version: str  # PK
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
    TL: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AgendaPending(BaseModel):
    """agenda_pending 테이블 - 미처리 이벤트"""

    id: Optional[int] = None
    event_id: Optional[str] = None
    raw_event_data: str
    error_reason: Optional[str] = None
    sender_type: Optional[str] = None
    sender_organization: Optional[str] = None
    sent_time: Optional[datetime] = None
    subject: Optional[str] = None
    received_at: Optional[datetime] = None
    processed: bool = False
    processed_at: Optional[datetime] = None
    retry_count: int = 0


# =============================================================================
# 상수 정의
# =============================================================================

# 조직 코드 목록
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
    "TL",
]

# 메일 타입
MAIL_TYPES = ["REQUEST", "RESPONSE", "NOTIFICATION", "COMPLETED", "OTHER"]

# 결정 상태
DECISION_STATUSES = ["created", "comment", "consolidated", "review", "decision"]

# 발신자 타입
SENDER_TYPES = ["CHAIR", "MEMBER"]

# 미처리 사유
PENDING_REASONS = [
    "no_agenda_code",
    "invalid_organization",
    "parsing_failed",
    "unknown_sender_type",
    "processing_error",
    "other",
]
