import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from infra.core import get_logger, get_database_manager, get_config
from .collector_service import MailCollectorService
from .collector_schema import CollectionStats

logger = get_logger(__name__)


class MailCollectorScheduler:
    """메일 수집 스케줄러"""
    
    def __init__(self):
        self.config = get_config()
        self.db = get_database_manager()
        self.service = MailCollectorService()
        self.scheduler = AsyncIOScheduler()
        
        # 설정값
        self.incremental_interval = int(
            self.config.get_setting("POLL_INTERVAL_MIN", "15")
        )
        self.backfill_interval = 60  # 백필은 1시간마다
        self.concurrent_limit = int(
            self.config.get_setting("CONCURRENT_COLLECTIONS", "5")
        )
        
        # 실행 상태
        self._running = False
        self._active_tasks = set()
    
    async def start(self):
        """스케줄러 시작"""
        if self._running:
            logger.warning("스케줄러가 이미 실행 중입니다")
            return
        
        logger.info("메일 수집 스케줄러 시작")
        self._running = True
        
        # 즉시 한 번 실행
        await self._run_incremental_collection()
        await self._run_backfill_collection()
        
        # 주기적 작업 등록
        self.scheduler.add_job(
            self._run_incremental_collection,
            IntervalTrigger(minutes=self.incremental_interval),
            id="incremental_collection",
            name="증분 메일 수집",
            max_instances=1
        )
        
        self.scheduler.add_job(
            self._run_backfill_collection,
            IntervalTrigger(minutes=self.backfill_interval),
            id="backfill_collection",
            name="백필 메일 수집",
            max_instances=1
        )
        
        # 통계 업데이트 (5분마다)
        self.scheduler.add_job(
            self._update_statistics,
            IntervalTrigger(minutes=5),
            id="update_statistics",
            name="수집 통계 업데이트"
        )
        
        self.scheduler.start()
        logger.info(
            f"스케줄러 시작 완료 - "
            f"증분: {self.incremental_interval}분, "
            f"백필: {self.backfill_interval}분"
        )
    
    async def stop(self):
        """스케줄러 중지"""
        if not self._running:
            return
        
        logger.info("메일 수집 스케줄러 중지 중...")
        self._running = False
        
        # 실행 중인 작업 대기
        if self._active_tasks:
            logger.info(f"실행 중인 작업 {len(self._active_tasks)}개 대기 중...")
            await asyncio.gather(*self._active_tasks, return_exceptions=True)
        
        self.scheduler.shutdown(wait=True)
        logger.info("메일 수집 스케줄러 중지 완료")
    
    async def _run_incremental_collection(self):
        """증분 수집 실행"""
        if not self._running:
            return
        
        logger.info("증분 수집 작업 시작")
        start_time = datetime.utcnow()
        
        try:
            # 활성 계정 목록 조회
            accounts = self._get_active_accounts_for_incremental()
            if not accounts:
                logger.info("증분 수집할 계정이 없습니다")
                return
            
            logger.info(f"증분 수집 대상: {len(accounts)}개 계정")
            
            # 병렬 처리
            tasks = []
            for account in accounts:
                if len(tasks) >= self.concurrent_limit:
                    # 동시 실행 제한
                    completed = await asyncio.gather(*tasks, return_exceptions=True)
                    self._log_batch_results(completed, "증분")
                    tasks = []
                
                task = asyncio.create_task(
                    self.service.collect_incremental(account['user_id'])
                )
                tasks.append(task)
                self._active_tasks.add(task)
                task.add_done_callback(self._active_tasks.discard)
            
            # 남은 작업 처리
            if tasks:
                completed = await asyncio.gather(*tasks, return_exceptions=True)
                self._log_batch_results(completed, "증분")
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"증분 수집 작업 완료: {len(accounts)}개 계정, {duration:.1f}초 소요")
            
        except Exception as e:
            logger.error(f"증분 수집 작업 실패: {str(e)}", exc_info=True)
    
    async def _run_backfill_collection(self):
        """백필 수집 실행"""
        if not self._running:
            return
        
        logger.info("백필 수집 작업 시작")
        start_time = datetime.utcnow()
        
        try:
            # 백필 필요 계정 목록 조회
            accounts = self._get_accounts_for_backfill()
            if not accounts:
                logger.info("백필할 계정이 없습니다")
                return
            
            logger.info(f"백필 대상: {len(accounts)}개 계정")
            
            # 순차 처리 (백필은 리소스 집약적이므로)
            success_count = 0
            for account in accounts:
                if not self._running:
                    break
                
                try:
                    result = await self.service.collect_backfill(account['user_id'])
                    if result.success:
                        success_count += 1
                except Exception as e:
                    logger.error(f"백필 실패: account_id={account['user_id']}, error={str(e)}")
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"백필 수집 작업 완료: {success_count}/{len(accounts)}개 성공, "
                f"{duration:.1f}초 소요"
            )
            
        except Exception as e:
            logger.error(f"백필 수집 작업 실패: {str(e)}", exc_info=True)
    
    def _get_active_accounts_for_incremental(self) -> List[Dict[str, Any]]:
        """증분 수집 대상 계정 조회"""
        # 1시간 이상 동기화되지 않은 활성 계정
        threshold = datetime.utcnow() - timedelta(hours=1)
        
        return self.db.fetch_all("""
            SELECT user_id, last_sync_time 
            FROM accounts 
            WHERE is_active = 1 
            AND collection_enabled = 1
            AND status IN ('ACTIVE')
            AND (last_sync_time IS NULL OR last_sync_time < ?)
            ORDER BY last_sync_time ASC NULLS FIRST
            LIMIT ?
        """, (threshold.isoformat(), self.concurrent_limit * 2))
    
    def _get_accounts_for_backfill(self) -> List[Dict[str, Any]]:
        """백필 대상 계정 조회"""
        return self.db.fetch_all("""
            SELECT user_id, backfill_status, backfill_completed_until
            FROM accounts 
            WHERE is_active = 1 
            AND collection_enabled = 1
            AND status IN ('ACTIVE')
            AND (backfill_status IS NULL OR backfill_status != 'COMPLETED')
            ORDER BY backfill_completed_until DESC NULLS FIRST
            LIMIT ?
        """, (self.concurrent_limit,))
    
    def _log_batch_results(self, results: List[Any], collection_type: str):
        """배치 처리 결과 로깅"""
        success_count = 0
        total_mails = 0
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"{collection_type} 수집 예외: {str(result)}")
            elif hasattr(result, 'success') and result.success:
                success_count += 1
                total_mails += result.mails_collected
        
        logger.info(
            f"{collection_type} 배치 완료: "
            f"{success_count}/{len(results)}개 성공, "
            f"총 {total_mails}개 메일 수집"
        )
    
    async def _update_statistics(self):
        """수집 통계 업데이트"""
        try:
            stats = self.get_collection_statistics()
            logger.info(
                f"수집 통계: "
                f"활성계정={stats.active_accounts}, "
                f"최신={stats.accounts_up_to_date}, "
                f"백필대기={stats.backfill_pending}, "
                f"총메일={stats.total_mails_in_db}"
            )
        except Exception as e:
            logger.error(f"통계 업데이트 실패: {str(e)}")
    
    def get_collection_statistics(self) -> CollectionStats:
        """전체 수집 통계 조회"""
        # 계정 통계
        account_stats = self.db.fetch_one("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN last_sync_time > datetime('now', '-1 hour') THEN 1 ELSE 0 END) as up_to_date,
                SUM(CASE WHEN last_sync_time <= datetime('now', '-1 hour') THEN 1 ELSE 0 END) as behind,
                SUM(CASE WHEN backfill_status = 'PENDING' THEN 1 ELSE 0 END) as backfill_pending,
                SUM(CASE WHEN backfill_status = 'IN_PROGRESS' THEN 1 ELSE 0 END) as backfill_progress,
                SUM(CASE WHEN backfill_status = 'COMPLETED' THEN 1 ELSE 0 END) as backfill_completed
            FROM accounts
            WHERE collection_enabled = 1
        """)
        
        # 메일 통계
        mail_stats = self.db.fetch_one("""
            SELECT 
                COUNT(*) as total_mails,
                MIN(received_time) as oldest_mail,
                MAX(received_time) as newest_mail,
                (SELECT COUNT(*) FROM mail_history WHERE DATE(processed_at) = DATE('now')) as today_collected
            FROM mail_history
        """)
        
        return CollectionStats(
            total_accounts=account_stats['total'] or 0,
            active_accounts=account_stats['active'] or 0,
            accounts_up_to_date=account_stats['up_to_date'] or 0,
            accounts_behind=account_stats['behind'] or 0,
            total_incremental_today=mail_stats['today_collected'] or 0,
            backfill_pending=account_stats['backfill_pending'] or 0,
            backfill_in_progress=account_stats['backfill_progress'] or 0,
            backfill_completed=account_stats['backfill_completed'] or 0,
            total_mails_in_db=mail_stats['total_mails'] or 0,
            oldest_mail_date=mail_stats['oldest_mail'],
            newest_mail_date=mail_stats['newest_mail'],
            collector_running=self._running,
            last_run_time=datetime.utcnow()
        )
    
    async def force_collection(
        self, 
        account_ids: Optional[List[str]] = None,
        collection_type: str = "both"
    ) -> Dict[str, Any]:
        """강제 수집 실행"""
        logger.info(f"강제 수집 시작: accounts={account_ids}, type={collection_type}")
        
        if not account_ids:
            # 모든 활성 계정
            accounts = self.db.fetch_all(
                "SELECT user_id FROM accounts WHERE is_active = 1 AND collection_enabled = 1"
            )
            account_ids = [acc['user_id'] for acc in accounts]
        
        results = {
            "incremental": [],
            "backfill": []
        }
        
        for account_id in account_ids:
            try:
                if collection_type in ["incremental", "both"]:
                    result = await self.service.collect_incremental(account_id)
                    results["incremental"].append(result.model_dump())
                
                if collection_type in ["backfill", "both"]:
                    result = await self.service.collect_backfill(account_id)
                    results["backfill"].append(result.model_dump())
                    
            except Exception as e:
                logger.error(f"강제 수집 실패: account_id={account_id}, error={str(e)}")
        
        return results