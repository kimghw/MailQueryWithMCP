"""
OneNote MCP Server Module
Microsoft Graph API를 통한 OneNote 읽기/쓰기/생성 기능
"""

from .schemas import (
    ListNotebooksRequest,
    ListNotebooksResponse,
    GetPageContentRequest,
    GetPageContentResponse,
    CreatePageRequest,
    CreatePageResponse,
    UpdatePageRequest,
    UpdatePageResponse,
)

__all__ = [
    "ListNotebooksRequest",
    "ListNotebooksResponse",
    "GetPageContentRequest",
    "GetPageContentResponse",
    "CreatePageRequest",
    "CreatePageResponse",
    "UpdatePageRequest",
    "UpdatePageResponse",
]
