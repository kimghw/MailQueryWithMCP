"""
OneDrive MCP Schemas
Pydantic models for OneDrive API requests and responses
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ListFilesRequest(BaseModel):
    """OneDrive 파일 목록 조회 요청"""
    user_id: str = Field(..., description="사용자 ID")
    folder_path: Optional[str] = Field(default=None, description="폴더 경로 (기본값: 루트)")
    search: Optional[str] = Field(default=None, description="검색어")


class ListFilesResponse(BaseModel):
    """OneDrive 파일 목록 조회 응답"""
    success: bool
    files: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None


class ReadFileRequest(BaseModel):
    """OneDrive 파일 읽기 요청"""
    user_id: str = Field(..., description="사용자 ID")
    file_path: str = Field(..., description="파일 경로 또는 파일 ID")


class ReadFileResponse(BaseModel):
    """OneDrive 파일 읽기 응답"""
    success: bool
    content: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    message: Optional[str] = None


class WriteFileRequest(BaseModel):
    """OneDrive 파일 쓰기 요청"""
    user_id: str = Field(..., description="사용자 ID")
    file_path: str = Field(..., description="파일 경로")
    content: str = Field(..., description="파일 내용")
    overwrite: Optional[bool] = Field(default=True, description="덮어쓰기 여부")


class WriteFileResponse(BaseModel):
    """OneDrive 파일 쓰기 응답"""
    success: bool
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    message: Optional[str] = None


class DeleteFileRequest(BaseModel):
    """OneDrive 파일 삭제 요청"""
    user_id: str = Field(..., description="사용자 ID")
    file_path: str = Field(..., description="파일 경로 또는 파일 ID")


class DeleteFileResponse(BaseModel):
    """OneDrive 파일 삭제 응답"""
    success: bool
    message: Optional[str] = None
