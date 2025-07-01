"""
Mail Collector 오케스트레이터
메일 수집 전체 플로우 관리
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from infra.core import get_logger, get_database_manager
from .collector_service import MailCollectorService
from .collector_scheduler import MailCollectorScheduler
from .collector_schema import (
    CollectionRequest, CollectionResult, CollectionProgress,
    CollectionStats, AccountCollectionConfig
)

logger = get_logger(__name__)


class MailCollectorOrchestrator:
    """메일 수집 오케스트레이터"""
    
    def __init__(self):
        self.db = get_database_manager()
        self.service = MailCollectorService()
        self.scheduler = MailCollectorScheduler()
    
    async def start_collection(self):
        """수집 시작"""
        logger.info("메일 수집 오케스트레이터 시작")
        await self.scheduler.start()
    
    async def stop_collection(self):
        """수집 중지"""
        logger.info("메일 수집 오케스트레이터 중지")
        await self.scheduler.stop()
    
    async def collect_account(
        self, 
        account_id: str, 
        collection_type: str = "both"
    ) -> Dict[str, CollectionResult]:
        """특정 계정 수집"""
        results = {}
        
        if collection_type in ["incremental", "both"]:
            results["incremental"] = await self.service.collect_incremental(account_id)
        
        if collection_type in ["backfill", "both"]:
            results["backfill"] = await self.service.collect_backfill(account_id)
        
        return results
    
    def get_account_progress(self, account_id: str) -> CollectionProgress:
        """계정별 진행 상황 조회"""
        return self.service.get_collection_progress(account_id)
    
    def get_all_accounts_progress(self) -> List[CollectionProgress]:
        """모든 계정 진행 상황 조회"""
        accounts = self.db.fetch_all(
            "SELECT user_id FROM accounts WHERE is_active = 1"
        )
        
        progress_list = []
        for account in accounts:
            try:
                progress = self.service.get_collection_progress(account['user_id'])
                progress_list.append(progress)
            except Exception as e:
                logger.error(f"진행 상황 조회 실패: {account['user_id']}, {str(e)}")
        
        return progress_list
    
    def get_collection_statistics(self) -> CollectionStats:
        """전체 수집 통계 조회"""
        return self.scheduler.get_collection_statistics()
    
    async def update_account_config(
        self, 
        account_id: str, 
        config: AccountCollectionConfig
    ) -> bool:
        """계정별 수집 설정 업데이트"""
        try:
            update_data = {
                "collection_enabled": config.collection_enabled,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 커스텀 설정이 있으면 별도 테이블에 저장 필요
            # 현재는 collection_enabled만 지원
            
            self.db.update(
                "accounts",
                update_data,
                "user_id = ?",
                (account_id,)
            )
            
            logger.info(f"계정 설정 업데이트: {account_id}, enabled={config.collection_enabled}")
            return True
            
        except Exception as e:
            logger.error(f"계정 설정 업데이트 실패: {account_id}, {str(e)}")
            return False
    
    async def force_collection(
        self,
        request: CollectionRequest
    ) -> Dict[str, Any]:
        """강제 수집 실행"""
        return await self.scheduler.force_collection(
            account_ids=request.account_ids,
            collection_type=request.collection_type.value.lower()
        )
    
    def get_collection_health(self) -> Dict[str, Any]:
        """수집 시스템 상태 확인"""
        try:
            stats = self.get_collection_statistics()
            
            # 상태 판단
            health_status = "healthy"
            issues = []
            
            # 지연된 계정이 많은 경우
            if stats.accounts_behind > stats.active_accounts * 0.5:
                health_status = "degraded"
                issues.append("50% 이상의 계정이 동기화 지연됨")
            
            # 백필이 너무 오래 걸리는 경우
            if stats.backfill_in_progress > 10:
                health_status = "degraded"
                issues.append("10개 이상의 계정이 백필 진행 중")
            
            # 수집기가 중지된 경우
            if not stats.collector_running:
                health_status = "stopped"
                issues.append("수집기가 실행되지 않음")
            
            return {
                "status": health_status,
                "issues": issues,
                "statistics": stats.model_dump(),
                "checked_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"상태 확인 실패: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }