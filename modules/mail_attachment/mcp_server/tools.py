"""Tool implementations for MCP Server"""

import csv
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from infra.core.database import get_database_manager
from infra.core.logger import get_logger
from modules.mail_attachment import AttachmentDownloader, EmailSaver, FileConverter
from modules.mail_query import (
    MailQueryFilters,
    MailQueryOrchestrator,
    MailQueryRequest,
    PaginationOptions,
)
from .config import get_config

logger = get_logger(__name__)


class MailAttachmentTools:
    """Tool implementations for mail attachment handling"""
    
    def __init__(self):
        self.config = get_config()
        self.db = get_database_manager()
        self.attachment_downloader = AttachmentDownloader(self.config.attachments_dir)
        self.file_converter = FileConverter()
        self.email_saver = EmailSaver(self.config.attachments_dir)
    
    async def query_email(self, arguments: Dict[str, Any]) -> str:
        """Handle mail query with attachments"""
        try:
            # Extract parameters
            user_id = arguments.get("user_id")
            if not user_id:
                return "Error: user_id is required"
            
            days_back = arguments.get("days_back", self.config.default_days_back)
            max_mails = arguments.get("max_mails", self.config.default_max_mails)
            include_body = arguments.get("include_body", True)
            download_attachments = arguments.get("download_attachments", False)
            save_emails = arguments.get("save_emails", True)
            save_csv = arguments.get("save_csv", False)
            start_date_str = arguments.get("start_date")
            end_date_str = arguments.get("end_date")
            sender_address = arguments.get("sender_address")
            recipient_address = arguments.get("recipient_address")
            subject_contains = arguments.get("subject_contains")
            conversation_with = arguments.get("conversation_with", [])
            
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
            
            # Check for conflicting parameters
            if conversation_with and sender_address:
                return "Error: conversation_with cannot be used with sender_address"
            if conversation_with and recipient_address:
                return "Error: conversation_with cannot be used with recipient_address"
            if sender_address and recipient_address:
                return "Error: sender_address and recipient_address cannot be used together"
            
            # Setup filters with the calculated date range
            filters = MailQueryFilters(date_from=start_date, date_to=end_date)
            
            
            if sender_address:
                filters.sender_address = sender_address
            
            if subject_contains:
                filters.subject_contains = subject_contains
            
            # Setup fields
            select_fields = [
                "id", "subject", "from", "sender", "receivedDateTime",
                "bodyPreview", "hasAttachments", "importance", "isRead"
            ]
            if include_body:
                select_fields.append("body")
            if download_attachments:
                select_fields.append("attachments")
            
            # Adjust query for conversation_with or recipient_address
            if conversation_with or recipient_address:
                # For conversation_with/recipient_address, we need to get more emails and filter client-side
                # Also need toRecipients field
                if "toRecipients" not in select_fields:
                    select_fields.append("toRecipients")
                
                # Get more emails to ensure we find conversations
                query_max_mails = min(max_mails * 3, 500)  # Get 3x more, max 500
            else:
                query_max_mails = max_mails
            
            # Create request
            request = MailQueryRequest(
                user_id=user_id,
                filters=filters,
                pagination=PaginationOptions(top=query_max_mails, skip=0, max_pages=1),
                select_fields=select_fields,
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
            
            # Display filters if applied
            if conversation_with:
                result_text += f"대화 필터: {', '.join(conversation_with)}\n"
            if sender_address:
                result_text += f"발신자 필터: {sender_address}\n"
            if recipient_address:
                result_text += f"수신자 필터: {recipient_address}\n"
            if subject_contains:
                result_text += f"제목 필터: '{subject_contains}' 포함\n"
            
            # Filter messages for conversation_with or recipient_address
            if conversation_with or recipient_address:
                filtered_messages = []
                conversation_emails = [email.lower() for email in conversation_with]
                
                for mail in response.messages:
                    include_mail = False
                    
                    # Get sender email
                    sender_email = ""
                    if mail.from_address and isinstance(mail.from_address, dict):
                        email_addr = mail.from_address.get("emailAddress", {})
                        sender_email = email_addr.get("address", "").lower()
                    
                    # For conversation_with filter
                    if conversation_with:
                        # Check if sender is in conversation_with
                        if sender_email in conversation_emails:
                            include_mail = True
                        
                        # Check if this is a sent mail (from the user)
                        elif sender_email and f"{user_id}@" in sender_email:
                            # This is a sent mail, check recipients
                            if hasattr(mail, "to_recipients") and mail.to_recipients:
                                for recipient in mail.to_recipients:
                                    if isinstance(recipient, dict):
                                        recip_addr = recipient.get("emailAddress", {})
                                        if isinstance(recip_addr, dict):
                                            recip_email = recip_addr.get("address", "").lower()
                                            if recip_email in conversation_emails:
                                                include_mail = True
                                                break
                    
                    # For recipient_address filter (only sent mails)
                    elif recipient_address:
                        # Only include if this is a sent mail from the user
                        if sender_email and f"{user_id}@" in sender_email:
                            # Check recipients
                            if hasattr(mail, "to_recipients") and mail.to_recipients:
                                for recipient in mail.to_recipients:
                                    if isinstance(recipient, dict):
                                        recip_addr = recipient.get("emailAddress", {})
                                        if isinstance(recip_addr, dict):
                                            recip_email = recip_addr.get("address", "").lower()
                                            if recip_email == recipient_address.lower():
                                                include_mail = True
                                                break
                    
                    if include_mail:
                        filtered_messages.append(mail)
                
                # Update response with filtered messages
                response.messages = filtered_messages[:max_mails]  # Limit to requested max
                actual_total = len(filtered_messages)
                result_text += f"총 메일 수: {len(response.messages)}개 (전체 {actual_total}개 중)\n\n"
            else:
                result_text += f"총 메일 수: {response.total_fetched}개\n\n"
            
            # Process each mail
            blocked_senders = self.config.blocked_senders  # 차단할 발신자 목록
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
                        mail_dict = mail.model_dump() if hasattr(mail, "model_dump") else mail.__dict__
                        
                        # Field name mapping (Graph API -> email_saver format)
                        if "receivedDateTime" in mail_dict:
                            mail_dict["received_date_time"] = mail_dict.get("receivedDateTime")
                        if "from" in mail_dict:
                            mail_dict["from_address"] = mail_dict.get("from")
                        if "toRecipients" in mail_dict:
                            mail_dict["to_recipients"] = mail_dict.get("toRecipients")
                        if "isRead" in mail_dict:
                            mail_dict["is_read"] = mail_dict.get("isRead")
                        if "hasAttachments" in mail_dict:
                            mail_dict["has_attachments"] = mail_dict.get("hasAttachments")
                        if "bodyPreview" in mail_dict:
                            mail_dict["body_preview"] = mail_dict.get("bodyPreview")
                        if "webLink" in mail_dict:
                            mail_dict["web_link"] = mail_dict.get("webLink")
                        
                        saved_result = await self.email_saver.save_email_as_text(
                            mail_dict,
                            user_id,
                            include_headers=True,
                            save_html=include_body,
                            upload_to_onedrive=False,
                            graph_client=None,
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
                    "attachments": [],
                }
                
                # Add body content to mail_info if available
                if include_body and mail.body:
                    content_type = mail.body.get("contentType", "text")
                    content = mail.body.get("content", "")
                    
                    if content_type.lower() == "html":
                        # Simple HTML stripping
                        import re
                        text_content = re.sub("<[^<]+?>", "", content)
                        text_content = text_content.replace("&nbsp;", " ")
                        text_content = text_content.replace("&lt;", "<")
                        text_content = text_content.replace("&gt;", ">")
                        text_content = text_content.replace("&amp;", "&")
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
                        content = re.sub("<[^<]+?>", "", content)
                        content = content.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">")
                    result_text += f"   본문:\n{content[:500]}...\n" if len(content) > 500 else f"   본문:\n{content}\n"
                
                # Process attachments
                if download_attachments and mail.has_attachments and hasattr(mail, "attachments") and mail.attachments:
                    result_text += f"\n   📎 첨부파일:\n"
                    
                    for attachment in mail.attachments:
                        att_name = attachment.get("name", "unknown")
                        att_size = attachment.get("size", 0)
                        result_text += f"      - {att_name} ({att_size:,} bytes)\n"
                        
                        # Add attachment info to mail_info
                        attachment_info = {"name": att_name, "size": att_size}
                        
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
                                    sender_email=sender_email,
                                )
                                
                                if file_path:
                                    result_text += f"        ✅ 다운로드: {file_path['file_path']}\n"
                                    attachment_info["file_path"] = str(file_path["file_path"])
                                    
                                    # Convert to text if supported
                                    if self.file_converter.is_supported(file_path["file_path"]):
                                        text_content = self.file_converter.convert_to_text(file_path["file_path"])
                                        text_file = self.file_converter.save_as_text(
                                            file_path["file_path"],
                                            text_content,
                                            att_name,
                                        )
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
                
                result_text += "\n" + "-" * 60 + "\n"
            
            # CSV로 메일 메타데이터 저장
            if save_csv and processed_mails:
                try:
                    csv_file = self.save_emails_to_csv(processed_mails, user_id)
                    result_text += f"\n📊 메일 메타데이터 CSV 저장 완료: {csv_file}\n"
                except Exception as e:
                    logger.error(f"CSV 저장 실패: {str(e)}")
                    result_text += f"\n❌ CSV 저장 중 오류 발생: {str(e)}\n"
            
            # 포맷팅 지침 추가
            result_text += "\n\n" + "=" * 60 + "\n"
            result_text += "📧 이메일 조회 결과 포맷팅 지침\n"
            result_text += "=" * 60 + "\n"
            result_text += f"""
조회 사용자: {user_id}

다음 순서와 형식으로 테이블을 작성하세요:
**모든 송수신 메일 리스트에 대해서 작성해 주세요**
**모든 송수신 메일 리스트에 대해서 작성해 주세요**

**📊 표 구성 (필수 열)**:
| 유형 | 날짜 | 발신자/수신자 | 제목 | 주요내용 | 응답필요성 | 응답기한 | 첨부 |

**각 열 작성 지침**:
1. **유형**: 
   - 📥 받은메일: 발신자 이메일이 조회 사용자({user_id})와 다른 경우
   - 📨 보낸메일: 발신자 이메일이 조회 사용자({user_id})와 같은 경우
2. **날짜**: YYYY-MM-DD HH:MM 형식
3. **발신자/수신자**: 
   - 받은메일: 발신자 이름 (이메일)
   - 보낸메일: → 수신자 이름 (이메일)
4. **제목**: 전체 제목 (너무 길면 ... 사용)
5. **주요내용**: 핵심 내용 1-2줄 요약
6. **응답필요성**: 
   - 받은메일: 🔴 중요 (응답 필요) / 🟢 일반 (참고용)
   - 보낸메일: ✅ 발송완료 / ⏳ 응답대기
7. **응답기한**: 구체적 날짜 또는 "즉시", "3일 내", "없음" 등
8. **첨부**: 파일명 (파일형식) 또는 "없음"

**응답 필요성 판단 기준**:
- 질문이 포함된 경우
- "회신 요청", "답변 부탁" 등의 표현
- 마감일이 명시된 경우
- 승인/검토 요청이 있는 경우

**예시**:
| 📥 | 2024-01-15 09:30 | 김철수 (kim@company.com) | 프로젝트 진행 현황 보고 | Q1 목표 달성률 85%, 추가 예산 승인 요청 | 🔴 중요 | 1/17까지 | 보고서.pdf |
| 📤 | 2024-01-15 11:20 | → 이영희 (lee@company.com) | Re: 프로젝트 진행 현황 보고 | 예산 승인 완료, 진행하시기 바랍니다 | ✅ 발송완료 | - | 없음 |

이메일 내용과 첨부파일을 분석하여 응답 필요성과 기한을 정확히 판단하세요.
"""
            
            # 다운로드된 파일들 삭제 (설정에 따라)
            if self.config.cleanup_after_query:
                try:
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
    
    async def list_active_accounts(self) -> str:
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
            result_text += "=" * 60 + "\n\n"
            
            for account in accounts:
                result_text += f"• {account['user_id']}"
                if account["user_name"]:
                    result_text += f" ({account['user_name']})"
                if account["email"]:
                    result_text += f" - {account['email']}"
                result_text += f"\n  상태: {account['status']}"
                if account["last_sync_time"]:
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
        with open(csv_file, "w", newline="", encoding=self.config.get("email.csv_encoding", "utf-8-sig")) as f:
            # UTF-8 BOM for Korean characters in Excel
            fieldnames = [
                "번호", "제목", "발신자", "발신자_이메일", "수신일시",
                "읽음상태", "중요도", "첨부파일", "첨부파일_개수", "첨부파일_목록",
                "본문_미리보기", "폴더명", "message_id"
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for idx, email in enumerate(emails, 1):
                # Process attachment info
                attachment_names = []
                attachment_count = 0
                if email.get("attachments"):
                    attachment_names = [att["name"] for att in email["attachments"]]
                    attachment_count = len(attachment_names)
                
                # Generate folder name (same as actual save folder)
                safe_subject = self.attachment_downloader._sanitize_filename(
                    email.get("subject", "NoSubject")[:50]
                )
                received_datetime = email.get("received_date_time", datetime.now())
                date_str = (
                    received_datetime.strftime("%Y%m%d_%H%M%S")
                    if isinstance(received_datetime, datetime)
                    else datetime.now().strftime("%Y%m%d_%H%M%S")
                )
                safe_sender = self.attachment_downloader._sanitize_filename(
                    email.get("sender_email", "unknown")
                )
                folder_name = f"{safe_subject}_{date_str}_{safe_sender}"
                
                # Get body preview
                body_preview = ""
                if "body" in email:
                    body_preview = email["body"][:100].replace("\n", " ").replace("\r", " ")
                elif "body_preview" in email:
                    body_preview = email["body_preview"][:100].replace("\n", " ").replace("\r", " ")
                
                row = {
                    "번호": idx,
                    "제목": email.get("subject", ""),
                    "발신자": email.get("sender", ""),
                    "발신자_이메일": email.get("sender_email", ""),
                    "수신일시": email.get("received_date", ""),
                    "읽음상태": "읽음" if email.get("is_read", False) else "안읽음",
                    "중요도": email.get("importance", "normal"),
                    "첨부파일": "있음" if email.get("has_attachments", False) else "없음",
                    "첨부파일_개수": attachment_count,
                    "첨부파일_목록": "; ".join(attachment_names) if attachment_names else "",
                    "본문_미리보기": body_preview,
                    "폴더명": folder_name,
                    "message_id": email.get("id", ""),
                }
                
                writer.writerow(row)
        
        logger.info(f"Email metadata CSV saved: {csv_file}")
        return csv_file