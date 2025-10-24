"""
Teams MCP Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# ========================================
# Teams Schemas
# ========================================

class ListTeamsRequest(BaseModel):
    """팀 목록 조회 요청"""
    user_id: str = Field(..., description="사용자 ID")


class ListTeamsResponse(BaseModel):
    """팀 목록 조회 응답"""
    success: bool
    teams: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None


class ListChannelsRequest(BaseModel):
    """채널 목록 조회 요청"""
    user_id: str = Field(..., description="사용자 ID")
    team_id: str = Field(..., description="팀 ID")


class ListChannelsResponse(BaseModel):
    """채널 목록 조회 응답"""
    success: bool
    channels: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None


class SendMessageRequest(BaseModel):
    """메시지 전송 요청"""
    user_id: str = Field(..., description="사용자 ID")
    team_id: str = Field(..., description="팀 ID")
    channel_id: str = Field(..., description="채널 ID")
    content: str = Field(..., description="메시지 내용")


class SendMessageResponse(BaseModel):
    """메시지 전송 응답"""
    success: bool
    message_id: Optional[str] = None
    message: Optional[str] = None


class GetMessagesRequest(BaseModel):
    """메시지 조회 요청"""
    user_id: str = Field(..., description="사용자 ID")
    team_id: str = Field(..., description="팀 ID")
    channel_id: str = Field(..., description="채널 ID")
    limit: Optional[int] = Field(50, description="조회할 메시지 수")


class GetMessagesResponse(BaseModel):
    """메시지 조회 응답"""
    success: bool
    messages: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None


class GetRepliesRequest(BaseModel):
    """답글 조회 요청"""
    user_id: str = Field(..., description="사용자 ID")
    team_id: str = Field(..., description="팀 ID")
    channel_id: str = Field(..., description="채널 ID")
    message_id: str = Field(..., description="메시지 ID")


class GetRepliesResponse(BaseModel):
    """답글 조회 응답"""
    success: bool
    replies: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None
