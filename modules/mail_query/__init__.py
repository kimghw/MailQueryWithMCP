"""
Mail Query 모듈
Microsoft Graph API를 통한 메일 조회 기능 제공
"""

from .mail_query_orchestrator import MailQueryOrchestrator
from .mail_query_schema import (
    MailQueryRequest,
    MailQueryResponse,
    MailQueryFilters,
    PaginationOptions,
    GraphMailItem,
    KeywordFilter,
    # 단일 메일 조회
    SingleEmailRequest,
    SingleEmailResponse,
    # 첨부파일 조회
    AttachmentItem,
    EmailAttachmentsRequest,
    EmailAttachmentsResponse,
    # 첨부파일 다운로드
    AttachmentDownloadRequest,
    AttachmentDownloadResponse,
)

__all__ = [
    "MailQueryOrchestrator",
    "MailQueryRequest",
    "MailQueryResponse",
    "MailQueryFilters",
    "PaginationOptions",
    "GraphMailItem",
    "KeywordFilter",
    # 단일 메일 조회
    "SingleEmailRequest",
    "SingleEmailResponse",
    # 첨부파일 조회
    "AttachmentItem",
    "EmailAttachmentsRequest",
    "EmailAttachmentsResponse",
    # 첨부파일 다운로드
    "AttachmentDownloadRequest",
    "AttachmentDownloadResponse",
]
