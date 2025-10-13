"""
IACS MCP stdio 서버
Claude Desktop과 통합
"""

import asyncio
import json
import sys
from typing import Any
from mcp.server.models import InitializationOptions
from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from infra.core.logger import get_logger
from modules.mail_iacs import (
    IACSTools,
    InsertInfoRequest,
    SearchAgendaRequest,
    SearchResponsesRequest,
    InsertDefaultValueRequest,
)

logger = get_logger(__name__)

# MCP 서버 인스턴스 생성
app = Server("iacs-mail-server")
tools = IACSTools()


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """사용 가능한 도구 목록 반환"""
    return [
        Tool(
            name="insert_info",
            description="패널 의장 및 멤버 정보 삽입. 패널 이름과 의장 주소가 중복되면 기존 데이터를 삭제하고 새 데이터를 삽입합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "chair_address": {
                        "type": "string",
                        "description": "의장 이메일 주소",
                    },
                    "panel_name": {
                        "type": "string",
                        "description": "패널 이름 (예: sdtp)",
                    },
                    "kr_panel_member": {
                        "type": "string",
                        "description": "한국 패널 멤버 이메일 주소",
                    },
                },
                "required": ["chair_address", "panel_name", "kr_panel_member"],
            },
        ),
        Tool(
            name="search_agenda",
            description="의장이 보낸 아젠다 메일 검색. 날짜 범위, 아젠다 코드로 필터링 가능. $filter 방식 사용.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "시작 날짜 (ISO 형식, 기본값: 현재)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "종료 날짜 (ISO 형식, 기본값: 3개월 전)",
                    },
                    "content_field": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "조회할 필드 목록 (기본값: [\"subject\"])",
                    },
                    "agenda_code": {
                        "type": "string",
                        "description": "아젠다 코드 키워드 (옵션)",
                    },
                    "panel_name": {
                        "type": "string",
                        "description": "패널 이름 (옵션, 없으면 기본 패널 사용)",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="search_responses",
            description="멤버들이 보낸 응답 메일 검색. 아젠다 코드로 제목 검색 (앞 7자 매칭). $search 방식 사용.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content_field": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "조회할 필드 목록 (기본값: [\"subject\"])",
                    },
                    "agenda_code": {
                        "type": "string",
                        "description": "아젠다 코드 키워드 (필수, 최소 7자)",
                    },
                    "send_address": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "발신자 주소 리스트 (옵션)",
                    },
                },
                "required": ["agenda_code"],
            },
        ),
        Tool(
            name="insert_default_value",
            description="기본 패널 이름 설정. 이후 panel_name이 지정되지 않은 경우 이 패널을 사용합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "panel_name": {
                        "type": "string",
                        "description": "기본 패널 이름",
                    },
                },
                "required": ["panel_name"],
            },
        ),
    ]


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """도구 호출 처리"""
    try:
        logger.info(f"Tool 호출: {name}, 인자: {arguments}")

        if name == "insert_info":
            request = InsertInfoRequest(**arguments)
            response = await tools.insert_info(request)
            return [TextContent(type="text", text=response.model_dump_json(indent=2))]

        elif name == "search_agenda":
            request = SearchAgendaRequest(**arguments)
            response = await tools.search_agenda(request)
            return [TextContent(type="text", text=response.model_dump_json(indent=2))]

        elif name == "search_responses":
            request = SearchResponsesRequest(**arguments)
            response = await tools.search_responses(request)
            return [TextContent(type="text", text=response.model_dump_json(indent=2))]

        elif name == "insert_default_value":
            request = InsertDefaultValueRequest(**arguments)
            response = await tools.insert_default_value(request)
            return [TextContent(type="text", text=response.model_dump_json(indent=2))]

        else:
            raise ValueError(f"알 수 없는 도구: {name}")

    except Exception as e:
        logger.error(f"Tool 실행 오류: {name}, {str(e)}")
        error_response = {"success": False, "message": f"오류 발생: {str(e)}"}
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]


async def main():
    """메인 함수"""
    logger.info("IACS MCP stdio 서버 시작")

    try:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="iacs-mail-server",
                    server_version="1.0.0",
                    capabilities=app.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    except Exception as e:
        logger.error(f"서버 실행 오류: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
