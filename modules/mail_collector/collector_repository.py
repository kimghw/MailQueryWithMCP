from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from infra.core import get_database_manager, get_logger
from .collector_schema import CollectionResult, BackfillStatus

logger = get_logger(__name__)


class MailCollectorRepository:
    """메일 수집 데이터 접근"""
    
    def __init__(self):
        self.db = get_database_manager()
    
    def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """계정 정보 조회"""
        return self.db.fetch_one(
            "SELECT * FROM accounts WHERE user_id = ?",
            (account_id,)
        )
    
    def get_accounts_for_incremental(self, limit: int = 100) -> List[Dict[str, Any]]:
        """증분 수집 대상 계정"""
        threshold = datetime.utcnow() - timedelta(hours=1)
        return self.db.fetch_all("""
            SELECT * FROM accounts 
            WHERE is_active = 1 
            AND status = 'ACTIVE'
            AND (last_sync_time IS NULL OR last_sync_time < ?)
            ORDER BY last_sync_time ASC NULLS FIRST
            LIMIT ?
        """, (threshold.isoformat(), limit))
    
    def get_accounts_for_backfill(self, limit: int = 50) -> List[Dict[str, Any]]:
        """백필 대상 계정"""
        return self.db.fetch_all("""
            SELECT * FROM accounts 
            WHERE is_active = 1 
            AND status = 'ACTIVE'
            AND (backfill_status IS NULL OR backfill_status != 'COMPLETED')
            ORDER BY backfill_completed_until DESC NULLS FIRST
            LIMIT ?
        """, (limit,))
    
    def update_last_sync_time(self, account_id: str, sync_time: datetime):
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
    
    def update_backfill_status(
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
    
    def save_collection_result(self, result: CollectionResult):
        """수집 결과 저장"""
        try:
            log_data = {
                "run_id": f"collection_{datetime.utcnow().isoformat()}",
                "account_id": result.account_id,
                "log_level": "INFO" if result.success else "ERROR",
                "message": f"수집 완료: {result.mails_collected}개 메일",
                "timestamp": datetime.utcnow()
            }
            
            # account_id로 accounts.id 조회
            account = self.get_account(result.account_id)
            if account:
                log_data["account_id"] = account['id']
            
            self.db.insert("processing_logs", log_data)
        except Exception as e:
            logger.error(f"수집 결과 저장 실패: {str(e)}")
    
    def get_account_statistics(self, account_id: int) -> Dict[str, Any]:
        """계정 통계 조회"""
        result = self.db.fetch_one("""
            SELECT 
                COUNT(*) as total_mails,
                MIN(received_time) as oldest_mail,
                MAX(received_time) as newest_mail
            FROM mail_history
            WHERE account_id = ?
        """, (account_id,))
        
        return {
            'total_mails': result['total_mails'] or 0,
            'oldest_mail': result['oldest_mail'],
            'newest_mail': result['newest_mail']
        }
    
    def get_overall_statistics(self) -> Dict[str, Any]:
        """전체 통계 조회"""
        account_stats = self.db.fetch_one("""
            SELECT 
                COUNT(*) as total_accounts,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_accounts,
                SUM(CASE WHEN last_sync_time > datetime('now', '-1 hour') THEN 1 ELSE 0 END) as up_to_date,
                SUM(CASE WHEN backfill_status = 'COMPLETED' THEN 1 ELSE 0 END) as backfill_completed
            FROM accounts
        """)
        
        mail_stats = self.db.fetch_one("""
            SELECT COUNT(*) as total_mails
            FROM mail_history
        """)
        
        return {
            'total_accounts': account_stats['total_accounts'] or 0,
            'active_accounts': account_stats['active_accounts'] or 0,
            'accounts_up_to_date': account_stats['up_to_date'] or 0,
            'backfill_completed': account_stats['backfill_completed'] or 0,
            'total_mails': mail_stats['total_mails'] or 0
        }