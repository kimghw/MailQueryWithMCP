"""
Mail Collector 헬퍼 함수
유틸리티 및 도우미 함수들
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple

from infra.core import get_logger

logger = get_logger(__name__)


def calculate_backfill_range(
    current_end: Optional[datetime],
    chunk_months: int,
    max_months: int
) -> Tuple[datetime, datetime, bool]:
    """
    백필 범위 계산
    
    Args:
        current_end: 현재 백필 완료 지점
        chunk_months: 청크 크기 (월)
        max_months: 최대 백필 기간 (월)
        
    Returns:
        (시작일, 종료일, 완료여부)
    """
    if current_end is None:
        # 첫 백필
        end_date = datetime.utcnow()
    else:
        end_date = current_end
    
    # 청크 크기만큼 이전으로
    start_date = end_date - timedelta(days=chunk_months * 30)
    
    # 최대 백필 기간 체크
    max_backfill_date = datetime.utcnow() - timedelta(days=max_months * 30)
    
    is_completed = False
    if start_date <= max_backfill_date:
        start_date = max_backfill_date
        is_completed = True
    
    return start_date, end_date, is_completed


def estimate_collection_time(mail_count: int) -> float:
    """
    수집 예상 시간 계산 (초)
    
    Args:
        mail_count: 메일 수
        
    Returns:
        예상 소요 시간 (초)
    """
    # 대략적인 예상: 메일당 0.1초 + 기본 오버헤드 5초
    return 5.0 + (mail_count * 0.1)


def format_duration(seconds: float) -> str:
    """
    시간 포맷팅
    
    Args:
        seconds: 초
        
    Returns:
        포맷된 문자열 (예: "2분 30초")
    """
    if seconds < 60:
        return f"{seconds:.1f}초"
    
    minutes = int(seconds // 60)
    seconds = seconds % 60
    
    if minutes < 60:
        return f"{minutes}분 {seconds:.0f}초"
    
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours}시간 {minutes}분"


def calculate_progress_percentage(
    start_date: datetime,
    end_date: datetime,
    target_date: datetime
) -> float:
    """
    진행률 계산
    
    Args:
        start_date: 시작 날짜
        end_date: 종료 날짜
        target_date: 현재 위치
        
    Returns:
        진행률 (0-100)
    """
    if start_date >= end_date:
        return 100.0
    
    total_days = (end_date - start_date).days
    completed_days = (target_date - start_date).days
    
    if completed_days <= 0:
        return 0.0
    if completed_days >= total_days:
        return 100.0
    
    return (completed_days / total_days) * 100


def should_skip_collection(
    last_sync_time: Optional[datetime],
    min_interval_minutes: int = 5
) -> bool:
    """
    수집 스킵 여부 판단
    
    Args:
        last_sync_time: 마지막 동기화 시간
        min_interval_minutes: 최소 간격 (분)
        
    Returns:
        스킵 여부
    """
    if not last_sync_time:
        return False
    
    min_interval = timedelta(minutes=min_interval_minutes)
    return datetime.utcnow() - last_sync_time < min_interval


def get_collection_summary(stats: dict) -> str:
    """
    수집 통계 요약 문자열 생성
    
    Args:
        stats: 통계 딕셔너리
        
    Returns:
        요약 문자열
    """
    return (
        f"수집 요약: "
        f"활성계정 {stats.get('active_accounts', 0)}개, "
        f"최신 {stats.get('accounts_up_to_date', 0)}개, "
        f"지연 {stats.get('accounts_behind', 0)}개, "
        f"백필대기 {stats.get('backfill_pending', 0)}개, "
        f"총메일 {stats.get('total_mails_in_db', 0):,}개"
    )