"""
Email Dashboard Orchestrator

Email Dashboard 모듈의 메인 오케스트레이터입니다.
이벤트 처리, 조회, 통계 기능을 조율합니다.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from infra.core import get_logger
from infra.core.exceptions import BusinessLogicError, ValidationError

from .event_processor import EmailDashboardEventProcessor
from .query import EmailDashboardQuery
from .repository import EmailDashboardRepository
from .schema import (
    AgendaDetail,
    AgendaSearchFilter,
    AgendaStatusSummary,
    AgendaTimeline,
    DashboardRequest,
    DashboardStats,
)


class EmailDashboardOrchestrator:
    """Email Dashboard 메인 오케스트레이터"""

    def __init__(self):
        self.logger = get_logger(__name__)

        # 의존성 주입 - 모듈 간 의존성 없이 생성
        self.event_processor = EmailDashboardEventProcessor()
        self.repository = EmailDashboardRepository()
        self.query = EmailDashboardQuery()

        self.logger.info("Email Dashboard Orchestrator 초기화 완료")

    # =========================================================================
    # 이벤트 처리 관련 메서드
    # =========================================================================

    def email_dashboard_handle_email_event(
        self, event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        이메일 이벤트 처리

        Args:
            event_data: 이메일 관련 이벤트 데이터

        Returns:
            처리 결과
        """
        try:
            self.logger.info(
                f"이메일 이벤트 처리 시작: event_id={event_data.get('event_id', 'unknown')}"
            )

            # 이벤트 타입 검증
            if event_data.get("event_type") != "email-dashboard":
                return {
                    "success": True,
                    "action": "ignored",
                    "reason": "not_email_dashboard_event",
                    "message": f"Email Dashboard 이벤트가 아님: {event_data.get('event_type')}",
                }

            # 이벤트 처리
            result = self.event_processor.email_dashboard_process_event(event_data)

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
                "message": f"이메일 이벤트 처리 실패: {str(e)}",
            }

    def email_dashboard_handle_batch_events(
        self, events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        배치 이메일 이벤트 처리

        Args:
            events: 이메일 이벤트 목록

        Returns:
            배치 처리 결과
        """
        try:
            self.logger.info(f"배치 이메일 이벤트 처리 시작: {len(events)}개 이벤트")

            # 이메일 대시보드 이벤트만 필터링
            dashboard_events = []
            for event in events:
                if event.get("event_type") == "email-dashboard":
                    dashboard_events.append(event)

            if not dashboard_events:
                return {
                    "success": True,
                    "action": "no_events_to_process",
                    "message": "처리할 Email Dashboard 이벤트가 없음",
                }

            # 배치 처리
            result = self.event_processor.email_dashboard_process_batch_events(
                dashboard_events
            )

            self.logger.info(
                f"배치 이메일 이벤트 처리 완료: 총 {len(events)}개 중 "
                f"{len(dashboard_events)}개 처리, 성공 {result.get('success_count', 0)}개"
            )

            return result

        except Exception as e:
            self.logger.error(f"배치 이메일 이벤트 처리 실패: {str(e)}")
            return {
                "success": False,
                "error": "batch_event_handling_error",
                "message": f"배치 이메일 이벤트 처리 실패: {str(e)}",
            }

    # =========================================================================
    # 아젠다 조회 관련 메서드
    # =========================================================================

    def email_dashboard_search_agendas(
        self,
        filter_params: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        아젠다 검색

        Args:
            filter_params: 검색 필터 매개변수
            limit: 조회 제한 수
            offset: 오프셋

        Returns:
            검색 결과
        """
        try:
            self.logger.debug(
                f"아젠다 검색 시작: filter={filter_params}, limit={limit}"
            )

            # 필터 생성
            search_filter = AgendaSearchFilter()
            if filter_params:
                # 날짜 문자열을 datetime 객체로 변환
                if "start_date" in filter_params and filter_params["start_date"]:
                    filter_params["start_date"] = datetime.fromisoformat(
                        filter_params["start_date"]
                    )
                if "end_date" in filter_params and filter_params["end_date"]:
                    filter_params["end_date"] = datetime.fromisoformat(
                        filter_params["end_date"]
                    )
                if (
                    "deadline_start" in filter_params
                    and filter_params["deadline_start"]
                ):
                    filter_params["deadline_start"] = datetime.fromisoformat(
                        filter_params["deadline_start"]
                    )
                if "deadline_end" in filter_params and filter_params["deadline_end"]:
                    filter_params["deadline_end"] = datetime.fromisoformat(
                        filter_params["deadline_end"]
                    )

                search_filter = AgendaSearchFilter(**filter_params)

            # 검색 실행
            agendas = self.query.email_dashboard_query_get_agendas_by_filter(
                search_filter, limit, offset
            )

            # 결과 변환
            agenda_list = [agenda.model_dump() for agenda in agendas]

            self.logger.info(f"아젠다 검색 완료: {len(agenda_list)}개 조회")

            return {
                "success": True,
                "data": agenda_list,
                "count": len(agenda_list),
                "filter": search_filter.model_dump(),
                "pagination": {"limit": limit, "offset": offset},
            }

        except ValidationError as e:
            self.logger.error(f"아젠다 검색 필터 오류: {str(e)}")
            return {
                "success": False,
                "error": "validation_error",
                "message": f"검색 필터 오류: {str(e)}",
            }
        except Exception as e:
            self.logger.error(f"아젠다 검색 실패: {str(e)}")
            return {
                "success": False,
                "error": "search_error",
                "message": f"아젠다 검색 실패: {str(e)}",
            }

    def email_dashboard_get_agenda_detail(self, agenda_no: str) -> Dict[str, Any]:
        """
        아젠다 상세 정보 조회

        Args:
            agenda_no: 아젠다 번호

        Returns:
            아젠다 상세 정보
        """
        try:
            self.logger.debug(f"아젠다 상세 조회: {agenda_no}")

            # 기본 아젠다 정보 조회
            agenda = self.repository.email_dashboard_get_agenda(agenda_no)
            if not agenda:
                return {
                    "success": False,
                    "error": "not_found",
                    "message": f"아젠다를 찾을 수 없음: {agenda_no}",
                }

            # 응답 정보 조회
            responses = self.query._email_dashboard_query_get_agenda_responses(
                agenda_no
            )
            response_count = len([r for r in responses if r.has_responded])

            # AgendaDetail 객체 생성
            agenda_detail = AgendaDetail(
                agenda_no=agenda.agenda_no,
                panel_id=agenda.panel_id,
                round_no=agenda.round_no,
                agenda_sequence=agenda.agenda_sequence,
                send_time=agenda.send_time,
                deadline=agenda.deadline,
                mail_type=agenda.mail_type,
                decision_status=agenda.decision_status,
                summary=agenda.summary,
                responses=responses,
                response_count=response_count,
                total_organizations=len(responses),
            )

            self.logger.info(f"아젠다 상세 조회 완료: {agenda_no}")

            return {"success": True, "data": agenda_detail.model_dump()}

        except Exception as e:
            self.logger.error(f"아젠다 상세 조회 실패: {agenda_no}, error={str(e)}")
            return {
                "success": False,
                "error": "detail_query_error",
                "message": f"아젠다 상세 조회 실패: {str(e)}",
            }

    def email_dashboard_get_agenda_timeline(self, agenda_no: str) -> Dict[str, Any]:
        """
        아젠다 타임라인 조회

        Args:
            agenda_no: 아젠다 번호

        Returns:
            아젠다 타임라인
        """
        try:
            self.logger.debug(f"아젠다 타임라인 조회: {agenda_no}")

            timeline = self.query.email_dashboard_query_get_agenda_timeline(agenda_no)

            self.logger.info(
                f"아젠다 타임라인 조회 완료: {agenda_no}, 이벤트 {len(timeline.events)}개"
            )

            return {"success": True, "data": timeline.model_dump()}

        except Exception as e:
            self.logger.error(f"아젠다 타임라인 조회 실패: {agenda_no}, error={str(e)}")
            return {
                "success": False,
                "error": "timeline_query_error",
                "message": f"아젠다 타임라인 조회 실패: {str(e)}",
            }

    # =========================================================================
    # 대시보드 통계 관련 메서드
    # =========================================================================

    def email_dashboard_get_dashboard_stats(
        self, request_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        대시보드 통계 조회

        Args:
            request_params: 요청 매개변수

        Returns:
            대시보드 통계
        """
        try:
            self.logger.debug(f"대시보드 통계 조회 시작: params={request_params}")

            # 요청 매개변수 처리
            dashboard_request = DashboardRequest()
            if request_params:
                dashboard_request = DashboardRequest(**request_params)

            # 통계 조회
            stats = self.query.email_dashboard_query_get_dashboard_stats(
                dashboard_request.date_range_days
            )

            self.logger.info(
                f"대시보드 통계 조회 완료: 총 아젠다 {stats.total_agendas}개, "
                f"응답률 {stats.overall_response_rate:.2%}"
            )

            return {
                "success": True,
                "data": stats.model_dump(),
                "request_params": dashboard_request.model_dump(),
            }

        except Exception as e:
            self.logger.error(f"대시보드 통계 조회 실패: {str(e)}")
            return {
                "success": False,
                "error": "stats_query_error",
                "message": f"대시보드 통계 조회 실패: {str(e)}",
            }

    def email_dashboard_get_pending_agendas(self) -> Dict[str, Any]:
        """
        진행중인 아젠다 목록 조회

        Returns:
            진행중인 아젠다 목록
        """
        try:
            self.logger.debug("진행중인 아젠다 조회 시작")

            pending_agendas = self.query.email_dashboard_query_get_pending_agendas()

            # 결과 변환
            agenda_list = [agenda.model_dump() for agenda in pending_agendas]

            self.logger.info(f"진행중인 아젠다 조회 완료: {len(agenda_list)}개")

            return {"success": True, "data": agenda_list, "count": len(agenda_list)}

        except Exception as e:
            self.logger.error(f"진행중인 아젠다 조회 실패: {str(e)}")
            return {
                "success": False,
                "error": "pending_query_error",
                "message": f"진행중인 아젠다 조회 실패: {str(e)}",
            }

    def email_dashboard_get_overdue_agendas(self) -> Dict[str, Any]:
        """
        마감 지난 아젠다 목록 조회

        Returns:
            마감 지난 아젠다 목록
        """
        try:
            self.logger.debug("마감 지난 아젠다 조회 시작")

            overdue_agendas = self.query.email_dashboard_query_get_overdue_agendas()

            # 결과 변환
            agenda_list = [agenda.model_dump() for agenda in overdue_agendas]

            self.logger.info(f"마감 지난 아젠다 조회 완료: {len(agenda_list)}개")

            return {"success": True, "data": agenda_list, "count": len(agenda_list)}

        except Exception as e:
            self.logger.error(f"마감 지난 아젠다 조회 실패: {str(e)}")
            return {
                "success": False,
                "error": "overdue_query_error",
                "message": f"마감 지난 아젠다 조회 실패: {str(e)}",
            }

    # =========================================================================
    # 관리자 기능
    # =========================================================================

    def email_dashboard_clear_all_data(self) -> Dict[str, Any]:
        """
        모든 Email Dashboard 데이터 삭제 (개발/테스트용)

        Returns:
            삭제 결과
        """
        try:
            self.logger.warning("Email Dashboard 전체 데이터 삭제 시작")

            result = self.repository.email_dashboard_clear_all_data()

            if result["success"]:
                self.logger.warning(
                    f"Email Dashboard 전체 데이터 삭제 완료: {result['total_deleted']}개 레코드"
                )
            else:
                self.logger.error(
                    f"Email Dashboard 데이터 삭제 실패: {result.get('error')}"
                )

            return result

        except Exception as e:
            self.logger.error(f"Email Dashboard 데이터 삭제 중 오류: {str(e)}")
            return {
                "success": False,
                "error": "clear_data_error",
                "message": f"데이터 삭제 중 오류: {str(e)}",
            }

    def email_dashboard_get_health_status(self) -> Dict[str, Any]:
        """
        Email Dashboard 모듈 상태 확인

        Returns:
            모듈 상태
        """
        try:
            # 데이터베이스 연결 확인
            db_status = self.repository.db.table_exists("email_agendas_chair")

            # 기본 통계 조회 (간단한 동작 확인)
            stats = self.query.email_dashboard_query_get_dashboard_stats(7)  # 최근 7일

            return {
                "success": True,
                "module": "email_dashboard",
                "status": "healthy",
                "database_connected": db_status,
                "recent_agendas": stats.total_agendas,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Email Dashboard 상태 확인 실패: {str(e)}")
            return {
                "success": False,
                "module": "email_dashboard",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
