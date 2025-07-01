from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class CollectionType(str, Enum):
    """수집 타입"""
    INCREMENTAL = "INCREMENTAL"
    BACKFILL = "BACKFILL"


class BackfillStatus(str, Enum):
    """백필 상태"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AccountStatus(str, Enum):
    """계정 상태"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    REAUTH_REQUIRED = "REAUTH_REQUIRED"
    LOCKED = "LOCKED"


class CollectionProgress(BaseModel):
    """수집 진행 상황"""
    account_id: str = Field(..., description="계정 ID")
    collection_type: CollectionType = Field(..., description="수집 타입")
    
    # 증분 수집 관련
    last_sync_time: Optional[datetime] = Field(None, description="마지막 동기화 시간")
    incremental_mails_collected: int = Field(default=0, description="증분 수집된 메일 수")
    
    # 백필 관련
    backfill_status: Optional[BackfillStatus] = Field(None, description="백필 상태")
    backfill_completed_until: Optional[datetime] = Field(None, description="백필 완료 시점")
    backfill_target_date: Optional[datetime] = Field(None, description="백필 목표 날짜")
    backfill_progress_percentage: float = Field(default=0.0, description="백필 진행률")
    
    # 통계
    total_mails_in_db: int = Field(default=0, description="DB에 저장된 총 메일 수")
    oldest_mail_date: Optional[datetime] = Field(None, description="가장 오래된 메일 날짜")
    newest_mail_date: Optional[datetime] = Field(None, description="가장 최근 메일 날짜")
    
    # 상태
    is_running: bool = Field(default=False, description="현재 실행 중 여부")
    last_error: Optional[str] = Field(None, description="마지막 오류 메시지")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="업데이트 시간")


class CollectionRequest(BaseModel):
    """수집 요청"""
    account_ids: Optional[List[str]] = Field(None, description="수집할 계정 ID 목록")
    collection_type: CollectionType = Field(..., description="수집 타입")
    force: bool = Field(default=False, description="강제 실행 여부")
    
    # 백필 옵션
    backfill_months: int = Field(default=3, description="백필 청크 크기(월)")
    max_backfill_months: int = Field(default=24, description="최대 백필 기간(월)")


class CollectionResult(BaseModel):
    """수집 결과"""
    account_id: str = Field(..., description="계정 ID")
    collection_type: CollectionType = Field(..., description="수집 타입")
    
    # 결과
    success: bool = Field(..., description="성공 여부")
    mails_collected: int = Field(default=0, description="수집된 메일 수")
    duplicates_skipped: int = Field(default=0, description="중복 건너뛴 수")
    
    # 시간 정보
    start_time: datetime = Field(..., description="시작 시간")
    end_time: datetime = Field(..., description="종료 시간")
    duration_seconds: float = Field(..., description="소요 시간(초)")
    
    # 범위
    date_from: Optional[datetime] = Field(None, description="수집 시작 날짜")
    date_to: Optional[datetime] = Field(None, description="수집 종료 날짜")
    
    # 오류
    error_message: Optional[str] = Field(None, description="오류 메시지")
    error_details: Optional[Dict[str, Any]] = Field(None, description="오류 상세")


class CollectionStats(BaseModel):
    """수집 통계"""
    total_accounts: int = Field(..., description="전체 계정 수")
    active_accounts: int = Field(..., description="활성 계정 수")
    
    # 증분 수집
    accounts_up_to_date: int = Field(..., description="최신 상태 계정 수")
    accounts_behind: int = Field(..., description="지연된 계정 수")
    total_incremental_today: int = Field(..., description="오늘 증분 수집된 메일 수")
    
    # 백필
    backfill_pending: int = Field(..., description="백필 대기 계정 수")
    backfill_in_progress: int = Field(..., description="백필 진행 중 계정 수")
    backfill_completed: int = Field(..., description="백필 완료 계정 수")
    
    # 전체 메일
    total_mails_in_db: int = Field(..., description="DB 전체 메일 수")
    oldest_mail_date: Optional[datetime] = Field(None, description="가장 오래된 메일")
    newest_mail_date: Optional[datetime] = Field(None, description="가장 최근 메일")
    
    # 상태
    collector_running: bool = Field(..., description="수집기 실행 중 여부")
    last_run_time: Optional[datetime] = Field(None, description="마지막 실행 시간")


class AccountCollectionConfig(BaseModel):
    """계정별 수집 설정"""
    account_id: str = Field(..., description="계정 ID")
    collection_enabled: bool = Field(default=True, description="수집 활성화")
    incremental_enabled: bool = Field(default=True, description="증분 수집 활성화")
    backfill_enabled: bool = Field(default=True, description="백필 활성화")
    
    # 커스텀 설정
    custom_poll_interval: Optional[int] = Field(None, description="커스텀 폴링 간격(분)")
    custom_backfill_chunk: Optional[int] = Field(None, description="커스텀 백필 청크(월)")
    
    # 제한
    max_mails_per_sync: Optional[int] = Field(None, description="동기화당 최대 메일 수")
    daily_quota_limit: Optional[int] = Field(None, description="일일 할당량")