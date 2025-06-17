"""Mail Processor 모듈 스키마 정의"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# 데이터 스키마 객체에 대해서 가각 설명해주는 주석을 추가합니다.
## GrapMailItem 클래스는 Microsoft Graph API를 통해 가져온 메일 아이템을 표현합니다.
## ProcessingStatus 클래스는 메일 처리 상태를 나타내는 Enum입니다.
## MailReceivedEvent 클래스는 메일 수신 이벤트를 Kafka로 전송하기 위한 스키마입니다.
## ProcessedMailData 클래스는 처리된 메일 데이터를 표현합니다.
## MailProcessingResult 클래스는 메일 처리 결과를 요약합니다.
## AccountProcessingStatus 클래스는 계정별 메일 처리 상태를 나타냅니다.
## KeywordExtractionRequest 클래스는 키워드 추출 요청을 표현합니다.
## KeywordExtractionResponse 클래스는 키워드 추출 응답을 표현합니다.


# 스키마와 호출 파이프라인을 주석으로 작성합니다.
# GraphMailItem: Microsoft Graph API를 통해 가져온 메일 아이템을 표현합니다.


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


class ProcessingStatus(str, Enum):
    """처리 상태"""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


# 이벤트 발행 스키마
class MailReceivedEvent(BaseModel):
    """Kafka로 전송될 메일 수신 이벤트"""

    event_type: str = "email.raw_data_received"
    event_id: str
    account_id: str
    occurred_at: datetime
    api_endpoint: str = "/v1.0/me/messages"
    response_status: int = 200
    request_params: Dict[str, Any]
    response_data: Dict[str, Any]  # 전체 Graph API 응답
    response_timestamp: datetime


class ProcessedMailData(BaseModel):
    """처리된 메일 데이터"""

    mail_id: str
    account_id: str
    sender_address: str
    subject: str
    body_preview: str
    sent_time: datetime
    keywords: List[str] = Field(default_factory=list)
    processing_status: ProcessingStatus
    error_message: Optional[str] = None
    processed_at: datetime = Field(default_factory=datetime.now)


class MailProcessingResult(BaseModel):
    """메일 처리 결과"""

    account_id: str
    total_fetched: int
    processed_count: int
    skipped_count: int
    failed_count: int
    last_sync_time: datetime
    execution_time_ms: int
    errors: List[str] = Field(default_factory=list)


class AccountProcessingStatus(BaseModel):
    """계정별 처리 상태"""

    account_id: str
    email: str
    status: str
    last_sync_at: Optional[datetime] = None
    error_message: Optional[str] = None


class KeywordExtractionRequest(BaseModel):
    """키워드 추출 요청"""

    text: str
    max_keywords: int = 5


class KeywordExtractionResponse(BaseModel):
    """키워드 추출 응답"""

    keywords: List[str]
    method: str  # "openrouter", "fallback", "empty_text", "fallback_error"
    model: str  # 사용된 모델명 (예: "openai/o3-mini", "rule_based")
    execution_time_ms: int
    token_info: Dict[str, Any] = Field(
        default_factory=dict, description="토큰 사용량 정보"
    )
