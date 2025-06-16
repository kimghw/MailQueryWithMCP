"""
Mail Query 모듈
Microsoft Graph API를 통한 메일 데이터 조회 및 필터링
"""

from .mail_query_orchestrator import MailQueryOrchestrator
from .mail_query_schema import (
    MailQueryRequest,
    MailQueryResponse,
    MailQueryFilters,
    PaginationOptions,
    GraphMailItem,
    MailboxInfo,
    MailQueryLog
)

# 모듈 버전
__version__ = "1.0.0"

# 모듈 메타데이터
__author__ = "IACSGRAPH Team"
__description__ = "Microsoft Graph API 메일 조회 모듈"

# 공개 API
__all__ = [
    "MailQueryOrchestrator",
    "MailQueryRequest",
    "MailQueryResponse", 
    "MailQueryFilters",
    "PaginationOptions",
    "GraphMailItem",
    "MailboxInfo",
    "MailQueryLog"
]

# 모듈 초기화 함수
def get_mail_query_orchestrator() -> MailQueryOrchestrator:
    """Mail Query 오케스트레이터 인스턴스 반환"""
    return MailQueryOrchestrator()

# 편의 함수들
async def query_user_emails(request: MailQueryRequest) -> MailQueryResponse:
    """사용자 메일 조회 편의 함수"""
    orchestrator = get_mail_query_orchestrator()
    return await orchestrator.mail_query_user_emails(request)

async def search_messages(user_id: str, search_term: str, **kwargs) -> MailQueryResponse:
    """메시지 검색 편의 함수"""
    orchestrator = get_mail_query_orchestrator()
    return await orchestrator.mail_query_search_messages(user_id, search_term, **kwargs)

async def get_mailbox_info(user_id: str) -> MailboxInfo:
    """메일박스 정보 조회 편의 함수"""
    orchestrator = get_mail_query_orchestrator()
    return await orchestrator.mail_query_get_mailbox_info(user_id)

async def get_message_by_id(user_id: str, message_id: str, **kwargs) -> GraphMailItem:
    """특정 메시지 조회 편의 함수"""
    orchestrator = get_mail_query_orchestrator()
    return await orchestrator.mail_query_get_message_by_id(user_id, message_id, **kwargs)
