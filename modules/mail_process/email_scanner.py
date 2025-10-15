"""Email Scanner for Subscription Tracking"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

from infra.core.database import get_database_manager
from infra.core.logger import get_logger
from modules.mail_query import (
    MailQuerySeverFilters,
    MailQueryOrchestrator,
    MailQueryRequest,
    PaginationOptions
)
from modules.subscription_tracker.config import get_subscription_config

logger = get_logger(__name__)


class SubscriptionEmailScanner:
    """Scanner for subscription-related emails"""

    def __init__(self):
        """Initialize email scanner"""
        self.db = get_database_manager()
        self.config = get_subscription_config()

    async def scan_emails(self, user_id: str, days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Scan emails for subscription-related content

        Args:
            user_id: User ID to scan
            days_back: Number of days to look back

        Returns:
            List of subscription emails with attachments
        """
        logger.info(f"🔍 Scanning subscription emails for user: {user_id}")

        # Calculate date range
        end_date = datetime.now(timezone.utc).replace(tzinfo=None)
        start_date = end_date - timedelta(days=days_back)

        subscription_emails = []

        # Scan each subscription sender
        for sender_email in self.config.subscription_senders:
            logger.info(f"📧 Scanning emails from: {sender_email}")

            try:
                # Create mail query orchestrator
                orchestrator = MailQueryOrchestrator()

                # Create filters for this sender
                filters = MailQuerySeverFilters(
                    date_from=start_date,
                    date_to=end_date,
                    sender_address=sender_email
                )

                # Create request
                request = MailQueryRequest(
                    user_id=user_id,
                    filters=filters,
                    pagination=PaginationOptions(top=50, skip=0, max_pages=1),
                    select_fields=["id", "subject", "from", "receivedDateTime",
                                 "hasAttachments", "attachments"]
                )

                # Execute query
                async with orchestrator:
                    response = await orchestrator.mail_query_user_emails(request)

                # Filter emails with relevant attachments
                for mail in response.messages:
                    if self._has_relevant_attachments_from_mail(mail):
                        sender_addr = ""
                        if mail.from_address and isinstance(mail.from_address, dict):
                            email_addr = mail.from_address.get("emailAddress", {})
                            sender_addr = email_addr.get("address", "")

                        subscription_emails.append({
                            "email_id": mail.id,
                            "subject": mail.subject,
                            "sender": sender_addr,
                            "received_datetime": mail.received_date_time.isoformat(),
                            "has_attachments": mail.has_attachments,
                            "attachments": self._extract_relevant_attachments_from_mail(mail)
                        })

                logger.info(f"✅ Found {len(response.messages)} emails from {sender_email}")

            except Exception as e:
                logger.error(f"❌ Error scanning {sender_email}: {e}")
                continue

        logger.info(f"📊 Total subscription emails found: {len(subscription_emails)}")
        return subscription_emails

    def _has_relevant_attachments_from_mail(self, mail) -> bool:
        """Check if mail has attachments with subscription keywords"""
        if not mail.has_attachments:
            return False

        if not hasattr(mail, "attachments") or not mail.attachments:
            return False

        for attachment in mail.attachments:
            if isinstance(attachment, dict):
                filename = attachment.get("name", "")
            else:
                filename = getattr(attachment, "name", "")

            if self.config.has_subscription_keyword(filename):
                return True

        return False

    def _extract_relevant_attachments_from_mail(self, mail) -> List[Dict[str, str]]:
        """Extract attachments that match subscription keywords"""
        relevant_attachments = []

        if not hasattr(mail, "attachments") or not mail.attachments:
            return relevant_attachments

        for attachment in mail.attachments:
            if isinstance(attachment, dict):
                att_id = attachment.get("id")
                filename = attachment.get("name", "")
                content_type = attachment.get("contentType", "")
                size = attachment.get("size", 0)
            else:
                att_id = getattr(attachment, "id", "")
                filename = getattr(attachment, "name", "")
                content_type = getattr(attachment, "contentType", "")
                size = getattr(attachment, "size", 0)

            if self.config.has_subscription_keyword(filename):
                relevant_attachments.append({
                    "id": att_id,
                    "name": filename,
                    "content_type": content_type,
                    "size": size
                })

        return relevant_attachments
