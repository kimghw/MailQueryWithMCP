"""통계 서비스 - 처리 통계 관리 및 기록 (중복 체크 개선)"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import uuid
from infra.core.logger import get_logger
from infra.core.database import get_database_manager
from infra.core.kafka_client import get_kafka_client

logger = get_logger(__name__)


class StatisticsService:
    """통계 관리 서비스"""

    def __init__(self):
        self.db = get_database_manager()
        self.kafka = get_kafka_client()
        self.logger = get_logger(__name__)
        self._current_stats = {}  # 현재 처리 통계
        self._collected_keywords = []  # 수집된 키워드

    async def record_statistics(
        self,
        account_id: str,
        total_count: int,
        filtered_count: int,
        new_count: int,
        duplicate_count: int,
        saved_results: Dict,
        publish_batch_event: bool,
        processed_mails: List[Dict] = None,
    ) -> Dict:
        """통계 기록 및 반환 (중복 정보 포함)"""

        # 키워드 수집 (신규 처리된 메일에서만)
        keywords = []
        if processed_mails:
            for mail in processed_mails:
                if "_processed" in mail and "keywords" in mail["_processed"]:
                    keywords.extend(mail["_processed"]["keywords"])

        # 통계 계산
        statistics = {
            "account_id": account_id,
            "total_mails": total_count,
            "filtered_mails": filtered_count,
            "new_mails": new_count,
            "duplicate_mails": duplicate_count,
            "processed_mails": len(processed_mails) if processed_mails else 0,
            "saved_mails": saved_results.get("saved", 0),
            "events_published": saved_results.get("events_published", 0),
            "skipped_mails": total_count - filtered_count,
            "db_errors": saved_results.get("failed", 0),
            "event_errors": 0,  # 이벤트 에러는 별도로 추적 필요시 구현
            "success_rate": self._calculate_success_rate(
                saved_results.get("saved", 0), new_count  # 신규 메일 대비 성공률
            ),
            "duplication_rate": self._calculate_duplication_rate(
                duplicate_count, filtered_count  # 필터링된 메일 대비 중복률
            ),
            "keywords": keywords,
            "unique_keywords": list(set(keywords)),
            "keyword_count": len(keywords),
            "unique_keyword_count": len(set(keywords)),
            "duplicate_check_enabled": saved_results.get(
                "duplicate_check_enabled", True
            ),
            "processing_efficiency": self._calculate_efficiency(
                new_count,
                duplicate_count,
                len(processed_mails) if processed_mails else 0,
            ),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 현재 통계 저장
        self._current_stats = statistics
        self._collected_keywords = keywords

        # DB에 통계 기록
        self._record_to_db(account_id, statistics)

        # 배치 완료 이벤트 발행 (선택적)
        if publish_batch_event and total_count > 1:
            await self._publish_batch_complete_event(statistics)

        self.logger.info(
            f"통계 완료: account={account_id}, "
            f"total={total_count}, new={new_count}, "
            f"duplicate={duplicate_count}, saved={statistics['saved_mails']}, "
            f"keywords={statistics['unique_keyword_count']}, "
            f"efficiency={statistics['processing_efficiency']}%"
        )

        return statistics

    def _calculate_efficiency(
        self, new_count: int, duplicate_count: int, processed_count: int
    ) -> float:
        """처리 효율성 계산 (중복 체크로 인한 처리 절감률)"""
        if new_count + duplicate_count == 0:
            return 0.0

        # 중복 체크로 절감된 처리 비율
        saved_processing = duplicate_count
        total_potential = new_count + duplicate_count
        efficiency = (saved_processing / total_potential) * 100

        return round(efficiency, 2)

    def get_current_statistics(self) -> Dict:
        """현재 처리 중인 통계 반환 (부분 실패 시 사용)"""
        return self._current_stats.copy()

    def get_collected_keywords(self) -> List[str]:
        """수집된 키워드 반환"""
        return self._collected_keywords.copy()

    def _calculate_success_rate(self, saved: int, total: int) -> float:
        """성공률 계산"""
        if total == 0:
            return 0.0
        return round((saved / total) * 100, 2)

    def _calculate_duplication_rate(self, duplicates: int, total: int) -> float:
        """중복률 계산"""
        if total == 0:
            return 0.0
        return round((duplicates / total) * 100, 2)

    def _record_to_db(self, account_id: str, stats: Dict):
        """통계를 DB에 기록 (동기)"""
        try:
            # 통계 요약 생성
            summary = (
                f"Batch processed for {account_id}: "
                f"total={stats['total_mails']}, "
                f"new={stats['new_mails']}, "
                f"duplicates={stats['duplicate_mails']}, "
                f"saved={stats['saved_mails']}, "
                f"keywords={stats['unique_keyword_count']}, "
                f"efficiency={stats['processing_efficiency']}%, "
                f"success_rate={stats['success_rate']}%"
            )

            # processing_logs에 기록
            log_data = {
                "run_id": str(uuid.uuid4()),
                "account_id": self._get_account_db_id(account_id),
                "log_level": "INFO",
                "message": summary,
                "timestamp": datetime.utcnow(),
            }

            self.db.insert("processing_logs", log_data)

        except Exception as e:
            self.logger.error(f"통계 DB 기록 실패: {str(e)}")

    async def _publish_batch_complete_event(self, stats: Dict):
        """배치 완료 이벤트 발행"""
        try:
            event_data = {
                "event_type": "email.batch_processing_complete",
                "event_id": str(uuid.uuid4()),
                "account_id": stats["account_id"],
                "occurred_at": datetime.utcnow().isoformat(),
                "statistics": {
                    "total_count": stats["total_mails"],
                    "new_count": stats["new_mails"],
                    "duplicate_count": stats["duplicate_mails"],
                    "processed_count": stats["saved_mails"],
                    "skipped_count": stats["skipped_mails"],
                    "keyword_count": stats["unique_keyword_count"],
                    "success_rate": stats["success_rate"],
                    "duplication_rate": stats["duplication_rate"],
                    "processing_efficiency": stats["processing_efficiency"],
                },
                "keywords": stats["unique_keywords"][:20],  # 상위 20개 키워드만
            }

            self.kafka.produce_event(
                topic="email-processing-events",
                event_data=event_data,
                key=f"{stats['account_id']}_batch",
            )

            self.logger.debug("배치 완료 이벤트 발행됨")

        except Exception as e:
            self.logger.error(f"배치 완료 이벤트 발행 실패: {str(e)}")

    def _get_account_db_id(self, account_id: str) -> Optional[int]:
        """account_id로 DB의 실제 ID 조회"""
        try:
            account = self.db.fetch_one(
                "SELECT id FROM accounts WHERE user_id = ?", (account_id,)
            )
            return account["id"] if account else None
        except:
            return None

    async def get_processing_efficiency_report(
        self, account_id: str, days: int = 7
    ) -> Dict:
        """처리 효율성 리포트 생성"""
        try:
            db_id = self._get_account_db_id(account_id)
            if not db_id:
                return {}

            # 최근 처리 통계 조회
            query = """
                SELECT 
                    DATE(processed_at) as process_date,
                    COUNT(*) as mail_count,
                    COUNT(DISTINCT content_hash) as unique_content_count
                FROM mail_history
                WHERE account_id = ? 
                AND processed_at >= datetime('now', ? || ' days')
                GROUP BY DATE(processed_at)
                ORDER BY process_date DESC
            """

            results = self.db.fetch_all(query, (db_id, f"-{days}"))

            efficiency_data = []
            for row in results:
                duplicate_rate = 0
                if row["mail_count"] > 0:
                    duplicate_rate = (
                        (row["mail_count"] - row["unique_content_count"])
                        / row["mail_count"]
                    ) * 100

                efficiency_data.append(
                    {
                        "date": row["process_date"],
                        "total_mails": row["mail_count"],
                        "unique_mails": row["unique_content_count"],
                        "duplicate_rate": round(duplicate_rate, 2),
                    }
                )

            return {
                "account_id": account_id,
                "period_days": days,
                "efficiency_data": efficiency_data,
                "average_duplicate_rate": round(
                    (
                        sum(d["duplicate_rate"] for d in efficiency_data)
                        / len(efficiency_data)
                        if efficiency_data
                        else 0
                    ),
                    2,
                ),
            }

        except Exception as e:
            self.logger.error(f"효율성 리포트 생성 실패: {str(e)}")
            return {}
