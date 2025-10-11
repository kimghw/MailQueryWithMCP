"""Email query tool for MCP server"""

import logging
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from infra.core import get_database_manager, get_logger
from modules.mail_query import (
    MailQueryFilters,
    MailQueryOrchestrator,
    MailQueryRequest,
    PaginationOptions
)
from modules.mail_query_without_db import AttachmentDownloader, EmailSaver

logger = get_logger(__name__)


class EmailQueryTool:
    """Tool for querying and retrieving emails"""

    def __init__(self, config):
        """
        Initialize email query tool

        Args:
            config: Configuration object
        """
        self.config = config
        self.email_saver = EmailSaver(output_dir=str(self.config.emails_dir))
        self.attachment_downloader = AttachmentDownloader(
            output_dir=str(self.config.attachments_dir)
        )
        # Define KST timezone (UTC+9)
        self.KST = timezone(timedelta(hours=9))

    def parse_datetime_kst_to_utc(self, date_str: str) -> datetime:
        """
        Parse datetime string in KST and convert to UTC

        Supports formats:
        - YYYY-MM-DD HH:MM (assumes KST)
        - YYYY-MM-DD (assumes 00:00:00 KST)

        Args:
            date_str: Date string to parse

        Returns:
            UTC datetime without timezone info
        """
        # Try parsing with time (minutes only)
        try:
            dt_kst = datetime.strptime(date_str, "%Y-%m-%d %H:%M").replace(tzinfo=self.KST)
            return dt_kst.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            pass

        # Try parsing date only (assumes 00:00:00 KST)
        try:
            dt_kst = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=self.KST)
            return dt_kst.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            raise ValueError(f"Invalid date format. Expected 'YYYY-MM-DD [HH:MM]', got '{date_str}'")

    def parse_date_range(self, arguments: Dict[str, Any]) -> tuple:
        """
        Parse date range from arguments

        Args:
            arguments: Tool arguments containing date parameters

        Returns:
            Tuple of (start_date, end_date, days_back)
        """
        start_date_str = arguments.get("start_date")
        end_date_str = arguments.get("end_date")
        days_back = arguments.get("days_back", self.config.default_days_back)

        start_date = None
        end_date = None

        # Both dates specified
        if start_date_str and end_date_str:
            start_date = self.parse_datetime_kst_to_utc(start_date_str)

            # For end_date, if only date is provided, use current time on that date
            if len(end_date_str) == 10:  # YYYY-MM-DD format
                # Get current time in KST
                now_kst = datetime.now(self.KST)
                # Parse the end_date and use current time
                end_date_only = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                dt_kst = datetime.combine(end_date_only, now_kst.time()).replace(tzinfo=self.KST)
                end_date = dt_kst.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                end_date = self.parse_datetime_kst_to_utc(end_date_str)

            if start_date >= end_date:
                raise ValueError("start_date is later than or equal to end_date")

            days_back = (end_date - start_date).days

        # Only start date specified
        elif start_date_str:
            start_date = self.parse_datetime_kst_to_utc(start_date_str)
            end_date = datetime.now(timezone.utc).replace(tzinfo=None)
            days_back = (end_date - start_date).days + 1

        # Only end date specified
        elif end_date_str:
            if len(end_date_str) == 10:  # YYYY-MM-DD format
                # Get current time in KST
                now_kst = datetime.now(self.KST)
                # Parse the end_date and use current time
                end_date_only = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                dt_kst = datetime.combine(end_date_only, now_kst.time()).replace(tzinfo=self.KST)
                end_date = dt_kst.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                end_date = self.parse_datetime_kst_to_utc(end_date_str)

            start_date = end_date - timedelta(days=days_back)

        # No dates specified, use days_back from now
        else:
            end_date = datetime.now(timezone.utc).replace(tzinfo=None)
            start_date = end_date - timedelta(days=days_back - 1)

        return start_date, end_date, days_back

    def validate_parameters(self, arguments: Dict[str, Any]) -> Optional[str]:
        """
        Validate query parameters

        Args:
            arguments: Tool arguments

        Returns:
            Error message if validation fails, None otherwise
        """
        # Check required parameters
        if not arguments.get("user_id"):
            return "Error: user_id is required"

        # Check for conflicting parameters
        conversation_with = arguments.get("conversation_with", [])
        sender_address = arguments.get("sender_address")
        recipient_address = arguments.get("recipient_address")

        if conversation_with and sender_address:
            return "Error: conversation_with cannot be used with sender_address"
        if conversation_with and recipient_address:
            return "Error: conversation_with cannot be used with recipient_address"
        if sender_address and recipient_address:
            return "Error: sender_address and recipient_address cannot be used together"

        return None

    def filter_by_keyword(self, messages: List, keyword_filter) -> List:
        """
        Filter messages by structured keyword filter

        Args:
            messages: List of email messages
            keyword_filter: KeywordFilter object with and_keywords, or_keywords, not_keywords

        Returns:
            Filtered list of messages
        """
        if not keyword_filter:
            return messages

        filtered_messages = []

        for mail in messages:
            mail_text = self._get_searchable_text(mail).lower()
            include_mail = True

            # AND condition: all keywords must be present
            if keyword_filter.and_keywords:
                and_keywords = [kw.lower() for kw in keyword_filter.and_keywords]
                if not all(kw in mail_text for kw in and_keywords):
                    include_mail = False

            # OR condition: at least one keyword must be present
            if include_mail and keyword_filter.or_keywords:
                or_keywords = [kw.lower() for kw in keyword_filter.or_keywords]
                if not any(kw in mail_text for kw in or_keywords):
                    include_mail = False

            # NOT condition: none of these keywords should be present
            if include_mail and keyword_filter.not_keywords:
                not_keywords = [kw.lower() for kw in keyword_filter.not_keywords]
                if any(kw in mail_text for kw in not_keywords):
                    include_mail = False

            if include_mail:
                filtered_messages.append(mail)

        return filtered_messages

    def _get_searchable_text(self, mail) -> str:
        """
        Extract all searchable text from an email

        Args:
            mail: Email message object

        Returns:
            Combined text from all searchable fields
        """
        text_parts = []

        # Add subject
        if hasattr(mail, 'subject') and mail.subject:
            text_parts.append(str(mail.subject))

        # Add body preview or body
        if hasattr(mail, 'body_preview') and mail.body_preview:
            text_parts.append(str(mail.body_preview))
        elif hasattr(mail, 'body') and mail.body:
            if isinstance(mail.body, dict):
                content = mail.body.get('content', '')
                if content:
                    # Remove HTML tags if present
                    import re
                    content = re.sub('<[^<]+?>', '', content)
                    text_parts.append(content[:1000])  # Limit to first 1000 chars
            else:
                text_parts.append(str(mail.body)[:1000])

        # Add sender information
        if hasattr(mail, 'from_address') and mail.from_address:
            if isinstance(mail.from_address, dict):
                email_addr = mail.from_address.get('emailAddress', {})
                if isinstance(email_addr, dict):
                    sender_email = email_addr.get('address', '')
                    sender_name = email_addr.get('name', '')
                    text_parts.append(sender_email)
                    text_parts.append(sender_name)

        # Add recipient information (for sent emails)
        if hasattr(mail, 'to_recipients') and mail.to_recipients:
            for recipient in mail.to_recipients:
                if isinstance(recipient, dict):
                    email_addr = recipient.get('emailAddress', {})
                    if isinstance(email_addr, dict):
                        text_parts.append(email_addr.get('address', ''))
                        text_parts.append(email_addr.get('name', ''))

        # Add attachment names
        if hasattr(mail, 'attachments') and mail.attachments:
            for attachment in mail.attachments:
                if isinstance(attachment, dict):
                    text_parts.append(attachment.get('name', ''))

        return ' '.join(text_parts)

    def _simple_keyword_filter(self, messages: List, keyword: str) -> List:
        """
        Simple keyword filtering without boolean operators

        Args:
            messages: List of email messages
            keyword: Search keyword (lowercase)

        Returns:
            Filtered list of messages
        """
        filtered_messages = []
        for mail in messages:
            mail_text = self._get_searchable_text(mail).lower()
            if keyword in mail_text:
                filtered_messages.append(mail)
        return filtered_messages

    def filter_messages(self, messages: List, user_id: str, filters: Dict) -> List:
        """
        Filter messages based on conversation_with, recipient_address, or keyword

        Args:
            messages: List of email messages
            user_id: User ID
            filters: Filter parameters (conversation_with, recipient_address, keyword_filter)

        Returns:
            Filtered list of messages
        """
        conversation_with = filters.get("conversation_with", [])
        recipient_address = filters.get("recipient_address")
        keyword_filter = filters.get("keyword_filter")

        # First, apply keyword filter if provided
        if keyword_filter:
            messages = self.filter_by_keyword(messages, keyword_filter)

        # If no other filters, return keyword-filtered results
        if not conversation_with and not recipient_address:
            return messages

        filtered_messages = []
        conversation_emails = [email.lower() for email in conversation_with]

        for mail in messages:
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

        return filtered_messages

    def format_email_info(self, mail, index: int, user_id: str, save_emails: bool,
                          download_attachments: bool, graph_client=None) -> Dict[str, Any]:
        """
        Format email information for display and storage

        Args:
            mail: Email message object
            index: Email index
            user_id: User ID
            save_emails: Whether to save emails
            download_attachments: Whether to download attachments
            graph_client: Graph API client for attachment download

        Returns:
            Formatted email information dictionary
        """
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

        # Check if sender should be blocked
        blocked_senders = self.config.blocked_senders
        if sender_email and any(blocked in sender_email.lower() for blocked in blocked_senders):
            logger.info(f"Skipping email from blocked sender: {sender_email}")
            return None

        # Save email if requested
        mail_saved_path = None
        if save_emails:
            try:
                saved_info = self.email_saver.save_email(mail, user_id=user_id)
                mail_saved_path = saved_info.get('email_path')
                logger.info(f"Email saved: {mail_saved_path}")
            except Exception as e:
                logger.error(f"Failed to save email: {str(e)}")

        # Convert received time to KST for display
        received_kst = mail.received_date_time.replace(tzinfo=timezone.utc).astimezone(self.KST)

        # Collect mail info
        mail_info = {
            "id": mail.id,
            "subject": mail.subject,
            "sender": sender,
            "sender_email": sender_email or "unknown@email.com",
            "received_date": received_kst.strftime("%Y-%m-%d %H:%M"),
            "received_date_time": mail.received_date_time,
            "has_attachments": mail.has_attachments,
            "is_read": mail.is_read,
            "importance": mail.importance,
            "attachments": [],
            "saved_path": mail_saved_path
        }

        # Add body content if available
        if mail.body:
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
                mail_info["body"] = text_content[:500] if len(text_content) > 500 else text_content
            else:
                mail_info["body"] = content[:500] if len(content) > 500 else content
        elif mail.body_preview:
            mail_info["body_preview"] = mail.body_preview

        # Process attachments if requested
        if download_attachments and mail.has_attachments and hasattr(mail, "attachments"):
            if mail.attachments:
                for attachment in mail.attachments:
                    att_info = self.process_attachment(
                        attachment, mail.id, user_id, graph_client
                    )
                    if att_info:
                        mail_info["attachments"].append(att_info)

        return mail_info

    def process_attachment(self, attachment: Dict, mail_id: str, user_id: str,
                          graph_client) -> Optional[Dict]:
        """
        Process a single attachment

        Args:
            attachment: Attachment data
            mail_id: Email ID
            user_id: User ID
            graph_client: Graph API client

        Returns:
            Attachment information or None if processing failed
        """
        try:
            att_name = attachment.get("name", "unknown")
            att_size = attachment.get("size", 0)
            att_id = attachment.get("id")

            # Skip if too large
            if att_size > self.config.max_file_size_mb * 1024 * 1024:
                logger.warning(f"Attachment too large: {att_name} ({att_size} bytes)")
                return {
                    "name": att_name,
                    "size": att_size,
                    "status": "skipped_too_large"
                }

            # Download attachment
            if att_id and graph_client:
                saved_path = self.attachment_downloader.download_and_save(
                    graph_client=graph_client,
                    user_id=user_id,
                    mail_id=mail_id,
                    attachment_id=att_id,
                    attachment_name=att_name
                )

                if saved_path:
                    return {
                        "name": att_name,
                        "size": att_size,
                        "saved_path": str(saved_path),
                        "status": "downloaded"
                    }

            return {
                "name": att_name,
                "size": att_size,
                "status": "failed"
            }

        except Exception as e:
            logger.error(f"Error processing attachment: {str(e)}")
            return None

    async def query_email(self, arguments: Dict[str, Any]) -> str:
        """
        Handle mail query with attachments

        Args:
            arguments: Tool arguments

        Returns:
            Query result as formatted string
        """
        try:
            # Validate parameters
            error = self.validate_parameters(arguments)
            if error:
                return error

            # Extract parameters
            user_id = arguments.get("user_id")
            max_mails = arguments.get("max_mails", self.config.default_max_mails)
            include_body = arguments.get("include_body", True)
            download_attachments = arguments.get("download_attachments", False)
            save_emails = arguments.get("save_emails", True)
            save_csv = arguments.get("save_csv", False)

            # Parse date range
            try:
                start_date, end_date, days_back = self.parse_date_range(arguments)
            except ValueError as e:
                return f"Error: {str(e)}"

            # Create mail query
            orchestrator = MailQueryOrchestrator()

            # Setup filters - keyword_filter will be applied client-side, not server-side
            keyword_filter = None

            # Handle keyword_filter parameter (structured)
            keyword_filter_dict = arguments.get("keyword_filter")
            if keyword_filter_dict:
                from modules.mail_query import KeywordFilter
                keyword_filter = KeywordFilter(**keyword_filter_dict)

            # Handle legacy keyword parameter (simple string)
            keyword = arguments.get("keyword")
            if keyword and not keyword_filter:
                from modules.mail_query import KeywordFilter
                # Convert simple keyword to and_keywords for backward compatibility
                keyword_filter = KeywordFilter(and_keywords=[keyword])

            # Traditional filtering with date range
            filters = MailQueryFilters(date_from=start_date, date_to=end_date)

            if arguments.get("sender_address"):
                filters.sender_address = arguments["sender_address"]

            if arguments.get("subject_contains"):
                filters.subject_contains = arguments["subject_contains"]

            # Setup fields
            select_fields = [
                "id", "subject", "from", "sender", "receivedDateTime",
                "bodyPreview", "hasAttachments", "importance", "isRead"
            ]
            if include_body:
                select_fields.append("body")
            if download_attachments:
                select_fields.append("attachments")

            # Adjust query for conversation filters or keyword
            conversation_with = arguments.get("conversation_with", [])
            recipient_address = arguments.get("recipient_address")

            # If using client-side filters (keyword_filter, conversation_with, recipient_address),
            # fetch more emails to filter from
            if keyword_filter or conversation_with or recipient_address:
                if "toRecipients" not in select_fields:
                    select_fields.append("toRecipients")
                # Fetch more emails when using client-side filtering
                query_max_mails = min(max_mails * 3, 500)  # Get more for filtering
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

            # Filter messages if needed (client-side filtering)
            if keyword_filter or conversation_with or recipient_address:
                response.messages = self.filter_messages(
                    response.messages,
                    user_id,
                    {
                        "keyword_filter": keyword_filter,
                        "conversation_with": conversation_with,
                        "recipient_address": recipient_address
                    }
                )
                # Limit to max_mails after filtering
                response.messages = response.messages[:max_mails]

            # Format results
            result_text = self.format_results(
                response.messages,
                user_id,
                start_date,
                end_date,
                days_back,
                arguments,
                save_emails,
                download_attachments,
                graph_client,
                save_csv
            )

            return result_text

        except Exception as e:
            logger.error(f"Error in query_email: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return f"Error querying emails: {str(e)}"

    def format_results(self, messages: List, user_id: str, start_date, end_date,
                       days_back: int, filters: Dict, save_emails: bool,
                       download_attachments: bool, graph_client, save_csv: bool) -> str:
        """
        Format query results for display

        Args:
            messages: List of email messages
            user_id: User ID
            start_date: Query start date
            end_date: Query end date
            days_back: Number of days queried
            filters: Applied filters
            save_emails: Whether emails were saved
            download_attachments: Whether attachments were downloaded
            graph_client: Graph API client
            save_csv: Whether to save as CSV

        Returns:
            Formatted result string
        """
        result_text = f"📧 메일 조회 결과 - {user_id}\n"
        result_text += f"{'='*60}\n"

        # Display date range info (convert UTC back to KST for display)
        if start_date and end_date:
            start_kst = start_date.replace(tzinfo=timezone.utc).astimezone(self.KST)
            end_kst = end_date.replace(tzinfo=timezone.utc).astimezone(self.KST)
            result_text += f"조회 기간: {start_kst.strftime('%Y-%m-%d %H:%M')} ~ "
            result_text += f"{end_kst.strftime('%Y-%m-%d %H:%M')} KST ({days_back}일간)\n"
        else:
            result_text += f"조회 기간: 최근 {days_back}일\n"

        # Display filters if applied
        if filters.get("conversation_with"):
            result_text += f"대화 필터: {', '.join(filters['conversation_with'])}\n"
        if filters.get("sender_address"):
            result_text += f"발신자 필터: {filters['sender_address']}\n"
        if filters.get("recipient_address"):
            result_text += f"수신자 필터: {filters['recipient_address']}\n"
        if filters.get("subject_contains"):
            result_text += f"제목 필터: '{filters['subject_contains']}' 포함\n"

        result_text += f"총 메일 수: {len(messages)}개\n\n"

        # Process each mail
        processed_mails = []
        for i, mail in enumerate(messages, 1):
            mail_info = self.format_email_info(
                mail, i, user_id, save_emails, download_attachments, graph_client
            )

            if mail_info:  # Skip if None (blocked sender)
                processed_mails.append(mail_info)

                # Add to result text
                result_text += f"\n[{i}] {mail.subject}\n"
                result_text += f"   발신자: {mail_info['sender']}\n"
                result_text += f"   수신일: {mail_info['received_date']} KST\n"
                result_text += f"   읽음: {'✓' if mail.is_read else '✗'}\n"
                result_text += f"   첨부: {'📎' if mail.has_attachments else '-'}\n"

                if save_emails and mail_info.get('saved_path'):
                    result_text += f"   💾 저장됨: {mail_info['saved_path']}\n"

                # Include body preview if available
                if filters.get("include_body"):
                    if mail_info.get("body"):
                        body_preview = mail_info["body"][:200] + "..." if len(mail_info["body"]) > 200 else mail_info["body"]
                        result_text += f"   내용: {body_preview}\n"
                    elif mail_info.get("body_preview"):
                        result_text += f"   미리보기: {mail_info['body_preview'][:100]}...\n"

                # Show attachment info
                if mail_info.get("attachments"):
                    result_text += f"   첨부파일 ({len(mail_info['attachments'])}개):\n"
                    for att in mail_info["attachments"]:
                        status = att.get("status", "unknown")
                        result_text += f"     - {att['name']} ({att['size']:,} bytes) [{status}]\n"

        # Save to CSV if requested
        if save_csv and processed_mails:
            csv_path = self.save_emails_to_csv(processed_mails, user_id)
            result_text += f"\n\n📊 CSV 파일 저장됨: {csv_path}"

        result_text += f"\n\n✅ 총 {len(processed_mails)}개의 이메일이 처리되었습니다."

        # Add formatting instructions from prompts.py
        result_text += f"\n\n{'='*80}\n"
        result_text += "📋 **결과 포맷팅 요청**\n"
        result_text += f"{'='*80}\n\n"
        result_text += self._get_format_instructions(user_id)

        return result_text

    def _get_format_instructions(self, user_id: str) -> str:
        """Get email formatting instructions from prompts"""
        return f"""
위 메일 리스트를 다음 형식의 **마크다운 테이블**로 재구성해주세요:

**📊 표 구성 (필수 열)**:
| 유형 | 날짜 | 발신자/수신자 | 제목 | 주요내용 | 응답필요성 | 응답기한 | 첨부 |

**각 열 작성 지침**:
1. **유형**:
   - 📥 받은메일: 발신자 이메일이 {user_id}와 다른 경우
   - 📨 보낸메일: 발신자 이메일이 {user_id}와 같은 경우
2. **날짜**: YYYY-MM-DD HH:MM 형식 (위에서 제공된 수신일 사용)
3. **발신자/수신자**:
   - 받은메일: 발신자 이름 (이메일)
   - 보낸메일: → 수신자 이름 (이메일)
4. **제목**: 전체 제목 (너무 길면 50자 이하로 축약하고 ... 사용)
5. **주요내용**:
   - 메일 본문이 제공된 경우 핵심 내용 1-2줄로 요약
   - 본문이 없으면 제목에서 유추하여 작성
6. **응답필요성**:
   - 받은메일:
     * 🔴 긴급: 질문이 포함되거나 "회신 요청", "답변 부탁", 마감일 명시, 승인/검토 요청 등
     * 🟢 일반: 단순 정보 공유, 참고용 메일
   - 보낸메일: ✅ 발송완료 또는 ⏳ 응답대기
7. **응답기한**:
   - 메일 내용에 날짜가 있으면 구체적 날짜
   - 긴급하면 "즉시" 또는 "1-2일 내"
   - 일반이면 "3-7일 내" 또는 "없음"
8. **첨부**:
   - 첨부파일 있으면: 파일명 (확장자)
   - 여러 개면: "파일명1.pdf 외 2개"
   - 없으면: "-"

**예시**:
| 📥 | 2024-01-15 09:30 | 김철수 (kim@company.com) | 프로젝트 진행 현황 보고 | Q1 목표 달성률 85%, 추가 예산 승인 요청 | 🔴 긴급 | 1/17까지 | 보고서.pdf |
| 📨 | 2024-01-15 11:20 | → 이영희 (lee@company.com) | Re: 프로젝트 진행 현황 보고 | 예산 승인 완료, 진행하시기 바랍니다 | ✅ 발송완료 | - | - |

**중요**:
- 모든 메일을 빠짐없이 테이블에 포함시켜주세요
- 응답 필요성과 기한은 메일 내용을 분석하여 합리적으로 판단해주세요
- 테이블 형식을 정확히 지켜주세요 (파이프 | 구분자 사용)
"""

    def save_emails_to_csv(self, emails: List[Dict[str, Any]], user_id: str) -> Path:
        """
        Save email data to CSV file

        Args:
            emails: List of email dictionaries
            user_id: User ID

        Returns:
            Path to saved CSV file
        """
        # Create output directory
        csv_dir = Path(self.config.save_directory) / user_id / "exports"
        csv_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = csv_dir / f"email_metadata_{timestamp}.csv"

        # Write CSV
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            if emails:
                # Define field names
                fieldnames = [
                    'subject', 'sender', 'sender_email', 'received_date',
                    'has_attachments', 'is_read', 'importance', 'body_preview'
                ]

                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for email in emails:
                    row = {
                        'subject': email.get('subject', ''),
                        'sender': email.get('sender', ''),
                        'sender_email': email.get('sender_email', ''),
                        'received_date': email.get('received_date', ''),
                        'has_attachments': email.get('has_attachments', False),
                        'is_read': email.get('is_read', False),
                        'importance': email.get('importance', 'normal'),
                        'body_preview': email.get('body', '')[:200] if email.get('body') else email.get('body_preview', '')[:200]
                    }
                    writer.writerow(row)

        logger.info(f"CSV file saved: {csv_file}")
        return csv_file
