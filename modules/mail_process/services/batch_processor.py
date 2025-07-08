"""
메일 배치 처리 서비스
개별 메일의 처리 로직을 관리
modules/mail_process/services/batch_processor.py
"""

import asyncio
from typing import List, Dict, Any

from infra.core.logger import get_logger
from modules.mail_process.mail_processor_schema import ProcessingStatus, GraphMailItem
from .db_service import MailDatabaseService
from .processing_service import ProcessingService
from .persistence_service import PersistenceService
from .event_service import MailEventService

logger = get_logger(__name__)


class MailBatchProcessor:
    """메일 배치 처리 서비스"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.db_service = MailDatabaseService()
        self.processing_service = ProcessingService()
        self.persistence_service = PersistenceService()
        self.event_service = MailEventService()

    async def process_mail_batch(
        self, account_id: str, mails: List[GraphMailItem]
    ) -> Dict[str, Any]:
        """
        메일 배치를 처리

        Args:
            account_id: 계정 ID
            mails: 메일 리스트

        Returns:
            처리 통계
        """
        stats = self._initialize_stats()

        # 동시 처리를 위한 세마포어 (동시에 5개까지)
        semaphore = asyncio.Semaphore(5)

        # 처리 태스크 생성
        tasks = [
            self._process_single_mail_with_semaphore(mail, account_id, stats, semaphore)
            for mail in mails
        ]

        # 모든 메일을 비동기로 처리
        await asyncio.gather(*tasks, return_exceptions=True)

        # 배치 처리 완료 이벤트 발행
        await self.event_service.publish_batch_complete_event(
            account_id=account_id,
            processed_count=stats["processed_count"],
            skipped_count=stats["skipped_count"],
            failed_count=stats["failed_count"],
        )

        stats["events_published"] = (
            stats["processed_count"] + 1
        )  # 개별 메일 이벤트 + 배치 완료 이벤트

        return stats

    async def _process_single_mail_with_semaphore(
        self,
        mail: GraphMailItem,
        account_id: str,
        stats: Dict[str, Any],
        semaphore: asyncio.Semaphore,
    ):
        """세마포어를 사용한 개별 메일 처리"""
        async with semaphore:
            await self._process_single_mail(mail, account_id, stats)

    async def _process_single_mail(
        self, mail: GraphMailItem, account_id: str, stats: Dict[str, Any]
    ):
        """개별 메일 처리"""
        try:
            # 1. 중복 확인 (message_id 기반)
            is_duplicate = self.db_service.check_duplicate_by_id(mail.id)

            if is_duplicate:
                stats["duplicate_count"] += 1
                logger.debug(f"중복 메일 발견 - ID: {mail.id}")
                return

            # 2. 메일 처리
            processed_mail = await self.processing_service.process_mail(
                account_id=account_id, mail=mail
            )

            if processed_mail.processing_status == ProcessingStatus.SUCCESS:
                # 3. DB 저장
                save_success = self.persistence_service.save_processed_mail(
                    processed_mail
                )

                if save_success:
                    stats["saved_count"] += 1
                    stats["new_count"] += 1

                    # 4. 이벤트 발행
                    await self.event_service.publish_mail_event(
                        account_id=account_id,
                        mail=mail.model_dump(),
                        keywords=processed_mail.keywords,
                        clean_content=processed_mail.clean_content or "",
                    )

                    logger.debug(f"메일 저장 및 이벤트 발행 완료 - ID: {mail.id}")
                else:
                    stats["failed_count"] += 1
                    stats["errors"].append(f"저장 실패: {mail.id}")

                stats["processed_count"] += 1

            elif processed_mail.processing_status == ProcessingStatus.SKIPPED:
                stats["skipped_count"] += 1
                logger.debug(f"메일 처리 건너뜀 - ID: {mail.id}")

            else:  # FAILED or PARTIAL
                stats["failed_count"] += 1
                if processed_mail.error_message:
                    stats["errors"].append(processed_mail.error_message)
                logger.warning(
                    f"메일 처리 실패 - ID: {mail.id}, 상태: {processed_mail.processing_status}"
                )

        except Exception as e:
            stats["failed_count"] += 1
            error_msg = f"메일 처리 실패 - ID: {mail.id}, Error: {str(e)}"
            stats["errors"].append(error_msg)
            logger.error(error_msg, exc_info=True)

    def _initialize_stats(self) -> Dict[str, Any]:
        """통계 초기화"""
        return {
            "new_count": 0,
            "duplicate_count": 0,
            "processed_count": 0,
            "saved_count": 0,
            "failed_count": 0,
            "skipped_count": 0,
            "events_published": 0,
            "errors": [],
            "warnings": [],
        }
