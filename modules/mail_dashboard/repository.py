"""
Email Dashboard Repository

데이터베이스 접근 및 CRUD 작업을 담당합니다.
미처리 이벤트 저장 기능 추가
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from infra.core import get_database_manager, get_logger
from infra.core.exceptions import DatabaseError, ValidationError

from .schema import (
    ORGANIZATIONS,
    EmailAgendaChair,
    EmailAgendaMemberResponse,
    EmailAgendaMemberResponseTime,
    EmailEventUnprocessed,
)


class EmailDashboardRepository:
    """Email Dashboard 데이터베이스 리포지토리"""

    def __init__(self):
        self.db = get_database_manager()
        self.logger = get_logger(__name__)

    # =========================================================================
    # 아젠다 관리 (email_agendas_chair)
    # =========================================================================

    def email_dashboard_create_or_update_agenda(
        self,
        panel_id: str,
        agenda_no: str,
        send_time: datetime,
        deadline: Optional[datetime],
        mail_type: str,
        decision_status: str = "created",
        summary: Optional[str] = None,
        round_no: Optional[str] = None,
        round_version: Optional[str] = None,
    ) -> bool:
        """
        아젠다 생성 또는 업데이트

        Args:
            panel_id: 패널 식별자
            agenda_no: 아젠다 번호
            send_time: 발송 시간
            deadline: 마감 시간
            mail_type: 메일 타입
            decision_status: 결정 상태
            summary: 요약 내용
            round_no: 회차 번호
            round_version: 회차 버전

        Returns:
            생성/업데이트 성공 여부
        """
        try:
            with self.db.transaction():
                # 기존 아젠다 확인
                existing = self.db.fetch_one(
                    "SELECT agenda_no FROM email_agendas_chair WHERE agenda_no = ?",
                    (agenda_no,),
                )

                current_time = datetime.now(timezone.utc)

                if existing:
                    # 기존 아젠다 업데이트
                    self.db.update(
                        table="email_agendas_chair",
                        data={
                            "panel_id": panel_id,
                            "send_time": send_time.isoformat(),
                            "deadline": deadline.isoformat() if deadline else None,
                            "mail_type": mail_type,
                            "decision_status": decision_status,
                            "summary": summary,
                            "round_no": round_no,
                            "round_version": round_version,
                            "updated_at": current_time.isoformat(),
                        },
                        where_clause="agenda_no = ?",
                        where_params=(agenda_no,),
                    )
                    self.logger.info(f"아젠다 업데이트 완료: {agenda_no}")
                else:
                    # 새 아젠다 생성
                    self.db.insert(
                        table="email_agendas_chair",
                        data={
                            "panel_id": panel_id,
                            "agenda_no": agenda_no,
                            "round_no": round_no,
                            "round_version": round_version,
                            "send_time": send_time.isoformat(),
                            "deadline": deadline.isoformat() if deadline else None,
                            "mail_type": mail_type,
                            "decision_status": decision_status,
                            "summary": summary,
                            "created_at": current_time.isoformat(),
                            "updated_at": current_time.isoformat(),
                        },
                    )

                    # 응답 테이블 초기화
                    self._email_dashboard_initialize_response_tables(agenda_no)
                    self.logger.info(f"새 아젠다 생성 완료: {agenda_no}")

                return True

        except Exception as e:
            self.logger.error(f"아젠다 생성/업데이트 실패: {agenda_no}, error={str(e)}")
            raise DatabaseError(
                f"아젠다 생성/업데이트 실패: {str(e)}",
                operation="create_or_update_agenda",
                table="email_agendas_chair",
            ) from e

    def _email_dashboard_initialize_response_tables(self, agenda_no: str) -> None:
        """응답 테이블 초기화"""
        current_time = datetime.now(timezone.utc).isoformat()

        # 응답 내용 테이블 초기화
        self.db.insert(
            table="email_agenda_member_responses",
            data={
                "agenda_no": agenda_no,
                "created_at": current_time,
                "updated_at": current_time,
            },
        )

        # 응답 시간 테이블 초기화
        self.db.insert(
            table="email_agenda_member_response_times",
            data={
                "agenda_no": agenda_no,
                "created_at": current_time,
                "updated_at": current_time,
            },
        )

    def email_dashboard_get_agenda(self, agenda_no: str) -> Optional[EmailAgendaChair]:
        """아젠다 조회"""
        try:
            row = self.db.fetch_one(
                """
                SELECT panel_id, agenda_no, round_no, round_version,
                       send_time, deadline, mail_type, decision_status, summary,
                       created_at, updated_at
                FROM email_agendas_chair 
                WHERE agenda_no = ?
                """,
                (agenda_no,),
            )

            if not row:
                return None

            return EmailAgendaChair(
                panel_id=row["panel_id"],
                agenda_no=row["agenda_no"],
                round_no=row["round_no"],
                round_version=row["round_version"],
                send_time=datetime.fromisoformat(row["send_time"]),
                deadline=(
                    datetime.fromisoformat(row["deadline"]) if row["deadline"] else None
                ),
                mail_type=row["mail_type"],
                decision_status=row["decision_status"],
                summary=row["summary"],
                created_at=(
                    datetime.fromisoformat(row["created_at"])
                    if row["created_at"]
                    else None
                ),
                updated_at=(
                    datetime.fromisoformat(row["updated_at"])
                    if row["updated_at"]
                    else None
                ),
            )

        except Exception as e:
            self.logger.error(f"아젠다 조회 실패: {agenda_no}, error={str(e)}")
            raise DatabaseError(
                f"아젠다 조회 실패: {str(e)}",
                operation="get_agenda",
                table="email_agendas_chair",
            ) from e

    # =========================================================================
    # 멤버 응답 관리
    # =========================================================================

    def email_dashboard_update_member_response(
        self,
        agenda_no: str,
        organization: str,
        response_content: str,
        response_time: datetime,
    ) -> bool:
        """
        멤버 기관 응답 업데이트

        Args:
            agenda_no: 아젠다 번호
            organization: 기관 코드 (ABS, BV, CCS 등)
            response_content: 응답 내용
            response_time: 응답 시간

        Returns:
            업데이트 성공 여부
        """
        try:
            # 기관 코드 유효성 검사
            if organization not in ORGANIZATIONS:
                raise ValidationError(
                    f"유효하지 않은 기관 코드: {organization}",
                    field="organization",
                    value=organization,
                )

            # 아젠다 존재 확인
            if not self.email_dashboard_get_agenda(agenda_no):
                self.logger.warning(f"아젠다가 존재하지 않음: {agenda_no}")
                return False

            current_time = datetime.now(timezone.utc).isoformat()

            with self.db.transaction():
                # 응답 내용 업데이트
                self.db.update(
                    table="email_agenda_member_responses",
                    data={organization: response_content, "updated_at": current_time},
                    where_clause="agenda_no = ?",
                    where_params=(agenda_no,),
                )

                # 응답 시간 업데이트
                self.db.update(
                    table="email_agenda_member_response_times",
                    data={
                        organization: response_time.isoformat(),
                        "updated_at": current_time,
                    },
                    where_clause="agenda_no = ?",
                    where_params=(agenda_no,),
                )

                # 아젠다 상태 업데이트 (필요시)
                self._email_dashboard_update_agenda_status(agenda_no)

            self.logger.info(
                f"멤버 응답 업데이트 완료: {agenda_no}, org={organization}"
            )
            return True

        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(
                f"멤버 응답 업데이트 실패: {agenda_no}, org={organization}, error={str(e)}"
            )
            raise DatabaseError(
                f"멤버 응답 업데이트 실패: {str(e)}",
                operation="update_member_response",
                table="email_agenda_member_responses",
            ) from e

    def _email_dashboard_update_agenda_status(self, agenda_no: str) -> None:
        """아젠다 상태 자동 업데이트"""
        try:
            # 응답 수 계산
            response_count = self.email_dashboard_get_response_count(agenda_no)
            total_organizations = len(ORGANIZATIONS)

            # 상태 결정 로직
            if response_count == 0:
                new_status = "created"
            elif response_count < total_organizations:
                new_status = "comment"
            else:
                new_status = "consolidated"

            # 상태 업데이트
            self.db.update(
                table="email_agendas_chair",
                data={
                    "decision_status": new_status,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                where_clause="agenda_no = ?",
                where_params=(agenda_no,),
            )

        except Exception as e:
            self.logger.warning(
                f"아젠다 상태 자동 업데이트 실패: {agenda_no}, error={str(e)}"
            )

    def email_dashboard_get_response_count(self, agenda_no: str) -> int:
        """아젠다의 응답 수 계산"""
        try:
            # 각 기관별 응답 여부 확인
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

            # NULL이 아닌 응답 수 계산
            count = 0
            for org in ORGANIZATIONS:
                if response_row[org] is not None and response_row[org].strip():
                    count += 1

            return count

        except Exception as e:
            self.logger.error(f"응답 수 계산 실패: {agenda_no}, error={str(e)}")
            return 0

    def email_dashboard_get_member_responses(
        self, agenda_no: str
    ) -> Tuple[EmailAgendaMemberResponse, EmailAgendaMemberResponseTime]:
        """멤버 응답 정보 조회"""
        try:
            # 응답 내용 조회
            content_row = self.db.fetch_one(
                f"""
                SELECT agenda_no, {', '.join(ORGANIZATIONS)}, created_at, updated_at
                FROM email_agenda_member_responses 
                WHERE agenda_no = ?
                """,
                (agenda_no,),
            )

            # 응답 시간 조회
            time_row = self.db.fetch_one(
                f"""
                SELECT agenda_no, {', '.join(ORGANIZATIONS)}, created_at, updated_at
                FROM email_agenda_member_response_times 
                WHERE agenda_no = ?
                """,
                (agenda_no,),
            )

            if not content_row or not time_row:
                raise ValidationError(f"응답 정보를 찾을 수 없음: {agenda_no}")

            # 응답 내용 객체 생성
            content_data = {"agenda_no": agenda_no}
            for org in ORGANIZATIONS:
                content_data[org] = content_row[org]
            content_data["created_at"] = (
                datetime.fromisoformat(content_row["created_at"])
                if content_row["created_at"]
                else None
            )
            content_data["updated_at"] = (
                datetime.fromisoformat(content_row["updated_at"])
                if content_row["updated_at"]
                else None
            )

            # 응답 시간 객체 생성
            time_data = {"agenda_no": agenda_no}
            for org in ORGANIZATIONS:
                time_data[org] = (
                    datetime.fromisoformat(time_row[org]) if time_row[org] else None
                )
            time_data["created_at"] = (
                datetime.fromisoformat(time_row["created_at"])
                if time_row["created_at"]
                else None
            )
            time_data["updated_at"] = (
                datetime.fromisoformat(time_row["updated_at"])
                if time_row["updated_at"]
                else None
            )

            return (
                EmailAgendaMemberResponse(**content_data),
                EmailAgendaMemberResponseTime(**time_data),
            )

        except Exception as e:
            self.logger.error(f"멤버 응답 조회 실패: {agenda_no}, error={str(e)}")
            raise DatabaseError(
                f"멤버 응답 조회 실패: {str(e)}",
                operation="get_member_responses",
                table="email_agenda_member_responses",
            ) from e

    # =========================================================================
    # 미처리 이벤트 관리 (신규)
    # =========================================================================

    def email_dashboard_save_unprocessed_event(
        self,
        event_id: str,
        event_type: str,
        mail_id: Optional[str],
        sender_type: Optional[str],
        sender_organization: Optional[str],
        agenda_no: Optional[str],
        send_time: Optional[datetime],
        subject: Optional[str],
        summary: Optional[str],
        keywords: List[str],
        mail_type: Optional[str],
        decision_status: Optional[str],
        has_deadline: bool,
        deadline: Optional[datetime],
        unprocessed_reason: str,
        raw_event_data: str,
    ) -> bool:
        """
        미처리 이벤트 저장

        Args:
            event_id: 이벤트 ID
            event_type: 이벤트 타입
            mail_id: 메일 ID
            sender_type: 발신자 타입
            sender_organization: 발신 기관
            agenda_no: 아젠다 번호
            send_time: 발송 시간
            subject: 제목
            summary: 요약
            keywords: 키워드 목록
            mail_type: 메일 타입
            decision_status: 결정 상태
            has_deadline: 마감일 여부
            deadline: 마감일
            unprocessed_reason: 미처리 사유
            raw_event_data: 원본 이벤트 데이터 (JSON)

        Returns:
            저장 성공 여부
        """
        try:
            current_time = datetime.now(timezone.utc)

            # 키워드를 JSON 문자열로 변환
            keywords_json = (
                json.dumps(keywords, ensure_ascii=False) if keywords else "[]"
            )

            self.db.insert(
                table="email_events_unprocessed",
                data={
                    "event_id": event_id,
                    "event_type": event_type,
                    "mail_id": mail_id,
                    "sender_type": sender_type,
                    "sender_organization": sender_organization,
                    "agenda_no": agenda_no,
                    "send_time": send_time.isoformat() if send_time else None,
                    "subject": subject,
                    "summary": summary,
                    "keywords": keywords_json,
                    "mail_type": mail_type,
                    "decision_status": decision_status,
                    "has_deadline": has_deadline,
                    "deadline": deadline.isoformat() if deadline else None,
                    "unprocessed_reason": unprocessed_reason,
                    "raw_event_data": raw_event_data,
                    "created_at": current_time.isoformat(),
                    "processed": False,
                    "processed_at": None,
                },
            )

            self.logger.info(
                f"미처리 이벤트 저장 완료: event_id={event_id}, "
                f"reason={unprocessed_reason}, org={sender_organization}"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"미처리 이벤트 저장 실패: event_id={event_id}, error={str(e)}"
            )
            return False

    def email_dashboard_get_unprocessed_events(
        self, filter_params: Optional[Dict[str, Any]] = None
    ) -> List[EmailEventUnprocessed]:
        """
        미처리 이벤트 조회

        Args:
            filter_params: 필터 조건

        Returns:
            미처리 이벤트 목록
        """
        try:
            # WHERE 조건 구성
            where_conditions = ["1=1"]  # 항상 참인 조건으로 시작
            params = []

            if filter_params:
                if filter_params.get("unprocessed_reason"):
                    where_conditions.append("unprocessed_reason = ?")
                    params.append(filter_params["unprocessed_reason"])

                if filter_params.get("sender_organization"):
                    where_conditions.append("sender_organization = ?")
                    params.append(filter_params["sender_organization"])

                if filter_params.get("start_date"):
                    where_conditions.append("created_at >= ?")
                    params.append(filter_params["start_date"].isoformat())

                if filter_params.get("end_date"):
                    where_conditions.append("created_at <= ?")
                    params.append(filter_params["end_date"].isoformat())

                if filter_params.get("processed") is not None:
                    where_conditions.append("processed = ?")
                    params.append(1 if filter_params["processed"] else 0)

            where_clause = " AND ".join(where_conditions)

            # 쿼리 실행
            query = f"""
                SELECT id, event_id, event_type, mail_id, sender_type, 
                       sender_organization, agenda_no, send_time, subject, 
                       summary, keywords, mail_type, decision_status, 
                       has_deadline, deadline, unprocessed_reason, 
                       raw_event_data, created_at, processed, processed_at
                FROM email_events_unprocessed
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """

            limit = filter_params.get("limit", 100) if filter_params else 100
            offset = filter_params.get("offset", 0) if filter_params else 0
            params.extend([limit, offset])

            rows = self.db.fetch_all(query, params)

            events = []
            for row in rows:
                # 키워드 JSON 파싱
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
                events.append(event)

            return events

        except Exception as e:
            self.logger.error(f"미처리 이벤트 조회 실패: {str(e)}")
            return []

    def email_dashboard_mark_event_processed(self, event_id: str) -> bool:
        """
        미처리 이벤트를 처리됨으로 표시

        Args:
            event_id: 이벤트 ID

        Returns:
            업데이트 성공 여부
        """
        try:
            current_time = datetime.now(timezone.utc)

            self.db.update(
                table="email_events_unprocessed",
                data={"processed": True, "processed_at": current_time.isoformat()},
                where_clause="event_id = ?",
                where_params=(event_id,),
            )

            self.logger.info(f"미처리 이벤트 처리 완료 표시: event_id={event_id}")
            return True

        except Exception as e:
            self.logger.error(
                f"미처리 이벤트 업데이트 실패: event_id={event_id}, error={str(e)}"
            )
            return False

    def email_dashboard_get_unprocessed_stats(self) -> Dict[str, Any]:
        """
        미처리 이벤트 통계 조회

        Returns:
            통계 정보
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

            return {
                "total_count": total_count,
                "by_reason": by_reason,
                "by_organization": by_organization,
            }

        except Exception as e:
            self.logger.error(f"미처리 이벤트 통계 조회 실패: {str(e)}")
            return {"total_count": 0, "by_reason": {}, "by_organization": {}}

    # =========================================================================
    # 유틸리티 메서드
    # =========================================================================

    def email_dashboard_agenda_exists(self, agenda_no: str) -> bool:
        """아젠다 존재 여부 확인"""
        try:
            result = self.db.fetch_one(
                "SELECT 1 FROM email_agendas_chair WHERE agenda_no = ?", (agenda_no,)
            )
            return result is not None
        except Exception as e:
            self.logger.error(f"아젠다 존재 확인 실패: {agenda_no}, error={str(e)}")
            return False

    def email_dashboard_clear_all_data(self) -> Dict[str, Any]:
        """모든 Email Dashboard 데이터 삭제 (개발/테스트용)"""
        try:
            tables = [
                "email_events_unprocessed",  # 추가
                "email_agenda_member_response_times",
                "email_agenda_member_responses",
                "email_agendas_chair",
            ]

            results = []
            for table in tables:
                result = self.db.clear_table_data(table)
                results.append({"table": table, **result})

            total_deleted = sum(r["deleted_count"] for r in results if r.get("success"))

            self.logger.info(
                f"Email Dashboard 데이터 정리 완료: 총 {total_deleted}개 레코드 삭제"
            )

            return {
                "success": True,
                "total_deleted": total_deleted,
                "table_results": results,
                "message": f"Email Dashboard 데이터 정리 완료: {total_deleted}개 레코드 삭제",
            }

        except Exception as e:
            self.logger.error(f"Email Dashboard 데이터 정리 실패: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Email Dashboard 데이터 정리 중 오류 발생",
            }
