"""
Mail Processor 오케스트레이터
mail_query로부터 받은 메일을 처리하는 메인 오케스트레이션 로직
modules/mail_process/mail_processor_orchestrator.py
"""

import time
from datetime import datetime
from typing import Dict, Optional

from infra.core.logger import get_logger
from modules.mail_query import (
    MailQueryOrchestrator,
    MailQueryRequest,
    MailQueryFilters,
    PaginationOptions,
)
from .mail_processor_schema import MailProcessingResult
from .services.db_service import MailDatabaseService
from .services.batch_processor import MailBatchProcessor
from .services.filtering_service import FilteringService
from .services.statistics_service import StatisticsService
from .services.batch_processor import MailBatchProcessor

logger = get_logger(__name__)


class MailProcessorOrchestrator:
    """메일 처리 오케스트레이터 - 순수한 조정 로직만 포함"""

    def __init__(self):
        self.logger = get_logger(__name__)

        # 서비스 초기화
        self.db_service = MailDatabaseService()
        self.batch_processor = MailBatchProcessor()
        self.filtering_service = FilteringService()
        self.statistics_service = StatisticsService()

        # Mail Query 오케스트레이터
        self.mail_query_orchestrator = None

    async def __aenter__(self):
        """컨텍스트 매니저 진입"""
        self.mail_query_orchestrator = MailQueryOrchestrator()
        await self.mail_query_orchestrator.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        if self.mail_query_orchestrator:
            await self.mail_query_orchestrator.__aexit__(exc_type, exc_val, exc_tb)

    async def process_user_mails(
        self,
        user_id: str,
        filters: Optional[MailQueryFilters] = None,
        pagination: Optional[PaginationOptions] = None,
    ) -> MailProcessingResult:
        """
        특정 사용자의 메일을 조회하고 처리

        Args:
            user_id: 사용자 ID
            filters: 메일 필터 조건
            pagination: 페이징 옵션

        Returns:
            MailProcessingResult: 처리 결과
        """
        start_time = time.time()

        try:
            # 1. Mail Query 모듈을 통해 메일 조회
            mail_response = await self._fetch_mails(user_id, filters, pagination)

            # 2. 필터링 적용
            filtered_mails = await self.filtering_service.filter_mails(
                mail_response.messages
            )

            # 3. 메일 배치 처리
            processing_stats = await self.batch_processor.process_mail_batch(
                user_id, filtered_mails
            )

            # 4. 처리 결과 생성
            result = self.statistics_service.create_processing_result(
                account_id=user_id,
                total_fetched=mail_response.total_fetched,
                filtered_count=len(filtered_mails),
                processing_stats=processing_stats,
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

            # 5. 통계 업데이트
            await self.statistics_service.update_processing_stats(result)

            # 6. 동기화 시간 업데이트
            self.db_service.update_account_sync_time(user_id, datetime.now())

            logger.info(
                f"메일 처리 완료 - user_id: {user_id}, "
                f"총 {result.total_fetched}개 중 {result.processed_count}개 처리, "
                f"{result.duplicate_count}개 중복, "
                f"실행시간: {result.execution_time_ms}ms"
            )

            return result

        except Exception as e:
            logger.error(
                f"메일 처리 중 오류 발생 - user_id: {user_id}, error: {str(e)}"
            )
            raise

    async def process_all_active_accounts(self) -> Dict[str, MailProcessingResult]:
        """
        모든 활성 계정의 메일을 처리

        Returns:
            계정별 처리 결과
        """
        logger.info("전체 활성 계정 메일 처리 시작")

        # 활성 계정 목록 조회
        active_accounts = self.db_service.get_active_accounts()
        results = {}

        for account in active_accounts:
            try:
                user_id = account["user_id"]
                logger.info(f"계정 처리 시작: {user_id}")

                # 마지막 동기화 시간 기반 필터 생성
                filters = self._create_sync_filters(account.get("last_sync_time"))

                # 메일 처리
                result = await self.process_user_mails(user_id, filters)
                results[user_id] = result

            except Exception as e:
                logger.error(f"계정 처리 실패 - user_id: {user_id}, error: {str(e)}")
                self.db_service.record_account_error(user_id, str(e))
                continue

        logger.info(f"전체 계정 처리 완료 - 처리된 계정 수: {len(results)}")
        return results

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
