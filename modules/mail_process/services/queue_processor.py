"""
메일 큐 프로세서 - 큐에서 배치를 꺼내어 처리
modules/mail_process/services/queue_processor.py
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import time

from infra.core.logger import get_logger
from modules.mail_process.mail_processor_schema import (
    ProcessedMailData,
    ProcessingStatus,
    GraphMailItem,
)
from .queue_service import get_queue_service
from .processing_service import ProcessingService
from .persistence_service import PersistenceService
from .event_service import MailEventService


class MailQueueProcessor:
    """메일 큐 프로세서 - 배치 단위로 큐에서 메일을 꺼내어 처리"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.queue_service = get_queue_service()
        self.processing_service = ProcessingService()
        self.persistence_service = PersistenceService()
        self.event_service = MailEventService()

        # 처리 상태
        self._is_running = False
        self._processing_task: Optional[asyncio.Task] = None

        # 처리 통계
        self._stats = {
            "batches_processed": 0,
            "total_processed": 0,
            "total_saved": 0,
            "total_failed": 0,
            "total_skipped": 0,
            "processing_time_ms": 0,
        }

    async def start_processing(self, continuous: bool = True) -> None:
        """
        큐 처리 시작

        Args:
            continuous: True면 계속 처리, False면 한 번만 처리
        """
        if self._is_running:
            self.logger.warning("큐 프로세서가 이미 실행 중입니다")
            return

        self._is_running = True
        self.logger.info("큐 프로세서 시작")

        try:
            if continuous:
                await self._continuous_processing()
            else:
                await self._process_single_batch()
        finally:
            self._is_running = False
            self.logger.info("큐 프로세서 종료")

    async def stop_processing(self) -> None:
        """큐 처리 중지"""
        self.logger.info("큐 프로세서 중지 요청")
        self._is_running = False

        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

    async def _continuous_processing(self) -> None:
        """지속적인 배치 처리"""
        empty_queue_wait_time = int(os.getenv("MAIL_QUEUE_WAIT_TIME", "5"))

        while self._is_running:
            try:
                # 큐 상태 확인
                queue_status = await self.queue_service.get_queue_status()

                if queue_status["is_empty"]:
                    self.logger.debug(f"큐가 비어있음 - {empty_queue_wait_time}초 대기")
                    await asyncio.sleep(empty_queue_wait_time)
                    continue

                # 배치 처리
                await self._process_single_batch()

                # 처리 간격 (과부하 방지)
                process_interval = float(os.getenv("MAIL_PROCESS_INTERVAL", "0.1"))
                await asyncio.sleep(process_interval)

            except Exception as e:
                self.logger.error(f"배치 처리 중 오류: {str(e)}", exc_info=True)
                await asyncio.sleep(empty_queue_wait_time)

    async def _process_single_batch(self) -> Dict[str, Any]:
        """단일 배치 처리"""
        start_time = time.time()

        # 배치 가져오기
        batch = await self.queue_service.dequeue_batch()

        if not batch:
            return {"processed": 0, "message": "큐가 비어있음"}

        self.logger.info(f"배치 처리 시작 - 크기: {len(batch)}")

        # 배치 처리
        batch_stats = await self._process_batch_items(batch)

        # 전체 통계 업데이트
        self._update_global_stats(batch_stats)

        execution_time_ms = int((time.time() - start_time) * 1000)

        self.logger.info(
            f"배치 처리 완료 - "
            f"처리: {batch_stats['processed']}, "
            f"저장: {batch_stats['saved']}, "
            f"실패: {batch_stats['failed']}, "
            f"실행시간: {execution_time_ms}ms"
        )

        return {
            "batch_size": len(batch),
            "stats": batch_stats,
            "execution_time_ms": execution_time_ms,
        }

    async def _process_batch_items(self, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """배치 아이템 처리"""
        stats = {
            "processed": 0,
            "saved": 0,
            "failed": 0,
            "skipped": 0,
            "events_published": 0,
        }

        failed_items = []

        # 동시 처리를 위한 세마포어
        semaphore = asyncio.Semaphore(5)

        # 처리 태스크 생성
        tasks = []
        for item in batch:
            task = self._process_queue_item_with_semaphore(
                item, stats, failed_items, semaphore
            )
            tasks.append(task)

        # 모든 아이템 비동기 처리
        await asyncio.gather(*tasks, return_exceptions=True)

        # 실패한 아이템 재큐잉
        if failed_items:
            requeued = await self.queue_service.requeue_failed_items(failed_items)
            self.logger.info(f"실패 아이템 재큐잉: {requeued}/{len(failed_items)}")

        return stats

    async def _process_queue_item_with_semaphore(
        self,
        item: Dict[str, Any],
        stats: Dict[str, Any],
        failed_items: List[Dict[str, Any]],
        semaphore: asyncio.Semaphore,
    ) -> None:
        """세마포어를 사용한 큐 아이템 처리"""
        async with semaphore:
            await self._process_queue_item(item, stats, failed_items)

    async def _process_queue_item(
        self,
        item: Dict[str, Any],
        stats: Dict[str, Any],
        failed_items: List[Dict[str, Any]],
    ) -> None:
        """개별 큐 아이템 처리"""
        account_id = item["account_id"]
        mail_data = item["mail"]
        cleaned_content = item["cleaned_content"]

        try:
            # GraphMailItem으로 변환
            mail = GraphMailItem(**mail_data)

            # 메일 처리
            processed_mail = await self.processing_service.process_mail(
                account_id=account_id, mail=mail
            )

            # cleaned_content 적용
            processed_mail.clean_content = cleaned_content

            if processed_mail.processing_status == ProcessingStatus.SUCCESS:
                # DB 저장
                save_success = self.persistence_service.save_processed_mail(
                    processed_mail
                )

                if save_success:
                    stats["saved"] += 1

                    # 이벤트 발행
                    await self.event_service.publish_mail_event(
                        account_id=account_id,
                        mail=mail_data,
                        keywords=processed_mail.keywords,
                        clean_content=cleaned_content,
                    )
                    stats["events_published"] += 1

                    self.logger.debug(f"메일 처리 성공 - ID: {mail.id}")
                else:
                    stats["failed"] += 1
                    failed_items.append(item)
                    self.logger.warning(f"메일 저장 실패 - ID: {mail.id}")

                stats["processed"] += 1

            elif processed_mail.processing_status == ProcessingStatus.SKIPPED:
                stats["skipped"] += 1
                self.logger.debug(f"메일 처리 건너뜀 - ID: {mail.id}")

            else:  # FAILED or PARTIAL
                stats["failed"] += 1
                failed_items.append(item)
                self.logger.warning(
                    f"메일 처리 실패 - ID: {mail.id}, "
                    f"상태: {processed_mail.processing_status}"
                )

        except Exception as e:
            stats["failed"] += 1
            failed_items.append(item)
            self.logger.error(
                f"큐 아이템 처리 실패 - "
                f"mail_id: {mail_data.get('id', 'unknown')}, "
                f"error: {str(e)}",
                exc_info=True,
            )

    def _update_global_stats(self, batch_stats: Dict[str, Any]) -> None:
        """전체 통계 업데이트"""
        self._stats["batches_processed"] += 1
        self._stats["total_processed"] += batch_stats["processed"]
        self._stats["total_saved"] += batch_stats["saved"]
        self._stats["total_failed"] += batch_stats["failed"]
        self._stats["total_skipped"] += batch_stats["skipped"]

    async def get_processor_stats(self) -> Dict[str, Any]:
        """프로세서 통계 조회"""
        queue_status = await self.queue_service.get_queue_status()

        return {
            "processor": {"is_running": self._is_running, "stats": self._stats.copy()},
            "queue": queue_status,
        }

    async def reset_stats(self) -> None:
        """통계 초기화"""
        for key in self._stats:
            if key != "processing_time_ms":
                self._stats[key] = 0

        self.logger.info("프로세서 통계 초기화됨")


# 싱글톤 인스턴스
_processor_instance: Optional[MailQueueProcessor] = None


def get_queue_processor() -> MailQueueProcessor:
    """큐 프로세서 싱글톤 인스턴스 반환"""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = MailQueueProcessor()
    return _processor_instance
