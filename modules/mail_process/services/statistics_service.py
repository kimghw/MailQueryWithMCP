"""통계 서비스 - 처리 통계 관리 및 기록"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import uuid
from infra.core import get_logger, get_database_manager, get_kafka_client

logger = get_logger(__name__)


class StatisticsService:
    """통계 관리 서비스"""
    
    def __init__(self):
        self.db = get_database_manager()
        self.kafka = get_kafka_client()
        self.logger = get_logger(__name__)
        self._current_stats = {}  # 현재 처리 통계
    
    async def record_statistics(
        self, 
        account_id: str,
        total_count: int,
        filtered_count: int,
        saved_results: Dict,
        publish_batch_event: bool
    ) -> Dict:
        """통계 기록 및 반환"""
        
        # 통계 계산
        statistics = {
            'account_id': account_id,
            'total_mails': total_count,
            'filtered_mails': filtered_count,
            'processed_mails': filtered_count,
            'saved_mails': saved_results.get('saved', 0),
            'duplicate_mails': saved_results.get('duplicates', 0),
            'events_published': saved_results.get('events_published', 0),
            'skipped_mails': total_count - filtered_count,
            'db_errors': saved_results.get('db_errors', 0),
            'event_errors': saved_results.get('event_errors', 0),
            'success_rate': self._calculate_success_rate(
                saved_results.get('saved', 0), 
                filtered_count
            ),
            'duplication_rate': self._calculate_duplication_rate(
                saved_results.get('duplicates', 0),
                filtered_count
            ),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # 현재 통계 저장
        self._current_stats = statistics
        
        # DB에 통계 기록
        self._record_to_db(account_id, statistics)
        
        # 배치 완료 이벤트 발행 (선택적)
        if publish_batch_event and total_count > 1:
            await self._publish_batch_complete_event(statistics)
        
        self.logger.info(
            f"통계 완료: account={account_id}, "
            f"total={total_count}, saved={statistics['saved_mails']}, "
            f"success_rate={statistics['success_rate']}%"
        )
        
        return statistics
    
    def get_current_statistics(self) -> Dict:
        """현재 처리 중인 통계 반환 (부분 실패 시 사용)"""
        return self._current_stats.copy()
    
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
                f"saved={stats['saved_mails']}, "
                f"duplicates={stats['duplicate_mails']}, "
                f"success_rate={stats['success_rate']}%"
            )
            
            # processing_logs에 기록
            log_data = {
                'run_id': str(uuid.uuid4()),
                'account_id': self._get_account_db_id(account_id),
                'log_level': 'INFO',
                'message': summary,
                'timestamp': datetime.utcnow()
            }
            
            self.db.insert('processing_logs', log_data)
            
        except Exception as e:
            self.logger.error(f"통계 DB 기록 실패: {str(e)}")
    
    async def _publish_batch_complete_event(self, stats: Dict):
        """배치 완료 이벤트 발행"""
        try:
            event_data = {
                "event_type": "email.batch_processing_complete",
                "event_id": str(uuid.uuid4()),
                "account_id": stats['account_id'],
                "occurred_at": datetime.utcnow().isoformat(),
                "statistics": {
                    "total_count": stats['total_mails'],
                    "processed_count": stats['saved_mails'],
                    "skipped_count": stats['skipped_mails'],
                    "duplicate_count": stats['duplicate_mails'],
                    "success_rate": stats['success_rate'],
                    "duplication_rate": stats['duplication_rate']
                }
            }
            
            self.kafka.produce_event(
                topic="email-processing-events",
                event_data=event_data,
                key=f"{stats['account_id']}_batch"
            )
            
            self.logger.debug("배치 완료 이벤트 발행됨")
            
        except Exception as e:
            self.logger.error(f"배치 완료 이벤트 발행 실패: {str(e)}")
    
    def _get_account_db_id(self, account_id: str) -> Optional[int]:
        """account_id로 DB의 실제 ID 조회"""
        try:
            account = self.db.fetch_one(
                "SELECT id FROM accounts WHERE user_id = ?",
                (account_id,)
            )
            return account['id'] if account else None
        except:
            return None
    
    async def get_account_statistics(self, account_id: str, days: int = 7) -> Dict:
        """특정 계정의 통계 조회"""
        try:
            db_id = self._get_account_db_id(account_id)
            if not db_id:
                return {}
            
            query = """
                SELECT 
                    COUNT(*) as total_mails,
                    COUNT(DISTINCT sender) as unique_senders,
                    COUNT(DISTINCT content_hash) as unique_contents,
                    MIN(received_time) as oldest_mail,
                    MAX(received_time) as newest_mail
                FROM mail_history
                WHERE account_id = ? 
                AND processed_at >= datetime('now', ? || ' days')
            """
            
            result = self.db.fetch_one(query, (db_id, f'-{days}'))
            
            return {
                'account_id': account_id,
                'period_days': days,
                'total_mails': result['total_mails'] or 0,
                'unique_senders': result['unique_senders'] or 0,
                'unique_contents': result['unique_contents'] or 0,
                'oldest_mail': result['oldest_mail'],
                'newest_mail': result['newest_mail']
            }
            
        except Exception as e:
            self.logger.error(f"계정 통계 조회 실패: {str(e)}")
            return {}
    
    async def get_processing_summary(self, account_id: str, 
                                   time_range: timedelta) -> Dict:
        """지정 기간의 처리 요약 통계"""
        try:
            db_id = self._get_account_db_id(account_id)
            if not db_id:
                return {}
            
            # 시간대별 처리량 조회
            query = """
                SELECT 
                    DATE(processed_at) as process_date,
                    COUNT(*) as mail_count,
                    COUNT(DISTINCT sender) as unique_senders
                FROM mail_history
                WHERE account_id = ? 
                AND processed_at >= datetime('now', ? || ' days')
                GROUP BY DATE(processed_at)
                ORDER BY process_date DESC
            """
            
            days = int(time_range.total_seconds() / 86400)
            results = self.db.fetch_all(query, (db_id, f'-{days}'))
            
            daily_stats = []
            for row in results:
                daily_stats.append({
                    'date': row['process_date'],
                    'mail_count': row['mail_count'],
                    'unique_senders': row['unique_senders']
                })
            
            return {
                'account_id': account_id,
                'time_range_days': days,
                'daily_statistics': daily_stats,
                'total_processed': sum(d['mail_count'] for d in daily_stats)
            }
            
        except Exception as e:
            self.logger.error(f"처리 요약 조회 실패: {str(e)}")
            return {}
    
    async def get_keyword_trends(self, account_id: str, days: int = 7) -> List[Dict]:
        """키워드 트렌드 분석"""
        try:
            db_id = self._get_account_db_id(account_id)
            if not db_id:
                return []
            
            # 최근 키워드 트렌드 조회
            query = """
                SELECT 
                    DATE(processed_at) as date,
                    keywords
                FROM mail_history
                WHERE account_id = ? 
                AND processed_at >= datetime('now', ? || ' days')
                AND keywords IS NOT NULL AND keywords != '[]'
                ORDER BY processed_at DESC
            """
            
            results = self.db.fetch_all(query, (db_id, f'-{days}'))
            
            # 날짜별 키워드 집계
            daily_keywords = {}
            for row in results:
                date = row['date']
                try:
                    import json
                    keywords = json.loads(row['keywords'])
                    
                    if date not in daily_keywords:
                        daily_keywords[date] = {}
                    
                    for keyword in keywords:
                        if keyword not in daily_keywords[date]:
                            daily_keywords[date][keyword] = 0
                        daily_keywords[date][keyword] += 1
                        
                except:
                    continue
            
            # 트렌드 데이터 구성
            trends = []
            for date, keyword_counts in daily_keywords.items():
                top_keywords = sorted(
                    keyword_counts.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:10]
                
                trends.append({
                    'date': date,
                    'top_keywords': [
                        {'keyword': kw, 'count': cnt} 
                        for kw, cnt in top_keywords
                    ]
                })
            
            return sorted(trends, key=lambda x: x['date'], reverse=True)
            
        except Exception as e:
            self.logger.error(f"키워드 트렌드 조회 실패: {str(e)}")
            return []
