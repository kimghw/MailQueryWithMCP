# scripts/sync_mails.py
"""
메일 동기화 단일 실행 스크립트
모든 시간은 UTC 기준으로 처리
"""
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import time

from infra.core import (
    get_database_manager,
    get_logger,
    get_config,
    get_token_service
)
from infra.core.exceptions import TokenExpiredError, DatabaseError
from modules.mail_query import (
    MailQueryOrchestrator,
    MailQueryRequest,
    MailQueryFilters,
    PaginationOptions
)
from modules.mail_process import MailProcessorOrchestrator

logger = get_logger(__name__)


class MailSyncRunner:
    """메일 동기화 실행기"""
    
    def __init__(self):
        self.config = get_config()
        self.db = get_database_manager()
        self.token_service = get_token_service()
        
        # 설정값 로드
        self.initial_months = int(self.config.get_setting("MAIL_SYNC_INITIAL_MONTHS", "3"))
        self.batch_size = int(self.config.get_setting("MAIL_SYNC_BATCH_SIZE", "10"))
    
    def get_active_accounts(self) -> List[Dict[str, Any]]:
        """활성화된 계정 목록 조회"""
        try:
            query = """
                SELECT id, user_id, user_name, last_sync_time, 
                       created_at, updated_at
                FROM accounts 
                WHERE is_active = 1 AND status = 'ACTIVE'
                ORDER BY last_sync_time ASC NULLS FIRST
            """
            
            accounts = self.db.fetch_all(query)
            return [dict(account) for account in accounts]
            
        except DatabaseError as e:
            logger.error(f"활성 계정 조회 실패: {str(e)}")
            return []
    
    def parse_utc_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """데이터베이스의 UTC 시간 문자열을 datetime 객체로 변환"""
        if not dt_str:
            return None
            
        try:
            # 다양한 형식 시도
            if 'T' in dt_str:
                # ISO 형식 (2025-07-01T14:30:00Z 또는 2025-07-01T14:30:00)
                if dt_str.endswith('Z'):
                    return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                else:
                    # timezone 정보가 없으면 UTC로 가정
                    dt = datetime.fromisoformat(dt_str)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
            else:
                # SQLite 기본 형식 (2025-07-01 14:30:00)
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                # 데이터베이스는 UTC 기준이므로 UTC timezone 추가
                return dt.replace(tzinfo=timezone.utc)
                
        except Exception as e:
            logger.warning(f"날짜 파싱 실패: {dt_str}, error: {str(e)}")
            return None
    
    def calculate_sync_date_range(self, last_sync_time: Optional[str]) -> tuple[datetime, datetime]:
        """동기화 날짜 범위 계산 (모두 UTC 기준)"""
        # 현재 시간 (UTC)
        date_to = datetime.now(timezone.utc)
        
        if last_sync_time:
            # last_sync_time 파싱 (데이터베이스는 UTC 저장)
            date_from = self.parse_utc_datetime(last_sync_time)
            
            if date_from:
                logger.debug(f"증분 동기화: {date_from.isoformat()} (UTC) 이후")
            else:
                # 파싱 실패 시 기본값 (7일 전)
                date_from = date_to - timedelta(days=7)
                logger.warning(f"last_sync_time 파싱 실패, 최근 7일로 설정")
        else:
            # 초기 동기화: 설정된 개월 수만큼 이전부터
            date_from = date_to - timedelta(days=30 * self.initial_months)
            logger.debug(f"초기 동기화: 최근 {self.initial_months}개월")
        
        # 두 datetime 모두 UTC timezone-aware 상태 확인
        assert date_from.tzinfo is not None, "date_from must be timezone-aware"
        assert date_to.tzinfo is not None, "date_to must be timezone-aware"
        
        return date_from, date_to
    
    async def sync_account_emails(self, account: Dict[str, Any]) -> Dict[str, Any]:
        """단일 계정의 메일 동기화"""
        user_id = account['user_id']
        result = {
            'user_id': user_id,
            'success': False,
            'mail_count': 0,
            'error': None,
            'duration_ms': 0
        }
        
        start_time = time.time()
        
        async with MailQueryOrchestrator() as mail_query:
            try:
                # 날짜 범위 계산 (UTC 기준)
                date_from, date_to = self.calculate_sync_date_range(
                    account.get('last_sync_time')
                )
                
                logger.info(
                    f"메일 동기화 시작: {user_id} "
                    f"({date_from.strftime('%Y-%m-%d %H:%M UTC')} ~ "
                    f"{date_to.strftime('%Y-%m-%d %H:%M UTC')})"
                )
                
                # 메일 조회 요청 생성
                filters = MailQueryFilters(
                    date_from=date_from,
                    date_to=date_to
                )
                
                request = MailQueryRequest(
                    user_id=user_id,
                    filters=filters,
                    pagination=PaginationOptions(
                        top=100,
                        max_pages=50  # 최대 5000개
                    ),
                    select_fields=[
                        "id", "subject", "from", "sender", 
                        "receivedDateTime", "bodyPreview", "body",
                        "hasAttachments", "importance", "isRead"
                    ]
                )
                
                # 메일 조회 실행
                response = await mail_query.mail_query_user_emails(request)
                
                # 메일 프로세싱 실행
                if response.messages:
                    async with MailProcessorOrchestrator() as mail_processor:
                        # GraphMailItem을 Dict로 변환
                        mail_dicts = [message.model_dump() for message in response.messages]
                        
                        # 배치 처리로 메일 프로세싱
                        processing_result = await mail_processor.process_mails(
                            account_id=user_id,
                            mails=mail_dicts,
                            publish_batch_event=True
                        )
                        
                        logger.info(
                            f"메일 프로세싱 완료: {user_id} - "
                            f"저장={processing_result.get('saved', 0)}, "
                            f"중복={processing_result.get('duplicates', 0)}, "
                            f"실패={processing_result.get('failed', 0)}"
                        )
                
                # last_sync_time 업데이트 (UTC 기준)
                await self.token_service.update_last_sync_time(user_id)
                
                result['success'] = True
                result['mail_count'] = response.total_fetched
                result['duration_ms'] = int((time.time() - start_time) * 1000)
                
                logger.info(
                    f"메일 동기화 완료: {user_id} "
                    f"({response.total_fetched}개, {result['duration_ms']}ms)"
                )
                
            except TokenExpiredError:
                error_msg = f"토큰 만료됨"
                logger.warning(f"{error_msg}: {user_id}")
                result['error'] = error_msg
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"동기화 실패: {user_id} - {error_msg}", exc_info=True)
                result['error'] = error_msg
                result['duration_ms'] = int((time.time() - start_time) * 1000)
        
        return result
    
    async def run(self) -> Dict[str, Any]:
        """메일 동기화 실행"""
        start_time = time.time()
        
        # 활성 계정 조회
        accounts = self.get_active_accounts()
        
        if not accounts:
            logger.info("동기화할 활성 계정이 없습니다.")
            return {
                'status': 'success',
                'total_accounts': 0,
                'success_count': 0,
                'failed_count': 0,
                'total_mails': 0,
                'duration_seconds': 0
            }
        
        logger.info(f"동기화 시작: {len(accounts)}개 계정")
        
        # 계정별 동기화 실행
        all_results = []
        
        # 배치 처리
        for i in range(0, len(accounts), self.batch_size):
            batch = accounts[i:i + self.batch_size]
            
            # 동시 실행
            tasks = [self.sync_account_emails(account) for account in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 예외 처리
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    all_results.append({
                        'user_id': batch[j]['user_id'],
                        'success': False,
                        'error': str(result),
                        'mail_count': 0
                    })
                else:
                    all_results.append(result)
            
            # 배치 간 짧은 대기
            if i + self.batch_size < len(accounts):
                await asyncio.sleep(0.5)
        
        # 결과 집계
        success_count = sum(1 for r in all_results if r.get('success'))
        failed_count = len(all_results) - success_count
        total_mails = sum(r.get('mail_count', 0) for r in all_results)
        duration = round(time.time() - start_time, 2)
        
        # 실패 로그
        for result in all_results:
            if not result.get('success'):
                logger.error(
                    f"동기화 실패 상세: {result['user_id']} - {result.get('error')}"
                )
        
        summary = {
            'status': 'success' if failed_count == 0 else 'partial',
            'total_accounts': len(accounts),
            'success_count': success_count,
            'failed_count': failed_count,
            'total_mails': total_mails,
            'duration_seconds': duration,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(
            f"동기화 완료: 성공={success_count}/{len(accounts)}, "
            f"메일={total_mails}개, 시간={duration}초"
        )
        
        return summary


async def main():
    """메인 함수"""
    try:
        runner = MailSyncRunner()
        result = await runner.run()
        
        # 종료 코드 결정
        if result['status'] == 'success':
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"예상치 못한 오류: {str(e)}", exc_info=True)
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
