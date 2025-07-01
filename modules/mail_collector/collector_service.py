"""
Mail Collector 서비스
실제 메일 수집 로직 구현
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from infra.core import get_logger, get_database_manager, get_config
from infra.core.exceptions import AuthenticationError, APIConnectionError
from modules.mail_query import MailQueryOrchestrator, MailQueryRequest, MailQueryFilters
from modules.mail_process import MailProcessorOrchestrator
from .collector_schema import (
    CollectionType, BackfillStatus, CollectionResult, 
    CollectionProgress
)

logger = get_logger(__name__)


class MailCollectorService:
    """메일 수집 서비스"""
    
    def __init__(self):
        self.config = get_config()
        self.db = get_database_manager()
        self.mail_query = MailQueryOrchestrator()
        self.mail_processor = MailProcessorOrchestrator()
        
        # 설정값
        self.backfill_chunk_months = int(
            self.config.get_setting("BACKFILL_CHUNK_MONTHS", "3")
        )
        self.max_backfill_months = int(
            self.config.get_setting("MAX_BACKFILL_MONTHS", "24")
        )
        self.default_lookback_days = 7  # 첫 증분 수집 시 기본 조회 기간
    
    async def collect_incremental(self, account_id: str) -> CollectionResult:
        """증분 수집 - 마지막 동기화 이후 새 메일"""
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"증분 수집 시작: account_id={account_id}")
            
            # 1. 계정 정보 및 마지막 동기화 시간 조회
            account = self._get_account_info(account_id)
            if not account:
                raise ValueError(f"계정을 찾을 수 없습니다: {account_id}")
            
            if not account['is_active']:
                logger.warning(f"비활성 계정 스킵: {account_id}")
                return self._create_result(
                    account_id, CollectionType.INCREMENTAL,
                    success=False, error_message="계정이 비활성 상태입니다",
                    start_time=start_time
                )
            
            # 2. 수집 범위 결정
            last_sync = account.get('last_sync_time')
            if last_sync:
                if isinstance(last_sync, str):
                    last_sync = datetime.fromisoformat(last_sync)
                date_from = last_sync
            else:
                # 첫 수집인 경우 기본 7일 전부터
                date_from = datetime.utcnow() - timedelta(days=self.default_lookback_days)
            
            date_to = datetime.utcnow()
            
            logger.info(f"증분 수집 범위: {date_from} ~ {date_to}")
            
            # 3. Mail Query를 통해 메일 조회
            filters = MailQueryFilters(
                date_from=date_from,
                date_to=date_to
            )
            
            request = MailQueryRequest(
                user_id=account_id,
                filters=filters
            )
            
            response = await self.mail_query.mail_query_user_emails(request)
            
            if not response.messages:
                logger.info(f"새 메일 없음: account_id={account_id}")
                # last_sync_time만 업데이트
                self._update_last_sync_time(account_id, date_to)
                return self._create_result(
                    account_id, CollectionType.INCREMENTAL,
                    success=True, mails_collected=0,
                    start_time=start_time, date_from=date_from, date_to=date_to
                )
            
            # 4. Mail Processor로 처리
            mail_dicts = [msg.model_dump() for msg in response.messages]
            process_result = await self.mail_processor.process_mails(
                account_id=account_id,
                mails=mail_dicts
            )
            
            # 5. 마지막 동기화 시간 업데이트
            self._update_last_sync_time(account_id, date_to)
            
            logger.info(
                f"증분 수집 완료: account_id={account_id}, "
                f"수집={process_result.get('saved_mails', 0)}, "
                f"중복={process_result.get('duplicate_mails', 0)}"
            )
            
            return self._create_result(
                account_id, CollectionType.INCREMENTAL,
                success=True,
                mails_collected=process_result.get('saved_mails', 0),
                duplicates_skipped=process_result.get('duplicate_mails', 0),
                start_time=start_time,
                date_from=date_from,
                date_to=date_to
            )
            
        except Exception as e:
            logger.error(f"증분 수집 실패: account_id={account_id}, error={str(e)}")
            return self._create_result(
                account_id, CollectionType.INCREMENTAL,
                success=False,
                error_message=str(e),
                start_time=start_time
            )
    
    async def collect_backfill(self, account_id: str) -> CollectionResult:
        """백필 수집 - 과거 데이터를 3개월 단위로 수집"""
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"백필 수집 시작: account_id={account_id}")
            
            # 1. 계정 정보 및 백필 상태 조회
            account = self._get_account_backfill_status(account_id)
            if not account:
                raise ValueError(f"계정을 찾을 수 없습니다: {account_id}")
            
            # 백필 완료 여부 확인
            if account['backfill_status'] == 'COMPLETED':
                logger.info(f"백필 이미 완료됨: account_id={account_id}")
                return self._create_result(
                    account_id, CollectionType.BACKFILL,
                    success=True,
                    error_message="백필이 이미 완료되었습니다",
                    start_time=start_time
                )
            
            # 2. 백필 범위 계산
            if account['backfill_completed_until']:
                # 이전에 백필한 날짜가 있으면 그 이전부터
                if isinstance(account['backfill_completed_until'], str):
                    end_date = datetime.fromisoformat(account['backfill_completed_until'])
                else:
                    end_date = account['backfill_completed_until']
            else:
                # 첫 백필이면 현재 시점부터
                end_date = datetime.utcnow()
            
            # 3개월 전 계산
            start_date = end_date - timedelta(days=self.backfill_chunk_months * 30)
            
            # 최대 백필 기간 체크
            max_backfill_date = datetime.utcnow() - timedelta(days=self.max_backfill_months * 30)
            if start_date < max_backfill_date:
                start_date = max_backfill_date
                # 백필 완료로 표시
                self._update_backfill_status(account_id, BackfillStatus.COMPLETED, start_date)
                logger.info(f"백필 완료: account_id={account_id}, 최종 날짜={start_date}")
            
            logger.info(f"백필 수집 범위: {start_date} ~ {end_date}")
            
            # 3. Mail Query를 통해 메일 조회
            filters = MailQueryFilters(
                date_from=start_date,
                date_to=end_date
            )
            
            request = MailQueryRequest(
                user_id=account_id,
                filters=filters
            )
            
            response = await self.mail_query.mail_query_user_emails(request)
            
            if not response.messages:
                logger.info(f"백필 메일 없음: account_id={account_id}, 기간={start_date}~{end_date}")
                # 백필 진행 상황 업데이트
                self._update_backfill_status(account_id, BackfillStatus.IN_PROGRESS, start_date)
                return self._create_result(
                    account_id, CollectionType.BACKFILL,
                    success=True, mails_collected=0,
                    start_time=start_time, date_from=start_date, date_to=end_date
                )
            
            # 4. Mail Processor로 처리
            mail_dicts = [msg.model_dump() for msg in response.messages]
            process_result = await self.mail_processor.process_mails(
                account_id=account_id,
                mails=mail_dicts
            )
            
            # 5. 백필 진행 상황 업데이트
            self._update_backfill_status(account_id, BackfillStatus.IN_PROGRESS, start_date)
            
            logger.info(
                f"백필 수집 완료: account_id={account_id}, "
                f"기간={start_date}~{end_date}, "
                f"수집={process_result.get('saved_mails', 0)}, "
                f"중복={process_result.get('duplicate_mails', 0)}"
            )
            
            return self._create_result(
                account_id, CollectionType.BACKFILL,
                success=True,
                mails_collected=process_result.get('saved_mails', 0),
                duplicates_skipped=process_result.get('duplicate_mails', 0),
                start_time=start_time,
                date_from=start_date,
                date_to=end_date
            )
            
        except Exception as e:
            logger.error(f"백필 수집 실패: account_id={account_id}, error={str(e)}")
            return self._create_result(
                account_id, CollectionType.BACKFILL,
                success=False,
                error_message=str(e),
                start_time=start_time
            )
    
    def get_collection_progress(self, account_id: str) -> CollectionProgress:
        """계정의 수집 진행 상황 조회"""
        try:
            # 계정 정보 및 통계 조회
            result = self.db.fetch_one("""
                SELECT 
                    a.user_id,
                    a.status,
                    a.last_sync_time,
                    a.backfill_status,
                    a.backfill_completed_until,
                    a.collection_enabled,
                    COUNT(mh.id) as total_mails,
                    MIN(mh.received_time) as oldest_mail,
                    MAX(mh.received_time) as newest_mail,
                    (SELECT COUNT(*) FROM mail_history 
                     WHERE account_id = a.id 
                     AND DATE(processed_at) = DATE('now')) as today_collected
                FROM accounts a
                LEFT JOIN mail_history mh ON mh.account_id = a.id
                WHERE a.user_id = ?
                GROUP BY a.id
            """, (account_id,))
            
            if not result:
                raise ValueError(f"계정을 찾을 수 없습니다: {account_id}")
            
            # 백필 진행률 계산
            backfill_progress = 0.0
            if result['backfill_status'] == 'COMPLETED':
                backfill_progress = 100.0
            elif result['backfill_completed_until']:
                completed_until = datetime.fromisoformat(result['backfill_completed_until'])
                total_days = self.max_backfill_months * 30
                completed_days = (datetime.utcnow() - completed_until).days
                backfill_progress = min((completed_days / total_days) * 100, 100.0)
            
            return CollectionProgress(
                account_id=account_id,
                collection_type=CollectionType.INCREMENTAL,  # 기본값
                last_sync_time=result['last_sync_time'],
                incremental_mails_collected=result['today_collected'] or 0,
                backfill_status=result['backfill_status'],
                backfill_completed_until=result['backfill_completed_until'],
                backfill_progress_percentage=backfill_progress,
                total_mails_in_db=result['total_mails'] or 0,
                oldest_mail_date=result['oldest_mail'],
                newest_mail_date=result['newest_mail'],
                is_running=False,  # TODO: 실시간 상태 추적 구현
                updated_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"진행 상황 조회 실패: account_id={account_id}, error={str(e)}")
            raise
    
    def _get_account_info(self, account_id: str) -> Optional[Dict[str, Any]]:
        """계정 정보 조회"""
        return self.db.fetch_one(
            "SELECT * FROM accounts WHERE user_id = ?",
            (account_id,)
        )
    
    def _get_account_backfill_status(self, account_id: str) -> Optional[Dict[str, Any]]:
        """계정의 백필 상태 조회"""
        return self.db.fetch_one(
            """SELECT user_id, backfill_status, backfill_completed_until, is_active 
               FROM accounts WHERE user_id = ?""",
            (account_id,)
        )
    
    def _update_last_sync_time(self, account_id: str, sync_time: datetime):
        """마지막 동기화 시간 업데이트"""
        self.db.update(
            "accounts",
            {
                "last_sync_time": sync_time.isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            },
            "user_id = ?",
            (account_id,)
        )
    
    def _update_backfill_status(
        self, 
        account_id: str, 
        status: BackfillStatus, 
        completed_until: datetime
    ):
        """백필 상태 업데이트"""
        self.db.update(
            "accounts",
            {
                "backfill_status": status.value,
                "backfill_completed_until": completed_until.isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            },
            "user_id = ?",
            (account_id,)
        )
    
    def _create_result(
        self,
        account_id: str,
        collection_type: CollectionType,
        success: bool,
        mails_collected: int = 0,
        duplicates_skipped: int = 0,
        error_message: Optional[str] = None,
        start_time: Optional[datetime] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> CollectionResult:
        """수집 결과 생성"""
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds() if start_time else 0
        
        return CollectionResult(
            account_id=account_id,
            collection_type=collection_type,
            success=success,
            mails_collected=mails_collected,
            duplicates_skipped=duplicates_skipped,
            start_time=start_time or end_time,
            end_time=end_time,
            duration_seconds=duration,
            date_from=date_from,
            date_to=date_to,
            error_message=error_message
        )