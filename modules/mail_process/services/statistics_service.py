"""
메일 처리 통계 서비스
처리 결과 생성 및 통계 계산
modules/mail_process/services/statistics_service.py
"""

from datetime import datetime
from typing import Dict, Any

from infra.core.logger import get_logger
from modules.mail_process.mail_processor_schema import MailProcessingResult

logger = get_logger(__name__)


class StatisticsService:
    """메일 처리 통계 서비스"""

    def __init__(self):
        self.logger = get_logger(__name__)

    def create_processing_result(
        self,
        account_id: str,
        total_fetched: int,
        filtered_count: int,
        processing_stats: Dict[str, Any],
        execution_time_ms: int,
    ) -> MailProcessingResult:
        """
        처리 결과 객체 생성

        Args:
            account_id: 계정 ID
            total_fetched: 조회된 총 메일 수
            filtered_count: 필터링 후 메일 수
            processing_stats: 처리 통계
            execution_time_ms: 실행 시간(밀리초)

        Returns:
            MailProcessingResult 객체
        """
        return MailProcessingResult(
            account_id=account_id,
            total_fetched=total_fetched,
            filtered_count=filtered_count,
            new_count=processing_stats.get("new_count", 0),
            duplicate_count=processing_stats.get("duplicate_count", 0),
            processed_count=processing_stats.get("processed_count", 0),
            saved_count=processing_stats.get("saved_count", 0),
            failed_count=processing_stats.get("failed_count", 0),
            skipped_count=processing_stats.get("skipped_count", 0),
            events_published=processing_stats.get("events_published", 0),
            last_sync_time=datetime.now(),
            execution_time_ms=execution_time_ms,
            success_rate=self.calculate_success_rate(processing_stats),
            duplication_rate=self.calculate_duplication_rate(processing_stats),
            processing_efficiency=self.calculate_efficiency(processing_stats),
            errors=processing_stats.get("errors", []),
            warnings=processing_stats.get("warnings", []),
        )

    def calculate_success_rate(self, stats: Dict[str, Any]) -> float:
        """
        성공률 계산

        Args:
            stats: 처리 통계

        Returns:
            성공률 (%)
        """
        total = (
            stats.get("processed_count", 0)
            + stats.get("failed_count", 0)
            + stats.get("skipped_count", 0)
        )
        if total == 0:
            return 0.0
        return round((stats.get("processed_count", 0) / total) * 100, 2)

    def calculate_duplication_rate(self, stats: Dict[str, Any]) -> float:
        """
        중복률 계산

        Args:
            stats: 처리 통계

        Returns:
            중복률 (%)
        """
        total = stats.get("new_count", 0) + stats.get("duplicate_count", 0)
        if total == 0:
            return 0.0
        return round((stats.get("duplicate_count", 0) / total) * 100, 2)

    def calculate_efficiency(self, stats: Dict[str, Any]) -> float:
        """
        처리 효율성 계산 (저장 성공률)

        Args:
            stats: 처리 통계

        Returns:
            효율성 (%)
        """
        processed = stats.get("processed_count", 0)
        if processed == 0:
            return 0.0
        return round((stats.get("saved_count", 0) / processed) * 100, 2)

    async def update_processing_stats(self, result: MailProcessingResult) -> None:
        """
        처리 통계 업데이트 (향후 확장용)

        Args:
            result: 처리 결과
        """
        # 현재는 로깅만 수행
        self.logger.info(
            f"처리 통계 - "
            f"계정: {result.account_id}, "
            f"총 메일: {result.total_fetched}, "
            f"처리됨: {result.processed_count}, "
            f"저장됨: {result.saved_count}, "
            f"중복: {result.duplicate_count}, "
            f"성공률: {result.success_rate}%, "
            f"중복률: {result.duplication_rate}%, "
            f"효율성: {result.processing_efficiency}%"
        )

        # 향후 여기에 다음과 같은 기능 추가 가능:
        # - 통계 데이터베이스 저장
        # - 메트릭 수집 시스템 연동
        # - 알림 발송 (임계값 초과 시)
        # - 대시보드 업데이트

    def get_summary_stats(
        self, results: Dict[str, MailProcessingResult]
    ) -> Dict[str, Any]:
        """
        여러 계정의 처리 결과를 요약

        Args:
            results: 계정별 처리 결과

        Returns:
            요약 통계
        """
        total_accounts = len(results)
        total_mails = sum(r.total_fetched for r in results.values())
        total_processed = sum(r.processed_count for r in results.values())
        total_saved = sum(r.saved_count for r in results.values())
        total_duplicates = sum(r.duplicate_count for r in results.values())
        total_failed = sum(r.failed_count for r in results.values())
        total_events = sum(r.events_published for r in results.values())

        avg_success_rate = (
            sum(r.success_rate for r in results.values()) / total_accounts
            if total_accounts > 0
            else 0.0
        )

        avg_duplication_rate = (
            sum(r.duplication_rate for r in results.values()) / total_accounts
            if total_accounts > 0
            else 0.0
        )

        total_execution_time = sum(r.execution_time_ms for r in results.values())

        return {
            "total_accounts": total_accounts,
            "total_mails_fetched": total_mails,
            "total_mails_processed": total_processed,
            "total_mails_saved": total_saved,
            "total_duplicates": total_duplicates,
            "total_failed": total_failed,
            "total_events_published": total_events,
            "average_success_rate": round(avg_success_rate, 2),
            "average_duplication_rate": round(avg_duplication_rate, 2),
            "total_execution_time_ms": total_execution_time,
            "average_execution_time_ms": (
                round(total_execution_time / total_accounts)
                if total_accounts > 0
                else 0
            ),
        }
