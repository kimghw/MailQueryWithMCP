"""
메일 처리 오케스트레이터 - 단순화된 플로우
modules/mail_process/mail_orchestrator.py
"""

import os
from typing import Any, Dict, List, Optional
from datetime import datetime

from infra.core.logger import get_logger
from infra.core.config import get_config

from .mail_processor_schema import MailProcessingResult
from .services.filtering_service import FilteringService
from .services.persistence_service import PersistenceService
from .services.processing_service import ProcessingService
from .services.statistics_service import StatisticsService
from .services.phase_processor import PhaseProcessor
from .utilities.iacs.iacs_code_parser import IACSCodeParser

logger = get_logger(__name__)


class MailProcessingOrchestrator:
    """메일 처리 흐름 관리 오케스트레이터 - 단순화된 플로우"""

    def __init__(
        self,
        filtering_service: Optional[FilteringService] = None,
        processing_service: Optional[ProcessingService] = None,
        persistence_service: Optional[PersistenceService] = None,
        statistics_service: Optional[StatisticsService] = None,
    ):
        self.logger = get_logger(__name__)
        self.config = get_config()

        # 환경변수 검증
        self._validate_configuration()

        # 서비스 초기화
        self.filtering_service = filtering_service or FilteringService()
        self.processing_service = processing_service or ProcessingService()
        self.persistence_service = persistence_service or PersistenceService()
        self.statistics_service = statistics_service or StatisticsService()

        # 통합 IACS 파서 초기화
        self.iacs_parser = IACSCodeParser()

        # Phase 프로세서 초기화
        self.phase_processor = PhaseProcessor(self)

        # 설정값 로드
        self.max_mails_per_account = int(os.getenv("MAX_MAILS_PER_ACCOUNT", "200"))
        self.enable_dashboard_events = (
            os.getenv("ENABLE_DASHBOARD_EVENTS", "true").lower() == "true"
        )

        self.logger.info(
            f"메일 처리 오케스트레이터 초기화 완료 "
            f"(최대 처리: {self.max_mails_per_account})"
        )

    def _validate_configuration(self):
        """환경설정 검증"""
        required_configs = [
            ("ENABLE_MAIL_FILTERING", "true"),
            ("ENABLE_MAIL_DUPLICATE_CHECK", "true"),
            ("ENABLE_BATCH_KEYWORD_EXTRACTION", "true"),
            ("ENABLE_MAIL_HISTORY", "true"),
            ("MAX_KEYWORDS_PER_MAIL", "5"),
            ("MIN_MAIL_CONTENT_LENGTH", "10"),
        ]

        for config_name, default_value in required_configs:
            value = os.getenv(config_name)
            if value is None:
                self.logger.warning(
                    f"환경변수 누락: {config_name}, 기본값 사용: {default_value}"
                )
                os.environ[config_name] = default_value

    async def process_mails(
        self, account_id: str, mails: List[Dict], publish_batch_event: bool = True
    ) -> MailProcessingResult:
        """메일 처리 메인 플로우 - 단순화된 버전"""
        start_time = datetime.now()
        self.logger.info(f"메일 처리 시작: account_id={account_id}, count={len(mails)}")

        # 처리 제한
        if len(mails) > self.max_mails_per_account:
            self.logger.warning(
                f"처리 제한 적용: {len(mails)} -> {self.max_mails_per_account}"
            )
            mails = mails[: self.max_mails_per_account]

        try:
            # 1. 필터링
            filtered = await self.phase_processor.filter_mails(mails)

            # 2. 중복 체크
            new_mails, duplicate_mails = await self.phase_processor.check_duplicates(
                account_id, filtered
            )

            # 3. 데이터 추출 (IACS + OpenRouter)
            enriched = await self.phase_processor.enrich_mails(account_id, new_mails)

            # 4. 저장 및 이벤트
            results = await self.phase_processor.persist_and_publish(
                account_id, enriched
            )

            # 5. 통계 생성
            execution_time_ms = int(
                (datetime.now() - start_time).total_seconds() * 1000
            )

            return await self.phase_processor.create_result(
                account_id=account_id,
                total_count=len(mails),
                filtered_count=len(filtered),
                new_count=len(new_mails),
                duplicate_count=len(duplicate_mails),
                saved_results=results,
                execution_time_ms=execution_time_ms,
                publish_batch_event=publish_batch_event,
                processed_mails=enriched,
            )

        except Exception as e:
            self.logger.error(f"메일 처리 중 예외 발생: {str(e)}", exc_info=True)

            # 부분 실패 결과 반환
            execution_time_ms = int(
                (datetime.now() - start_time).total_seconds() * 1000
            )
            return MailProcessingResult(
                account_id=account_id,
                total_fetched=len(mails),
                filtered_count=0,
                new_count=0,
                duplicate_count=0,
                processed_count=0,
                saved_count=0,
                failed_count=len(mails),
                skipped_count=0,
                events_published=0,
                last_sync_time=datetime.now(),
                execution_time_ms=execution_time_ms,
                success_rate=0.0,
                duplication_rate=0.0,
                processing_efficiency=0.0,
                errors=[str(e)],
                warnings=[],
            )

    async def __aenter__(self):
        """컨텍스트 매니저 진입"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        await self.close()

    async def close(self):
        """리소스 정리"""
        try:
            if self.processing_service:
                await self.processing_service.close()
        except Exception as e:
            self.logger.error(f"리소스 정리 중 오류: {str(e)}")

    def set_chair_emails(self, emails: List[str]):
        """Chair 이메일 주소 설정"""
        self.iacs_parser.set_chair_emails(emails)
        self.logger.info(f"Chair 이메일 {len(emails)}개 설정됨")

    def set_member_emails(self, organization: str, emails: List[str]):
        """특정 조직의 멤버 이메일 주소 설정"""
        self.iacs_parser.set_member_emails(organization, emails)
        self.logger.info(f"{organization} 멤버 이메일 {len(emails)}개 설정됨")

    def get_processing_statistics(self) -> Dict[str, Any]:
        """현재 처리 통계 반환"""
        return {
            "filtering_stats": self.filtering_service.get_filter_stats(),
            "duplicate_check_enabled": self.persistence_service.get_duplicate_check_status(),
            "max_mails_per_account": self.max_mails_per_account,
            "dashboard_events_enabled": self.enable_dashboard_events,
        }
