"""
OneNote MCP Handlers
MCP 프로토콜 핸들러 레이어 - HTTP/stdio 공통 로직
"""

import json
from typing import Any, Dict, List
from mcp.types import Tool, TextContent

from infra.core.logger import get_logger
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


class OneNoteHandlers:
    """OneNote MCP Protocol Handlers"""

    def __init__(self):
        """Initialize handlers with OneNote handler instance"""
        self.onenote_handler = OneNoteHandler()
        self.db_service = OneNoteDBService()
        self.db_service.initialize_tables()
        logger.info("✅ OneNoteHandlers initialized")

    # ========================================================================
    # MCP Protocol: list_tools
    # ========================================================================

    async def handle_list_tools(self) -> List[Tool]:
        """List available MCP tools (OneNote only)"""
        logger.info("🔧 [MCP Handler] list_tools() called")

        # Define OneNote-specific tools
        onenote_tools = [
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
                description="섹션 목록을 조회합니다. section_name 파라미터로 이름 필터링 가능.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "사용자 ID"
                        },
                        "section_name": {
                            "type": "string",
                            "description": "섹션 이름 (선택, 필터링용)"
                        }
                    },
                    "required": ["user_id"]
                }
            ),
            Tool(
                name="list_pages",
                description="페이지 목록을 조회합니다. section_id, section_name, page_title로 필터링 가능.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "사용자 ID"
                        },
                        "section_id": {
                            "type": "string",
                            "description": "섹션 ID (선택, 특정 섹션의 페이지만 조회)"
                        },
                        "section_name": {
                            "type": "string",
                            "description": "섹션 이름 (선택, DB에서 섹션 ID 조회)"
                        },
                        "page_title": {
                            "type": "string",
                            "description": "페이지 제목 (선택, 필터링용)"
                        }
                    },
                    "required": ["user_id"]
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
                name="edit_page",
                description="OneNote 페이지 내용을 편집합니다 (내용 추가/append).",
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
            Tool(
                name="db_onenote_update",
                description="OneNote 섹션 또는 페이지 정보를 데이터베이스에 저장/업데이트합니다.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "사용자 ID"
                        },
                        "section_id": {
                            "type": "string",
                            "description": "섹션 ID (섹션 저장 시 필수)"
                        },
                        "section_name": {
                            "type": "string",
                            "description": "섹션 이름 (섹션 저장 시 필수)"
                        },
                        "notebook_id": {
                            "type": "string",
                            "description": "노트북 ID (섹션 저장 시 선택)"
                        },
                        "notebook_name": {
                            "type": "string",
                            "description": "노트북 이름 (섹션 저장 시 선택)"
                        },
                        "page_id": {
                            "type": "string",
                            "description": "페이지 ID (페이지 저장 시 필수)"
                        },
                        "page_title": {
                            "type": "string",
                            "description": "페이지 제목 (페이지 저장 시 필수)"
                        }
                    },
                    "required": ["user_id"]
                }
            ),
        ]

        # Return OneNote tools only
        return onenote_tools

    # ========================================================================
    # MCP Protocol: call_tool
    # ========================================================================

    async def handle_call_tool(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle MCP tool calls (OneNote only)"""
        logger.info(f"🔨 [MCP Handler] call_tool({name}) with args: {arguments}")

        try:
            # Handle OneNote-specific tools
            if name == "create_section":
                user_id = arguments.get("user_id")
                notebook_id = arguments.get("notebook_id")
                section_name = arguments.get("section_name")
                result = await self.onenote_handler.create_section(user_id, notebook_id, section_name)

                # DB에 섹션 자동 저장
                if result.get("success") and result.get("section"):
                    section = result["section"]
                    section_id = section.get("id")
                    section_display_name = section.get("displayName", section_name)

                    if section_id:
                        self.db_service.save_section(
                            user_id, notebook_id, section_id, section_display_name,
                            notebook_name=None,
                            mark_as_recent=False,
                            update_accessed=True
                        )
                        logger.info(f"✅ 생성된 섹션 DB 저장: {section_display_name}")

                return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

            elif name == "list_sections":
                user_id = arguments.get("user_id")
                filter_section_name = arguments.get("section_name")  # 선택적 필터

                result = await self.onenote_handler.list_sections(user_id)

                # DB에 섹션들 저장 및 필터링
                if result.get("success") and result.get("sections"):
                    sections = result["sections"]

                    for section in sections:
                        section_id = section.get("id")
                        section_name = section.get("displayName") or section.get("name")
                        # parentNotebook에서 notebook 정보 추출
                        parent_notebook = section.get("parentNotebook", {})
                        notebook_id = parent_notebook.get("id", "")
                        notebook_name = parent_notebook.get("displayName", "")

                        if section_id and section_name:
                            self.db_service.save_section(
                                user_id, notebook_id, section_id, section_name,
                                notebook_name=notebook_name,
                                update_accessed=True  # 조회 시 last_accessed 업데이트
                            )
                            logger.info(f"✅ 섹션 자동 저장: {section_name}")

                    # section_name 필터링
                    if filter_section_name:
                        sections = [s for s in sections if filter_section_name.lower() in (s.get("displayName") or s.get("name") or "").lower()]
                        result["sections"] = sections
                        logger.info(f"🔍 섹션 이름 필터 적용: '{filter_section_name}' -> {len(sections)}개")

                    # 사용자 친화적인 출력 포맷 추가
                    output_lines = [f"📁 총 {len(sections)}개 섹션 조회됨\n"]
                    for section in sections:
                        section_name = section.get("displayName") or section.get("name")
                        section_id = section.get("id")
                        web_url = section.get("links", {}).get("oneNoteWebUrl", {}).get("href")
                        output_lines.append(f"• {section_name}")
                        output_lines.append(f"  ID: {section_id}")
                        if web_url:
                            output_lines.append(f"  🔗 {web_url}")
                        output_lines.append("")

                    formatted_output = "\n".join(output_lines) + "\n" + json.dumps(result, indent=2, ensure_ascii=False)
                    return [TextContent(type="text", text=formatted_output)]

                return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

            elif name == "list_pages":
                user_id = arguments.get("user_id")
                section_id = arguments.get("section_id")
                section_name_filter = arguments.get("section_name")
                page_title_filter = arguments.get("page_title")

                # section_name으로 section_id 조회
                if section_name_filter and not section_id:
                    section_info = self.db_service.get_section(user_id, section_name_filter)
                    if section_info:
                        section_id = section_info['section_id']
                        logger.info(f"📌 DB에서 섹션 ID 조회: {section_name_filter} -> {section_id}")

                result = await self.onenote_handler.list_pages(user_id, section_id)

                # DB에 페이지들 저장 및 필터링
                if result.get("success") and result.get("pages"):
                    pages = result["pages"]

                    for page in pages:
                        page_id = page.get("id")
                        page_title = page.get("title")
                        # parentSection에서 section_id 추출 (모든 페이지 조회 시)
                        if not section_id:
                            parent_section = page.get("parentSection", {})
                            page_section_id = parent_section.get("id", "")
                        else:
                            page_section_id = section_id

                        if page_id and page_title and page_section_id:
                            self.db_service.save_page(
                                user_id, page_section_id, page_id, page_title,
                                update_accessed=True  # 조회 시 last_accessed 업데이트
                            )
                            logger.info(f"✅ 페이지 자동 저장: {page_title}")

                    # page_title 필터링
                    if page_title_filter:
                        pages = [p for p in pages if page_title_filter.lower() in (p.get("title") or "").lower()]
                        result["pages"] = pages
                        logger.info(f"🔍 페이지 제목 필터 적용: '{page_title_filter}' -> {len(pages)}개")

                    # 사용자 친화적인 출력 포맷 추가
                    output_lines = [f"📄 총 {len(pages)}개 페이지 조회됨\n"]
                    for page in pages:
                        page_title = page.get("title", "제목 없음")
                        page_id = page.get("id")
                        web_url = page.get("links", {}).get("oneNoteWebUrl", {}).get("href")
                        output_lines.append(f"• {page_title}")
                        output_lines.append(f"  ID: {page_id}")
                        if web_url:
                            output_lines.append(f"  🔗 {web_url}")
                        output_lines.append("")

                    formatted_output = "\n".join(output_lines) + "\n" + json.dumps(result, indent=2, ensure_ascii=False)
                    return [TextContent(type="text", text=formatted_output)]

                return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

            elif name == "get_page_content":
                request = GetPageContentRequest(**arguments)

                # 페이지 ID가 없으면 최근 사용 페이지 조회
                page_id = request.page_id
                if not page_id:
                    recent_page = self.db_service.get_recent_page(request.user_id)
                    if recent_page:
                        page_id = recent_page['page_id']
                        logger.info(f"📌 최근 사용 페이지 자동 선택: {recent_page['page_title']} ({page_id})")

                result = await self.onenote_handler.get_page_content(
                    request.user_id,
                    page_id
                )

                # 조회한 페이지를 최근 사용으로 마킹
                if result.get("success") and page_id:
                    page_title = result.get("title", "")
                    # DB에서 섹션 ID 조회
                    page_info = self.db_service.get_page(request.user_id, page_title) if page_title else None
                    if page_info:
                        self.db_service.save_page(
                            request.user_id,
                            page_info['section_id'],
                            page_id,
                            page_title,
                            mark_as_recent=True,
                            update_accessed=True  # 조회 시 last_accessed 업데이트
                        )

                response = GetPageContentResponse(**result)
                return [TextContent(type="text", text=response.model_dump_json(indent=2))]

            elif name == "create_page":
                request = CreatePageRequest(**arguments)

                # 섹션 ID가 없으면 최근 사용 섹션 조회
                section_id = request.section_id
                if not section_id:
                    recent_section = self.db_service.get_recent_section(request.user_id)
                    if recent_section:
                        section_id = recent_section['section_id']
                        logger.info(f"📌 최근 사용 섹션 자동 선택: {recent_section['section_name']} ({section_id})")

                result = await self.onenote_handler.create_page(
                    request.user_id,
                    section_id,
                    request.title,
                    request.content
                )

                # DB에 페이지 자동 저장
                if result.get("success") and result.get("page_id"):
                    self.db_service.save_page(
                        request.user_id,
                        section_id,
                        result["page_id"],
                        request.title,
                        mark_as_recent=False,
                        update_accessed=True  # 생성 시 last_accessed 업데이트
                    )
                    logger.info(f"✅ 생성된 페이지 DB 저장: {request.title}")

                response = CreatePageResponse(**result)
                return [TextContent(type="text", text=response.model_dump_json(indent=2))]

            elif name == "edit_page":
                request = UpdatePageRequest(**arguments)

                # 페이지 ID가 없으면 최근 사용 페이지 조회
                page_id = request.page_id
                if not page_id:
                    recent_page = self.db_service.get_recent_page(request.user_id)
                    if recent_page:
                        page_id = recent_page['page_id']
                        logger.info(f"📌 최근 사용 페이지 자동 선택: {recent_page['page_title']} ({page_id})")

                result = await self.onenote_handler.update_page(
                    request.user_id,
                    page_id,
                    request.content
                )

                # 업데이트한 페이지를 최근 사용으로 마킹
                if result.get("success") and page_id:
                    page_info = self.db_service.get_page(request.user_id, "")  # 제목으로 조회 안함
                    if page_info:
                        self.db_service.save_page(
                            request.user_id,
                            page_info.get('section_id', ''),
                            page_id,
                            page_info.get('page_title', ''),
                            mark_as_recent=True
                        )

                response = UpdatePageResponse(**result)
                return [TextContent(type="text", text=response.model_dump_json(indent=2))]

            elif name == "db_onenote_update":
                user_id = arguments.get("user_id")
                section_id = arguments.get("section_id")
                section_name = arguments.get("section_name")
                notebook_id = arguments.get("notebook_id")
                notebook_name = arguments.get("notebook_name")
                page_id = arguments.get("page_id")
                page_title = arguments.get("page_title")

                results = []

                # 섹션 정보 저장
                if section_id and section_name:
                    section_id = self.onenote_handler._normalize_onenote_id(section_id)
                    if notebook_id:
                        notebook_id = self.onenote_handler._normalize_onenote_id(notebook_id)

                    success = self.db_service.save_section(
                        user_id, notebook_id or "", section_id, section_name,
                        notebook_name=notebook_name,
                        update_accessed=True
                    )
                    results.append({
                        "type": "section",
                        "success": success,
                        "message": f"섹션 정보 저장: {section_name}" if success else "섹션 저장 실패"
                    })

                # 페이지 정보 저장
                if page_id and page_title:
                    page_id = self.onenote_handler._normalize_onenote_id(page_id)
                    if section_id:
                        section_id = self.onenote_handler._normalize_onenote_id(section_id)

                    success = self.db_service.save_page(
                        user_id, section_id or "", page_id, page_title,
                        update_accessed=True
                    )
                    results.append({
                        "type": "page",
                        "success": success,
                        "message": f"페이지 정보 저장: {page_title}" if success else "페이지 저장 실패"
                    })

                result = {
                    "success": all(r["success"] for r in results) if results else False,
                    "updates": results
                }
                return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

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
            # Handle OneNote-specific tools
            if name == "create_section":
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
                filter_section_name = arguments.get("section_name")
                result = await self.onenote_handler.list_sections(user_id)

                # DB에 섹션들 저장 및 필터링
                if result.get("success") and result.get("sections"):
                    sections = result["sections"]
                    for section in sections:
                        section_id = section.get("id")
                        section_name = section.get("displayName") or section.get("name")
                        parent_notebook = section.get("parentNotebook", {})
                        notebook_id = parent_notebook.get("id", "")
                        notebook_name = parent_notebook.get("displayName", "")

                        if section_id and section_name:
                            self.db_service.save_section(
                                user_id, notebook_id, section_id, section_name,
                                notebook_name=notebook_name,
                                update_accessed=True
                            )

                    if filter_section_name:
                        sections = [s for s in sections if filter_section_name.lower() in (s.get("displayName") or s.get("name") or "").lower()]
                        result["sections"] = sections

                return result

            elif name == "list_pages":
                user_id = arguments.get("user_id")
                section_id = arguments.get("section_id")
                section_name_filter = arguments.get("section_name")
                page_title_filter = arguments.get("page_title")

                # section_name으로 section_id 조회
                if section_name_filter and not section_id:
                    section_info = self.db_service.get_section(user_id, section_name_filter)
                    if section_info:
                        section_id = section_info['section_id']

                result = await self.onenote_handler.list_pages(user_id, section_id)

                # DB에 페이지들 저장 및 필터링
                if result.get("success") and result.get("pages"):
                    pages = result["pages"]
                    for page in pages:
                        page_id = page.get("id")
                        page_title = page.get("title")
                        if not section_id:
                            parent_section = page.get("parentSection", {})
                            page_section_id = parent_section.get("id", "")
                        else:
                            page_section_id = section_id

                        if page_id and page_title and page_section_id:
                            self.db_service.save_page(
                                user_id, page_section_id, page_id, page_title,
                                update_accessed=True
                            )

                    if page_title_filter:
                        pages = [p for p in pages if page_title_filter.lower() in (p.get("title") or "").lower()]
                        result["pages"] = pages

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

            elif name == "edit_page":
                request = UpdatePageRequest(**arguments)
                result = await self.onenote_handler.update_page(
                    request.user_id,
                    request.page_id,
                    request.content
                )
                return result

            elif name == "db_onenote_update":
                user_id = arguments.get("user_id")
                section_id = arguments.get("section_id")
                section_name = arguments.get("section_name")
                notebook_id = arguments.get("notebook_id")
                notebook_name = arguments.get("notebook_name")
                page_id = arguments.get("page_id")
                page_title = arguments.get("page_title")

                results = []

                # 섹션 정보 저장
                if section_id and section_name:
                    section_id = self.onenote_handler._normalize_onenote_id(section_id)
                    if notebook_id:
                        notebook_id = self.onenote_handler._normalize_onenote_id(notebook_id)

                    success = self.db_service.save_section(
                        user_id, notebook_id or "", section_id, section_name,
                        notebook_name=notebook_name,
                        update_accessed=True
                    )
                    results.append({
                        "type": "section",
                        "success": success,
                        "message": f"섹션 정보 저장: {section_name}" if success else "섹션 저장 실패"
                    })

                # 페이지 정보 저장
                if page_id and page_title:
                    page_id = self.onenote_handler._normalize_onenote_id(page_id)
                    if section_id:
                        section_id = self.onenote_handler._normalize_onenote_id(section_id)

                    success = self.db_service.save_page(
                        user_id, section_id or "", page_id, page_title,
                        update_accessed=True
                    )
                    results.append({
                        "type": "page",
                        "success": success,
                        "message": f"페이지 정보 저장: {page_title}" if success else "페이지 저장 실패"
                    })

                return {
                    "success": all(r["success"] for r in results) if results else False,
                    "updates": results
                }

            else:
                raise ValueError(f"알 수 없는 도구: {name}")

        except Exception as e:
            logger.error(f"❌ Tool 실행 오류: {name}, {str(e)}", exc_info=True)
            raise
