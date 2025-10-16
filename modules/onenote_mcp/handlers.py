"""
OneNote MCP Handlers
MCP 프로토콜 핸들러 레이어 - HTTP/stdio 공통 로직
"""

import json
from typing import Any, Dict, List
from mcp.types import Tool, TextContent

from infra.core.logger import get_logger
from infra.handlers import AuthHandlers
from .onenote_handler import OneNoteHandler
from .db_service import OneNoteDBService
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

logger = get_logger(__name__)


class OneNoteHandlers(AuthHandlers):
    """OneNote MCP Protocol Handlers with Authentication Support"""

    def __init__(self):
        """Initialize handlers with OneNote handler instance and authentication support"""
        super().__init__()  # Initialize AuthHandlers
        self.onenote_handler = OneNoteHandler()
        self.db_service = OneNoteDBService()
        logger.info("✅ OneNoteHandlers initialized (with AuthHandlers + DBService)")

    # ========================================================================
    # MCP Protocol: list_tools
    # ========================================================================

    async def handle_list_tools(self) -> List[Tool]:
        """List available MCP tools (Authentication + OneNote)"""
        logger.info("🔧 [MCP Handler] list_tools() called")

        # Get authentication tools from parent class
        auth_tools = self.get_auth_tools()

        # Define OneNote-specific tools
        onenote_tools = [
            Tool(
                name="list_notebooks",
                description="사용자의 OneNote 노트북 목록을 조회합니다.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "사용자 ID"
                        }
                    },
                    "required": ["user_id"]
                }
            ),
            Tool(
                name="create_section",
                description="노트북에 새 섹션을 생성합니다. 섹션 ID를 응답으로 받아 재사용할 수 있습니다.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "사용자 ID"
                        },
                        "notebook_id": {
                            "type": "string",
                            "description": "노트북 ID"
                        },
                        "section_name": {
                            "type": "string",
                            "description": "생성할 섹션 이름"
                        }
                    },
                    "required": ["user_id", "notebook_id", "section_name"]
                }
            ),
            Tool(
                name="list_sections",
                description="노트북의 섹션 목록을 조회합니다.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "사용자 ID"
                        },
                        "notebook_id": {
                            "type": "string",
                            "description": "노트북 ID"
                        }
                    },
                    "required": ["user_id", "notebook_id"]
                }
            ),
            Tool(
                name="list_pages",
                description="섹션의 페이지 목록을 조회합니다.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "사용자 ID"
                        },
                        "section_id": {
                            "type": "string",
                            "description": "섹션 ID"
                        }
                    },
                    "required": ["user_id", "section_id"]
                }
            ),
            Tool(
                name="get_page_content",
                description="OneNote 페이지의 내용을 HTML 형식으로 조회합니다.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "사용자 ID"
                        },
                        "page_id": {
                            "type": "string",
                            "description": "OneNote 페이지 ID"
                        }
                    },
                    "required": ["user_id", "page_id"]
                }
            ),
            Tool(
                name="create_page",
                description="OneNote 섹션에 새 페이지를 생성합니다.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "사용자 ID"
                        },
                        "section_id": {
                            "type": "string",
                            "description": "섹션 ID"
                        },
                        "title": {
                            "type": "string",
                            "description": "페이지 제목"
                        },
                        "content": {
                            "type": "string",
                            "description": "페이지 내용 (HTML)"
                        }
                    },
                    "required": ["user_id", "section_id", "title", "content"]
                }
            ),
            Tool(
                name="update_page",
                description="OneNote 페이지에 내용을 추가합니다 (append).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "사용자 ID"
                        },
                        "page_id": {
                            "type": "string",
                            "description": "OneNote 페이지 ID"
                        },
                        "content": {
                            "type": "string",
                            "description": "추가할 내용 (HTML)"
                        }
                    },
                    "required": ["user_id", "page_id", "content"]
                }
            ),
        ]

        # Return combined list: auth tools + OneNote tools
        return auth_tools + onenote_tools

    # ========================================================================
    # MCP Protocol: call_tool
    # ========================================================================

    async def handle_call_tool(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle MCP tool calls (Authentication + OneNote)"""
        logger.info(f"🔨 [MCP Handler] call_tool({name}) with args: {arguments}")

        try:
            # Check if it's an authentication tool
            if self.is_auth_tool(name):
                return await self.handle_auth_tool(name, arguments)

            # Handle OneNote-specific tools
            if name == "list_notebooks":
                request = ListNotebooksRequest(**arguments)
                result = await self.onenote_handler.list_notebooks(request.user_id)
                response = ListNotebooksResponse(**result)
                return [TextContent(type="text", text=response.model_dump_json(indent=2))]

            elif name == "create_section":
                user_id = arguments.get("user_id")
                notebook_id = arguments.get("notebook_id")
                section_name = arguments.get("section_name")
                result = await self.onenote_handler.create_section(user_id, notebook_id, section_name)

                # DB에 섹션 저장
                if result.get("success") and result.get("section"):
                    section_id = result["section"].get("id")
                    if section_id:
                        self.db_service.save_section(user_id, notebook_id, section_id, section_name)

                return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

            elif name == "list_sections":
                user_id = arguments.get("user_id")
                notebook_id = arguments.get("notebook_id")
                result = await self.onenote_handler.list_sections(user_id, notebook_id)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            elif name == "list_pages":
                user_id = arguments.get("user_id")
                section_id = arguments.get("section_id")
                result = await self.onenote_handler.list_pages(user_id, section_id)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            elif name == "get_page_content":
                request = GetPageContentRequest(**arguments)
                result = await self.onenote_handler.get_page_content(
                    request.user_id,
                    request.page_id
                )
                response = GetPageContentResponse(**result)
                return [TextContent(type="text", text=response.model_dump_json(indent=2))]

            elif name == "create_page":
                request = CreatePageRequest(**arguments)
                result = await self.onenote_handler.create_page(
                    request.user_id,
                    request.section_id,
                    request.title,
                    request.content
                )

                # DB에 페이지 저장
                if result.get("success") and result.get("page_id"):
                    self.db_service.save_page(
                        request.user_id,
                        request.section_id,
                        result["page_id"],
                        request.title
                    )

                response = CreatePageResponse(**result)
                return [TextContent(type="text", text=response.model_dump_json(indent=2))]

            elif name == "update_page":
                request = UpdatePageRequest(**arguments)
                result = await self.onenote_handler.update_page(
                    request.user_id,
                    request.page_id,
                    request.content
                )
                response = UpdatePageResponse(**result)
                return [TextContent(type="text", text=response.model_dump_json(indent=2))]

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
        """
        try:
            # Check if it's an authentication tool
            if self.is_auth_tool(name):
                text_contents = await self.handle_auth_tool(name, arguments)
                return {"text": text_contents[0].text if text_contents else ""}

            # Handle OneNote-specific tools
            if name == "list_notebooks":
                request = ListNotebooksRequest(**arguments)
                result = await self.onenote_handler.list_notebooks(request.user_id)
                return result

            elif name == "create_section":
                user_id = arguments.get("user_id")
                notebook_id = arguments.get("notebook_id")
                section_name = arguments.get("section_name")
                result = await self.onenote_handler.create_section(user_id, notebook_id, section_name)

                # DB에 섹션 저장
                if result.get("success") and result.get("section"):
                    section_id = result["section"].get("id")
                    if section_id:
                        self.db_service.save_section(user_id, notebook_id, section_id, section_name)

                return result

            elif name == "list_sections":
                user_id = arguments.get("user_id")
                notebook_id = arguments.get("notebook_id")
                result = await self.onenote_handler.list_sections(user_id, notebook_id)
                return result

            elif name == "list_pages":
                user_id = arguments.get("user_id")
                section_id = arguments.get("section_id")
                result = await self.onenote_handler.list_pages(user_id, section_id)
                return result

            elif name == "get_page_content":
                request = GetPageContentRequest(**arguments)
                result = await self.onenote_handler.get_page_content(
                    request.user_id,
                    request.page_id
                )
                return result

            elif name == "create_page":
                request = CreatePageRequest(**arguments)
                result = await self.onenote_handler.create_page(
                    request.user_id,
                    request.section_id,
                    request.title,
                    request.content
                )

                # DB에 페이지 저장
                if result.get("success") and result.get("page_id"):
                    self.db_service.save_page(
                        request.user_id,
                        request.section_id,
                        result["page_id"],
                        request.title
                    )

                return result

            elif name == "update_page":
                request = UpdatePageRequest(**arguments)
                result = await self.onenote_handler.update_page(
                    request.user_id,
                    request.page_id,
                    request.content
                )
                return result

            else:
                raise ValueError(f"알 수 없는 도구: {name}")

        except Exception as e:
            logger.error(f"❌ Tool 실행 오류: {name}, {str(e)}", exc_info=True)
            raise
