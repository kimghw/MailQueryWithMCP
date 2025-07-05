"""
Email Dashboard Query

대시보드 조회 및 통계 기능을 제공합니다.
미처리 이벤트 조회 기능 추가
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from infra.core import get_database_manager, get_logger
from infra.core.exceptions import DatabaseError

from .schema import (
    ORGANIZATIONS,
    AgendaDetail,
    AgendaSearchFilter,
    AgendaStatusSummary,
    AgendaTimeline,
    DashboardStats,
    EmailEventUnprocessed,
    OrganizationResponse,
    OrganizationStats,
    TimelineEvent,
    UnprocessedEventFilter,
    UnprocessedEventSummary,
)


class EmailDashboardQuery:
    """Email Dashboard 조회 및 통계 서비스"""

    def __init__(self):
        self.db = get_database_manager()
        self.logger = get_logger(__name__)

    # =========================================================================
    # 기본 아젠다 조회
    # =========================================================================

    def email_dashboard_query_get_agendas_by_filter(
        self, filter_params: AgendaSearchFilter, limit: int = 50, offset: int = 0
    ) -> List[AgendaDetail]:
        """
        필터 조건에 따른 아젠다 목록 조회

        Args:
            filter_params: 검색 필터
            limit: 조회 제한 수
            offset: 오프셋

        Returns:
            아젠다 상세 목록
        """
        try:
            # WHERE 조건 구성
            where_conditions = []
            params = []

            if filter_params.panel_id:
                where_conditions.append("c.panel_id = ?")
                params.append(filter_params.panel_id)

            if filter_params.round_no:
                where_conditions.append("c.round_no = ?")
                params.append(filter_params.round_no)

            if filter_params.agenda_version:
                where_conditions.append("c.agenda_version = ?")
                params.append(filter_params.agenda_version)

            if filter_params.decision_status:
                where_conditions.append("c.decision_status = ?")
                params.append(filter_params.decision_status)

            if filter_params.mail_type:
                where_conditions.append("c.mail_type = ?")
                params.append(filter_params.mail_type)

            if filter_params.start_date:
                where_conditions.append("c.send_time >= ?")
                params.append(filter_params.start_date.isoformat())

            if filter_params.end_date:
                where_conditions.append("c.send_time <= ?")
                params.append(filter_params.end_date.isoformat())

            if filter_params.deadline_start:
                where_conditions.append("c.deadline >= ?")
                params.append(filter_params.deadline_start.isoformat())

            if filter_params.deadline_end:
                where_conditions.append("c.deadline <= ?")
                params.append(filter_params.deadline_end.isoformat())

            if filter_params.has_deadline is not None:
                if filter_params.has_deadline:
                    where_conditions.append("c.deadline IS NOT NULL")
                else:
                    where_conditions.append("c.deadline IS NULL")

            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            # 기본 쿼리
            query = f"""
                SELECT c.panel_id, c.agenda_no, c.round_no, c.agenda_version,
                       c.send_time, c.deadline, c.mail_type, c.decision_status, c.summary
                FROM email_agendas_chair c
                WHERE {where_clause}
                ORDER BY c.send_time DESC
                LIMIT ? OFFSET ?
            """

            params.extend([limit, offset])

            rows = self.db.fetch_all(query, params)

            agendas = []
            for row in rows:
                agenda = self._email_dashboard_query_build_agenda_detail(row)

                # 필터 추가 처리 (응답 상태 기반)
                if filter_params.organization or filter_params.response_status:
                    if self._email_dashboard_query_matches_response_filter(
                        agenda, filter_params
                    ):
                        agendas.append(agenda)
                else:
                    agendas.append(agenda)

            return agendas

        except Exception as e:
            self.logger.error(f"아젠다 필터 조회 실패: {str(e)}")
            raise DatabaseError(
                f"아젠다 필터 조회 실패: {str(e)}", operation="get_agendas_by_filter"
            ) from e

    def _email_dashboard_query_build_agenda_detail(
        self, row: Dict[str, Any]
    ) -> AgendaDetail:
        """데이터베이스 row에서 AgendaDetail 객체 생성"""
        agenda_no = row["agenda_no"]

        # 응답 정보 조회
        responses = self._email_dashboard_query_get_agenda_responses(agenda_no)
        response_count = len([r for r in responses if r.has_responded])

        return AgendaDetail(
            agenda_no=agenda_no,
            panel_id=row["panel_id"],
            round_no=row["round_no"],
            agenda_version=row["agenda_version"],
            send_time=datetime.fromisoformat(row["send_time"]),
            deadline=(
                datetime.fromisoformat(row["deadline"]) if row["deadline"] else None
            ),
            mail_type=row["mail_type"],
            decision_status=row["decision_status"],
            summary=row["summary"],
            responses=responses,
            response_count=response_count,
            total_organizations=len(ORGANIZATIONS),
        )

    def _email_dashboard_query_get_agenda_responses(
        self, agenda_no: str
    ) -> List[OrganizationResponse]:
        """아젠다의 기관별 응답 정보 조회"""
        try:
            # 응답 내용과 시간 조회
            content_row = self.db.fetch_one(
                f"""
                SELECT {', '.join(ORGANIZATIONS)}
                FROM email_agenda_member_responses 
                WHERE agenda_no = ?
                """,
                (agenda_no,),
            )

            time_row = self.db.fetch_one(
                f"""
                SELECT {', '.join(ORGANIZATIONS)}
                FROM email_agenda_member_response_times 
                WHERE agenda_no = ?
                """,
                (agenda_no,),
            )

            responses = []
            for org in ORGANIZATIONS:
                response_content = content_row[org] if content_row else None
                response_time_str = time_row[org] if time_row else None
                response_time = (
                    datetime.fromisoformat(response_time_str)
                    if response_time_str
                    else None
                )

                has_responded = (
                    response_content is not None and response_content.strip() != ""
                )

                responses.append(
                    OrganizationResponse(
                        organization=org,
                        response_content=response_content,
                        response_time=response_time,
                        has_responded=has_responded,
                    )
                )

            return responses

        except Exception as e:
            self.logger.error(f"아젠다 응답 조회 실패: {agenda_no}, error={str(e)}")
            return []

    def _email_dashboard_query_matches_response_filter(
        self, agenda: AgendaDetail, filter_params: AgendaSearchFilter
    ) -> bool:
        """응답 기반 필터 매칭 확인"""
        if filter_params.organization:
            # 특정 기관이 응답한 아젠다만
            org_response = next(
                (
                    r
                    for r in agenda.responses
                    if r.organization == filter_params.organization
                ),
                None,
            )
            if not org_response or not org_response.has_responded:
                return False

        if filter_params.response_status:
            if filter_params.response_status == "responded":
                # 모든 기관이 응답한 아젠다만
                if agenda.response_count < agenda.total_organizations:
                    return False
            elif filter_params.response_status == "not_responded":
                # 미응답이 있는 아젠다만
                if agenda.response_count >= agenda.total_organizations:
                    return False

        return True

    # =========================================================================
    # 아젠다 상태 조회
    # =========================================================================

    def email_dashboard_query_get_pending_agendas(self) -> List[AgendaStatusSummary]:
        """진행중인 아젠다 요약 목록"""
        try:
            query = """
                SELECT c.agenda_no, c.panel_id, c.decision_status, c.deadline
                FROM email_agendas_chair c
                WHERE c.decision_status IN ('created', 'comment', 'consolidated')
                ORDER BY c.deadline ASC, c.send_time ASC
            """

            rows = self.db.fetch_all(query)

            summaries = []
            current_time = datetime.now(timezone.utc)

            for row in rows:
                # 응답률 계산
                response_count = self._email_dashboard_query_get_response_count(
                    row["agenda_no"]
                )
                response_rate = response_count / len(ORGANIZATIONS)

                # 마감일 계산
                deadline = (
                    datetime.fromisoformat(row["deadline"]) if row["deadline"] else None
                )
                days_until_deadline = None
                is_overdue = False

                if deadline:
                    time_diff = deadline - current_time
                    days_until_deadline = time_diff.days
                    is_overdue = time_diff.total_seconds() < 0

                summaries.append(
                    AgendaStatusSummary(
                        agenda_no=row["agenda_no"],
                        panel_id=row["panel_id"],
                        decision_status=row["decision_status"],
                        response_rate=response_rate,
                        days_until_deadline=days_until_deadline,
                        is_overdue=is_overdue,
                    )
                )

            return summaries

        except Exception as e:
            self.logger.error(f"진행중 아젠다 조회 실패: {str(e)}")
            raise DatabaseError(
                f"진행중 아젠다 조회 실패: {str(e)}", operation="get_pending_agendas"
            ) from e

    def email_dashboard_query_get_overdue_agendas(self) -> List[AgendaStatusSummary]:
        """마감 지난 아젠다 목록"""
        try:
            current_time = datetime.now(timezone.utc)

            query = """
                SELECT c.agenda_no, c.panel_id, c.decision_status, c.deadline
                FROM email_agendas_chair c
                WHERE c.deadline < ? 
                  AND c.decision_status IN ('created', 'comment', 'consolidated')
                ORDER BY c.deadline ASC
            """

            rows = self.db.fetch_all(query, (current_time.isoformat(),))

            summaries = []
            for row in rows:
                response_count = self._email_dashboard_query_get_response_count(
                    row["agenda_no"]
                )
                response_rate = response_count / len(ORGANIZATIONS)

                deadline = datetime.fromisoformat(row["deadline"])
                days_until_deadline = (deadline - current_time).days

                summaries.append(
                    AgendaStatusSummary(
                        agenda_no=row["agenda_no"],
                        panel_id=row["panel_id"],
                        decision_status=row["decision_status"],
                        response_rate=response_rate,
                        days_until_deadline=days_until_deadline,
                        is_overdue=True,
                    )
                )

            return summaries

        except Exception as e:
            self.logger.error(f"마감 지난 아젠다 조회 실패: {str(e)}")
            raise DatabaseError(
                f"마감 지난 아젠다 조회 실패: {str(e)}", operation="get_overdue_agendas"
            ) from e

    def _email_dashboard_query_get_response_count(self, agenda_no: str) -> int:
        """아젠다의 응답 수 계산"""
        try:
            response_row = self.db.fetch_one(
                f"""
                SELECT {', '.join(ORGANIZATIONS)}
                FROM email_agenda_member_responses 
                WHERE agenda_no = ?
                """,
                (agenda_no,),
            )

            if not response_row:
                return 0

            count = 0
            for org in ORGANIZATIONS:
                if response_row[org] is not None and response_row[org].strip():
                    count += 1

            return count

        except Exception as e:
            self.logger.error(f"응답 수 계산 실패: {agenda_no}, error={str(e)}")
            return 0

    # =========================================================================
    # 대시보드 통계
    # =========================================================================

    def email_dashboard_query_get_dashboard_stats(
        self, date_range_days: int = 30
    ) -> DashboardStats:
        """대시보드 전체 통계"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=date_range_days)
            current_time = datetime.now(timezone.utc)
            today_start = current_time.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            today_end = today_start + timedelta(days=1)

            # 기본 통계
            total_agendas = self._email_dashboard_query_get_agenda_count(start_date)
            pending_agendas = self._email_dashboard_query_get_pending_count()
            completed_agendas = self._email_dashboard_query_get_completed_count(
                start_date
            )
            overdue_agendas = self._email_dashboard_query_get_overdue_count()
            today_deadline_agendas = (
                self._email_dashboard_query_get_today_deadline_count(
                    today_start, today_end
                )
            )

            # 전체 응답률
            overall_response_rate = (
                self._email_dashboard_query_calculate_overall_response_rate(start_date)
            )

            # 기관별 통계
            organization_stats = self._email_dashboard_query_get_organization_stats(
                start_date
            )

            # 미처리 이벤트 수 추가
            unprocessed_events_count = (
                self._email_dashboard_query_get_unprocessed_count()
            )

            return DashboardStats(
                total_agendas=total_agendas,
                pending_agendas=pending_agendas,
                completed_agendas=completed_agendas,
                overdue_agendas=overdue_agendas,
                today_deadline_agendas=today_deadline_agendas,
                overall_response_rate=overall_response_rate,
                organization_stats=organization_stats,
                unprocessed_events_count=unprocessed_events_count,
            )

        except Exception as e:
            self.logger.error(f"대시보드 통계 조회 실패: {str(e)}")
            raise DatabaseError(
                f"대시보드 통계 조회 실패: {str(e)}", operation="get_dashboard_stats"
            ) from e

    def _email_dashboard_query_get_agenda_count(self, start_date: datetime) -> int:
        """기간 내 총 아젠다 수"""
        result = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM email_agendas_chair WHERE send_time >= ?",
            (start_date.isoformat(),),
        )
        return result["count"] if result else 0

    def _email_dashboard_query_get_pending_count(self) -> int:
        """진행중인 아젠다 수"""
        result = self.db.fetch_one(
            """
            SELECT COUNT(*) as count 
            FROM email_agendas_chair 
            WHERE decision_status IN ('created', 'comment', 'consolidated')
            """
        )
        return result["count"] if result else 0

    def _email_dashboard_query_get_completed_count(self, start_date: datetime) -> int:
        """완료된 아젠다 수"""
        result = self.db.fetch_one(
            """
            SELECT COUNT(*) as count 
            FROM email_agendas_chair 
            WHERE decision_status = 'decision' AND send_time >= ?
            """,
            (start_date.isoformat(),),
        )
        return result["count"] if result else 0

    def _email_dashboard_query_get_overdue_count(self) -> int:
        """마감 지난 아젠다 수"""
        current_time = datetime.now(timezone.utc)
        result = self.db.fetch_one(
            """
            SELECT COUNT(*) as count 
            FROM email_agendas_chair 
            WHERE deadline < ? AND decision_status IN ('created', 'comment', 'consolidated')
            """,
            (current_time.isoformat(),),
        )
        return result["count"] if result else 0

    def _email_dashboard_query_get_today_deadline_count(
        self, today_start: datetime, today_end: datetime
    ) -> int:
        """오늘 마감 아젠다 수"""
        result = self.db.fetch_one(
            """
            SELECT COUNT(*) as count 
            FROM email_agendas_chair 
            WHERE deadline >= ? AND deadline < ?
            """,
            (today_start.isoformat(), today_end.isoformat()),
        )
        return result["count"] if result else 0

    def _email_dashboard_query_get_unprocessed_count(self) -> int:
        """미처리 이벤트 수"""
        result = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM email_events_unprocessed WHERE processed = 0"
        )
        return result["count"] if result else 0

    def _email_dashboard_query_calculate_overall_response_rate(
        self, start_date: datetime
    ) -> float:
        """전체 응답률 계산"""
        try:
            # 기간 내 아젠다 목록
            agendas = self.db.fetch_all(
                "SELECT agenda_no FROM email_agendas_chair WHERE send_time >= ?",
                (start_date.isoformat(),),
            )

            if not agendas:
                return 0.0

            total_possible_responses = len(agendas) * len(ORGANIZATIONS)
            total_actual_responses = 0

            for agenda in agendas:
                response_count = self._email_dashboard_query_get_response_count(
                    agenda["agenda_no"]
                )
                total_actual_responses += response_count

            return (
                total_actual_responses / total_possible_responses
                if total_possible_responses > 0
                else 0.0
            )

        except Exception as e:
            self.logger.error(f"전체 응답률 계산 실패: {str(e)}")
            return 0.0

    def _email_dashboard_query_get_organization_stats(
        self, start_date: datetime
    ) -> List[OrganizationStats]:
        """기관별 통계"""
        try:
            # 기간 내 아젠다 목록
            agendas = self.db.fetch_all(
                "SELECT agenda_no FROM email_agendas_chair WHERE send_time >= ?",
                (start_date.isoformat(),),
            )

            organization_stats = []

            for org in ORGANIZATIONS:
                total_agendas = len(agendas)
                responded_agendas = 0
                total_response_time = 0
                response_time_count = 0

                for agenda in agendas:
                    # 응답 여부 확인
                    content_row = self.db.fetch_one(
                        f"SELECT {org} FROM email_agenda_member_responses WHERE agenda_no = ?",
                        (agenda["agenda_no"],),
                    )

                    if (
                        content_row
                        and content_row[org] is not None
                        and content_row[org].strip()
                    ):
                        responded_agendas += 1

                        # 응답 시간 계산
                        time_row = self.db.fetch_one(
                            f"SELECT {org} FROM email_agenda_member_response_times WHERE agenda_no = ?",
                            (agenda["agenda_no"],),
                        )

                        agenda_row = self.db.fetch_one(
                            "SELECT send_time FROM email_agendas_chair WHERE agenda_no = ?",
                            (agenda["agenda_no"],),
                        )

                        if (
                            time_row
                            and time_row[org]
                            and agenda_row
                            and agenda_row["send_time"]
                        ):
                            response_time = datetime.fromisoformat(time_row[org])
                            send_time = datetime.fromisoformat(agenda_row["send_time"])

                            time_diff = response_time - send_time
                            hours = time_diff.total_seconds() / 3600

                            total_response_time += hours
                            response_time_count += 1

                response_rate = (
                    responded_agendas / total_agendas if total_agendas > 0 else 0.0
                )
                avg_response_time = (
                    total_response_time / response_time_count
                    if response_time_count > 0
                    else None
                )

                organization_stats.append(
                    OrganizationStats(
                        organization=org,
                        total_agendas=total_agendas,
                        responded_agendas=responded_agendas,
                        response_rate=response_rate,
                        avg_response_time_hours=avg_response_time,
                    )
                )

            return organization_stats

        except Exception as e:
            self.logger.error(f"기관별 통계 조회 실패: {str(e)}")
            return []

    # =========================================================================
    # 타임라인 및 상세 분석
    # =========================================================================

    def email_dashboard_query_get_agenda_timeline(
        self, agenda_no: str
    ) -> AgendaTimeline:
        """아젠다 타임라인 조회"""
        try:
            # 아젠다 기본 정보
            agenda = self.db.fetch_one(
                "SELECT send_time, deadline FROM email_agendas_chair WHERE agenda_no = ?",
                (agenda_no,),
            )

            if not agenda:
                raise DatabaseError(f"아젠다를 찾을 수 없음: {agenda_no}")

            events = []

            # 발송 이벤트
            send_time = datetime.fromisoformat(agenda["send_time"])
            events.append(
                TimelineEvent(
                    timestamp=send_time,
                    event_type="sent",
                    description=f"아젠다 {agenda_no} 발송",
                )
            )

            # 응답 이벤트들
            response_times = self.db.fetch_one(
                f"""
                SELECT {', '.join(ORGANIZATIONS)}
                FROM email_agenda_member_response_times 
                WHERE agenda_no = ?
                """,
                (agenda_no,),
            )

            if response_times:
                for org in ORGANIZATIONS:
                    if response_times[org]:
                        response_time = datetime.fromisoformat(response_times[org])
                        events.append(
                            TimelineEvent(
                                timestamp=response_time,
                                event_type="response_received",
                                organization=org,
                                description=f"{org} 응답 수신",
                            )
                        )

            # 마감일 이벤트
            if agenda["deadline"]:
                deadline = datetime.fromisoformat(agenda["deadline"])
                events.append(
                    TimelineEvent(
                        timestamp=deadline,
                        event_type="deadline",
                        description=f"아젠다 {agenda_no} 마감",
                    )
                )

            # 시간순 정렬
            events.sort(key=lambda x: x.timestamp)

            return AgendaTimeline(agenda_no=agenda_no, events=events)

        except Exception as e:
            self.logger.error(f"아젠다 타임라인 조회 실패: {agenda_no}, error={str(e)}")
            raise DatabaseError(
                f"아젠다 타임라인 조회 실패: {str(e)}", operation="get_agenda_timeline"
            ) from e

    # =========================================================================
    # 미처리 이벤트 조회 (신규)
    # =========================================================================

    def email_dashboard_query_get_unprocessed_events_summary(
        self, filter_params: Optional[UnprocessedEventFilter] = None
    ) -> UnprocessedEventSummary:
        """
        미처리 이벤트 요약 조회

        Args:
            filter_params: 필터 조건

        Returns:
            미처리 이벤트 요약
        """
        try:
            # 전체 미처리 수
            total_count = self.db.fetch_one(
                "SELECT COUNT(*) as count FROM email_events_unprocessed WHERE processed = 0"
            )["count"]

            # 사유별 통계
            by_reason = {}
            reason_rows = self.db.fetch_all(
                """
                SELECT unprocessed_reason, COUNT(*) as count 
                FROM email_events_unprocessed 
                WHERE processed = 0
                GROUP BY unprocessed_reason
                """
            )
            for row in reason_rows:
                by_reason[row["unprocessed_reason"]] = row["count"]

            # 기관별 통계
            by_organization = {}
            org_rows = self.db.fetch_all(
                """
                SELECT sender_organization, COUNT(*) as count 
                FROM email_events_unprocessed 
                WHERE processed = 0 AND sender_organization IS NOT NULL
                GROUP BY sender_organization
                ORDER BY count DESC
                """
            )
            for row in org_rows:
                by_organization[row["sender_organization"]] = row["count"]

            # 최근 이벤트 10개
            recent_query = """
                SELECT id, event_id, event_type, mail_id, sender_type, 
                       sender_organization, agenda_no, send_time, subject, 
                       summary, keywords, mail_type, decision_status, 
                       has_deadline, deadline, unprocessed_reason, 
                       raw_event_data, created_at, processed, processed_at
                FROM email_events_unprocessed
                WHERE processed = 0
                ORDER BY created_at DESC
                LIMIT 10
            """

            recent_rows = self.db.fetch_all(recent_query)
            recent_events = []

            for row in recent_rows:
                # 키워드 JSON 파싱
                import json

                keywords = []
                if row["keywords"]:
                    try:
                        keywords = json.loads(row["keywords"])
                    except json.JSONDecodeError:
                        keywords = []

                event = EmailEventUnprocessed(
                    id=row["id"],
                    event_id=row["event_id"],
                    event_type=row["event_type"],
                    mail_id=row["mail_id"],
                    sender_type=row["sender_type"],
                    sender_organization=row["sender_organization"],
                    agenda_no=row["agenda_no"],
                    send_time=(
                        datetime.fromisoformat(row["send_time"])
                        if row["send_time"]
                        else None
                    ),
                    subject=row["subject"],
                    summary=row["summary"],
                    keywords=keywords,
                    mail_type=row["mail_type"],
                    decision_status=row["decision_status"],
                    has_deadline=bool(row["has_deadline"]),
                    deadline=(
                        datetime.fromisoformat(row["deadline"])
                        if row["deadline"]
                        else None
                    ),
                    unprocessed_reason=row["unprocessed_reason"],
                    raw_event_data=row["raw_event_data"],
                    created_at=(
                        datetime.fromisoformat(row["created_at"])
                        if row["created_at"]
                        else None
                    ),
                    processed=bool(row["processed"]),
                    processed_at=(
                        datetime.fromisoformat(row["processed_at"])
                        if row["processed_at"]
                        else None
                    ),
                )
                recent_events.append(event)

            return UnprocessedEventSummary(
                total_count=total_count,
                by_reason=by_reason,
                by_organization=by_organization,
                recent_events=recent_events,
            )

        except Exception as e:
            self.logger.error(f"미처리 이벤트 요약 조회 실패: {str(e)}")
            return UnprocessedEventSummary(
                total_count=0, by_reason={}, by_organization={}, recent_events=[]
            )
