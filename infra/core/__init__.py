"""
Email Dashboard 모듈

이메일 아젠다 및 응답 관리를 위한 대시보드 기능을 제공합니다.
- 의장 발송 아젠다 관리
- 멤버 기관 응답 관리
- 대시보드 통계 및 현황 조회
- 자동 테이블 초기화
- 이벤트 구독 및 처리

주요 컴포넌트:
- EmailDashboardOrchestrator: 메인 오케스트레이터
- EmailDashboardEventProcessor: 이벤트 처리
- EmailDashboardRepository: 데이터베이스 접근
- EmailDashboardQuery: 대시보드 조회 기능
- EmailDashboardService: 모듈 서비스 관리
"""

# 안전한 import를 위한 예외 처리
try:
    from .schema import (
        EmailDashboardEvent,
        EmailAgendaChair,
        EmailAgendaMemberResponse,
        EmailAgendaMemberResponseTime,
        DashboardStats,
        AgendaStatusSummary,
        ORGANIZATIONS,
    )

    from .repository import EmailDashboardRepository
    from .query import EmailDashboardQuery
    from .event_processor import EmailDashboardEventProcessor
    from .orchestrator import EmailDashboardOrchestrator
    from .service import EmailDashboardService

except ImportError as e:
    print(f"Email Dashboard 모듈 import 오류: {e}")
    print("의존성 확인:")
    print("1. infra.core 모듈이 올바르게 설정되었는지 확인")
    print("2. 프로젝트 루트에서 실행하고 있는지 확인")
    print("3. PYTHONPATH가 올바르게 설정되었는지 확인")
    raise

__all__ = [
    "EmailDashboardOrchestrator",
    "EmailDashboardEventProcessor",
    "EmailDashboardRepository",
    "EmailDashboardQuery",
    "EmailDashboardService",
    "EmailDashboardEvent",
    "EmailAgendaChair",
    "EmailAgendaMemberResponse",
    "EmailAgendaMemberResponseTime",
    "DashboardStats",
    "AgendaStatusSummary",
    "ORGANIZATIONS",
]

# 모듈 레벨에서 서비스 인스턴스 생성 (싱글톤 방식)
_dashboard_service = None


def get_dashboard_service() -> EmailDashboardService:
    """Email Dashboard 서비스 인스턴스를 반환합니다 (싱글톤)"""
    global _dashboard_service
    if _dashboard_service is None:
        _dashboard_service = EmailDashboardService()
    return _dashboard_service


def initialize_dashboard_module() -> bool:
    """
    Email Dashboard 모듈을 초기화합니다.

    Returns:
        초기화 성공 여부
    """
    try:
        service = get_dashboard_service()
        return service.initialize()
    except Exception as e:
        print(f"Email Dashboard 모듈 초기화 실패: {str(e)}")
        return False


def start_dashboard_event_subscription() -> bool:
    """
    Email Dashboard 이벤트 구독을 시작합니다.

    Returns:
        구독 시작 성공 여부
    """
    try:
        service = get_dashboard_service()
        return service.start_event_subscription()
    except Exception as e:
        print(f"Email Dashboard 이벤트 구독 시작 실패: {str(e)}")
        return False


def stop_dashboard_event_subscription() -> bool:
    """
    Email Dashboard 이벤트 구독을 중지합니다.

    Returns:
        구독 중지 성공 여부
    """
    try:
        service = get_dashboard_service()
        return service.stop_event_subscription()
    except Exception as e:
        print(f"Email Dashboard 이벤트 구독 중지 실패: {str(e)}")
        return False
