"""
Calendar MCP Schemas
Pydantic 스키마 정의
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class CalendarEvent(BaseModel):
    """Calendar Event 데이터 모델"""
    id: Optional[str] = None
    subject: str
    body: Optional[str] = None
    start: str  # ISO 8601 format
    end: str  # ISO 8601 format
    location: Optional[str] = None
    attendees: Optional[List[str]] = None
    is_all_day: Optional[bool] = False
    is_online_meeting: Optional[bool] = False
    online_meeting_url: Optional[str] = None


class ListEventsRequest(BaseModel):
    """일정 목록 조회 요청"""
    user_id: str
    start_date: Optional[str] = None  # ISO 8601 format (YYYY-MM-DD)
    end_date: Optional[str] = None  # ISO 8601 format (YYYY-MM-DD)
    limit: Optional[int] = Field(default=50, ge=1, le=1000)
    search_query: Optional[str] = None


class ListEventsResponse(BaseModel):
    """일정 목록 조회 응답"""
    success: bool
    message: Optional[str] = None
    events: Optional[List[Dict[str, Any]]] = None
    count: Optional[int] = 0


class CreateEventRequest(BaseModel):
    """일정 생성 요청"""
    user_id: str
    subject: str
    body: Optional[str] = None
    start: str  # ISO 8601 format
    end: str  # ISO 8601 format
    location: Optional[str] = None
    attendees: Optional[List[str]] = None
    is_all_day: Optional[bool] = False
    is_online_meeting: Optional[bool] = False


class CreateEventResponse(BaseModel):
    """일정 생성 응답"""
    success: bool
    message: Optional[str] = None
    event_id: Optional[str] = None
    event: Optional[Dict[str, Any]] = None


class UpdateEventRequest(BaseModel):
    """일정 수정 요청"""
    user_id: str
    event_id: str
    subject: Optional[str] = None
    body: Optional[str] = None
    start: Optional[str] = None  # ISO 8601 format
    end: Optional[str] = None  # ISO 8601 format
    location: Optional[str] = None
    attendees: Optional[List[str]] = None
    is_online_meeting: Optional[bool] = None


class UpdateEventResponse(BaseModel):
    """일정 수정 응답"""
    success: bool
    message: Optional[str] = None
    event: Optional[Dict[str, Any]] = None


class DeleteEventRequest(BaseModel):
    """일정 삭제 요청"""
    user_id: str
    event_id: str


class DeleteEventResponse(BaseModel):
    """일정 삭제 응답"""
    success: bool
    message: Optional[str] = None
