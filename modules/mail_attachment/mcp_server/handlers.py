"""MCP Protocol handlers"""

import json
import logging
from typing import Any, Dict, List

from mcp.types import Prompt, PromptArgument, PromptMessage, TextContent, Tool

from infra.core.logger import get_logger
from .prompts import get_prompt
from .tools import MailAttachmentTools
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
                name="list_active_accounts",
                title="👥 List Active Email Accounts",
                description="List all active email accounts",
                inputSchema={"type": "object", "properties": {}},
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
            if name == "query_email":
                result = await self.tools.query_email(arguments)
                return [TextContent(type="text", text=result)]
            
            elif name == "list_active_accounts":
                result = await self.tools.list_active_accounts()
                return [TextContent(type="text", text=result)]
            
            else:
                raise ValueError(f"Unknown tool: {name}")
        
        except Exception as e:
            logger.error(f"❌ Error in tool {name}: {str(e)}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def handle_list_prompts(self) -> List[Prompt]:
        """List available prompts"""
        logger.info("📋 [MCP Handler] list_prompts() called")
        
        # Return empty list as requested
        return []
    
    async def handle_get_prompt(self, name: str, arguments: Dict[str, Any]) -> PromptMessage:
        """Get specific prompt"""
        logger.info(f"📝 [MCP Handler] get_prompt() called with prompt: {name}")
        
        return await get_prompt(name, arguments)