"""Mail Processor 모듈 - 메일 처리 및 키워드 추출"""

from .mail_processor_orchestrator import MailProcessorOrchestrator
from .mail_processor_schema import (
    ProcessingStatus,
    MailReceivedEvent,
    ProcessedMailData,
    MailProcessingResult,
    AccountProcessingStatus,
    KeywordExtractionRequest,
    KeywordExtractionResponse,
    GraphMailItem,
)
from .keyword_extractor_service import MailProcessorKeywordExtractorService
from .mail_filter_service import MailProcessorFilterService

__all__ = [
    # 메인 오케스트레이터
    "MailProcessorOrchestrator",
    # 스키마
    "ProcessingStatus",
    "MailReceivedEvent",
    "ProcessedMailData",
    "MailProcessingResult",
    "AccountProcessingStatus",
    "KeywordExtractionRequest",
    "KeywordExtractionResponse",
    "GraphMailItem",
    "ProcessedMailEvent",
    # 서비스
    "MailProcessorKeywordExtractorService",
    "MailProcessorFilterService",
]
