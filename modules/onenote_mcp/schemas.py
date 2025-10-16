"""
OneNote MCP Schemas
Request/Response 모델 정의
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# ============================================================================
# Notebook/Section/Page 조회
# ============================================================================

class ListNotebooksRequest(BaseModel):
    """노트북 목록 조회 요청"""
    user_id: str = Field(..., description="사용자 ID")


class NotebookInfo(BaseModel):
    """노트북 정보"""
    id: str
    displayName: str
    createdDateTime: Optional[str] = None
    lastModifiedDateTime: Optional[str] = None


class SectionInfo(BaseModel):
    """섹션 정보"""
    id: str
    displayName: str
    parentNotebook: Optional[Dict[str, str]] = None


class PageInfo(BaseModel):
    """페이지 정보"""
    id: str
    title: str
    createdDateTime: Optional[str] = None
    lastModifiedDateTime: Optional[str] = None
    contentUrl: Optional[str] = None


class ListNotebooksResponse(BaseModel):
    """노트북 목록 조회 응답"""
    success: bool
    notebooks: List[NotebookInfo] = []
    message: Optional[str] = None


# ============================================================================
# 페이지 컨텐츠 조회
# ============================================================================

class GetPageContentRequest(BaseModel):
    """페이지 컨텐츠 조회 요청"""
    user_id: str = Field(..., description="사용자 ID")
    page_id: str = Field(..., description="OneNote 페이지 ID")


class GetPageContentResponse(BaseModel):
    """페이지 컨텐츠 조회 응답"""
    success: bool
    page_id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    content_type: str = "html"  # html or text
    message: Optional[str] = None


# ============================================================================
# 페이지 생성
# ============================================================================

class CreatePageRequest(BaseModel):
    """페이지 생성 요청"""
    user_id: str = Field(..., description="사용자 ID")
    section_id: str = Field(..., description="섹션 ID")
    title: str = Field(..., description="페이지 제목")
    content: str = Field(..., description="페이지 내용 (HTML)")


class CreatePageResponse(BaseModel):
    """페이지 생성 응답"""
    success: bool
    page_id: Optional[str] = None
    title: Optional[str] = None
    content_url: Optional[str] = None
    message: Optional[str] = None


# ============================================================================
# 페이지 업데이트
# ============================================================================

class UpdatePageRequest(BaseModel):
    """페이지 업데이트 요청"""
    user_id: str = Field(..., description="사용자 ID")
    page_id: str = Field(..., description="OneNote 페이지 ID")
    content: str = Field(..., description="새 내용 (HTML)")


class UpdatePageResponse(BaseModel):
    """페이지 업데이트 응답"""
    success: bool
    page_id: Optional[str] = None
    message: Optional[str] = None
