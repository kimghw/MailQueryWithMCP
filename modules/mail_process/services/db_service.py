# modules/mail_process/services/db_service.py
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import hashlib

from infra.core.database import get_database_manager
from infra.core.logger import get_logger
from infra.core.config import get_config
from modules.mail_process.mail_processor_schema import (
    ProcessedMailData,
    MailHistoryData,
)


class MailDatabaseService:
    """메일 데이터베이스 서비스"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.db_manager = get_database_manager()
        self.config = get_config()

    def check_duplicate_by_id(self, message_id: str) -> bool:
        """
        메시지 ID로 중복 확인

        Args:
            message_id: 메일의 고유 ID

        Returns:
            True if duplicate exists, False otherwise
        """
        query = "SELECT id FROM mail_history WHERE message_id = ? LIMIT 1"

        try:
            result = self.db_manager.fetch_one(query, (message_id,))

            if result:
                self.logger.debug(f"중복 메일 발견 - message_id: {message_id}")
                return True
            return False

        except Exception as e:
            self.logger.error(
                f"중복 확인 실패 - message_id: {message_id}, error: {str(e)}"
            )
            # 에러 발생 시 안전하게 중복으로 처리
            return True

    def check_duplicate_by_content_hash(
        self, mail_id: str, content: str
    ) -> Tuple[bool, List[str]]:
        """
        내용 해시 기반 중복 확인

        Args:
            mail_id: 메일 ID
            content: 정제된 메일 내용

        Returns:
            (중복 여부, 기존 키워드 리스트)
        """
        # 내용 해시 생성
        content_hash = self._generate_content_hash(content)

        # 해시 또는 메일 ID로 중복 검사
        query = """
            SELECT keywords 
            FROM mail_history 
            WHERE content_hash = ? OR message_id = ?
            LIMIT 1
        """

        result = self.db_manager.fetch_one(query, (content_hash, mail_id))

        if result:
            # 기존 키워드 파싱
            try:
                existing_keywords = (
                    json.loads(result["keywords"]) if result["keywords"] else []
                )
            except (json.JSONDecodeError, TypeError):
                existing_keywords = []

            self.logger.debug(
                f"중복 메일 발견 - ID: {mail_id}, 해시: {content_hash[:8]}..."
            )
            return True, existing_keywords

        return False, []

    def save_mail_history(self, processed_mail: ProcessedMailData) -> bool:
        """
        메일 히스토리 저장 (infra.database 활용)

        Args:
            processed_mail: 처리된 메일 데이터

        Returns:
            저장 성공 여부
        """
        # 실제 account_id 조회
        actual_account_id = self._get_actual_account_id(processed_mail.account_id)

        # content_hash 컬럼 확인 및 추가
        self._ensure_content_hash_column()

        # 메일 히스토리 저장 데이터 준비
        mail_data = {
            "account_id": actual_account_id,
            "message_id": processed_mail.mail_id,
            "received_time": processed_mail.sent_time,
            "subject": processed_mail.subject,
            "sender": processed_mail.sender_address,
            "keywords": json.dumps(processed_mail.keywords, ensure_ascii=False),
            "processed_at": processed_mail.processed_at,
            "content_hash": self._generate_content_hash(
                processed_mail.clean_content or ""
            ),
        }

        try:
            # infra.database의 insert 메서드 사용
            inserted_id = self.db_manager.insert("mail_history", mail_data)

            self.logger.info(
                f"메일 저장 완료 - ID: {inserted_id}, "
                f"mail_id: {processed_mail.mail_id}, "
                f"account_id: {actual_account_id}"
            )
            return True

        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                self.logger.warning(
                    f"메일 저장 실패 (중복) - mail_id: {processed_mail.mail_id}"
                )
            else:
                self.logger.error(
                    f"메일 저장 실패 - mail_id: {processed_mail.mail_id}, error: {str(e)}"
                )
            return False

    async def save_processed_mail(self, processed_mail: ProcessedMailData) -> bool:
        """
        처리된 메일을 DB에 저장 (비동기 래퍼)

        Args:
            processed_mail: 처리된 메일 데이터

        Returns:
            저장 성공 여부
        """
        return self.save_mail_history(processed_mail)

    def get_active_accounts(self) -> List[dict]:
        """
        활성 계정 목록 조회

        Returns:
            활성 계정 리스트
        """
        query = """
            SELECT id, user_id, user_name, last_sync_time, access_token, refresh_token
            FROM accounts 
            WHERE is_active = 1 
            ORDER BY last_sync_time ASC NULLS FIRST
        """

        rows = self.db_manager.fetch_all(query)
        accounts = []

        for row in rows:
            account = dict(row)
            # datetime 변환
            if account["last_sync_time"]:
                account["last_sync_time"] = datetime.fromisoformat(
                    account["last_sync_time"]
                )
            accounts.append(account)

        self.logger.info(f"활성 계정 {len(accounts)}개 조회됨")
        return accounts

    def update_account_sync_time(self, account_id: str, sync_time: datetime) -> None:
        """
        계정 동기화 시간 업데이트

        Args:
            account_id: 계정 ID (user_id)
            sync_time: 동기화 시간
        """
        update_data = {"last_sync_time": sync_time, "updated_at": datetime.now()}

        rows_affected = self.db_manager.update(
            table="accounts",
            data=update_data,
            where_clause="user_id = ?",
            where_params=(account_id,),
        )

        if rows_affected > 0:
            self.logger.debug(f"계정 {account_id} 동기화 시간 업데이트: {sync_time}")
        else:
            self.logger.warning(
                f"계정 {account_id} 동기화 시간 업데이트 실패 - 계정을 찾을 수 없음"
            )

    def record_account_error(self, account_id: str, error_message: str) -> None:
        """
        계정 에러 기록

        Args:
            account_id: 계정 ID (user_id)
            error_message: 에러 메시지
        """
        import uuid

        # 실제 account_id 조회
        actual_account_id = self._get_actual_account_id(account_id)

        log_data = {
            "run_id": str(uuid.uuid4()),
            "account_id": actual_account_id,
            "log_level": "ERROR",
            "message": error_message,
            "timestamp": datetime.now(),
        }

        try:
            self.db_manager.insert("processing_logs", log_data)
            self.logger.error(f"계정 {account_id} 에러 기록: {error_message}")
        except Exception as e:
            self.logger.error(f"에러 로그 기록 실패: {str(e)}")

    def get_mail_statistics(self, account_id: str, days: int = 30) -> Dict[str, Any]:
        """
        계정의 메일 처리 통계 조회

        Args:
            account_id: 계정 ID (user_id)
            days: 조회할 과거 일수

        Returns:
            통계 정보
        """
        query = """
            SELECT 
                COUNT(*) as total_mails,
                COUNT(DISTINCT sender) as unique_senders,
                COUNT(DISTINCT content_hash) as unique_contents,
                MIN(received_time) as oldest_mail,
                MAX(received_time) as newest_mail,
                AVG(json_array_length(keywords)) as avg_keywords_per_mail
            FROM mail_history mh
            JOIN accounts a ON mh.account_id = a.id
            WHERE a.user_id = ? 
            AND mh.processed_at >= datetime('now', ? || ' days')
        """

        result = self.db_manager.fetch_one(query, (account_id, f"-{days}"))

        if result:
            return {
                "total_mails": result["total_mails"] or 0,
                "unique_senders": result["unique_senders"] or 0,
                "unique_contents": result["unique_contents"] or 0,
                "oldest_mail": result["oldest_mail"],
                "newest_mail": result["newest_mail"],
                "avg_keywords": round(result["avg_keywords_per_mail"] or 0, 2),
                "days_analyzed": days,
            }

        return {
            "total_mails": 0,
            "unique_senders": 0,
            "unique_contents": 0,
            "days_analyzed": days,
        }

    async def get_statistics(self) -> Dict[str, Any]:
        """
        데이터베이스 통계 조회

        Returns:
            통계 정보
        """
        try:
            # 전체 메일 수
            total_result = self.db_manager.fetch_one(
                "SELECT COUNT(*) as count FROM mail_history"
            )

            # 오늘 처리된 메일 수
            today_result = self.db_manager.fetch_one(
                """
                SELECT COUNT(*) as count 
                FROM mail_history 
                WHERE processed_at >= date('now', 'start of day')
                """
            )

            # 최근 7일간 처리된 메일 수
            week_result = self.db_manager.fetch_one(
                """
                SELECT COUNT(*) as count 
                FROM mail_history 
                WHERE processed_at >= datetime('now', '-7 days')
                """
            )

            # 계정별 통계
            account_stats = self.db_manager.fetch_all(
                """
                SELECT 
                    a.user_id,
                    COUNT(mh.id) as mail_count,
                    MAX(mh.processed_at) as last_processed
                FROM accounts a
                LEFT JOIN mail_history mh ON a.id = mh.account_id
                WHERE a.is_active = 1
                GROUP BY a.user_id
                ORDER BY mail_count DESC
                LIMIT 10
                """
            )

            return {
                "total_mails": total_result["count"] if total_result else 0,
                "today_mails": today_result["count"] if today_result else 0,
                "week_mails": week_result["count"] if week_result else 0,
                "top_accounts": (
                    [dict(row) for row in account_stats] if account_stats else []
                ),
            }

        except Exception as e:
            self.logger.error(f"통계 조회 실패: {str(e)}")
            return {
                "total_mails": 0,
                "today_mails": 0,
                "week_mails": 0,
                "top_accounts": [],
            }

    def _generate_content_hash(self, content: str) -> str:
        """내용 해시 생성"""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _get_actual_account_id(self, account_id: str) -> int:
        """문자열 account_id(user_id)를 실제 DB ID로 변환"""
        if isinstance(account_id, int):
            return account_id

        account_query = "SELECT id FROM accounts WHERE user_id = ?"
        account_result = self.db_manager.fetch_one(account_query, (account_id,))

        if account_result:
            return account_result["id"]
        else:
            # 테스트용 계정이 없는 경우 임시로 생성
            self.logger.warning(f"계정 {account_id}가 존재하지 않음, 임시 계정 생성")

            temp_account_data = {
                "user_id": account_id,
                "user_name": f"Test User ({account_id})",
                "is_active": True,
            }

            account_id_int = self.db_manager.insert("accounts", temp_account_data)
            return account_id_int

    def check_and_save_mail(
        self, processed_mail: ProcessedMailData
    ) -> Tuple[bool, bool]:
        """
        중복 확인 후 저장 및 다음 단계 진행 여부 결정

        Args:
            processed_mail: 처리된 메일 데이터

        Returns:
            (저장_성공_여부, 다음_단계_진행_여부)
        """
        # 1. 중복 확인
        is_duplicate = self.check_duplicate_by_id(processed_mail.mail_id)

        if is_duplicate:
            self.logger.info(f"중복 메일 발견: {processed_mail.mail_id}")
            # 환경설정에 따라 다음 단계 진행 여부 결정
            should_continue = self.config.process_duplicate_mails
            self.logger.debug(f"중복 메일 처리 설정: {should_continue}")
            return False, should_continue

        # 2. 중복이 아닌 경우 - MailHistoryData로 변환 후 저장
        mail_history_data = self._convert_to_mail_history(processed_mail)
        save_success = self._save_mail_history_simple(mail_history_data)

        # 3. 저장 성공 시 다음 단계로 진행
        return save_success, save_success

    def _convert_to_mail_history(
        self, processed_mail: ProcessedMailData
    ) -> MailHistoryData:
        """ProcessedMailData를 MailHistoryData로 변환"""
        return MailHistoryData(
            account_id=processed_mail.account_id,
            message_id=processed_mail.mail_id,
            received_time=processed_mail.sent_time,
            subject=processed_mail.subject,
            sender=processed_mail.sender_address,
            processed_at=processed_mail.processed_at,
        )

    def _save_mail_history_simple(self, mail_history_data: MailHistoryData) -> bool:
        """
        단순화된 메일 히스토리 저장 (keywords, content_hash 제외)

        Args:
            mail_history_data: 메일 히스토리 데이터

        Returns:
            저장 성공 여부
        """
        # 실제 account_id 조회
        actual_account_id = self._get_actual_account_id(mail_history_data.account_id)

        # 메일 히스토리 저장 데이터 준비
        mail_data = {
            "account_id": actual_account_id,
            "message_id": mail_history_data.message_id,
            "received_time": mail_history_data.received_time,
            "subject": mail_history_data.subject,
            "sender": mail_history_data.sender,
            "processed_at": mail_history_data.processed_at,
        }

        try:
            # infra.database의 insert 메서드 사용
            inserted_id = self.db_manager.insert("mail_history", mail_data)

            self.logger.info(
                f"메일 저장 완료 - ID: {inserted_id}, "
                f"message_id: {mail_history_data.message_id}, "
                f"account_id: {actual_account_id}"
            )
            return True

        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                self.logger.warning(
                    f"메일 저장 실패 (중복) - message_id: {mail_history_data.message_id}"
                )
            else:
                self.logger.error(
                    f"메일 저장 실패 - message_id: {mail_history_data.message_id}, error: {str(e)}"
                )
            return False

    def check_and_save_mail_history(
        self, mail_history_data: MailHistoryData
    ) -> Tuple[bool, bool]:
        """
        MailHistoryData 중복 확인 후 저장 및 다음 단계 진행 여부 결정

        Args:
            mail_history_data: 메일 히스토리 데이터

        Returns:
            (저장_성공_여부, 다음_단계_진행_여부)
        """
        # 1. 중복 확인
        is_duplicate = self.check_duplicate_by_id(mail_history_data.message_id)

        if is_duplicate:
            self.logger.info(f"중복 메일 발견: {mail_history_data.message_id}")
            # 환경설정에 따라 다음 단계 진행 여부 결정
            should_continue = self.config.process_duplicate_mails
            self.logger.debug(f"중복 메일 처리 설정: {should_continue}")
            return False, should_continue

        # 2. 중복이 아닌 경우 저장
        save_success = self._save_mail_history_simple(mail_history_data)

        # 3. 저장 성공 시 다음 단계로 진행
        return save_success, save_success

    def check_and_save_graph_mail(
        self, account_id: str, mail_item
    ) -> Tuple[bool, bool]:
        """
        GraphMailItem 중복 확인 후 MailHistoryData로 변환하여 저장

        Args:
            account_id: 계정 ID
            mail_item: GraphMailItem 객체

        Returns:
            (저장_성공_여부, 다음_단계_진행_여부)
        """
        # 1. 중복 확인
        is_duplicate = self.check_duplicate_by_id(mail_item.id)

        if is_duplicate:
            self.logger.info(f"중복 메일 발견: {mail_item.id}")
            # 환경설정에 따라 다음 단계 진행 여부 결정
            should_continue = self.config.process_duplicate_mails
            self.logger.debug(f"중복 메일 처리 설정: {should_continue}")
            return False, should_continue

        # 2. GraphMailItem을 MailHistoryData로 변환
        mail_history_data = self._convert_graph_mail_to_history(account_id, mail_item)

        # 3. 저장
        save_success = self._save_mail_history_simple(mail_history_data)

        # 4. 저장 성공 시 다음 단계로 진행
        return save_success, save_success

    def _convert_graph_mail_to_history(
        self, account_id: str, mail_item
    ) -> MailHistoryData:
        """GraphMailItem을 MailHistoryData로 변환"""
        # 발신자 정보 추출
        sender_info = mail_item.sender or mail_item.from_address or {}
        sender_name = sender_info.get("emailAddress", {}).get("name", "")
        sender_address = sender_info.get("emailAddress", {}).get("address", "")
        sender_display = (
            f"{sender_name} <{sender_address}>" if sender_name else sender_address
        )

        return MailHistoryData(
            account_id=str(account_id),  # 문자열로 변환
            message_id=mail_item.id,
            received_time=mail_item.received_date_time,
            subject=mail_item.subject or "",
            sender=sender_display,
        )

    def _ensure_content_hash_column(self) -> None:
        """content_hash 컬럼 존재 확인 및 추가 (레거시 지원용)"""
        try:
            # 컬럼 존재 여부 확인
            table_info = self.db_manager.get_table_info("mail_history")
            column_names = [col["name"] for col in table_info]

            if "content_hash" not in column_names:
                alter_query = "ALTER TABLE mail_history ADD COLUMN content_hash TEXT"
                self.db_manager.execute_query(alter_query)
                self.logger.info("mail_history 테이블에 content_hash 컬럼 추가됨")

                # 인덱스도 함께 생성
                index_query = "CREATE INDEX IF NOT EXISTS idx_mail_history_content_hash ON mail_history (content_hash)"
                self.db_manager.execute_query(index_query)
                self.logger.info("content_hash 인덱스 생성됨")
        except Exception as e:
            # 이미 컬럼이 있거나 다른 이유로 실패한 경우 무시
            self.logger.debug(f"content_hash 컬럼 확인/추가 중 오류 (무시됨): {str(e)}")
