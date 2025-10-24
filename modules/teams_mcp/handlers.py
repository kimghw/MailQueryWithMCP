"""
Teams MCP Handlers
MCP 프로토콜 핸들러 레이어 - HTTP/stdio 공통 로직
"""

import json
from typing import Any, Dict, List
from mcp.types import Tool, TextContent

from infra.core.logger import get_logger
from .teams_handler import TeamsHandler
from .schemas import (
    ListTeamsRequest,
    ListTeamsResponse,
    ListChannelsRequest,
    ListChannelsResponse,
    SendMessageRequest,
    SendMessageResponse,
    GetMessagesRequest,
    GetMessagesResponse,
    GetRepliesRequest,
    GetRepliesResponse,
)

logger = get_logger(__name__)


class TeamsHandlers:
    """Teams MCP Protocol Handlers"""

    def __init__(self):
        """Initialize handlers with Teams handler instance"""
        self.teams_handler = TeamsHandler()
        logger.info("✅ TeamsHandlers initialized")

    # ========================================================================
    # MCP Protocol: list_tools
    # ========================================================================

    async def handle_list_tools(self) -> List[Tool]:
        """List available MCP tools (Teams Chat only)"""
        logger.info("🔧 [MCP Handler] list_tools() called")

        # Define Teams Chat-specific tools (1:1 and group chats)
        teams_tools = [
            Tool(
                name="teams_list_chats",
                description="사용자의 1:1 및 그룹 채팅 목록을 조회합니다.",
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
                name="teams_get_chat_messages",
                description="채팅의 메시지 목록을 조회합니다.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "사용자 ID"
                        },
                        "chat_id": {
                            "type": "string",
                            "description": "채팅 ID"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "조회할 메시지 수 (기본 50)",
                            "default": 50
                        }
                    },
                    "required": ["user_id", "chat_id"]
                }
            ),
            Tool(
                name="teams_send_chat_message",
                description="채팅에 메시지를 전송합니다.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "사용자 ID"
                        },
                        "chat_id": {
                            "type": "string",
                            "description": "채팅 ID"
                        },
                        "content": {
                            "type": "string",
                            "description": "메시지 내용"
                        },
                        "prefix": {
                            "type": "string",
                            "description": "메시지 앞에 붙을 프리픽스 (기본값: '[claude]')",
                            "default": "[claude]"
                        }
                    },
                    "required": ["user_id", "chat_id", "content"]
                }
            ),
        ]

        # Return Teams tools only
        return teams_tools

    # ========================================================================
    # MCP Protocol: call_tool
    # ========================================================================

    async def handle_call_tool(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle MCP tool calls (Teams Chat only)"""
        logger.info(f"🔨 [MCP Handler] call_tool({name}) with args: {arguments}")

        try:
            # Handle Teams Chat-specific tools
            if name == "teams_list_chats":
                user_id = arguments.get("user_id")
                result = await self.teams_handler.list_chats(user_id)

                # 사용자 친화적인 출력 포맷
                if result.get("success") and result.get("chats"):
                    chats = result["chats"]
                    output_lines = [f"💬 총 {len(chats)}개 채팅 조회됨\n"]
                    for chat in chats:
                        chat_type = chat.get("chatType", "unknown")
                        chat_id = chat.get("id")
                        topic = chat.get("topic", "(제목 없음)")

                        # chatType에 따라 표시
                        if chat_type == "oneOnOne":
                            output_lines.append(f"• [1:1] {topic}")
                        elif chat_type == "group":
                            output_lines.append(f"• [그룹] {topic}")
                        else:
                            output_lines.append(f"• [{chat_type}] {topic}")

                        output_lines.append(f"  ID: {chat_id}")
                        output_lines.append("")

                    formatted_output = "\n".join(output_lines) + "\n" + json.dumps(result, indent=2, ensure_ascii=False)
                    return [TextContent(type="text", text=formatted_output)]

                return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

            elif name == "teams_get_chat_messages":
                user_id = arguments.get("user_id")
                chat_id = arguments.get("chat_id")
                limit = arguments.get("limit", 50)

                result = await self.teams_handler.get_chat_messages(user_id, chat_id, limit)

                # 사용자 친화적인 출력 포맷
                if result.get("success") and result.get("messages"):
                    messages = result["messages"]
                    output_lines = [f"💬 총 {len(messages)}개 메시지 조회됨\n"]
                    for msg in messages:
                        msg_id = msg.get("id")
                        from_user = msg.get("from", {}).get("user", {}).get("displayName", "알 수 없음")
                        created = msg.get("createdDateTime", "")
                        body = msg.get("body", {}).get("content", "")
                        # HTML 태그 제거 (간단하게)
                        import re
                        body_text = re.sub('<[^<]+?>', '', body)[:200]  # 처음 200자만

                        output_lines.append(f"• [{created}] {from_user}")
                        output_lines.append(f"  ID: {msg_id}")
                        output_lines.append(f"  내용: {body_text}...")
                        output_lines.append("")

                    formatted_output = "\n".join(output_lines) + "\n" + json.dumps(result, indent=2, ensure_ascii=False)
                    return [TextContent(type="text", text=formatted_output)]

                return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

            elif name == "teams_send_chat_message":
                user_id = arguments.get("user_id")
                chat_id = arguments.get("chat_id")
                content = arguments.get("content")
                prefix = arguments.get("prefix", "[claude]")

                result = await self.teams_handler.send_chat_message(user_id, chat_id, content, prefix)
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
            if name == "teams_list_chats":
                user_id = arguments.get("user_id")
                return await self.teams_handler.list_chats(user_id)

            elif name == "teams_get_chat_messages":
                user_id = arguments.get("user_id")
                chat_id = arguments.get("chat_id")
                limit = arguments.get("limit", 50)
                return await self.teams_handler.get_chat_messages(user_id, chat_id, limit)

            elif name == "teams_send_chat_message":
                user_id = arguments.get("user_id")
                chat_id = arguments.get("chat_id")
                content = arguments.get("content")
                return await self.teams_handler.send_chat_message(user_id, chat_id, content)

            else:
                raise ValueError(f"알 수 없는 도구: {name}")

        except Exception as e:
            logger.error(f"❌ Tool 실행 오류: {name}, {str(e)}", exc_info=True)
            raise
