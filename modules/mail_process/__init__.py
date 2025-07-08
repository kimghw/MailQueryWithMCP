#  modules/mail_process/services/processing_service.py

from .mail_processor_orchestrator import MailProcessorOrchestrator
from .mail_processor_schema import (
    MailProcessingResult,
    ProcessedMailData,
    ProcessingStatus,
    SenderType,
    MailType,
    DecisionStatus,
    GraphMailItem,
    ProcessedMailEvent,
    KeywordExtractionRequest,
    KeywordExtractionResponse,
    BatchExtractionRequest,
    BatchExtractionResponse,
)

__all__ = [
    "MailProcessorOrchestrator",
    "MailProcessingResult",
    "ProcessedMailData",
    "ProcessingStatus",
    "SenderType",
    "MailType",
    "DecisionStatus",
    "GraphMailItem",
    "ProcessedMailEvent",
    "KeywordExtractionRequest",
    "KeywordExtractionResponse",
    "BatchExtractionRequest",
    "BatchExtractionResponse",
]
