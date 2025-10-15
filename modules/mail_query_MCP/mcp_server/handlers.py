"""MCP Protocol handlers"""

import json
import logging
from typing import Any, Dict, List

from mcp.types import Prompt, PromptArgument, PromptMessage, TextContent, Tool

from infra.core.logger import get_logger
from infra.core.error_messages import ErrorCode, MCPError
from .prompts import get_prompt
from .tools import MailAttachmentTools  # This now imports from tools/__init__.py
from .utils import preprocess_arguments

logger = get_logger(__name__)


class MCPHandlers:
    """MCP Protocol handlers"""
    
    def __init__(self):
        self.tools = MailAttachmentTools()
    
    async def handle_list_tools(self) -> List[Tool]:
        """List available tools"""
        logger.info("🔧 [MCP Handler] list_tools() called")

        return [
            Tool(
                name="register_account",
                title="📝 Register Account",
                description="Register a new email account with OAuth credentials and save to database",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID (e.g., 'kimghw')"},
                        "email": {"type": "string", "description": "Email address (e.g., 'kimghw@krs.co.kr')"},
                        "user_name": {"type": "string", "description": "User display name (optional, defaults to user_id)"},
                        "oauth_client_id": {"type": "string", "description": "Microsoft Azure App OAuth Client ID"},
                        "oauth_client_secret": {"type": "string", "description": "Microsoft Azure App OAuth Client Secret"},
                        "oauth_tenant_id": {"type": "string", "description": "Microsoft Azure AD Tenant ID"},
                        "oauth_redirect_uri": {"type": "string", "description": "OAuth redirect URI (optional, defaults to http://localhost:5000/auth/callback)"},
                    },
                    "required": ["user_id", "email", "oauth_client_id", "oauth_client_secret", "oauth_tenant_id"]
                }
            ),
            Tool(
                name="get_account_status",
                title="📊 Get Account Status",
                description="Get detailed status and authentication information for a specific account",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID to query"}
                    },
                    "required": ["user_id"]
                }
            ),
            Tool(
                name="start_authentication",
                title="🔐 Start OAuth Authentication",
                description="Start OAuth authentication flow for a registered account. Returns an authentication URL that you MUST open in a browser to complete Microsoft login. The URL will be provided as a clickable link - please click it to authorize access to the email account.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID (must be already registered)"}
                    },
                    "required": ["user_id"]
                }
            ),
            Tool(
                name="query_email",
                title="📧 Query Email",
                description="Query emails and download/convert attachments to text. Date priority: start_date/end_date > days_back",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "User ID to query - email prefix without @domain (e.g., 'kimghw' for kimghw@krs.co.kr)",
                        },
                        "days_back": {
                            "type": "integer",
                            "description": "Number of days to look back",
                            "default": 30,
                        },
                        "max_mails": {
                            "type": "integer",
                            "description": "Maximum number of mails to retrieve",
                            "default": 300,
                        },
                        "include_body": {
                            "type": "boolean",
                            "description": "Include full email body content in the response. When true, returns complete HTML/text content of each email. When false, only returns email preview (first ~255 chars). Useful for detailed content analysis",
                            "default": True,
                        },
                        "download_attachments": {
                            "type": "boolean",
                            "description": "Download email attachments and convert supported formats (PDF, DOCX, XLSX, etc.) to text. When true, creates local copies and includes text content in response. When false, only shows attachment metadata (name, size)",
                            "default": False,
                        },
                        "save_emails": {
                            "type": "boolean",
                            "description": "Save each email as individual text file to disk (mcp_attachments/{user_id}/). Files include headers, body, and attachment list. Useful for archiving or offline access. File names contain subject, date, and sender",
                            "default": True,
                        },
                        "save_csv": {
                            "type": "boolean",
                            "description": "Export all retrieved emails' metadata to a single CSV file. Includes: subject, sender, date, read status, importance, attachment count/names, body preview (100 chars). Excel-compatible format with UTF-8 BOM encoding",
                            "default": False,
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM-DD format. When user says 'this week', calculate 7 days ago from today. When 'last month', calculate 30 days ago. When 'last 3 months', calculate 90 days ago.",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in YYYY-MM-DD format. When user mentions a time period without specific end date, use today's date. For 'this week' or 'last month', end_date should be today.",
                        },
                        "sender_address": {
                            "type": "string",
                            "description": "받은 메일 필터: 특정 발신자가 나에게 보낸 메일만 조회. 예: 'kim@company.com' → kim이 나에게 보낸 메일만. (내가 kim에게 보낸 메일은 포함 안 됨)",
                        },
                        "subject_contains": {
                            "type": "string",
                            "description": "Filter emails by subject text. Only emails containing this text in the subject will be retrieved. Case-insensitive partial matching (e.g., 'meeting' matches 'Weekly Meeting Report').",
                        },
                        "keyword": {
                            "type": "string",
                            "description": "전체 메일 검색 키워드 (클라이언트 측 필터링). 제목, 본문, 발신자, 수신자, 첨부파일명 등 모든 필드에서 검색. 날짜/발신자 필터와 함께 사용 가능. 단순 키워드 검색만 지원. 예: '계약서', '프로젝트'. 고급 검색은 keyword_filter를 사용하세요.",
                        },
                        "keyword_filter": {
                            "type": "object",
                            "description": "구조화된 키워드 검색 필터 (클라이언트 측 필터링). AND/OR/NOT 조건을 조합하여 복잡한 검색 가능. 예: {\"and_keywords\": [\"계약서\", \"2024\"], \"not_keywords\": [\"취소\"]} → 계약서와 2024가 모두 포함되고 취소는 제외",
                            "properties": {
                                "and_keywords": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "AND 조건: 모든 키워드가 포함되어야 함. 예: [\"계약서\", \"2024\"] → 둘 다 포함"
                                },
                                "or_keywords": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "OR 조건: 하나 이상의 키워드가 포함되어야 함. 예: [\"계약서\", \"제안서\"] → 둘 중 하나 이상"
                                },
                                "not_keywords": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "NOT 조건: 이 키워드들이 포함되지 않아야 함. 예: [\"취소\", \"반려\"] → 둘 다 제외"
                                }
                            }
                        },
                        "recipient_address": {
                            "type": "string",
                            "description": "보낸 메일 필터: 내가 특정 수신자에게 보낸 메일만 조회. 예: 'kim@company.com' → 내가 kim에게 보낸 메일만. (kim이 나에게 보낸 메일은 포함 안 됨)",
                        },
                        "conversation_with": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "대화 전체 조회: 특정 사람과 주고받은 모든 메일. 이메일 주소 배열로 입력. 예: ['kim@company.com', 'lee@company.com'] → ①이 사람들이 나에게 보낸 메일 + ②내가 이 사람들에게 보낸 메일 모두 포함. 완전한 대화 내역을 보려면 이것을 사용하세요.",
                        },
                        "query_context": {
                            "type": "object",
                            "description": "Query context information for handling multi-turn conversations",
                            "properties": {
                                "is_first_query": {
                                    "type": "boolean",
                                    "description": "Whether this is the first query in the conversation. When true, all required fields must be provided. When false, missing fields may use previous values",
                                    "default": True
                                },
                                "conversation_turn": {
                                    "type": "integer",
                                    "description": "The conversation turn number (1 for first query, 2 for second, etc.)",
                                    "default": 1
                                },
                                "previous_user_id": {
                                    "type": "string",
                                    "description": "User ID from the previous query that can be reused if not specified in current query"
                                }
                            }
                        },
                    },
                    "required": [
                        "user_id",
                        "start_date",
                        "end_date",
                        "query_context"
                    ],
                },
            ),
            Tool(
                name="help",
                title="❓ Help",
                description="Get detailed help and documentation for available tools. Use without parameters to see all tools, or specify tool_name for detailed information",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tool_name": {
                            "type": "string",
                            "description": "Name of the tool to get help for (optional). If not specified, shows list of all available tools",
                            "enum": [
                                "register_account",
                                "get_account_status",
                                "start_authentication",
                                "query_email",
                                "help"
                            ]
                        }
                    }
                }
            ),
        ]
    
    async def handle_call_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle tool calls"""
        logger.info(f"🛠️ [MCP Handler] call_tool() called with tool: {name}")
        logger.info(f"📝 [MCP Handler] Raw arguments: {json.dumps(arguments, indent=2, ensure_ascii=False)}")

        # Preprocess arguments
        arguments = preprocess_arguments(arguments)
        logger.info(f"🔄 [MCP Handler] Preprocessed arguments: {json.dumps(arguments, indent=2, ensure_ascii=False)}")

        try:
            if name == "register_account":
                result = await self.tools.register_account(arguments)
                return [TextContent(type="text", text=result)]

            elif name == "get_account_status":
                result = await self.tools.get_account_status(arguments)
                return [TextContent(type="text", text=result)]

            elif name == "start_authentication":
                result = await self.tools.start_authentication(arguments)
                return [TextContent(type="text", text=result)]

            elif name == "query_email":
                result = await self.tools.query_email(arguments)
                return [TextContent(type="text", text=result)]

            elif name == "help":
                result = await self.tools.help(arguments)
                return [TextContent(type="text", text=result)]

            else:
                raise MCPError(
                    ErrorCode.MCP_TOOL_NOT_FOUND,
                    tool_name=name
                )

        except MCPError as e:
            logger.error(f"❌ MCP Error in tool {name}: {e.get_user_message()}")
            return [TextContent(type="text", text=e.get_user_message())]
        except Exception as e:
            logger.error(f"❌ Unexpected error in tool {name}: {str(e)}", exc_info=True)
            error = MCPError(
                ErrorCode.MCP_TOOL_EXECUTION_FAILED,
                tool_name=name,
                original_exception=e
            )
            return [TextContent(type="text", text=error.get_user_message())]
    
    async def handle_list_prompts(self) -> List[Prompt]:
        """List available prompts"""
        logger.info("📋 [MCP Handler] list_prompts() called")
        
        # Return empty list as requested
        return []
    
    async def handle_get_prompt(self, name: str, arguments: Dict[str, Any]) -> PromptMessage:
        """Get specific prompt"""
        logger.info(f"📝 [MCP Handler] get_prompt() called with prompt: {name}")
        
        return await get_prompt(name, arguments)