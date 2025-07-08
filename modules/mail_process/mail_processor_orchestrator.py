"""
메일 처리 오케스트레이터 - 메일 처리 워크플로우 총괄
modules/mail_process/mail_processor_orchestrator.py
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

from infra.core.logger import get_logger
from infra.core.database import get_database_manager
from modules.mail_query import (
    MailQueryOrchestrator,
    MailQueryRequest,
    MailQueryFilters,
    PaginationOptions,
)
from .services.filtering_service import FilteringService
from .services.queue_service import MailQueueService
from .services.processing_service import ProcessingService
from .services.db_service import MailDatabaseService
from .mail_processor_schema import MailProcessingResult, ProcessedMailData


class MailProcessorOrchestrator:
    """메일 처리 오케스트레이터"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.db_manager = get_database_manager()

        # 서비스 초기화
        self.filtering_service = FilteringService()
        self.queue_service = MailQueueService()
        self.processing_service = ProcessingService()
        self.db_service = MailDatabaseService()

        # 메일 조회 오케스트레이터
        self.mail_query = MailQueryOrchestrator()

        # 백그라운드 태스크
        self._background_task: Optional[asyncio.Task] = None
        self._should_stop = False

        self.logger.info("오케스트레이터 초기화 완료")

    async def save_to_queue(
        self,
        user_id: str,
        filters: Optional[MailQueryFilters] = None,
        pagination: Optional[PaginationOptions] = None,
    ) -> Dict[str, Any]:
        """
        특정 계정의 메일을 조회하여 큐에 저장

        Args:
            user_id: 사용자 ID
            filters: 메일 필터
            pagination: 페이지네이션 옵션

        Returns:
            큐 저장 결과
        """
        try:
            self.logger.info(f"메일 조회 시작 - user_id: {user_id}")

            # 1. 메일 조회
            query_request = MailQueryRequest(
                user_id=user_id,
                filters=filters or MailQueryFilters(),
                pagination=pagination or PaginationOptions(top=50),
            )

            # mail_query_user_emails 메서드 사용 (올바른 메서드명)
            async with self.mail_query as mail_query:
                query_response = await mail_query.mail_query_user_emails(query_request)

            # MailQueryResponse 객체에서 messages 추출
            mails = query_response.messages
            self.logger.info(f"조회된 메일 수: {len(mails)}개")

            if not mails:
                return {
                    "account_id": user_id,
                    "enqueued": 0,
                    "duplicates": 0,
                    "queue_size": 0,
                }

            # 2. 큐에 저장 - GraphMailItem 객체 리스트를 전달
            queue_result = await self.queue_service.enqueue_mails(user_id, mails)

            return queue_result

        except Exception as e:
            self.logger.error(
                f"메일 큐 저장 중 오류 발생 - user_id: {user_id}, error: {str(e)}"
            )
            raise

    async def process_batch(self) -> List[MailProcessingResult]:
        """
        큐에서 배치를 가져와 처리

        Returns:
            처리 결과 리스트
        """
        try:
            # 1. 큐에서 배치 가져오기
            batch = await self.queue_service.dequeue_batch()

            if not batch:
                self.logger.debug("처리할 배치가 없음")
                return []

            self.logger.info(f"배치 처리 시작 - 크기: {len(batch)}")

            # 2. 배치 내 각 메일 처리
            results = []
            for item in batch:
                result = await self._process_single_mail(item)
                results.append(result)

            # 3. 처리 결과 통계
            success_count = sum(1 for r in results if r.success)
            self.logger.info(
                f"배치 처리 완료 - "
                f"전체: {len(results)}, "
                f"성공: {success_count}, "
                f"실패: {len(results) - success_count}"
            )

            return results

        except Exception as e:
            self.logger.error(f"배치 처리 중 오류 발생: {str(e)}")
            raise

    async def _process_single_mail(
        self, queue_item: Dict[str, Any]
    ) -> MailProcessingResult:
        """
        단일 메일 처리

        Args:
            queue_item: 큐 아이템

        Returns:
            처리 결과
        """
        mail_data = queue_item["mail"]
        account_id = queue_item["account_id"]
        cleaned_content = queue_item["cleaned_content"]

        try:
            # 1. 필터링
            if self.filtering_service.is_enabled():
                filter_result = await self.filtering_service.filter_mail(
                    {"mail": mail_data, "cleaned_content": cleaned_content}
                )

                if filter_result["filtered"]:
                    self.logger.info(
                        f"메일 필터링됨 - ID: {mail_data['id']}, "
                        f"이유: {filter_result['reason']}"
                    )
                    return MailProcessingResult(
                        success=True,
                        mail_id=mail_data["id"],
                        account_id=account_id,
                        filtered=True,
                        filter_reason=filter_result["reason"],
                    )

            # 2. 메일 처리
            processing_result = await self.processing_service.process_mail(
                account_id=account_id,
                mail_data=mail_data,
                cleaned_content=cleaned_content,
            )

            # 3. DB 저장
            if processing_result.success:
                await self.db_service.save_processed_mail(
                    processing_result.processed_data
                )

            return processing_result

        except Exception as e:
            self.logger.error(
                f"메일 처리 실패 - ID: {mail_data.get('id', 'unknown')}, "
                f"error: {str(e)}"
            )
            return MailProcessingResult(
                success=False,
                mail_id=mail_data.get("id", "unknown"),
                account_id=account_id,
                error=str(e),
            )

    async def start_background_processor(self):
        """백그라운드 큐 처리 시작"""
        if self._background_task and not self._background_task.done():
            self.logger.warning("백그라운드 프로세서가 이미 실행 중")
            return

        self._should_stop = False
        self._background_task = asyncio.create_task(self._background_processor())
        self.logger.info("백그라운드 큐 프로세서 시작됨")

    async def stop_background_processor(self):
        """백그라운드 큐 처리 중지"""
        if not self._background_task:
            return

        self._should_stop = True

        try:
            await asyncio.wait_for(self._background_task, timeout=10.0)
        except asyncio.TimeoutError:
            self.logger.warning("백그라운드 프로세서 종료 타임아웃")
            self._background_task.cancel()

        self._background_task = None
        self.logger.info("백그라운드 큐 프로세서 중지됨")

    async def _background_processor(self):
        """백그라운드 큐 처리 루프"""
        self.logger.info("큐 프로세서 시작")

        while not self._should_stop:
            try:
                # 큐 상태 확인
                status = await self.queue_service.get_queue_status()

                if status["is_empty"]:
                    # 큐가 비어있으면 잠시 대기
                    await asyncio.sleep(5)
                    continue

                # 배치 처리
                await self.process_batch()

                # 처리 간격
                await asyncio.sleep(1)

            except Exception as e:
                self.logger.error(f"백그라운드 처리 중 오류: {str(e)}")
                await asyncio.sleep(5)

        self.logger.info("큐 프로세서 종료")

    async def get_processing_stats(self) -> Dict[str, Any]:
        """처리 통계 조회"""
        queue_status = await self.queue_service.get_queue_status()
        db_stats = await self.db_service.get_statistics()

        return {
            "queue": queue_status,
            "database": db_stats,
            "background_processor": {
                "running": self._background_task is not None
                and not self._background_task.done()
            },
        }

    async def cleanup(self):
        """리소스 정리"""
        await self.stop_background_processor()
        self.logger.info("리소스 정리 완료")

    async def __aenter__(self):
        """컨텍스트 매니저 진입"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        await self.cleanup()
