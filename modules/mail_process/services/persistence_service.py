"""
지속성 관리 서비스
modules/mail_process/services/persistence_service.py
"""

import os
from typing import Dict, List, Optional, Any

from infra.core.logger import get_logger
from infra.core.config import get_config
from .db_service import MailDatabaseService
from .event_service import MailEventService
from .batch_processor import BatchProcessor


class PersistenceService:
    """지속성 관리 서비스"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.db_service = MailDatabaseService()
        self.event_service = MailEventService()
        self.batch_processor = BatchProcessor(self.db_service, self.event_service)

        # 중복 체크 활성화 여부 (환경변수에서 읽기)
        env_value = os.getenv("ENABLE_MAIL_DUPLICATE_CHECK", "true")
        # 주석 제거 (#로 시작하는 부분 제거)
        if "#" in env_value:
            env_value = env_value.split("#")[0].strip()

        self.duplicate_check_enabled = env_value.lower() == "true"

        # 메일 히스토리 저장 활성화 여부
        self.mail_history_enabled = (
            os.getenv("ENABLE_MAIL_HISTORY", "true").lower() == "true"
        )

        # Kafka 이벤트 활성화 여부
        self.kafka_events_enabled = (
            os.getenv("ENABLE_KAFKA_EVENTS", "true").lower() == "true"
        )

        # 배치 처리 설정
        self.batch_insert_size = int(os.getenv("DB_BATCH_INSERT_SIZE", "100"))

        self.logger.info(
            f"지속성 서비스 초기화 - "
            f"중복체크: {self.duplicate_check_enabled}, "
            f"히스토리: {self.mail_history_enabled}, "
            f"Kafka: {self.kafka_events_enabled}"
        )

    def get_existing_mail_ids(self, mail_ids: List[str]) -> List[str]:
        """여러 메일 ID의 존재 여부를 한 번에 확인 (배치 조회)"""
        if not mail_ids or not self.duplicate_check_enabled:
            return []

        try:
            # 배치 크기로 나누어 처리
            existing_ids = []
            for i in range(0, len(mail_ids), self.batch_insert_size):
                batch = mail_ids[i : i + self.batch_insert_size]

                # IN 절을 사용한 배치 조회
                placeholders = ",".join(["?" for _ in batch])
                query = f"""
                    SELECT message_id 
                    FROM mail_history 
                    WHERE message_id IN ({placeholders})
                """

                results = self.db_service.db_manager.fetch_all(query, batch)
                existing_ids.extend([row["message_id"] for row in results])

            self.logger.debug(
                f"배치 중복 체크: {len(mail_ids)}개 중 {len(existing_ids)}개 존재"
            )
            return existing_ids

        except Exception as e:
            self.logger.error(f"배치 중복 체크 오류: {str(e)}")
            # 오류 시 모든 ID를 존재하는 것으로 간주 (안전하게)
            return mail_ids

    def is_duplicate_by_id(self, mail_id: str) -> bool:
        """메일 ID로만 간단히 중복 체크 (단일 체크)"""
        if not self.duplicate_check_enabled:
            return False

        try:
            existing_mail = self.db_service.get_mail_by_id(mail_id)
            return existing_mail is not None
        except Exception as e:
            self.logger.error(f"중복 체크 오류: {str(e)}")
            # 오류 시 중복으로 간주하여 안전하게 처리
            return True

    async def persist_mails(
        self, account_id: str, mails: List[Dict], mails_for_events: List[Dict] = None
    ) -> Dict:
        """
        메일 데이터 저장 (배치 처리 지원)

        Args:
            account_id: 계정 ID
            mails: 처리된 메일 리스트 (DB 저장용)
            mails_for_events: 이벤트 발행용 메일 리스트

        Returns:
            저장 결과 통계
        """
        # 이벤트용 메일이 제공되지 않으면 기존 메일 사용
        if mails_for_events is None:
            mails_for_events = mails

        # 배치 처리를 위한 리스트
        mails_to_save = []
        events_to_publish = []

        saved_count = 0
        failed_count = 0
        event_published_count = 0

        for i, mail in enumerate(mails):
            try:
                # 이벤트용 메일 가져오기
                event_mail = mails_for_events[i] if i < len(mails_for_events) else mail

                # 중복 체크가 비활성화된 경우
                if not self.duplicate_check_enabled:
                    # DB 저장 없이 이벤트만 준비
                    if self.kafka_events_enabled:
                        events_to_publish.append((account_id, event_mail, mail))
                    saved_count += 1
                    continue

                # ProcessedMailData 생성
                processed_mail = self.batch_processor.create_processed_mail_data(
                    account_id, mail
                )

                # 메일 히스토리 저장이 활성화된 경우만 저장 준비
                if self.mail_history_enabled:
                    mails_to_save.append(
                        (processed_mail, mail.get("clean_content", ""))
                    )

                # 이벤트 준비
                if self.kafka_events_enabled:
                    events_to_publish.append((account_id, event_mail, mail))

                saved_count += 1

            except Exception as e:
                self.logger.error(f"메일 처리 실패: {str(e)}")
                failed_count += 1

        # 배치 DB 저장
        if mails_to_save and self.mail_history_enabled:
            db_results = await self.batch_processor.batch_save_to_database(
                mails_to_save
            )
            saved_count = db_results["saved"]
            failed_count += db_results["failed"]

        # 배치 이벤트 발행
        if events_to_publish and self.kafka_events_enabled:
            event_results = await self.batch_processor.batch_publish_events(
                events_to_publish
            )
            event_published_count = event_results["published"]

        results = {
            "saved": saved_count,
            "duplicates": 0,  # Phase 2에서 이미 제외됨
            "failed": failed_count,
            "total": len(mails),
            "events_published": event_published_count,
            "duplicate_check_enabled": self.duplicate_check_enabled,
            "mail_history_enabled": self.mail_history_enabled,
            "kafka_events_enabled": self.kafka_events_enabled,
        }

        self.logger.info(
            f"메일 처리 완료 - 저장: {saved_count}, "
            f"실패: {failed_count}, "
            f"이벤트 발행: {event_published_count}, "
            f"설정: 중복체크={self.duplicate_check_enabled}, "
            f"히스토리={self.mail_history_enabled}, "
            f"Kafka={self.kafka_events_enabled}"
        )

        return results

    def get_duplicate_check_status(self) -> bool:
        """중복 체크 활성화 상태 반환"""
        return self.duplicate_check_enabled

    def get_service_configuration(self) -> Dict[str, bool]:
        """서비스 설정 상태 반환"""
        return {
            "duplicate_check_enabled": self.duplicate_check_enabled,
            "mail_history_enabled": self.mail_history_enabled,
            "kafka_events_enabled": self.kafka_events_enabled,
        }

    async def get_mail_statistics(
        self, account_id: str, days: int = 30
    ) -> Dict[str, Any]:
        """계정의 메일 처리 통계 조회"""
        return self.db_service.get_mail_statistics(account_id, days)
