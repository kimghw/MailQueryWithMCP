"""HTTP Streaming-based MCP Server for Mail Attachments

This server uses HTTP streaming (chunked transfer encoding) for communication.
Provides email and attachment querying capabilities through MCP protocol.
"""

import asyncio
import csv
import json
import logging
import os
import secrets
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, AsyncIterator

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import (
    Tool,
    TextContent,
    Prompt,
    PromptMessage,
    PromptArgument,
)
from pydantic import BaseModel, Field
from starlette.applications import Starlette
from starlette.responses import StreamingResponse, JSONResponse, Response
from starlette.routing import Route
from starlette.requests import Request
import uvicorn

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from infra.core.database import get_database_manager
from infra.core.logger import get_logger
from modules.mail_query import (
    MailQueryFilters,
    MailQueryOrchestrator,
    MailQueryRequest,
    PaginationOptions,
)
from modules.mail_attachment import AttachmentDownloader, FileConverter, EmailSaver

logger = get_logger(__name__)


class HTTPStreamingMailAttachmentServer:
    """HTTP Streaming-based MCP Server for Mail Attachments"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8002):
        self.host = host
        self.port = port
        
        # MCP Server
        self.mcp_server = Server("mail-attachment-server")
        
        # Database
        self.db = get_database_manager()
        
        # Attachment handling components
        self.attachment_downloader = AttachmentDownloader("./mcp_attachments")
        self.file_converter = FileConverter()
        self.email_saver = EmailSaver("./mcp_attachments")
        
        # Active sessions
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        # Store handlers for direct access
        self._handlers = {}
        
        # Register handlers
        self._register_handlers()
        
        # Create Starlette app
        self.app = self._create_app()
        
        logger.info(f"🚀 HTTP Streaming Mail Attachment Server initialized on port {port}")
    
    def _register_handlers(self):
        """Register MCP protocol handlers"""
        
        @self.mcp_server.list_tools()
        async def handle_list_tools() -> List[Tool]:
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
                                "description": "User ID to query - email prefix without @domain (e.g., 'kimghw' for kimghw@krs.co.kr)"
                            },
                            "days_back": {
                                "type": "integer",
                                "description": "Number of days to look back",
                                "default": 30
                            },
                            "max_mails": {
                                "type": "integer",
                                "description": "Maximum number of mails to retrieve",
                                "default": 100
                            },
                            "include_body": {
                                "type": "boolean",
                                "description": "Include full email body",
                                "default": True
                            },
                            "download_attachments": {
                                "type": "boolean",
                                "description": "Download and convert attachments",
                                "default": True
                            },
                            "has_attachments_filter": {
                                "type": "boolean",
                                "description": "Filter for emails with attachments only"
                            },
                            "save_emails": {
                                "type": "boolean",
                                "description": "Save email bodies as text files",
                                "default": True
                            },
                            "save_csv": {
                                "type": "boolean",
                                "description": "Save email metadata as CSV file",
                                "default": True
                            },
                            "start_date": {
                                "type": "string",
                                "description": "Start date in YYYY-MM-DD format. When user says 'this week', calculate 7 days ago from today. When 'last month', calculate 30 days ago. When 'last 3 months', calculate 90 days ago."
                            },
                            "end_date": {
                                "type": "string",
                                "description": "End date in YYYY-MM-DD format. When user mentions a time period without specific end date, use today's date. For 'this week' or 'last month', end_date should be today."
                            }
                        },
                        "required": ["user_id", "start_date", "end_date", "max_mails", "include_body", "download_attachments", "save_emails", "save_csv"]
                    }
                ),
                Tool(
                    name="list_active_accounts",
                    title="👥 List Active Email Accounts",
                    description="List all active email accounts",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="convert_file_to_text",
                    title="📄 Convert File to Text",
                    description="Convert a file (PDF, Word, Excel, etc.) to text",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to convert"
                            }
                        },
                        "required": ["file_path"]
                    }
                )
            ]
        
        # Store handler for direct access
        self._handlers['list_tools'] = handle_list_tools
        
        @self.mcp_server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls"""
            logger.info(f"🛠️ [MCP Handler] call_tool() called with tool: {name}")
            logger.info(f"📝 [MCP Handler] Raw arguments: {json.dumps(arguments, indent=2, ensure_ascii=False)}")
            
            # Preprocess arguments
            arguments = self._preprocess_arguments(arguments)
            logger.info(f"🔄 [MCP Handler] Preprocessed arguments: {json.dumps(arguments, indent=2, ensure_ascii=False)}")
            
            try:
                if name == "query_email":
                    result = await self._handle_mail_query(arguments)
                    return [TextContent(type="text", text=result)]
                    
                    
                elif name == "list_active_accounts":
                    result = await self._handle_list_accounts()
                    return [TextContent(type="text", text=result)]
                    
                elif name == "convert_file_to_text":
                    result = await self._handle_file_conversion(arguments)
                    return [TextContent(type="text", text=result)]
                    
                else:
                    raise ValueError(f"Unknown tool: {name}")
                    
            except Exception as e:
                logger.error(f"❌ Error in tool {name}: {str(e)}", exc_info=True)
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        # Store handler for direct access
        self._handlers['call_tool'] = handle_call_tool
        
        @self.mcp_server.list_prompts()
        async def handle_list_prompts() -> List[Prompt]:
            """List available prompts"""
            logger.info("📋 [MCP Handler] list_prompts() called")
            
            return [
                Prompt(
                    name="mail_attachment_query",
                    description="Query emails with attachment handling",
                    arguments=[
                        PromptArgument(
                            name="user_query",
                            description="Natural language query about emails",
                            required=True
                        )
                    ]
                ),
                Prompt(
                    name="format_email_results",
                    description="Format email query results for user presentation",
                    arguments=[
                        PromptArgument(
                            name="format_style",
                            description="Formatting style (table, summary, detailed, bullet_points)",
                            required=True
                        ),
                        PromptArgument(
                            name="include_attachments",
                            description="Whether to include attachment content in the summary",
                            required=False
                        )
                    ]
                ),
                Prompt(
                    name="attachment_summary_format",
                    description="Format attachment contents for clear user presentation",
                    arguments=[
                        PromptArgument(
                            name="summary_length",
                            description="Length of summary (brief, standard, detailed)",
                            required=True
                        ),
                        PromptArgument(
                            name="highlight_sections",
                            description="Sections to highlight (dates, names, numbers, keywords)",
                            required=False
                        )
                    ]
                )
            ]
        
        # Store handler for direct access
        self._handlers['list_prompts'] = handle_list_prompts
        
        @self.mcp_server.get_prompt()
        async def handle_get_prompt(name: str, arguments: Dict[str, Any]) -> PromptMessage:
            """Get specific prompt"""
            logger.info(f"📝 [MCP Handler] get_prompt() called with prompt: {name}")
            
            if name == "mail_attachment_query":
                user_query = arguments.get("user_query", "")
                prompt_content = f"""
메일 첨부파일 조회 시스템입니다.

사용자 질의: {user_query}

사용 가능한 기능:
1. 특정 사용자의 메일 조회
2. 첨부파일 다운로드 및 텍스트 변환
3. 날짜 범위 및 필터 적용

조회할 사용자 ID와 조건을 지정해주세요.
"""
                
            elif name == "format_email_results":
                format_style = arguments.get("format_style", "summary")
                include_attachments = arguments.get("include_attachments", True)
                
                prompt_content = f"""
📧 이메일 조회 결과 포맷팅 지침

포맷 스타일: {format_style}
첨부파일 포함: {include_attachments}

다음 순서와 형식으로 테이블을 작성하세요:

**📊 표 구성 (필수 열)**:
| 날짜 | 발신자 | 제목 | 주요내용 | 응답필요성 | 응답기한 | 첨부 |

**각 열 작성 지침**:
1. **날짜**: YYYY-MM-DD HH:MM 형식
2. **발신자**: 이름 (이메일) 형식
3. **제목**: 전체 제목 (너무 길면 ... 사용)
4. **주요내용**: 핵심 내용 1-2줄 요약
5. **응답필요성**: 
   - 🔴 중요 (응답 필요)
   - 🟢 일반 (참고용)
6. **응답기한**: 구체적 날짜 또는 "즉시", "3일 내", "없음" 등
7. **첨부**: 파일명 (파일형식) 또는 "없음"

**응답 필요성 판단 기준**:
- 질문이 포함된 경우
- "회신 요청", "답변 부탁" 등의 표현
- 마감일이 명시된 경우
- 승인/검토 요청이 있는 경우

**예시**:
| 2024-01-15 09:30 | 김철수 (kim@company.com) | 프로젝트 진행 현황 보고 | Q1 목표 달성률 85%, 추가 예산 승인 요청 | 🔴 긴급 | 1/17까지 | 보고서.pdf |

이메일 내용과 첨부파일을 분석하여 응답 필요성과 기한을 정확히 판단하세요.
"""

            elif name == "attachment_summary_format":
                summary_length = arguments.get("summary_length", "standard")
                highlight_sections = arguments.get("highlight_sections", "")
                
                prompt_content = f"""
📎 첨부파일 내용 요약 지침

요약 길이: {summary_length}
강조 섹션: {highlight_sections}

첨부파일 내용을 다음 기준으로 정리하세요:

{'**간략 요약** (3-5줄)' if summary_length == 'brief' else ''}
{'- 핵심 내용만 추출' if summary_length == 'brief' else ''}
{'- 가장 중요한 정보 위주' if summary_length == 'brief' else ''}

{'**표준 요약** (10-15줄)' if summary_length == 'standard' else ''}
{'- 주요 섹션별로 정리' if summary_length == 'standard' else ''}
{'- 중요 데이터 포함' if summary_length == 'standard' else ''}

{'**상세 요약** (전체 구조 포함)' if summary_length == 'detailed' else ''}
{'- 모든 섹션 포함' if summary_length == 'detailed' else ''}
{'- 세부 내용까지 정리' if summary_length == 'detailed' else ''}

{f'강조할 내용: {highlight_sections}' if highlight_sections else ''}

포맷 규칙:
- 📅 날짜는 굵게 표시
- 👤 인물명은 밑줄
- 💰 금액/숫자는 하이라이트
- 🔑 중요 키워드는 백틱(`)으로 감싸기

명확하고 구조화된 형태로 제공하세요.
"""
                
            else:
                raise ValueError(f"Unknown prompt: {name}")
            
            return PromptMessage(
                role="assistant",
                content=TextContent(type="text", text=prompt_content)
            )
        
        # Store handler for direct access
        self._handlers['get_prompt'] = handle_get_prompt
    
    def _preprocess_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess arguments from Claude Desktop"""
        import json
        
        # Clean backslashes from all string values
        def clean_backslashes(obj):
            if isinstance(obj, str):
                return obj.replace("\\", "")
            elif isinstance(obj, dict):
                return {k: clean_backslashes(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_backslashes(item) for item in obj]
            return obj
        
        arguments = clean_backslashes(arguments)
        
        # Special handling for integer fields
        int_fields = ['days_back', 'max_mails', 'limit']
        for field in int_fields:
            if field in arguments and isinstance(arguments[field], str):
                cleaned_value = arguments[field].strip().strip("'").strip('"')
                try:
                    arguments[field] = int(cleaned_value)
                except ValueError:
                    pass
        
        # Handle string-wrapped JSON
        if "extracted_period" in arguments and isinstance(
            arguments["extracted_period"], str
        ):
            try:
                arguments["extracted_period"] = json.loads(
                    arguments["extracted_period"]
                )
            except:
                pass
        
        if "extracted_keywords" in arguments and isinstance(
            arguments["extracted_keywords"], str
        ):
            try:
                arguments["extracted_keywords"] = json.loads(
                    arguments["extracted_keywords"]
                )
            except:
                pass
        
        # Handle string "null" to actual null
        null_fields = ["extracted_organization", "category", "query_scope", "intent"]
        for key in null_fields:
            if key in arguments and arguments[key] == "null":
                arguments[key] = None
        
        # Handle boolean fields
        bool_fields = ['include_body', 'download_attachments', 'has_attachments_filter', 'execute', 'use_defaults']
        for field in bool_fields:
            if field in arguments:
                if isinstance(arguments[field], str):
                    arguments[field] = arguments[field].lower() == 'true'
        
        return arguments
    
    async def _handle_mail_query(self, arguments: Dict[str, Any]) -> str:
        """Handle mail query with attachments"""
        try:
            # Extract parameters
            user_id = arguments.get('user_id')
            if not user_id:
                return "Error: user_id is required"
            
            days_back = arguments.get('days_back', 30)
            max_mails = arguments.get('max_mails', 10)
            include_body = arguments.get('include_body', False)
            download_attachments = arguments.get('download_attachments', True)
            has_attachments_filter = arguments.get('has_attachments_filter')
            save_emails = arguments.get('save_emails', True)
            save_csv = arguments.get('save_csv', True)
            start_date_str = arguments.get('start_date')
            end_date_str = arguments.get('end_date')
            
            # Create mail query
            orchestrator = MailQueryOrchestrator()
            
            # Parse dates if provided - Priority: date range > days_back
            start_date = None
            end_date = None
            
            # Both dates specified
            if start_date_str and end_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                    
                    if start_date > end_date:
                        return "Error: start_date is later than end_date"
                    
                    # days_back is ignored when both dates are specified
                    days_back = (end_date - start_date).days + 1
                    
                except ValueError as e:
                    return f"Error: Invalid date format. Expected YYYY-MM-DD. {str(e)}"
            
            # Only start date specified
            elif start_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                    end_date = datetime.now()
                    days_back = (end_date - start_date).days + 1
                except ValueError:
                    return f"Error: Invalid start_date format. Expected YYYY-MM-DD, got {start_date_str}"
            
            # Only end date specified
            elif end_date_str:
                try:
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                    start_date = end_date - timedelta(days=days_back - 1)
                except ValueError:
                    return f"Error: Invalid end_date format. Expected YYYY-MM-DD, got {end_date_str}"
            
            # No dates specified, use days_back from now
            else:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days_back - 1)
            
            # Setup filters with the calculated date range
            filters = MailQueryFilters(
                date_from=start_date,
                date_to=end_date
            )
            
            if has_attachments_filter is not None:
                filters.has_attachments = has_attachments_filter
            
            # Setup fields
            select_fields = [
                "id", "subject", "from", "sender", "receivedDateTime",
                "bodyPreview", "hasAttachments", "importance", "isRead"
            ]
            if include_body:
                select_fields.append("body")
            if download_attachments or has_attachments_filter:
                select_fields.append("attachments")
            
            # Create request
            request = MailQueryRequest(
                user_id=user_id,
                filters=filters,
                pagination=PaginationOptions(top=max_mails, skip=0, max_pages=1),
                select_fields=select_fields
            )
            
            # Execute query
            async with orchestrator:
                response = await orchestrator.mail_query_user_emails(request)
                graph_client = orchestrator.graph_client if download_attachments else None
            
            # Format results
            result_text = f"📧 메일 조회 결과 - {user_id}\n"
            result_text += f"{'='*60}\n"
            # Display date range info
            if start_date and end_date:
                result_text += f"조회 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')} ({days_back}일간)\n"
            else:
                result_text += f"조회 기간: 최근 {days_back}일\n"
            result_text += f"총 메일 수: {response.total_fetched}개\n\n"
            
            # Process each mail
            blocked_senders = ['block@krs.co.kr']  # 차단할 발신자 목록
            processed_mails = []  # CSV를 위한 메일 정보 수집
            
            for i, mail in enumerate(response.messages, 1):
                # Extract sender info
                sender = "Unknown"
                sender_email = None
                if mail.from_address and isinstance(mail.from_address, dict):
                    email_addr = mail.from_address.get("emailAddress", {})
                    sender_email = email_addr.get("address", "Unknown")
                    sender = sender_email
                    sender_name = email_addr.get("name", "")
                    if sender_name:
                        sender = f"{sender_name} <{sender_email}>"
                
                # 차단된 발신자인 경우 스킵
                if sender_email and sender_email.lower() in [s.lower() for s in blocked_senders]:
                    continue
                
                # Save email if requested
                if save_emails:
                    try:
                        # Convert mail to dict format
                        mail_dict = mail.model_dump() if hasattr(mail, 'model_dump') else mail.__dict__
                        
                        # Field name mapping (Graph API -> email_saver format)
                        if 'receivedDateTime' in mail_dict:
                            mail_dict['received_date_time'] = mail_dict.get('receivedDateTime')
                        if 'from' in mail_dict:
                            mail_dict['from_address'] = mail_dict.get('from')
                        if 'toRecipients' in mail_dict:
                            mail_dict['to_recipients'] = mail_dict.get('toRecipients')
                        if 'isRead' in mail_dict:
                            mail_dict['is_read'] = mail_dict.get('isRead')
                        if 'hasAttachments' in mail_dict:
                            mail_dict['has_attachments'] = mail_dict.get('hasAttachments')
                        if 'bodyPreview' in mail_dict:
                            mail_dict['body_preview'] = mail_dict.get('bodyPreview')
                        if 'webLink' in mail_dict:
                            mail_dict['web_link'] = mail_dict.get('webLink')
                        
                        saved_result = await self.email_saver.save_email_as_text(
                            mail_dict,
                            user_id,
                            include_headers=True,
                            save_html=include_body,
                            upload_to_onedrive=False,
                            graph_client=None
                        )
                        
                        mail_saved_path = str(saved_result["text_file"])
                    except Exception as e:
                        logger.error(f"Failed to save email: {str(e)}")
                        mail_saved_path = None
                
                # Collect mail info for CSV
                mail_info = {
                    "id": mail.id,
                    "subject": mail.subject,
                    "sender": sender,
                    "sender_email": sender_email or "unknown@email.com",
                    "received_date": mail.received_date_time.strftime("%Y-%m-%d %H:%M"),
                    "received_date_time": mail.received_date_time,
                    "has_attachments": mail.has_attachments,
                    "is_read": mail.is_read,
                    "importance": mail.importance,
                    "attachments": []
                }
                
                # Add body content to mail_info if available
                if include_body and mail.body:
                    content_type = mail.body.get("contentType", "text")
                    content = mail.body.get("content", "")
                    
                    if content_type.lower() == "html":
                        # Simple HTML stripping
                        import re
                        text_content = re.sub('<[^<]+?>', '', content)
                        text_content = text_content.replace('&nbsp;', ' ')
                        text_content = text_content.replace('&lt;', '<')
                        text_content = text_content.replace('&gt;', '>')
                        text_content = text_content.replace('&amp;', '&')
                        mail_info["body"] = text_content
                    else:
                        mail_info["body"] = content
                elif mail.body_preview:
                    mail_info["body_preview"] = mail.body_preview
                
                # Format mail info
                result_text += f"\n[{i}] {mail.subject}\n"
                result_text += f"   발신자: {sender}\n"
                result_text += f"   수신일: {mail.received_date_time.strftime('%Y-%m-%d %H:%M')}\n"
                result_text += f"   읽음: {'✓' if mail.is_read else '✗'}\n"
                result_text += f"   첨부: {'📎' if mail.has_attachments else '-'}\n"
                if save_emails and mail_saved_path:
                    result_text += f"   💾 저장됨: {mail_saved_path}\n"
                
                # Include body if requested
                if include_body and mail.body:
                    content = mail.body.get("content", "")
                    if mail.body.get("contentType") == "html":
                        # Simple HTML stripping
                        import re
                        content = re.sub('<[^<]+?>', '', content)
                        content = content.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
                    result_text += f"   본문:\n{content[:500]}...\n" if len(content) > 500 else f"   본문:\n{content}\n"
                
                # Process attachments
                if download_attachments and mail.has_attachments and hasattr(mail, 'attachments') and mail.attachments:
                    result_text += f"\n   📎 첨부파일:\n"
                    
                    for attachment in mail.attachments:
                        att_name = attachment.get('name', 'unknown')
                        att_size = attachment.get('size', 0)
                        result_text += f"      - {att_name} ({att_size:,} bytes)\n"
                        
                        # Add attachment info to mail_info
                        attachment_info = {
                            "name": att_name,
                            "size": att_size
                        }
                        
                        # Download and convert
                        if graph_client:
                            try:
                                # Download attachment
                                file_path = await self.attachment_downloader.download_and_save(
                                    graph_client,
                                    mail.id,
                                    attachment,
                                    user_id,
                                    email_subject=mail.subject,
                                    email_date=mail.received_date_time,
                                    sender_email=sender_email
                                )
                                
                                if file_path:
                                    result_text += f"        ✅ 다운로드: {file_path['file_path']}\n"
                                    attachment_info["file_path"] = str(file_path['file_path'])
                                    
                                    # Convert to text if supported
                                    if self.file_converter.is_supported(file_path['file_path']):
                                        text_content = self.file_converter.convert_to_text(file_path['file_path'])
                                        text_file = self.file_converter.save_as_text(file_path['file_path'], text_content, att_name)
                                        result_text += f"        📄 텍스트 변환: {text_file}\n"
                                        attachment_info["text_path"] = str(text_file)
                                        
                                        # Include full text content
                                        attachment_info["text_content"] = text_content
                                        
                                        # Include preview
                                        preview = text_content[:3000] + "..." if len(text_content) > 3000 else text_content
                                        result_text += f"        미리보기: {preview}\n"
                                        attachment_info["text_preview"] = preview
                                    else:
                                        result_text += f"        ⚠️  지원하지 않는 형식\n"
                                        
                            except Exception as e:
                                result_text += f"        ❌ 처리 실패: {str(e)}\n"
                        
                        # Add attachment info to mail_info
                        mail_info["attachments"].append(attachment_info)
                
                # Add mail_info to processed_mails list
                processed_mails.append(mail_info)
                
                result_text += "\n" + "-"*60 + "\n"
            
            # CSV로 메일 메타데이터 저장
            if save_csv and processed_mails:
                try:
                    csv_file = self.save_emails_to_csv(processed_mails, user_id)
                    result_text += f"\n📊 메일 메타데이터 CSV 저장 완료: {csv_file}\n"
                except Exception as e:
                    logger.error(f"CSV 저장 실패: {str(e)}")
                    result_text += f"\n❌ CSV 저장 중 오류 발생: {str(e)}\n"
            
            # 포맷팅 지침 추가
            result_text += "\n\n" + "="*60 + "\n"
            result_text += "📊 LLM 응답 포맷팅 지침\n"
            result_text += "="*60 + "\n"
            result_text += """
위 메일들을 다음 테이블 형식으로 정리해주세요:

| 날짜 | 발신자 | 제목 | 주요내용 | 응답필요성 | 응답기한 | 첨부 |

응답필요성 기준:
- 🔴 중요: 응답 필요 (회신/승인/검토 요청 등)
- 🟢 일반: 단순 참고/공지 (응답 불필요)

각 메일의 내용과 첨부파일을 분석하여 응답 필요성과 기한을 판단하세요.
"""
            
            # 다운로드된 파일들 삭제
            try:
                import shutil
                user_dir = Path(self.attachment_downloader.output_dir) / user_id
                if user_dir.exists():
                    shutil.rmtree(user_dir)
                    logger.info(f"✅ 사용자 디렉토리 삭제 완료: {user_dir}")
            except Exception as e:
                logger.error(f"파일 삭제 중 오류: {str(e)}")
            
            return result_text
            
        except Exception as e:
            logger.error(f"Mail query error: {str(e)}", exc_info=True)
            return f"❌ 메일 조회 실패: {str(e)}"
    
    async def _handle_list_accounts(self) -> str:
        """List active email accounts"""
        try:
            query = """
                SELECT 
                    user_id, 
                    user_name, 
                    email,
                    is_active,
                    status,
                    last_sync_time
                FROM accounts 
                WHERE is_active = 1
                ORDER BY user_id
            """
            accounts = self.db.fetch_all(query)
            
            result_text = "👥 활성 이메일 계정 목록\n"
            result_text += "="*60 + "\n\n"
            
            for account in accounts:
                result_text += f"• {account['user_id']}"
                if account['user_name']:
                    result_text += f" ({account['user_name']})"
                if account['email']:
                    result_text += f" - {account['email']}"
                result_text += f"\n  상태: {account['status']}"
                if account['last_sync_time']:
                    result_text += f", 마지막 동기화: {account['last_sync_time']}"
                result_text += "\n\n"
            
            result_text += f"\n총 {len(accounts)}개 계정"
            
            return result_text
            
        except Exception as e:
            logger.error(f"List accounts error: {str(e)}", exc_info=True)
            return f"❌ 계정 목록 조회 실패: {str(e)}"
    
    def save_emails_to_csv(self, emails: List[Dict[str, Any]], user_id: str) -> Path:
        """Save email metadata to CSV file"""
        # CSV file path
        csv_dir = Path(self.attachment_downloader.output_dir) / user_id
        csv_dir.mkdir(parents=True, exist_ok=True)
        
        # Include timestamp in filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = csv_dir / f"email_metadata_{timestamp}.csv"
        
        # Write CSV
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            # UTF-8 BOM for Korean characters in Excel
            fieldnames = [
                '번호',
                '제목',
                '발신자',
                '발신자_이메일',
                '수신일시',
                '읽음상태',
                '중요도',
                '첨부파일',
                '첨부파일_개수',
                '첨부파일_목록',
                '본문_미리보기',
                '폴더명',
                'message_id'
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for idx, email in enumerate(emails, 1):
                # Process attachment info
                attachment_names = []
                attachment_count = 0
                if email.get('attachments'):
                    attachment_names = [att['name'] for att in email['attachments']]
                    attachment_count = len(attachment_names)
                
                # Generate folder name (same as actual save folder)
                safe_subject = self.attachment_downloader._sanitize_filename(email.get('subject', 'NoSubject')[:50])
                received_datetime = email.get('received_date_time', datetime.now())
                date_str = received_datetime.strftime('%Y%m%d_%H%M%S') if isinstance(received_datetime, datetime) else datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_sender = self.attachment_downloader._sanitize_filename(email.get('sender_email', 'unknown'))  # Use full email
                folder_name = f"{safe_subject}_{date_str}_{safe_sender}"
                
                # Get body preview
                body_preview = ""
                if 'body' in email:
                    body_preview = email['body'][:100].replace('\n', ' ').replace('\r', ' ')
                elif 'body_preview' in email:
                    body_preview = email['body_preview'][:100].replace('\n', ' ').replace('\r', ' ')
                
                row = {
                    '번호': idx,
                    '제목': email.get('subject', ''),
                    '발신자': email.get('sender', ''),
                    '발신자_이메일': email.get('sender_email', ''),
                    '수신일시': email.get('received_date', ''),
                    '읽음상태': '읽음' if email.get('is_read', False) else '안읽음',
                    '중요도': email.get('importance', 'normal'),
                    '첨부파일': '있음' if email.get('has_attachments', False) else '없음',
                    '첨부파일_개수': attachment_count,
                    '첨부파일_목록': '; '.join(attachment_names) if attachment_names else '',
                    '본문_미리보기': body_preview,
                    '폴더명': folder_name,
                    'message_id': email.get('id', '')
                }
                
                writer.writerow(row)
        
        logger.info(f"Email metadata CSV saved: {csv_file}")
        return csv_file
    
    async def _handle_file_conversion(self, arguments: Dict[str, Any]) -> str:
        """Convert file to text"""
        try:
            file_path = Path(arguments.get('file_path', ''))
            
            if not file_path.exists():
                return f"❌ 파일을 찾을 수 없습니다: {file_path}"
            
            if not self.file_converter.is_supported(file_path):
                return f"❌ 지원하지 않는 파일 형식: {file_path.suffix}"
            
            # Convert to text
            text_content = self.file_converter.convert_to_text(file_path)
            
            # Save as text file
            text_file = self.file_converter.save_as_text(file_path, text_content)
            
            result_text = f"📄 파일 변환 완료\n"
            result_text += f"{'='*60}\n"
            result_text += f"원본 파일: {file_path}\n"
            result_text += f"텍스트 파일: {text_file}\n"
            result_text += f"파일 크기: {len(text_content):,} 글자\n\n"
            result_text += f"내용:\n{'-'*60}\n"
            result_text += text_content
            
            return result_text
            
        except Exception as e:
            logger.error(f"File conversion error: {str(e)}", exc_info=True)
            return f"❌ 파일 변환 실패: {str(e)}"
    
    async def _send_list_changed_notifications(self, request: Request):
        """Send list changed notifications after initialization"""
        # Wait a bit to ensure client is ready
        await asyncio.sleep(0.1)
        
        # Note: In a real implementation, we would need to track the client's SSE connection
        # For now, we'll just log that we would send these
        logger.info("📤 Would send notifications/tools/list_changed")
        logger.info("📤 Would send notifications/prompts/list_changed")
        logger.info("📤 Would send notifications/resources/list_changed")
    
    async def _handle_streaming_request(self, request: Request):
        """Handle MCP request - returns single JSON response"""
        # Common headers
        base_headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS, DELETE",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Mcp-Session-Id, MCP-Protocol-Version",
            "Access-Control-Expose-Headers": "Mcp-Session-Id",
        }
        
        # Read and parse request
        try:
            body = await request.body()
            if not body:
                return JSONResponse(
                    {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Empty request body"}},
                    status_code=400,
                    headers=base_headers
                )
            
            try:
                rpc_request = json.loads(body)
            except json.JSONDecodeError as e:
                return JSONResponse(
                    {"jsonrpc": "2.0", "error": {"code": -32700, "message": f"Parse error: {str(e)}"}},
                    status_code=400,
                    headers=base_headers
                )
        except Exception as e:
            return JSONResponse(
                {"jsonrpc": "2.0", "error": {"code": -32603, "message": f"Internal error: {str(e)}"}},
                status_code=500,
                headers=base_headers
            )
        
        # Extract request details
        method = rpc_request.get('method')
        params = rpc_request.get('params', {}) or {}
        request_id = rpc_request.get('id')
        
        logger.info(f"📨 Received RPC request: {method} with id: {request_id}")
        
        # Handle notification (no id) - return 202 with no body
        if request_id is None:
            logger.info(f"📤 Handling notification: {method}")
            
            # If this is the initialized notification, send list changed notifications
            if method == 'notifications/initialized':
                # Send tools list changed notification after a short delay
                asyncio.create_task(self._send_list_changed_notifications(request))
            
            return Response(status_code=202, headers=base_headers)
        
        # Process based on method
        logger.info(f"📤 Processing method: {method} with params: {params}")
        
        if method == 'initialize':
            # Initialize session with standard Mcp-Session-Id
            session_id = secrets.token_urlsafe(24)
            caps = self.mcp_server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={}
            )
            
            # Fix null fields to empty objects/lists for spec compliance
            caps_dict = caps.model_dump()
            if caps_dict.get('logging') is None:
                caps_dict['logging'] = {}
            if caps_dict.get('resources') is None:
                caps_dict['resources'] = {
                    "listChanged": False
                }
            # Remove completions field if it's null (not supported by this server)
            if caps_dict.get('completions') is None:
                caps_dict.pop('completions', None)
            
            self.sessions[session_id] = {
                'initialized': True,
                'capabilities': caps_dict
            }
            
            # Use the protocol version requested by the client
            requested_version = params.get('protocolVersion', '2025-06-18')
            
            # Add session header and ensure it's exposed
            headers = base_headers.copy()
            headers["Mcp-Session-Id"] = session_id
            headers["MCP-Protocol-Version"] = requested_version
            headers["Access-Control-Expose-Headers"] = "Mcp-Session-Id, MCP-Protocol-Version"
            
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": requested_version,
                    # Use fixed capabilities (with logging as empty object)
                    "capabilities": caps_dict,
                    "serverInfo": {
                        "name": "mail-attachment-server",
                        "title": "📧 Mail Attachment Server",
                        "version": "2.0.0",
                        "description": "MCP server for email attachment handling"
                    },
                    "instructions": "이메일과 첨부파일을 조회하고 텍스트로 변환하는 MCP 서버입니다."
                }
            }
            logger.info(f"📤 Sending initialize response: {json.dumps(response, indent=2)}")
            return JSONResponse(response, headers=headers)
        
        elif method == 'tools/list':
            # List tools
            if 'list_tools' in self._handlers:
                tools = await self._handlers['list_tools']()
            else:
                tools = []
            
            # Clean up tool data - remove null fields
            tools_data = []
            for tool in tools:
                tool_dict = tool.model_dump()
                # Remove null fields as per spec
                cleaned_tool = {}
                for key, value in tool_dict.items():
                    if value is not None:
                        cleaned_tool[key] = value
                tools_data.append(cleaned_tool)
            
            # Debug: Log the actual tool data being sent
            logger.info(f"📤 Tool data details: {json.dumps(tools_data, indent=2)}")
            
            logger.info(f"📤 Returning {len(tools_data)} tools: {[t['name'] for t in tools_data]}")
            
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": tools_data
                }
            }
            return JSONResponse(response, headers=base_headers)
        
        elif method == 'tools/call':
            # Call tool
            tool_name = params.get('name')
            tool_args = params.get('arguments', {})
            
            logger.info(f"🔧 [MCP Server] Received tools/call request")
            logger.info(f"  • Tool: {tool_name}")
            logger.info(f"  • Arguments: {json.dumps(tool_args, indent=2, ensure_ascii=False)}")
            
            try:
                if 'call_tool' in self._handlers:
                    results = await self._handlers['call_tool'](tool_name, tool_args)
                else:
                    raise ValueError("Tool handler not available")
                    
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [content.model_dump() for content in results]
                    }
                }
            except Exception as e:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
            
            return JSONResponse(response, headers=base_headers)
        
        elif method == 'prompts/list':
            # List prompts
            if 'list_prompts' in self._handlers:
                prompts = await self._handlers['list_prompts']()
            else:
                prompts = []
                
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "prompts": [prompt.model_dump() for prompt in prompts]
                }
            }
            return JSONResponse(response, headers=base_headers)
        
        elif method == 'resources/list':
            # Resources not supported, return empty list
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "resources": []
                }
            }
            return JSONResponse(response, headers=base_headers)
        
        elif method == 'prompts/get':
            # Get prompt
            prompt_name = params.get('name')
            prompt_args = params.get('arguments', {})
            
            try:
                if 'get_prompt' in self._handlers:
                    prompt_msg = await self._handlers['get_prompt'](prompt_name, prompt_args)
                else:
                    raise ValueError("Prompt handler not available")
                    
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "messages": [prompt_msg.model_dump()]
                    }
                }
            except Exception as e:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
            
            return JSONResponse(response, headers=base_headers)
        
        else:
            # Unknown method
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
            return JSONResponse(response, status_code=404, headers=base_headers)
    
    def _create_app(self):
        """Create Starlette application"""
        async def health_check(request):
            """Health check endpoint"""
            return JSONResponse({
                "status": "healthy",
                "server": "mail-attachment-server",
                "version": "2.0.0",
                "transport": "http-streaming"
            }, headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Mcp-Session-Id, MCP-Protocol-Version",
                "Access-Control-Expose-Headers": "Mcp-Session-Id"
            })
        
        async def server_info(request):
            """Server information endpoint"""
            return JSONResponse({
                "name": "mail-attachment-server",
                "version": "2.0.0",
                "protocol": "mcp",
                "transport": "http-streaming",
                "endpoints": {
                    "streaming": "/stream",
                    "health": "/health",
                    "info": "/info"
                }
            })
        
        # OPTIONS handler for CORS preflight
        async def options_handler(request):
            return Response(
                "",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS, DELETE",
                    "Access-Control-Allow-Headers": "Content-Type, Mcp-Session-Id, Authorization, MCP-Protocol-Version",
                    "Access-Control-Expose-Headers": "Mcp-Session-Id",
                    "Access-Control-Max-Age": "3600"
                }
            )
        
        # Root endpoint handler
        async def root_handler(request):
            """Handle root endpoint requests"""
            if request.method == "POST":
                # For POST requests, handle as MCP request
                return await self._handle_streaming_request(request)
            else:
                # For GET/HEAD requests, return server info
                return JSONResponse({
                    "name": "mail-attachment-server",
                    "version": "2.0.0",
                    "protocol": "mcp",
                    "transport": "http",
                    "endpoints": {
                        "mcp": "/",
                        "health": "/health",
                        "info": "/info"
                    }
                }, headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS, HEAD, DELETE",
                    "Access-Control-Allow-Headers": "Content-Type, Mcp-Session-Id, Authorization, MCP-Protocol-Version",
                    "Access-Control-Expose-Headers": "Mcp-Session-Id"
                })
        
        # Register endpoint - for client registration
        async def register_handler(request):
            """Handle client registration"""
            return JSONResponse({
                "success": True,
                "message": "No registration required - this is an open server",
                "endpoint": "/stream"
            }, headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            })
        
        # OAuth discovery endpoints - indicate no auth required
        async def oauth_authorization_server(request):
            """OAuth authorization server metadata - returns empty to indicate no auth"""
            # Return 404 to indicate OAuth is not supported
            return JSONResponse(
                {"error": "OAuth not supported - this server does not require authentication"},
                status_code=404,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json"
                }
            )
        
        async def oauth_protected_resource(request):
            """OAuth protected resource metadata - returns empty to indicate no auth"""
            # Return 404 to indicate this resource is not OAuth protected
            return JSONResponse(
                {"error": "This resource does not require authentication"},
                status_code=404,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json"
                }
            )
        
        # Create routes
        routes = [
            # Root endpoint
            Route("/", endpoint=root_handler, methods=["GET", "POST", "HEAD"]),
            Route("/", endpoint=options_handler, methods=["OPTIONS"]),
            # MCP endpoint (alias for root)
            Route("/mcp", endpoint=self._handle_streaming_request, methods=["POST"]),
            Route("/mcp", endpoint=options_handler, methods=["OPTIONS"]),
            # Register endpoint
            Route("/register", endpoint=register_handler, methods=["POST"]),
            Route("/register", endpoint=options_handler, methods=["OPTIONS"]),
            # Health and info endpoints
            Route("/health", endpoint=health_check, methods=["GET"]),
            Route("/info", endpoint=server_info, methods=["GET"]),
            # Streaming endpoints (both /stream and /steam for compatibility)
            Route("/stream", endpoint=self._handle_streaming_request, methods=["POST"]),
            Route("/steam", endpoint=self._handle_streaming_request, methods=["POST", "GET", "HEAD"]),
            Route("/stream", endpoint=options_handler, methods=["OPTIONS"]),
            Route("/steam", endpoint=options_handler, methods=["OPTIONS"]),
            Route("/health", endpoint=options_handler, methods=["OPTIONS"]),
            Route("/info", endpoint=options_handler, methods=["OPTIONS"]),
            # OAuth discovery endpoints
            Route("/.well-known/oauth-authorization-server", endpoint=oauth_authorization_server, methods=["GET"]),
            Route("/.well-known/oauth-protected-resource", endpoint=oauth_protected_resource, methods=["GET"]),
            Route("/.well-known/oauth-authorization-server/stream", endpoint=oauth_authorization_server, methods=["GET"]),
            Route("/.well-known/oauth-protected-resource/stream", endpoint=oauth_protected_resource, methods=["GET"]),
            Route("/.well-known/oauth-authorization-server/steam", endpoint=oauth_authorization_server, methods=["GET"]),
            Route("/.well-known/oauth-protected-resource/steam", endpoint=oauth_protected_resource, methods=["GET"]),
        ]
        
        return Starlette(routes=routes)
    
    def run(self):
        """Run the HTTP streaming MCP server"""
        logger.info(f"🚀 Starting HTTP Streaming Mail Attachment Server on http://{self.host}:{self.port}")
        logger.info(f"📧 Streaming endpoint: http://{self.host}:{self.port}/stream")
        logger.info(f"💚 Health check: http://{self.host}:{self.port}/health")
        logger.info(f"ℹ️  Server info: http://{self.host}:{self.port}/info")
        
        # Run uvicorn
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )


def main():
    """Main entry point"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('mcp_mail_attachment_server.log')
        ]
    )
    
    # Get configuration from environment or use defaults
    server = HTTPStreamingMailAttachmentServer(
        host=os.getenv("MCP_HOST", "0.0.0.0"),
        port=int(os.getenv("MCP_PORT", "8002"))
    )
    
    # Run the server
    server.run()


if __name__ == "__main__":
    main()