"""
Mail Processor 오케스트레이터 V2 - 큐 기반 배치 처리
mail_query로부터 받은 메일을 큐에 저장하고 배치로 처리
modules/mail_process/mail_processor_orchestrator_v2.py
"""

import time
from datetime import datetime
from typing import Dict, Optional, List, Any
import asyncio

from infra.core.logger import get_logger
from modules.mail_query import (
    MailQueryOrchestrator,
    MailQueryRequest,
    MailQueryFilters,
    PaginationOptions,
)
from .mail_processor_schema import MailProcessingResult
from .services.db_service import MailDatabaseService
from .services.filtering_service import FilteringService
from .services.statistics_service import StatisticsService
from .services.queue_service import get_queue_service
from .services.queue_processor import get_queue_processor

logger = get_logger(__name__)


class MailProcessorOrchestrator:
    """메일 처리 오케스트레이터 V2 - 큐 기반 배치 처리"""

    def __init__(self):
        self.logger = get_logger(__name__)

        # 서비스 초기화
        self.db_service = MailDatabaseService()
        self.filtering_service = FilteringService()
        self.statistics_service = StatisticsService()
        self.queue_service = get_queue_service()
        self.queue_processor = get_queue_processor()

        # Mail Query 오케스트레이터
        self.mail_query_orchestrator = None

        # 백그라운드 프로세서 태스크
        self._processor_task: Optional[asyncio.Task] = None

    async def __aenter__(self):
        """컨텍스트 매니저 진입"""
        self.mail_query_orchestrator = MailQueryOrchestrator()
        await self.mail_query_orchestrator.__aenter__()

        # 백그라운드 프로세서 시작
        await self.start_background_processor()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        # 백그라운드 프로세서 중지
        await self.stop_background_processor()

        if self.mail_query_orchestrator:
            await self.mail_query_orchestrator.__aexit__(exc_type, exc_val, exc_tb)

    async def start_background_processor(self):
        """백그라운드 큐 프로세서 시작"""
        if not self._processor_task or self._processor_task.done():
            self._processor_task = asyncio.create_task(
                self.queue_processor.start_processing(continuous=True)
            )
            self.logger.info("백그라운드 큐 프로세서 시작됨")

    async def stop_background_processor(self):
        """백그라운드 큐 프로세서 중지"""
        if self._processor_task and not self._processor_task.done():
            await self.queue_processor.stop_processing()
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
            self.logger.info("백그라운드 큐 프로세서 중지됨")

    async def enqueue_user_mails(
        self,
        user_id: str,
        filters: Optional[MailQueryFilters] = None,
        pagination: Optional[PaginationOptions] = None,
    ) -> Dict[str, Any]:
        """
        특정 사용자의 메일을 조회하고 큐에 저장

        Args:
            user_id: 사용자 ID
            filters: 메일 필터 조건
            pagination: 페이징 옵션

        Returns:
            큐 저장 결과
        """
        start_time = time.time()

        try:
            # 1. Mail Query 모듈을 통해 메일 조회
            mail_response = await self._fetch_mails(user_id, filters, pagination)

            # 2. 필터링 적용
            filtered_mails = await self.filtering_service.filter_mails(
                mail_response.messages
            )

            # 3. 큐에 저장
            queue_result = await self.queue_service.enqueue_mails(
                user_id, filtered_mails
            )

            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"메일 큐 저장 완료 - user_id: {user_id}, "
                f"총 {mail_response.total_fetched}개 조회, "
                f"필터링 후 {len(filtered_mails)}개, "
                f"큐 저장 {queue_result['enqueued']}개, "
                f"중복 {queue_result['duplicates']}개, "
                f"실행시간: {execution_time_ms}ms"
            )

            return {
                "user_id": user_id,
                "total_fetched": mail_response.total_fetched,
                "filtered_count": len(filtered_mails),
                "enqueued": queue_result["enqueued"],
                "duplicates": queue_result["duplicates"],
                "queue_size": queue_result["queue_size"],
                "execution_time_ms": execution_time_ms,
            }

        except Exception as e:
            logger.error(
                f"메일 큐 저장 중 오류 발생 - user_id: {user_id}, error: {str(e)}"
            )
            raise

    async def process_user_mails_immediate(
        self,
        user_id: str,
        filters: Optional[MailQueryFilters] = None,
        pagination: Optional[PaginationOptions] = None,
    ) -> MailProcessingResult:
        """
        특정 사용자의 메일을 즉시 처리 (큐를 거치지 않음)
        기존 방식과의 호환성을 위해 유지
        """
        # 큐에 저장
        enqueue_result = await self.enqueue_user_mails(user_id, filters, pagination)

        # 즉시 처리
        await self.queue_processor._process_single_batch()

        # 처리 결과 생성
        processor_stats = await self.queue_processor.get_processor_stats()

        result = MailProcessingResult(
            account_id=user_id,
            total_fetched=enqueue_result["total_fetched"],
            filtered_count=enqueue_result["filtered_count"],
            new_count=enqueue_result["enqueued"],
            duplicate_count=enqueue_result["duplicates"],
            processed_count=processor_stats["processor"]["stats"]["total_processed"],
            saved_count=processor_stats["processor"]["stats"]["total_saved"],
            failed_count=processor_stats["processor"]["stats"]["total_failed"],
            skipped_count=processor_stats["processor"]["stats"]["total_skipped"],
            events_published=0,  # TODO: 이벤트 카운트 추가
            last_sync_time=datetime.now(),
            execution_time_ms=enqueue_result["execution_time_ms"],
            success_rate=0.0,  # TODO: 성공률 계산
            duplication_rate=0.0,  # TODO: 중복률 계산
            processing_efficiency=0.0,  # TODO: 효율성 계산
            errors=[],
            warnings=[],
        )

        # 동기화 시간 업데이트
        self.db_service.update_account_sync_time(user_id, datetime.now())

        return result

    async def enqueue_all_active_accounts(self) -> Dict[str, Dict[str, Any]]:
        """
        모든 활성 계정의 메일을 큐에 저장

        Returns:
            계정별 큐 저장 결과
        """
        logger.info("전체 활성 계정 메일 큐 저장 시작")

        # 활성 계정 목록 조회
        active_accounts = self.db_service.get_active_accounts()
        results = {}

        for account in active_accounts:
            try:
                user_id = account["user_id"]
                logger.info(f"계정 큐 저장 시작: {user_id}")

                # 마지막 동기화 시간 기반 필터 생성
                filters = self._create_sync_filters(account.get("last_sync_time"))

                # 메일 큐에 저장
                result = await self.enqueue_user_mails(user_id, filters)
                results[user_id] = result

            except Exception as e:
                logger.error(f"계정 큐 저장 실패 - user_id: {user_id}, error: {str(e)}")
                self.db_service.record_account_error(user_id, str(e))
                continue

        logger.info(f"전체 계정 큐 저장 완료 - 처리된 계정 수: {len(results)}")
        return results

    async def get_processing_status(self) -> Dict[str, Any]:
        """전체 처리 상태 조회"""
        processor_stats = await self.queue_processor.get_processor_stats()
        filter_stats = self.filtering_service.get_filter_stats()

        return {
            "processor": processor_stats["processor"],
            "queue": processor_stats["queue"],
            "filtering": filter_stats,
        }

    async def _fetch_mails(
        self,
        user_id: str,
        filters: Optional[MailQueryFilters],
        pagination: Optional[PaginationOptions],
    ):
        """메일 조회 로직"""
        request = MailQueryRequest(
            user_id=user_id,
            filters=filters,
            pagination=pagination or PaginationOptions(top=50, max_pages=10),
        )

        logger.info(f"메일 조회 시작 - user_id: {user_id}")
        mail_response = await self.mail_query_orchestrator.mail_query_user_emails(
            request
        )
        logger.info(f"조회된 메일 수: {mail_response.total_fetched}개")

        return mail_response

    def _create_sync_filters(
        self, last_sync_time: Optional[datetime]
    ) -> Optional[MailQueryFilters]:
        """동기화 필터 생성"""
        if last_sync_time:
            return MailQueryFilters(date_from=last_sync_time)
        return None

    async def force_process_queue(self) -> Dict[str, Any]:
        """큐 강제 처리 (관리용)"""
        logger.info("큐 강제 처리 시작")

        total_processed = 0
        batches = 0

        while True:
            result = await self.queue_processor._process_single_batch()

            if result.get("processed", 0) == 0:
                break

            total_processed += result.get("stats", {}).get("processed", 0)
            batches += 1

            # 너무 많은 배치 처리 방지
            if batches >= 100:
                logger.warning("강제 처리 중단 - 최대 배치 수 도달")
                break

        logger.info(
            f"큐 강제 처리 완료 - " f"배치: {batches}, " f"총 처리: {total_processed}"
        )

        return {"batches_processed": batches, "total_processed": total_processed}
