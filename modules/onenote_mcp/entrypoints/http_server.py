"""
OneNote MCP HTTP 서버
FastAPI 기반 RESTful API - MCP 표준 구조
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict
import os

from infra.core.logger import get_logger
from modules.onenote_mcp.handlers import OneNoteHandlers
from modules.onenote_mcp.db_service import OneNoteDBService
from modules.onenote_mcp import (
    ListNotebooksRequest,
    GetPageContentRequest,
    CreatePageRequest,
    UpdatePageRequest,
)

logger = get_logger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="OneNote MCP Server",
    description="Microsoft Graph API를 통한 OneNote 읽기/쓰기/생성 API",
    version="1.0.0",
)

# DB 초기화
db_service = OneNoteDBService()
db_service.initialize_tables()

# Handlers 인스턴스
handlers = OneNoteHandlers()


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "OneNote MCP Server",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy"}


@app.get("/api/tools")
async def list_tools():
    """사용 가능한 도구 목록 조회 (인증 + OneNote)"""
    try:
        tools = await handlers.handle_list_tools()
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                }
                for tool in tools
            ]
        }
    except Exception as e:
        logger.error(f"list_tools 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/list_notebooks")
async def list_notebooks(request: ListNotebooksRequest):
    """노트북 목록 조회 - Handler 위임"""
    try:
        response = await handlers.call_tool_as_dict("list_notebooks", request.model_dump())
        return response
    except Exception as e:
        logger.error(f"list_notebooks 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/create_section")
async def create_section(user_id: str, notebook_id: str, section_name: str):
    """섹션 생성 - Handler 위임"""
    try:
        response = await handlers.call_tool_as_dict(
            "create_section",
            {"user_id": user_id, "notebook_id": notebook_id, "section_name": section_name}
        )
        return response
    except Exception as e:
        logger.error(f"create_section 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/list_sections")
async def list_sections(user_id: str, notebook_id: str):
    """섹션 목록 조회 - Handler 위임"""
    try:
        response = await handlers.call_tool_as_dict(
            "list_sections",
            {"user_id": user_id, "notebook_id": notebook_id}
        )
        return response
    except Exception as e:
        logger.error(f"list_sections 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/list_pages")
async def list_pages(user_id: str, section_id: str):
    """페이지 목록 조회 - Handler 위임"""
    try:
        response = await handlers.call_tool_as_dict(
            "list_pages",
            {"user_id": user_id, "section_id": section_id}
        )
        return response
    except Exception as e:
        logger.error(f"list_pages 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/get_page_content")
async def get_page_content(request: GetPageContentRequest):
    """페이지 컨텐츠 조회 - Handler 위임"""
    try:
        response = await handlers.call_tool_as_dict("get_page_content", request.model_dump())
        return response
    except Exception as e:
        logger.error(f"get_page_content 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/create_page")
async def create_page(request: CreatePageRequest):
    """페이지 생성 - Handler 위임"""
    try:
        response = await handlers.call_tool_as_dict("create_page", request.model_dump())
        return response
    except Exception as e:
        logger.error(f"create_page 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/update_page")
async def update_page(request: UpdatePageRequest):
    """페이지 업데이트 - Handler 위임"""
    try:
        response = await handlers.call_tool_as_dict("update_page", request.model_dump())
        return response
    except Exception as e:
        logger.error(f"update_page 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tool/{tool_name}")
async def call_tool(tool_name: str, arguments: dict):
    """범용 도구 호출 엔드포인트 (인증 도구 등)"""
    try:
        response = await handlers.call_tool_as_dict(tool_name, arguments)
        return response
    except Exception as e:
        logger.error(f"{tool_name} 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """서버 실행"""
    logger.info("OneNote MCP HTTP 서버 시작")

    # 환경변수에서 포트 가져오기 (기본값: 8003)
    port = int(os.getenv("ONENOTE_SERVER_PORT", "8003"))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
