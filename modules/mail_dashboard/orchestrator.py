# modules/mail_dashboard/orchestrator.py
"""
Email Dashboard Orchestrator - 새로운 이벤트 구조 대응
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from infra.core import get_logger
from infra.core.exceptions import BusinessLogicError, ValidationError

from .event_processor import EmailDashboardEventProcessor
from .query import EmailDashboardQuery
from .repository import EmailDashboardRepository


class EmailDashboardOrchestrator:
    """Email Dashboard 메인 오케스트레이터"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.event_processor = EmailDashboardEventProcessor()
        self.repository = EmailDashboardRepository()
        self.query = EmailDashboardQuery()
        
        self.logger.info("Email Dashboard Orchestrator 초기화 완료")
    
    # =========================================================================
    # 이벤트 처리
    # =========================================================================
    
    def handle_email_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        email.received 이벤트 처리
        
        Args:
            event_data: 이벤트 데이터
            
        Returns:
            처리 결과
        """
        try:
            self.logger.info(f"이메일 이벤트 처리 시작: event_id={event_data.get('event_id', 'unknown')}")
            
            # 이벤트 타입 확인
            if event_data.get("event_type") != "email.received":
                return {
                    "success": True,
                    "action": "ignored",
                    "reason": "not_email_received_event",
                    "message": f"처리하지 않는 이벤트 타입: {event_data.get('event_type')}"
                }
            
            # 이벤트 처리
            result = self.event_processor.process_email_event(event_data)
            
            self.logger.info(
                f"이메일 이벤트 처리 완료: event_id={event_data.get('event_id')}, "
                f"success={result.get('success')}, action={result.get('action')}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"이메일 이벤트 처리 실패: {str(e)}")
            return {
                "success": False,
                "error": "event_handling_error",
                "message": f"이메일 이벤트 처리 실패: {str(e)}"
            }
    
    # =========================================================================
    # 아젠다 조회
    # =========================================================================
    
    def get_agendas(
        self, 
        panel_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        아젠다 목록 조회
        
        Args:
            panel_id: 패널 ID (선택)
            status: 상태 필터 (선택)
            limit: 조회 수 제한
            offset: 오프셋
            
        Returns:
            아젠다 목록
        """
        try:
            agendas = self.query.get_agendas(
                panel_id=panel_id,
                status=status,
                limit=limit,
                offset=offset
            )
            
            return {
                "success": True,
                "data": [agenda.model_dump() for agenda in agendas],
                "count": len(agendas),
                "pagination": {
                    "limit": limit,
                    "offset": offset
                }
            }
            
        except Exception as e:
            self.logger.error(f"아젠다 조회 실패: {str(e)}")
            return {
                "success": False,
                "error": "query_error",
                "message": f"아젠다 조회 실패: {str(e)}"
            }
    
    def get_agenda_detail(self, agenda_base_version: str) -> Dict[str, Any]:
        """
        아젠다 상세 조회
        
        Args:
            agenda_base_version: 아젠다 기본 버전
            
        Returns:
            아젠다 상세 정보
        """
        try:
            detail = self.query.get_agenda_detail(agenda_base_version)
            
            if not detail:
                return {
                    "success": False,
                    "error": "not_found",
                    "message": f"아젠다를 찾을 수 없음: {agenda_base_version}"
                }
            
            return {
                "success": True,
                "data": detail.model_dump()
            }
            
        except Exception as e:
            self.logger.error(f"아젠다 상세 조회 실패: {str(e)}")
            return {
                "success": False,
                "error": "query_error",
                "message": f"아젠다 상세 조회 실패: {str(e)}"
            }
    
    # =========================================================================
    # 대시보드 통계
    # =========================================================================
    
    def get_dashboard_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        대시보드 통계 조회
        
        Args:
            days: 조회 기간 (일)
            
        Returns:
            통계 정보
        """
        try:
            stats = self.repository.get_dashboard_stats(days)
            
            return {
                "success": True,
                "data": stats,
                "period_days": days
            }
            
        except Exception as e:
            self.logger.error(f"통계 조회 실패: {str(e)}")
            return {
                "success": False,
                "error": "stats_error",
                "message": f"통계 조회 실패: {str(e)}"
            }
    
    def get_organization_summary(self, organization: str) -> Dict[str, Any]:
        """
        특정 조직 요약 정보
        
        Args:
            organization: 조직 코드
            
        Returns:
            조직 요약 정보
        """
        try:
            summary = self.query.get_organization_summary(organization)
            
            return {
                "success": True,
                "data": summary
            }
            
        except Exception as e:
            self.logger.error(f"조직 요약 조회 실패: {str(e)}")
            return {
                "success": False,
                "error": "query_error",
                "message": f"조직 요약 조회 실패: {str(e)}"
            }
    
    # =========================================================================
    # 미처리 이벤트 관리
    # =========================================================================
    
    def get_pending_events(self, limit: int = 100) -> Dict[str, Any]:
        """
        미처리 이벤트 조회
        
        Args:
            limit: 조회 수 제한
            
        Returns:
            미처리 이벤트 목록
        """
        try:
            events = self.repository.get_pending_events(limit)
            
            return {
                "success": True,
                "data": [event.model_dump() for event in events],
                "count": len(events)
            }
            
        except Exception as e:
            self.logger.error(f"미처리 이벤트 조회 실패: {str(e)}")
            return {
                "success": False,
                "error": "query_error",
                "message": f"미처리 이벤트 조회 실패: {str(e)}"
            }
    
    def retry_pending_event(self, event_id: str) -> Dict[str, Any]:
        """
        미처리 이벤트 재시도
        
        Args:
            event_id: 이벤트 ID
            
        Returns:
            재시도 결과
        """
        try:
            # 이벤트 조회
            events = self.repository.get_pending_events(limit=1000)
            target_event = None
            
            for event in events:
                if event.event_id == event_id:
                    target_event = event
                    break
            
            if not target_event:
                return {
                    "success": False,
                    "error": "not_found",
                    "message": f"이벤트를 찾을 수 없음: {event_id}"
                }
            
            # 원본 이벤트 데이터 파싱
            import json
            raw_event = json.loads(target_event.raw_event_data)
            
            # 재처리
            result = self.event_processor.process_email_event(raw_event)
            
            if result.get("success") and result.get("action") not in ["saved_to_pending"]:
                # 성공적으로 처리된 경우
                self.repository.mark_pending_processed(event_id)
                result["retry_success"] = True
            else:
                result["retry_success"] = False
            
            return result
            
        except Exception as e:
            self.logger.error(f"이벤트 재시도 실패: {str(e)}")
            return {
                "success": False,
                "error": "retry_error",
                "message": f"이벤트 재시도 실패: {str(e)}"
            }
    
    # =========================================================================
    # 관리 기능
    # =========================================================================
    
    def clear_all_data(self) -> Dict[str, Any]:
        """
        모든 데이터 삭제 (개발/테스트용)
        
        Returns:
            삭제 결과
        """
        try:
            self.logger.warning("Email Dashboard 전체 데이터 삭제 시작")
            
            result = self.repository.clear_all_data()
            
            if result["success"]:
                self.logger.warning(f"Email Dashboard 전체 데이터 삭제 완료: {result['total_deleted']}개 레코드")
            else:
                self.logger.error(f"Email Dashboard 데이터 삭제 실패: {result.get('error')}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"데이터 삭제 중 오류: {str(e)}")
            return {
                "success": False,
                "error": "clear_data_error",
                "message": f"데이터 삭제 중 오류: {str(e)}"
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        모듈 상태 확인
        
        Returns:
            모듈 상태
        """
        try:
            # 데이터베이스 연결 확인
            from infra.core import get_database_manager
            db = get_database_manager()
            db_status = db.table_exists("agenda_all")
            
            # 기본 통계 조회
            stats = self.repository.get_dashboard_stats(7)
            
            return {
                "success": True,
                "module": "email_dashboard",
                "status": "healthy",
                "database_connected": db_status,
                "stats": stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"상태 확인 실패: {str(e)}")
            return {
                "success": False,
                "module": "email_dashboard",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }