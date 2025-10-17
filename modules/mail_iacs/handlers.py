"""
IACS MCP Handlers
MCP 프로토콜 핸들러 레이어 - HTTP/stdio 공통 로직
"""

import json
from typing import Any, Dict, List
from mcp.types import Tool, TextContent, Prompt, PromptArgument, PromptMessage

from infra.core.logger import get_logger
from .tools import IACSTools
from .prompts import get_prompt
from .schemas import (
    InsertInfoRequest,
    SearchAgendaRequest,
    SearchResponsesRequest,
    InsertDefaultValueRequest,
)

logger = get_logger(__name__)


class IACSHandlers:
    """IACS MCP Protocol Handlers"""

    def __init__(self):
        """Initialize handlers with tools instance"""
        self.tools = IACSTools()
        logger.info("✅ IACSHandlers initialized")

    # ========================================================================
    # MCP Protocol: list_tools
    # ========================================================================

    async def handle_list_tools(self) -> List[Tool]:
        """List available MCP tools"""
        logger.info("🔧 [MCP Handler] list_tools() called")

        # Define IACS tools
        iacs_tools = [
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
                            "description": "_S 시작 날짜 (ISO 형식, 기본값: 현재)",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "_S 종료 날짜 (ISO 형식, 기본값: 3개월 전)",
                        },
                        "agenda_code": {
                            "type": "string",
                            "description": "_S 아젠다 코드 키워드 (옵션)",
                        },
                        "panel_name": {
                            "type": "string",
                            "description": "패널 이름 (필수, 예: sdtp)",
                        },
                    },
                    "required": ["panel_name"],
                },
            ),
            Tool(
                name="search_responses",
                description="멤버들이 보낸 응답 메일 검색. 아젠다 코드 전체로 제목 검색. $search 방식 사용. panel_name 생략 시 기본 패널 사용.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agenda_code": {
                            "type": "string",
                            "description": "_S 아젠다 코드 전체 (필수, 예: PL24016a)",
                        },
                        "panel_name": {
                            "type": "string",
                            "description": "패널 이름 (옵션, 없으면 기본 패널 사용)",
                        },
                        "send_address": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "_C 발신자 주소 리스트 (옵션)",
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

        return iacs_tools

    # ========================================================================
    # MCP Protocol: call_tool
    # ========================================================================

    async def handle_call_tool(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle MCP tool calls"""
        logger.info(f"🔨 [MCP Handler] call_tool({name}) with args: {arguments}")

        try:
            # Handle IACS tools
            if name == "insert_info":
                request = InsertInfoRequest(**arguments)
                response = await self.tools.insert_info(request)
                return [
                    TextContent(
                        type="text", text=response.model_dump_json(indent=2)
                    )
                ]

            elif name == "search_agenda":
                request = SearchAgendaRequest(**arguments)
                response = await self.tools.search_agenda(request)
                # message 필드에 포맷팅된 텍스트가 들어있음
                return [
                    TextContent(
                        type="text", text=response.message
                    )
                ]

            elif name == "search_responses":
                request = SearchResponsesRequest(**arguments)
                response = await self.tools.search_responses(request)
                # message 필드에 포맷팅된 텍스트가 들어있음
                return [
                    TextContent(
                        type="text", text=response.message
                    )
                ]

            elif name == "insert_default_value":
                request = InsertDefaultValueRequest(**arguments)
                response = await self.tools.insert_default_value(request)
                return [
                    TextContent(
                        type="text", text=response.model_dump_json(indent=2)
                    )
                ]

            else:
                error_msg = f"알 수 없는 도구: {name}"
                logger.error(error_msg)
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {"success": False, "message": error_msg}, indent=2
                        ),
                    )
                ]

        except Exception as e:
            logger.error(f"❌ Tool 실행 오류: {name}, {str(e)}", exc_info=True)
            error_response = {"success": False, "message": f"오류 발생: {str(e)}"}
            return [
                TextContent(type="text", text=json.dumps(error_response, indent=2))
            ]

    # ========================================================================
    # Helper: Convert to dict (for HTTP responses)
    # ========================================================================

    async def call_tool_as_dict(
        self, name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        HTTP API용 헬퍼: call_tool 결과를 dict로 반환

        MCP는 TextContent를 반환하지만,
        HTTP API는 JSON dict를 반환해야 하므로 변환 헬퍼 제공
        """
        try:
            # Handle IACS tools
            if name == "insert_info":
                request = InsertInfoRequest(**arguments)
                response = await self.tools.insert_info(request)
                return response.model_dump()

            elif name == "search_agenda":
                request = SearchAgendaRequest(**arguments)
                response = await self.tools.search_agenda(request)
                return response.model_dump()

            elif name == "search_responses":
                request = SearchResponsesRequest(**arguments)
                response = await self.tools.search_responses(request)
                return response.model_dump()

            elif name == "insert_default_value":
                request = InsertDefaultValueRequest(**arguments)
                response = await self.tools.insert_default_value(request)
                return response.model_dump()

            else:
                raise ValueError(f"알 수 없는 도구: {name}")

        except Exception as e:
            logger.error(f"❌ Tool 실행 오류: {name}, {str(e)}", exc_info=True)
            raise

    # ========================================================================
    # MCP Protocol: list_prompts
    # ========================================================================

    async def handle_list_prompts(self) -> List[Prompt]:
        """List available MCP prompts"""
        logger.info("📋 [MCP Handler] list_prompts() called")

        return [
            Prompt(
                name="setup_panel",
                description="📋 IACS 패널 초기 설정 가이드 - 패널 정보 등록, 기본 패널 설정, 인증 설정 방법",
                arguments=[],
            ),
            Prompt(
                name="agenda_search_data",
                description="📧 아젠다 메일 검색 데이터 처리 가이드 - $filter 방식, 날짜 범위, 필드 선택, 성능 최적화",
                arguments=[
                    PromptArgument(
                        name="panel_name",
                        description="패널 이름 (예: sdtp)",
                        required=False,
                    )
                ],
            ),
            Prompt(
                name="response_search_data",
                description="💬 응답 메일 검색 데이터 처리 가이드 - $search 방식, agenda_code 사용법, 클라이언트 필터링",
                arguments=[],
            ),
            Prompt(
                name="data_management",
                description="🗄️ 데이터베이스 관리 가이드 - 스키마 구조, 데이터 처리 규칙, 백업/복구, 마이그레이션",
                arguments=[],
            ),
        ]

    # ========================================================================
    # MCP Protocol: get_prompt
    # ========================================================================

    async def handle_get_prompt(
        self, name: str, arguments: Dict[str, Any]
    ) -> PromptMessage:
        """Get specific prompt content"""
        logger.info(f"📝 [MCP Handler] get_prompt({name}) called with args: {arguments}")

        try:
            return await get_prompt(name, arguments)
        except Exception as e:
            logger.error(f"❌ Prompt 실행 오류: {name}, {str(e)}", exc_info=True)
            raise
