"""
Mail Processor 모듈 스키마 정의 - Pydantic v2 호환
modules/mail_process/mail_processor_schema.py
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# AgendaInfo 클래스 삭제됨 - 플랫한 구조로 변경

from pydantic import BaseModel, Field, ConfigDict


class ProcessingStatus(str, Enum):
    """처리 상태"""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    PARTIAL = "PARTIAL"


class SenderType(str, Enum):
    """발신자 타입"""

    CHAIR = "CHAIR"
    MEMBER = "MEMBER"
    UNKNOWN = "UNKNOWN"


class MailType(str, Enum):
    """메일 타입"""

    REQUEST = "REQUEST"
    RESPONSE = "RESPONSE"
    NOTIFICATION = "NOTIFICATION"
    COMPLETED = "COMPLETED"
    OTHER = "OTHER"


class DecisionStatus(str, Enum):
    """결정 상태"""

    CREATED = "created"
    COMMENT = "comment"
    CONSOLIDATED = "consolidated"
    REVIEW = "review"
    DECISION = "decision"


class GraphMailItem(BaseModel):
    """Graph API 메일 아이템"""

    model_config = ConfigDict(populate_by_name=True)

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


class MailHistoryData(BaseModel):
    """mail_history 테이블 저장용 데이터"""

    account_id: str
    message_id: str
    received_time: datetime
    subject: str
    sender: str
    processed_at: datetime = Field(default_factory=datetime.now)


class ProcessedMailData(BaseModel):
    """처리된 메일 데이터 - 통일된 네이밍"""

    # 기본 정보
    mail_id: str
    account_id: str
    subject: str
    body_preview: str
    sent_time: datetime
    processed_at: datetime = Field(default_factory=datetime.now)

    # 발신자 정보
    sender_address: str
    sender_name: str = ""
    sender_type: Optional[SenderType] = None
    sender_organization: Optional[str] = None

    # 처리 결과
    keywords: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    processing_status: ProcessingStatus
    error_message: Optional[str] = None

    # IACS 관련 정보 - 통일된 네이밍
    agenda_code: Optional[str] = None  # 전체 코드 (PL25016a)
    agenda_base: Optional[str] = None  # 기본 번호 (PL25016)
    agenda_version: Optional[str] = None  # 버전 (a)
    agenda_panel: Optional[str] = None  # 패널 (PL/PS/JWG-SDT 등) - agenda_org에서 변경
    response_org: Optional[str] = None  # 응답 조직 (IR)
    response_version: Optional[str] = None  # 응답 버전 (a)
    agenda_info: Optional[Dict[str, Any]] = None
    additional_agenda_references: List[str] = Field(default_factory=list)

    # 메일 메타정보
    mail_type: MailType = MailType.OTHER
    decision_status: DecisionStatus = DecisionStatus.CREATED
    urgency: str = "NORMAL"
    is_reply: bool = False
    reply_depth: Optional[int] = None
    is_forward: bool = False
    has_deadline: bool = False
    deadline: Optional[datetime] = None

    # 정제된 내용
    clean_content: Optional[str] = None

    # 추출 메타데이터
    extraction_metadata: Optional[Dict[str, Any]] = None


class MailReceivedEvent(BaseModel):
    """Kafka로 전송될 메일 수신 이벤트"""

    event_type: str = "email_type"
    event_id: str
    account_id: str
    occurred_at: datetime
    api_endpoint: str = "/v1.0/me/messages"
    response_status: int = 200
    request_params: Dict[str, Any]
    response_data: Dict[str, Any]
    response_timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class MailProcessingResult(BaseModel):
    """메일 처리 결과"""

    # 필수 필드들
    success: bool
    mail_id: str
    account_id: str

    # 선택적 필드들
    filtered: bool = False
    filter_reason: Optional[str] = None
    error: Optional[str] = None
    processed_data: Optional[ProcessedMailData] = None
    keywords: List[str] = Field(default_factory=list)

    # 배치 처리 통계 (선택적)
    total_fetched: Optional[int] = None
    filtered_count: Optional[int] = None
    new_count: Optional[int] = None
    duplicate_count: Optional[int] = None
    processed_count: Optional[int] = None
    saved_count: Optional[int] = None
    failed_count: Optional[int] = None
    skipped_count: Optional[int] = None
    events_published: Optional[int] = None
    last_sync_time: Optional[datetime] = None
    execution_time_ms: Optional[int] = None
    success_rate: Optional[float] = None
    duplication_rate: Optional[float] = None
    processing_efficiency: Optional[float] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ProcessedMailEvent(BaseModel):
    """처리된 메일 이벤트 - 통일된 네이밍"""

    model_config = ConfigDict(populate_by_name=True)

    # Graph API 필드
    id: str
    subject: str
    from_address: Optional[Dict[str, Any]] = Field(alias="from")
    receivedDateTime: datetime
    bodyPreview: str
    body: Dict[str, Any]

    # 추가된 필드들 - 통일된 네이밍
    sender_organization: Optional[str] = None
    sender_type: Optional[str] = None
    agenda_code: Optional[str] = None  # 전체 코드
    agenda_base: Optional[str] = None  # 기본 번호
    agenda_panel: Optional[str] = None  # 패널 (PL/PS/JWG-SDT 등) - agenda_org에서 변경
    response_org: Optional[str] = None  # 응답 조직
    response_version: Optional[str] = None  # 응답 버전
    extracted_keywords: List[str] = Field(default_factory=list)
    urgency: str = "NORMAL"
    is_reply: bool = False
    is_forward: bool = False
    mail_type: str = "OTHER"
    decision_status: str = "created"
    has_deadline: bool = False
    deadline: Optional[datetime] = None
    summary: Optional[str] = None


class KeywordExtractionRequest(BaseModel):
    """키워드 추출 요청"""

    text: str
    subject: Optional[str] = None
    sent_time: Optional[datetime] = None
    sender_address: Optional[str] = None
    sender_name: Optional[str] = None
    max_keywords: int = 5
    use_structured_response: bool = True


class KeywordExtractionResponse(BaseModel):
    """키워드 추출 응답"""

    keywords: List[str]
    method: str  # "openrouter", "fallback", "empty_text", "cache"
    model: str  # 사용된 모델명
    execution_time_ms: int
    cached: bool = False
    token_info: Dict[str, Any] = Field(default_factory=dict)
    structured_data: Optional[Dict[str, Any]] = None  # 구조화된 추출 데이터


class BatchExtractionRequest(BaseModel):
    """배치 키워드 추출 요청"""

    items: List[Dict[str, Any]]
    batch_size: int = 50
    concurrent_requests: int = 5


class BatchExtractionResponse(BaseModel):
    """배치 키워드 추출 응답"""

    results: List[List[str]]
    total_items: int
    successful_items: int
    failed_items: int
    execution_time_ms: int


# modules/mail_process/mail_processor_schema.py에 추가
class MailEventSchema(BaseModel):
    """메일 이벤트 표준 스키마"""

    event_type: str = Field(..., description="이벤트 타입")
    event_id: str = Field(..., description="고유 이벤트 ID")
    account_id: str = Field(..., description="계정 ID")
    mail_id: str = Field(..., description="메일 ID")
    occurred_at: str = Field(..., description="이벤트 발생 시간")
    source: str = Field(default="mail_process", description="이벤트 출처")
    version: str = Field(default="1.0", description="이벤트 버전")
    data: Dict[str, Any] = Field(..., description="이벤트 데이터")

    class Config:
        schema_extra = {
            "example": {
                "event_type": "email.received",
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "account_id": "user@company.com",
                "mail_id": "AAMkAGI2TG93AAA=",
                "occurred_at": "2024-01-01T12:00:00Z",
                "source": "mail_process",
                "version": "1.0",
                "data": {
                    "mail": {...},
                    "iacs_info": {...},
                    "keywords": ["PL25016", "urgent"],
                    "metadata": {...},
                },
            }
        }
