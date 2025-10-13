"""
IACS MCP HTTP 서버
FastAPI 기반 RESTful API
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from infra.core.logger import get_logger
from modules.mail_iacs import (
    IACSTools,
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

# Tools 인스턴스
tools = IACSTools()


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


@app.post("/api/insert_info")
async def insert_info(request: InsertInfoRequest):
    """패널 의장 및 멤버 정보 삽입"""
    try:
        response = await tools.insert_info(request)
        return response.model_dump()
    except Exception as e:
        logger.error(f"insert_info 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search_agenda")
async def search_agenda(request: SearchAgendaRequest):
    """아젠다 메일 검색"""
    try:
        response = await tools.search_agenda(request)
        return response.model_dump()
    except Exception as e:
        logger.error(f"search_agenda 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search_responses")
async def search_responses(request: SearchResponsesRequest):
    """응답 메일 검색"""
    try:
        response = await tools.search_responses(request)
        return response.model_dump()
    except Exception as e:
        logger.error(f"search_responses 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/insert_default_value")
async def insert_default_value(request: InsertDefaultValueRequest):
    """기본 패널 이름 설정"""
    try:
        response = await tools.insert_default_value(request)
        return response.model_dump()
    except Exception as e:
        logger.error(f"insert_default_value 오류: {str(e)}")
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
