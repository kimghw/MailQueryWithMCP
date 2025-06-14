from pydantic import BaseModel, Field
from typing import List, Optional
import datetime

class MailHistoryEntry(BaseModel):
    id: int
    account_id: int
    message_id: str
    received_time: datetime.datetime
    subject: Optional[str] = None
    sender: Optional[str] = None
    keywords: Optional[List[str]] = None
    processed_at: datetime.datetime

    class Config:
        from_attributes = True
