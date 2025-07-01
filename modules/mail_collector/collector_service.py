from datetime import datetime, timedelta
from typing import Dict, Any

from infra.core import get_logger, get_config
from modules.mail_query import MailQueryOrchestrator, MailQueryRequest, MailQueryFilters
from modules.mail_process import MailProcessorOrchestrator
from .collector_schema import CollectionResult, CollectionType, BackfillStatus
from .collector_repository import MailCollectorRepository

logger = get_logger(__name__)


class MailCollectorService:
    """메일 수집 비즈니스 로직"""
    
    def __init__(self):
        self.config = get_config()
        self.repository = MailCollectorRepository()
        self.mail_query = MailQueryOrchestrator()
        self.mail_processor = MailProcessorOrchestrator()
        
        # 설정
        self.default_lookback_days = 7
        self.backfill_chunk_months = 3
        self.max_backfill_months = 24
    
    async def collect_incremental(self, account: Dict[str, Any]) -> CollectionResult:
        """증분 수집"""
        account_id = account['user_id']
        start_time = datetime.utcnow()
        
        try:
            # 1. 수집 범위 결정
            last_sync = account.get('last_sync_time')
            if isinstance(last_sync, str):
                last_sync = datetime.fromisoformat(last_sync)
            
            date_from = last_sync or (datetime.utcnow() - timedelta(days=self.default_lookback_days))
            date_to = datetime.utcnow()
            
            # 2. 메일 조회
            query_request = MailQueryRequest(
                user_id=account_id,
                filters=MailQueryFilters(
                    date_from=date_from,
                    date_to=date_to
                )
            )
            
            response = await self.mail_query.mail_query_user_emails(query_request)
            
            # 3. 메일 처리
            if response.messages:
                mail_dicts = [msg.model_dump() for msg in response.messages]
                process_result = await self.mail_processor.process_mails(
                    account_id=account_id,
                    mails=mail_dicts
                )
                mails_collected = process_result.get('saved_mails', 0)
                duplicates = process_result.get('duplicate_mails', 0)
            else:
                mails_collected = 0
                duplicates = 0
            
            # 4. 상태 업데이트
            self.repository.update_last_sync_time(account_id, date_to)
            
            return CollectionResult(
                account_id=account_id,
                collection_type=CollectionType.INCREMENTAL,
                success=True,
                mails_collected=mails_collected,
                duplicates_skipped=duplicates,
                start_time=start_time,
                end_time=datetime.utcnow(),
                date_from=date_from,
                date_to=date_to
            )
            
        except Exception as e:
            logger.error(f"증분 수집 실패: {account_id}, {str(e)}")
            return CollectionResult(
                account_id=account_id,
                collection_type=CollectionType.INCREMENTAL,
                success=False,
                error_message=str(e),
                start_time=start_time,
                end_time=datetime.utcnow()
            )
    
    async def collect_backfill(self, account: Dict[str, Any]) -> CollectionResult:
        """백필 수집"""
        account_id = account['user_id']
        start_time = datetime.utcnow()
        
        try:
            # 1. 백필 완료 확인
            if account.get('backfill_status') == BackfillStatus.COMPLETED.value:
                return CollectionResult(
                    account_id=account_id,
                    collection_type=CollectionType.BACKFILL,
                    success=True,
                    mails_collected=0,
                    error_message="백필 이미 완료됨",
                    start_time=start_time,
                    end_time=datetime.utcnow()
                )
            
            # 2. 백필 범위 계산
            completed_until = account.get('backfill_completed_until')
            if isinstance(completed_until, str):
                completed_until = datetime.fromisoformat(completed_until)
            
            end_date = completed_until or datetime.utcnow()
            start_date = end_date - timedelta(days=self.backfill_chunk_months * 30)
            
            # 최대 백필 기간 체크
            max_date = datetime.utcnow() - timedelta(days=self.max_backfill_months * 30)
            if start_date < max_date:
                start_date = max_date
                is_completed = True
            else:
                is_completed = False
            
            # 3. 메일 조회
            query_request = MailQueryRequest(
                user_id=account_id,
                filters=MailQueryFilters(
                    date_from=start_date,
                    date_to=end_date
                )
            )
            
            response = await self.mail_query.mail_query_user_emails(query_request)
            
            # 4. 메일 처리
            if response.messages:
                mail_dicts = [msg.model_dump() for msg in response.messages]
                process_result = await self.mail_processor.process_mails(
                    account_id=account_id,
                    mails=mail_dicts
                )
                mails_collected = process_result.get('saved_mails', 0)
                duplicates = process_result.get('duplicate_mails', 0)
            else:
                mails_collected = 0
                duplicates = 0
            
            # 5. 백필 상태 업데이트
            status = BackfillStatus.COMPLETED if is_completed else BackfillStatus.IN_PROGRESS
            self.repository.update_backfill_status(account_id, status, start_date)
            
            return CollectionResult(
                account_id=account_id,
                collection_type=CollectionType.BACKFILL,
                success=True,
                mails_collected=mails_collected,
                duplicates_skipped=duplicates,
                start_time=start_time,
                end_time=datetime.utcnow(),
                date_from=start_date,
                date_to=end_date
            )
            
        except Exception as e:
            logger.error(f"백필 수집 실패: {account_id}, {str(e)}")
            return CollectionResult(
                account_id=account_id,
                collection_type=CollectionType.BACKFILL,
                success=False,
                error_message=str(e),
                start_time=start_time,
                end_time=datetime.utcnow()
            )
