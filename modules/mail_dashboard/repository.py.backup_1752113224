# modules/mail_dashboard/repository.py
"""
Email Dashboard Repository - 새로운 테이블 구조
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from infra.core import get_database_manager, get_logger
from infra.core.exceptions import DatabaseError

from .schema import (
    AgendaAll,
    AgendaChair,
    AgendaResponsesContent,
    AgendaResponsesReceivedTime,
    AgendaPending,
    ORGANIZATIONS,
)


class EmailDashboardRepository:
    """Email Dashboard 데이터베이스 리포지토리"""

    def __init__(self):
        self.db = get_database_manager()
        self.logger = get_logger(__name__)

    # =========================================================================
    # agenda_all 관리
    # =========================================================================

    def save_agenda_all(self, agenda: AgendaAll) -> bool:
        """agenda_all 테이블에 저장"""
        try:
            data = {
                "event_id": agenda.event_id,
                "agenda_code": agenda.agenda_code,
                "sender_type": agenda.sender_type,
                "sender_organization": agenda.sender_organization,
                "sent_time": agenda.sent_time,
                "mail_type": agenda.mail_type,
                "decision_status": agenda.decision_status,
                "subject": agenda.subject,
                "body": agenda.body,
                "keywords": json.dumps(agenda.keywords or [], ensure_ascii=False),
                "response_org": agenda.response_org,
                "response_version": agenda.response_version,
                "deadline": agenda.deadline,
                "has_deadline": agenda.has_deadline,
                "sender": agenda.sender,
                "sender_address": agenda.sender_address,
                "agenda_panel": agenda.agenda_panel,
                "agenda_year": agenda.agenda_year,
                "agenda_number": agenda.agenda_number,
                "agenda_base": agenda.agenda_base,
                "agenda_version": agenda.agenda_version,
                "agenda_base_version": agenda.agenda_base_version,
                "parsing_method": agenda.parsing_method,
                "hasAttachments": agenda.hasAttachments,
                "sentDateTime": agenda.sentDateTime,
                "webLink": agenda.webLink,
                "created_at": datetime.now(timezone.utc),
            }

            self.db.insert("agenda_all", data)
            return True

        except Exception as e:
            self.logger.error(f"agenda_all 저장 실패: {str(e)}")
            return False

    # =========================================================================
    # agenda_chair 관리
    # =========================================================================

    def save_or_update_agenda_chair(self, agenda: AgendaChair) -> bool:
        """agenda_chair 저장 또는 업데이트"""
        try:
            with self.db.transaction():
                # 기존 레코드 확인
                existing = self.db.fetch_one(
                    "SELECT agenda_base_version FROM agenda_chair WHERE agenda_base_version = ?",
                    (agenda.agenda_base_version,),
                )

                current_time = datetime.now(timezone.utc)

                if existing:
                    # 업데이트
                    update_data = {
                        "agenda_code": agenda.agenda_code,
                        "sender_organization": agenda.sender_organization,
                        "sent_time": agenda.sent_time,
                        "mail_type": agenda.mail_type,
                        "decision_status": agenda.decision_status,
                        "subject": agenda.subject,
                        "body": agenda.body,
                        "keywords": json.dumps(
                            agenda.keywords or [], ensure_ascii=False
                        ),
                        "deadline": agenda.deadline,
                        "has_deadline": agenda.has_deadline,
                        "sender": agenda.sender,
                        "sender_address": agenda.sender_address,
                        "agenda_panel": agenda.agenda_panel,
                        "agenda_year": agenda.agenda_year,
                        "agenda_number": agenda.agenda_number,
                        "agenda_version": agenda.agenda_version,
                        "parsing_method": agenda.parsing_method,
                        "hasAttachments": agenda.hasAttachments,
                        "updated_at": current_time,
                    }

                    self.db.update(
                        table="agenda_chair",
                        data=update_data,
                        where_clause="agenda_base_version = ?",
                        where_params=(agenda.agenda_base_version,),
                    )
                    self.logger.info(
                        f"agenda_chair 업데이트: {agenda.agenda_base_version}"
                    )

                else:
                    # 신규 저장
                    insert_data = agenda.model_dump(
                        exclude={"created_at", "updated_at"}
                    )
                    insert_data["keywords"] = json.dumps(
                        agenda.keywords or [], ensure_ascii=False
                    )
                    insert_data["created_at"] = current_time
                    insert_data["updated_at"] = current_time

                    self.db.insert("agenda_chair", insert_data)
                    self.logger.info(f"agenda_chair 생성: {agenda.agenda_base_version}")

                    # 응답 테이블 초기화 (트리거가 처리하지만 명시적으로도 실행)
                    self._initialize_response_tables(agenda.agenda_base_version)

                return True

        except Exception as e:
            self.logger.error(f"agenda_chair 저장/업데이트 실패: {str(e)}")
            return False

    def _initialize_response_tables(self, agenda_base_version: str) -> None:
        """응답 테이블 초기화"""
        try:
            current_time = datetime.now(timezone.utc)

            # 응답 내용 테이블 초기화
            self.db.insert(
                "agenda_responses_content",
                {
                    "agenda_base_version": agenda_base_version,
                    "created_at": current_time,
                    "updated_at": current_time,
                },
            )

            # 응답 시간 테이블 초기화
            self.db.insert(
                "agenda_responses_receivedtime",
                {
                    "agenda_base_version": agenda_base_version,
                    "created_at": current_time,
                    "updated_at": current_time,
                },
            )

        except Exception as e:
            # 이미 존재하는 경우 무시
            if "UNIQUE constraint failed" not in str(e):
                self.logger.error(f"응답 테이블 초기화 실패: {str(e)}")

    # =========================================================================
    # 멤버 응답 관리
    # =========================================================================

    def update_member_response(
        self,
        agenda_base_version: str,
        organization: str,
        response_content: str,
        response_time: datetime,
    ) -> bool:
        """멤버 응답 업데이트"""
        try:
            # 조직 코드 검증
            if organization not in ORGANIZATIONS:
                self.logger.error(f"유효하지 않은 조직 코드: {organization}")
                return False

            # agenda_chair 존재 확인
            chair = self.db.fetch_one(
                "SELECT agenda_base_version FROM agenda_chair WHERE agenda_base_version = ?",
                (agenda_base_version,),
            )

            if not chair:
                self.logger.warning(
                    f"해당 아젠다가 존재하지 않음: {agenda_base_version}"
                )
                return False

            current_time = datetime.now(timezone.utc)

            with self.db.transaction():
                # 응답 내용 업데이트
                self.db.update(
                    table="agenda_responses_content",
                    data={organization: response_content, "updated_at": current_time},
                    where_clause="agenda_base_version = ?",
                    where_params=(agenda_base_version,),
                )

                # 응답 시간 업데이트
                self.db.update(
                    table="agenda_responses_receivedtime",
                    data={organization: response_time, "updated_at": current_time},
                    where_clause="agenda_base_version = ?",
                    where_params=(agenda_base_version,),
                )

                # chair 테이블의 decision_status 업데이트
                self._update_chair_decision_status(agenda_base_version)

            self.logger.info(
                f"멤버 응답 업데이트: {agenda_base_version} - {organization}"
            )
            return True

        except Exception as e:
            self.logger.error(f"멤버 응답 업데이트 실패: {str(e)}")
            return False

    def _update_chair_decision_status(self, agenda_base_version: str) -> None:
        """응답 상태에 따른 decision_status 업데이트"""
        try:
            # 응답 수 계산
            response_count = self._get_response_count(agenda_base_version)
            total_orgs = len(ORGANIZATIONS)

            # 상태 결정
            if response_count == 0:
                new_status = "created"
            elif response_count < total_orgs:
                new_status = "comment"
            else:
                new_status = "consolidated"

            # 업데이트
            self.db.update(
                table="agenda_chair",
                data={
                    "decision_status": new_status,
                    "updated_at": datetime.now(timezone.utc),
                },
                where_clause="agenda_base_version = ?",
                where_params=(agenda_base_version,),
            )

        except Exception as e:
            self.logger.warning(f"decision_status 업데이트 실패: {str(e)}")

    def _get_response_count(self, agenda_base_version: str) -> int:
        """응답 수 계산"""
        try:
            # 각 조직의 응답 확인
            org_columns = ", ".join(ORGANIZATIONS)
            query = f"SELECT {org_columns} FROM agenda_responses_content WHERE agenda_base_version = ?"

            row = self.db.fetch_one(query, (agenda_base_version,))
            if not row:
                return 0

            count = 0
            for org in ORGANIZATIONS:
                if row.get(org) is not None and row[org].strip():
                    count += 1

            return count

        except Exception as e:
            self.logger.error(f"응답 수 계산 실패: {str(e)}")
            return 0

    # =========================================================================
    # agenda_pending 관리
    # =========================================================================

    def save_agenda_pending(self, pending: AgendaPending) -> bool:
        """agenda_pending 저장"""
        try:
            data = {
                "event_id": pending.event_id,
                "raw_event_data": pending.raw_event_data,
                "error_reason": pending.error_reason,
                "sender_type": pending.sender_type,
                "sender_organization": pending.sender_organization,
                "sent_time": pending.sent_time,
                "subject": pending.subject,
                "received_at": datetime.now(timezone.utc),
                "processed": pending.processed,
                "processed_at": pending.processed_at,
                "retry_count": pending.retry_count,
            }

            self.db.insert("agenda_pending", data)
            return True

        except Exception as e:
            self.logger.error(f"agenda_pending 저장 실패: {str(e)}")
            return False

    def get_pending_events(self, limit: int = 100) -> List[AgendaPending]:
        """미처리 이벤트 조회"""
        try:
            query = """
                SELECT * FROM agenda_pending 
                WHERE processed = 0 
                ORDER BY received_at ASC 
                LIMIT ?
            """

            rows = self.db.fetch_all(query, (limit,))

            events = []
            for row in rows:
                event = AgendaPending(**dict(row))
                events.append(event)

            return events

        except Exception as e:
            self.logger.error(f"미처리 이벤트 조회 실패: {str(e)}")
            return []

    def mark_pending_processed(self, event_id: str) -> bool:
        """미처리 이벤트를 처리됨으로 표시"""
        try:
            self.db.update(
                table="agenda_pending",
                data={"processed": True, "processed_at": datetime.now(timezone.utc)},
                where_clause="event_id = ?",
                where_params=(event_id,),
            )
            return True

        except Exception as e:
            self.logger.error(f"pending 처리 표시 실패: {str(e)}")
            return False

    # =========================================================================
    # 통계 및 조회
    # =========================================================================

    def get_dashboard_stats(self, days: int = 30) -> Dict[str, Any]:
        """대시보드 통계"""
        try:
            stats = {
                "total_agendas": self._get_total_agendas(days),
                "pending_agendas": self._get_pending_agendas(),
                "completed_agendas": self._get_completed_agendas(days),
                "total_responses": self._get_total_responses(days),
                "pending_events": self._get_pending_events_count(),
                "organization_stats": self._get_organization_stats(days),
            }

            return stats

        except Exception as e:
            self.logger.error(f"통계 조회 실패: {str(e)}")
            return {}

    def _get_total_agendas(self, days: int) -> int:
        """총 아젠다 수"""
        query = """
            SELECT COUNT(*) as count FROM agenda_chair 
            WHERE sent_time >= datetime('now', ? || ' days')
        """
        result = self.db.fetch_one(query, (f"-{days}",))
        return result["count"] if result else 0

    def _get_pending_agendas(self) -> int:
        """진행중인 아젠다 수"""
        query = """
            SELECT COUNT(*) as count FROM agenda_chair 
            WHERE decision_status IN ('created', 'comment')
        """
        result = self.db.fetch_one(query)
        return result["count"] if result else 0

    def _get_completed_agendas(self, days: int) -> int:
        """완료된 아젠다 수"""
        query = """
            SELECT COUNT(*) as count FROM agenda_chair 
            WHERE decision_status = 'consolidated' 
            AND sent_time >= datetime('now', ? || ' days')
        """
        result = self.db.fetch_one(query, (f"-{days}",))
        return result["count"] if result else 0

    def _get_total_responses(self, days: int) -> int:
        """총 응답 수"""
        query = """
            SELECT COUNT(*) as count FROM agenda_all 
            WHERE sender_type = 'MEMBER' 
            AND sent_time >= datetime('now', ? || ' days')
        """
        result = self.db.fetch_one(query, (f"-{days}",))
        return result["count"] if result else 0

    def _get_pending_events_count(self) -> int:
        """미처리 이벤트 수"""
        query = "SELECT COUNT(*) as count FROM agenda_pending WHERE processed = 0"
        result = self.db.fetch_one(query)
        return result["count"] if result else 0

    def _get_organization_stats(self, days: int) -> Dict[str, Dict[str, int]]:
        """조직별 통계"""
        stats = {}

        for org in ORGANIZATIONS:
            # 발송한 아젠다 수 (Chair로 활동)
            chair_query = """
                SELECT COUNT(*) as count FROM agenda_chair 
                WHERE sender_organization = ? 
                AND sent_time >= datetime('now', ? || ' days')
            """
            chair_result = self.db.fetch_one(chair_query, (org, f"-{days}"))

            # 응답한 수
            response_query = f"""
                SELECT COUNT(*) as count FROM agenda_responses_content 
                WHERE {org} IS NOT NULL AND {org} != ''
                AND updated_at >= datetime('now', ? || ' days')
            """
            response_result = self.db.fetch_one(response_query, (f"-{days}",))

            stats[org] = {
                "as_chair": chair_result["count"] if chair_result else 0,
                "responses": response_result["count"] if response_result else 0,
            }

        return stats

    # =========================================================================
    # 유틸리티
    # =========================================================================

    def clear_all_data(self) -> Dict[str, Any]:
        """모든 데이터 삭제 (개발/테스트용)"""
        try:
            tables = [
                "agenda_pending",
                "agenda_responses_receivedtime",
                "agenda_responses_content",
                "agenda_chair",
                "agenda_all",
            ]

            results = []
            for table in tables:
                result = self.db.clear_table_data(table)
                results.append({"table": table, **result})

            total_deleted = sum(r["deleted_count"] for r in results if r.get("success"))

            return {
                "success": True,
                "total_deleted": total_deleted,
                "table_results": results,
            }

        except Exception as e:
            self.logger.error(f"데이터 삭제 실패: {str(e)}")
            return {"success": False, "error": str(e)}
