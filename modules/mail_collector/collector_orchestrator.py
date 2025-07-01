from typing import Dict, Any, List, Optional
from datetime import datetime

from infra.core import get_logger
from .collector_service import MailCollectorService
from .collector_repository import MailCollectorRepository
from .collector_schema import (
    CollectionRequest, CollectionResult, CollectionStats,
    AccountProgress, CollectionType
)

logger = get_logger(__name__)


class MailCollectorOrchestrator:
    """메일 수집 플로우 제어"""
    
    def __init__(self):
        self.repository = MailCollectorRepository()
        self.service = MailCollectorService()
        logger.info("MailCollectorOrchestrator 초기화")
    
    async def collect_single_account(
        self,
        account_id: str,
        collection_type: CollectionType = CollectionType.INCREMENTAL
    ) -> CollectionResult:
        """
        단일 계정 수집
        
        플로우:
        1. 계정 검증
        2. 수집 실행
        3. 결과 반환
        """
        # 1. 계정 존재 확인
        account = self.repository.get_account(account_id)
        if not account:
            return CollectionResult(
                account_id=account_id,
                collection_type=collection_type,
                success=False,
                error_message="계정을 찾을 수 없습니다"
            )
        
        # 2. 수집 실행
        if collection_type == CollectionType.INCREMENTAL:
            result = await self.service.collect_incremental(account)
        else:
            result = await self.service.collect_backfill(account)
        
        # 3. 결과 저장
        self.repository.save_collection_result(result)
        
        return result
    
    async def collect_multiple_accounts(
        self,
        request: CollectionRequest
    ) -> Dict[str, Any]:
        """
        다중 계정 수집
        
        플로우:
        1. 대상 계정 선정
        2. 병렬 수집
        3. 결과 집계
        """
        # 1. 대상 계정 결정
        if request.account_ids:
            accounts = [
                self.repository.get_account(aid) 
                for aid in request.account_ids
            ]
            accounts = [a for a in accounts if a]  # None 제거
        else:
            # 전체 활성 계정
            if request.collection_type == CollectionType.INCREMENTAL:
                accounts = self.repository.get_accounts_for_incremental()
            else:
                accounts = self.repository.get_accounts_for_backfill()
        
        # 2. 수집 실행
        results = []
        for account in accounts[:request.max_accounts]:
            try:
                if request.collection_type == CollectionType.INCREMENTAL:
                    result = await self.service.collect_incremental(account)
                else:
                    result = await self.service.collect_backfill(account)
                
                results.append(result)
                self.repository.save_collection_result(result)
                
            except Exception as e:
                logger.error(f"수집 실패: {account['user_id']}, {str(e)}")
                results.append(CollectionResult(
                    account_id=account['user_id'],
                    collection_type=request.collection_type,
                    success=False,
                    error_message=str(e)
                ))
        
        # 3. 결과 요약
        return {
            "total": len(results),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "results": [r.model_dump() for r in results]
        }
    
    def get_account_progress(self, account_id: str) -> Optional[AccountProgress]:
        """계정 진행상황 조회"""
        account = self.repository.get_account(account_id)
        if not account:
            return None
        
        stats = self.repository.get_account_statistics(account['id'])
        return AccountProgress(
            account_id=account_id,
            last_sync_time=account.get('last_sync_time'),
            backfill_status=account.get('backfill_status'),
            backfill_completed_until=account.get('backfill_completed_until'),
            total_mails=stats['total_mails'],
            oldest_mail_date=stats['oldest_mail'],
            newest_mail_date=stats['newest_mail']
        )
    
    def get_collection_statistics(self) -> CollectionStats:
        """전체 통계 조회"""
        stats = self.repository.get_overall_statistics()
        return CollectionStats(**stats)