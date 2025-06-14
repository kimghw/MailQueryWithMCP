from pydantic import BaseModel, Field
from typing import List, Optional
import datetime

class ProcessedMailEvent(BaseModel):
    """
    메일 처리 후 Kafka로 전송될 이벤트 스키마
    """
    account_id: int
    message_id: str
    received_time: datetime.datetime
    subject: str
    sender: str
    keywords: List[str]
    processed_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
