"""
Email Dashboard 모듈

이메일 아젠다 및 응답 관리를 위한 대시보드 기능을 제공합니다.
- 의장 발송 아젠다 관리
- 멤버 기관 응답 관리
- 대시보드 통계 및 현황 조회

주요 컴포넌트:
- EmailDashboardOrchestrator: 메인 오케스트레이터
- EmailDashboardEventProcessor: 이벤트 처리
- EmailDashboardRepository: 데이터베이스 접근
- EmailDashboardQuery: 대시보드 조회 기능
"""

from .orchestrator import EmailDashboardOrchestrator
from .event_processor import EmailDashboardEventProcessor
from .repository import EmailDashboardRepository
from .query import EmailDashboardQuery
from .schema import (
    EmailDashboardEvent,
    EmailAgendaChair,
    EmailAgendaMemberResponse,
    EmailAgendaMemberResponseTime,
    DashboardStats,
    AgendaStatusSummary,
)

__all__ = [
    "EmailDashboardOrchestrator",
    "EmailDashboardEventProcessor",
    "EmailDashboardRepository",
    "EmailDashboardQuery",
    "EmailDashboardEvent",
    "EmailAgendaChair",
    "EmailAgendaMemberResponse",
    "EmailAgendaMemberResponseTime",
    "DashboardStats",
    "AgendaStatusSummary",
]
