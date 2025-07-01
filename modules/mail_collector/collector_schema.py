from datetime import datetime
from typing import Optional, List
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


class CollectionRequest(BaseModel):
    """수집 요청"""
    account_ids: Optional[List[str]] = Field(None, description="수집할 계정 목록")
    collection_type: CollectionType = Field(..., description="수집 타입")
    max_accounts: int = Field(default=100, description="최대 계정 수")


class CollectionResult(BaseModel):
    """수집 결과"""
    account_id: str
    collection_type: CollectionType
    success: bool
    mails_collected: int = 0
    duplicates_skipped: int = 0
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: datetime = Field(default_factory=datetime.utcnow)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    error_message: Optional[str] = None
    
    @property
    def duration_seconds(self) -> float:
        return (self.end_time - self.start_time).total_seconds()


class AccountProgress(BaseModel):
    """계정 진행상황"""
    account_id: str
    last_sync_time: Optional[datetime]
    backfill_status: Optional[str]
    backfill_completed_until: Optional[datetime]
    total_mails: int
    oldest_mail_date: Optional[datetime]
    newest_mail_date: Optional[datetime]


class CollectionStats(BaseModel):
    """수집 통계"""
    total_accounts: int
    active_accounts: int
    accounts_up_to_date: int
    backfill_completed: int
    total_mails: int