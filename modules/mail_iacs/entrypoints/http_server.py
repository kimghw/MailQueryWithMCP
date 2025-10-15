"""
IACS MCP HTTP 서버
FastAPI 기반 RESTful API - MCP 표준 구조
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from infra.core.logger import get_logger
from modules.mail_iacs.handlers import IACSHandlers
from modules.mail_iacs import (
    InsertInfoRequest,
    SearchAgendaRequest,
    SearchResponsesRequest,
    InsertDefaultValueRequest,
)

logger = get_logger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="IACS Mail Server",
    description="의장-멤버 간 아젠다 및 응답 메일 관리 API",
    version="1.0.0",
)

# Handlers 인스턴스
handlers = IACSHandlers()


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "IACS Mail Server",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy"}


@app.get("/api/tools")
async def list_tools():
    """사용 가능한 도구 목록 조회 (인증 + IACS)"""
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


@app.post("/api/insert_info")
async def insert_info(request: InsertInfoRequest):
    """패널 의장 및 멤버 정보 삽입 - Handler 위임"""
    try:
        response = await handlers.call_tool_as_dict("insert_info", request.model_dump())
        return response
    except Exception as e:
        logger.error(f"insert_info 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search_agenda")
async def search_agenda(request: SearchAgendaRequest):
    """아젠다 메일 검색 - Handler 위임"""
    try:
        response = await handlers.call_tool_as_dict("search_agenda", request.model_dump())
        return response
    except Exception as e:
        logger.error(f"search_agenda 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search_responses")
async def search_responses(request: SearchResponsesRequest):
    """응답 메일 검색 - Handler 위임"""
    try:
        response = await handlers.call_tool_as_dict("search_responses", request.model_dump())
        return response
    except Exception as e:
        logger.error(f"search_responses 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/insert_default_value")
async def insert_default_value(request: InsertDefaultValueRequest):
    """기본 패널 이름 설정 - Handler 위임"""
    try:
        response = await handlers.call_tool_as_dict("insert_default_value", request.model_dump())
        return response
    except Exception as e:
        logger.error(f"insert_default_value 오류: {str(e)}")
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


@app.get("/api/prompts")
async def list_prompts():
    """사용 가능한 프롬프트 목록 조회"""
    try:
        prompts = await handlers.handle_list_prompts()
        return {
            "prompts": [
                {
                    "name": p.name,
                    "description": p.description,
                    "arguments": [
                        {
                            "name": arg.name,
                            "description": arg.description,
                            "required": arg.required
                        }
                        for arg in (p.arguments or [])
                    ]
                }
                for p in prompts
            ]
        }
    except Exception as e:
        logger.error(f"list_prompts 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/prompts/{prompt_name}")
async def get_prompt(prompt_name: str, arguments: dict = {}):
    """특정 프롬프트 내용 조회"""
    try:
        prompt_msg = await handlers.handle_get_prompt(prompt_name, arguments)
        return {
            "role": prompt_msg.role,
            "content": prompt_msg.content.text
        }
    except Exception as e:
        logger.error(f"get_prompt 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """서버 실행"""
    logger.info("IACS MCP HTTP 서버 시작")

    # 환경변수에서 포트 가져오기 (기본값: 8002)
    import os

    port = int(os.getenv("IACS_SERVER_PORT", "8002"))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
