# scripts/sync_mails.py
"""
메일 동기화 단일 실행 스크립트
모든 시간은 UTC 기준으로 처리
대용량 처리를 위해 7일 단위로 분할하여 처리
"""
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
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
        
        # 분할 처리 설정
        self.chunk_days = int(self.config.get_setting("MAIL_SYNC_CHUNK_DAYS", "7"))  # 기본 7일
        self.max_mails_per_chunk = int(self.config.get_setting("MAIL_SYNC_MAX_MAILS_PER_CHUNK", "1000"))
    
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
    
    def calculate_sync_date_range(self, last_sync_time: Optional[str], force_initial: bool = False) -> tuple[datetime, datetime]:
        """동기화 날짜 범위 계산 (모두 UTC 기준)
        
        Args:
            last_sync_time: 마지막 동기화 시간
            force_initial: True면 last_sync_time 무시하고 초기 동기화 수행
        """
        # 현재 시간 (UTC)
        date_to = datetime.now(timezone.utc)
        
        if last_sync_time and not force_initial:
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
    
    def split_date_range(self, date_from: datetime, date_to: datetime) -> List[Tuple[datetime, datetime]]:
        """날짜 범위를 chunk_days 단위로 분할"""
        chunks = []
        current_from = date_from
        
        while current_from < date_to:
            current_to = min(current_from + timedelta(days=self.chunk_days), date_to)
            chunks.append((current_from, current_to))
            current_from = current_to
        
        return chunks
    
    async def sync_account_emails_chunk(
        self, 
        user_id: str, 
        date_from: datetime, 
        date_to: datetime,
        mail_query: MailQueryOrchestrator,
        mail_processor: MailProcessorOrchestrator
    ) -> Dict[str, Any]:
        """단일 시간 청크에 대한 메일 동기화"""
        
        chunk_result = {
            'mail_count': 0,
            'saved': 0,
            'duplicates': 0,
            'failed': 0,
            'error': None
        }
        
        try:
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
                    max_pages=self.max_mails_per_chunk // 100  # 청크당 최대 메일 수 제한
                ),
                select_fields=[
                    "id", "subject", "from", "sender", 
                    "receivedDateTime", "bodyPreview", "body",
                    "hasAttachments", "importance", "isRead"
                ]
            )
            
            # 메일 조회 실행
            response = await mail_query.mail_query_user_emails(request)
            chunk_result['mail_count'] = response.total_fetched
            
            # 메일 프로세싱 실행
            if response.messages:
                # GraphMailItem을 Dict로 변환
                mail_dicts = [message.model_dump() for message in response.messages]
                
                # 배치 처리로 메일 프로세싱
                processing_result = await mail_processor.process_mails(
                    account_id=user_id,
                    mails=mail_dicts,
                    publish_batch_event=False  # 청크별로는 배치 이벤트 발행 안함
                )
                
                chunk_result['saved'] = processing_result.get('saved', 0)
                chunk_result['duplicates'] = processing_result.get('duplicates', 0)
                chunk_result['failed'] = processing_result.get('failed', 0)
                
                logger.debug(
                    f"청크 처리 완료: {user_id} "
                    f"({date_from.strftime('%Y-%m-%d')} ~ {date_to.strftime('%Y-%m-%d')}) - "
                    f"조회={chunk_result['mail_count']}, 저장={chunk_result['saved']}"
                )
                
        except Exception as e:
            error_msg = f"청크 처리 실패: {str(e)}"
            logger.error(f"{error_msg} ({date_from} ~ {date_to})")
            chunk_result['error'] = error_msg
            
        return chunk_result
    
    async def sync_account_emails(self, account: Dict[str, Any], force_months: Optional[int] = None) -> Dict[str, Any]:
        """단일 계정의 메일 동기화 (청크 단위 처리)
        
        Args:
            account: 계정 정보
            force_months: 강제로 지정할 동기화 개월 수
        """
        user_id = account['user_id']
        result = {
            'user_id': user_id,
            'success': False,
            'mail_count': 0,
            'saved': 0,
            'duplicates': 0,
            'failed': 0,
            'chunks_processed': 0,
            'error': None,
            'duration_ms': 0
        }
        
        start_time = time.time()
        
        mail_query = None
        mail_processor = None
        
        try:
            mail_query = MailQueryOrchestrator()
            mail_processor = MailProcessorOrchestrator()
            
            # 전체 날짜 범위 계산 (UTC 기준)
            # force_months가 지정되면 last_sync_time 무시
            force_initial = force_months is not None
            date_from, date_to = self.calculate_sync_date_range(
                account.get('last_sync_time') if not force_initial else None,
                force_initial=force_initial
            )
            
            # 날짜 범위를 청크로 분할
            date_chunks = self.split_date_range(date_from, date_to)
            total_days = (date_to - date_from).days
            
            logger.info(
                f"메일 동기화 시작: {user_id} "
                f"(총 {total_days}일, {len(date_chunks)}개 청크)"
            )
            
            # 각 청크 처리
            for i, (chunk_from, chunk_to) in enumerate(date_chunks, 1):
                logger.debug(
                    f"청크 {i}/{len(date_chunks)} 처리 중: {user_id} "
                    f"({chunk_from.strftime('%Y-%m-%d')} ~ {chunk_to.strftime('%Y-%m-%d')})"
                )
                
                chunk_result = await self.sync_account_emails_chunk(
                    user_id, chunk_from, chunk_to, mail_query, mail_processor
                )
                
                # 결과 누적
                result['mail_count'] += chunk_result['mail_count']
                result['saved'] += chunk_result['saved']
                result['duplicates'] += chunk_result['duplicates']
                result['failed'] += chunk_result['failed']
                result['chunks_processed'] += 1
                
                # 청크 처리 후 짧은 대기 (API 부하 방지)
                if i < len(date_chunks):
                    await asyncio.sleep(0.5)
                
                # 에러 발생 시 중단 여부 판단
                if chunk_result.get('error') and 'TokenExpired' in chunk_result['error']:
                    result['error'] = "토큰 만료로 중단됨"
                    break
            
            # 배치 이벤트 발행 (전체 처리 완료 후)
            if result['saved'] > 0:
                # 여기서 배치 이벤트 발행 로직 추가 가능
                pass
            
            # last_sync_time 업데이트 (UTC 기준)
            await self.token_service.update_last_sync_time(user_id)
            
            result['success'] = True
            result['duration_ms'] = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"메일 동기화 완료: {user_id} - "
                f"청크={result['chunks_processed']}, "
                f"조회={result['mail_count']}, "
                f"저장={result['saved']}, "
                f"중복={result['duplicates']}, "
                f"시간={result['duration_ms']}ms"
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
            
        finally:
            # 리소스 정리
            if mail_query:
                await mail_query.close()
            if mail_processor:
                await mail_processor.close()
        
        return result
    
    async def run(self, target_user: Optional[str] = None, override_months: Optional[int] = None) -> Dict[str, Any]:
        """메일 동기화 실행
        
        Args:
            target_user: 특정 사용자만 동기화 (None이면 모든 활성 사용자)
            override_months: 동기화 기간 오버라이드 (None이면 설정값 사용)
        """
        start_time = time.time()
        
        # override_months가 있으면 initial_months 변경
        if override_months is not None:
            self.initial_months = override_months
            logger.info(f"동기화 기간 오버라이드: {override_months}개월")
        
        # 활성 계정 조회
        accounts = self.get_active_accounts()
        
        # 특정 사용자만 필터링
        if target_user:
            accounts = [acc for acc in accounts if acc['user_id'] == target_user]
            if not accounts:
                logger.error(f"사용자를 찾을 수 없거나 비활성 상태입니다: {target_user}")
                return {
                    'status': 'error',
                    'error': f'User not found or inactive: {target_user}',
                    'total_accounts': 0,
                    'success_count': 0,
                    'failed_count': 0,
                    'total_mails': 0,
                    'total_saved': 0,
                    'duration_seconds': 0
                }
        
        if not accounts:
            logger.info("동기화할 활성 계정이 없습니다.")
            return {
                'status': 'success',
                'total_accounts': 0,
                'success_count': 0,
                'failed_count': 0,
                'total_mails': 0,
                'total_saved': 0,
                'duration_seconds': 0
            }
        
        logger.info(f"동기화 시작: {len(accounts)}개 계정 (청크 크기: {self.chunk_days}일)")
        
        # 계정별 동기화 실행
        all_results = []
        
        # 배치 처리
        for i in range(0, len(accounts), self.batch_size):
            batch = accounts[i:i + self.batch_size]
            
            # 동시 실행
            tasks = [self.sync_account_emails(account, override_months) for account in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 예외 처리
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    all_results.append({
                        'user_id': batch[j]['user_id'],
                        'success': False,
                        'error': str(result),
                        'mail_count': 0,
                        'saved': 0,
                        'chunks_processed': 0
                    })
                else:
                    all_results.append(result)
            
            # 배치 간 짧은 대기
            if i + self.batch_size < len(accounts):
                await asyncio.sleep(1)
        
        # 결과 집계
        success_count = sum(1 for r in all_results if r.get('success'))
        failed_count = len(all_results) - success_count
        total_mails = sum(r.get('mail_count', 0) for r in all_results)
        total_saved = sum(r.get('saved', 0) for r in all_results)
        total_chunks = sum(r.get('chunks_processed', 0) for r in all_results)
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
            'total_saved': total_saved,
            'total_chunks': total_chunks,
            'duration_seconds': duration,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(
            f"동기화 완료: 성공={success_count}/{len(accounts)}, "
            f"메일={total_mails}개, 저장={total_saved}개, "
            f"청크={total_chunks}개, 시간={duration}초"
        )
        
        return summary


async def main():
    """메인 함수"""
    import argparse
    
    # 명령행 인수 파서 설정
    parser = argparse.ArgumentParser(description='IACSGRAPH 메일 동기화')
    parser.add_argument('--user', type=str, help='특정 사용자만 동기화')
    parser.add_argument('--months', type=int, help='동기화할 개월 수 (기본값: 설정파일)')
    
    args = parser.parse_args()
    
    try:
        runner = MailSyncRunner()
        result = await runner.run(
            target_user=args.user,
            override_months=args.months
        )
        
        # 종료 코드 결정
        if result['status'] == 'success':
            sys.exit(0)
        elif result['status'] == 'error':
            sys.exit(2)
        else:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"예상치 못한 오류: {str(e)}", exc_info=True)
        sys.exit(2)
    finally:
        # aiohttp 세션 정리를 위한 짧은 대기
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(main())
