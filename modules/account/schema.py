from pydantic import BaseModel, Field
from typing import Optional
import datetime

class AccountBase(BaseModel):
    user_id: str = Field(..., description="사용자 고유 ID (이메일)")
    user_name: str = Field(..., description="사용자 이름")
    is_active: bool = Field(True, description="계정 활성 상태")

class AccountCreate(AccountBase):
    pass

class AccountUpdate(BaseModel):
    user_name: Optional[str] = None
    is_active: Optional[bool] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expiry: Optional[datetime.datetime] = None
    last_sync_time: Optional[datetime.datetime] = None

class Account(AccountBase):
    id: int
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expiry: Optional[datetime.datetime] = None
    last_sync_time: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True
