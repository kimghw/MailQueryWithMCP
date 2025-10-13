"""Subscription Monitoring Tools for MCP Server"""

import json
from typing import Dict, Any

from infra.core.database import get_database_manager
from infra.core.logger import get_logger
from modules.mail_query import MailQueryOrchestrator
from ...config import get_subscription_config
from ...core.email_scanner import SubscriptionEmailScanner
from ...core.file_collector import SubscriptionFileCollector

logger = get_logger(__name__)


class SubscriptionMonitorTool:
    """Tool for monitoring and collecting subscription emails"""

    def __init__(self):
        """Initialize subscription monitor tool"""
        self.config = get_subscription_config()
        self.scanner = SubscriptionEmailScanner()
        self.collector = SubscriptionFileCollector()
        self.db = get_database_manager()

    async def add_subscription_sender(self, arguments: Dict[str, Any]) -> str:
        """
        Add a new subscription sender to monitor

        Args:
            arguments: {"sender_email": "netflix@netflix.com"}

        Returns:
            Result message
        """
        sender_email = arguments.get("sender_email")

        if not sender_email:
            return "❌ Error: sender_email is required"

        try:
            self.config.add_sender(sender_email)

            return f"""✅ Subscription sender added

Sender: {sender_email}
Total senders: {len(self.config.subscription_senders)}

Current subscription senders:
{chr(10).join(f"  • {s}" for s in self.config.subscription_senders)}"""

        except Exception as e:
            error_msg = f"Failed to add sender: {e}"
            logger.error(error_msg)
            return f"❌ Error: {error_msg}"

    async def list_subscriptions(self, arguments: Dict[str, Any]) -> str:
        """
        List all monitored subscription senders

        Returns:
            List of subscription senders
        """
        try:
            config_dict = self.config.to_dict()

            return f"""📋 Subscription Configuration

🪟 Windows Save Path: {config_dict['windows_path']}
🐧 WSL Save Path: {config_dict['save_path']}

📧 Monitored Senders ({len(config_dict['subscription_senders'])}):
{chr(10).join(f"  {i+1}. {s}" for i, s in enumerate(config_dict['subscription_senders']))}

🔍 Detection Keywords:
{', '.join(config_dict['keywords'])}

⚙️  Settings:
  • Organize by date: {config_dict['organize_by_date']}
  • Date format: {config_dict['date_format']}
  • Server: {config_dict['server_host']}:{config_dict['server_port']}"""

        except Exception as e:
            error_msg = f"Failed to list subscriptions: {e}"
            logger.error(error_msg)
            return f"❌ Error: {error_msg}"

    async def scan_subscription_emails(self, arguments: Dict[str, Any]) -> str:
        """
        Scan and collect subscription emails

        Args:
            arguments: {
                "user_id": "kimghw",
                "start_date": "2025-01-01",  # required
                "end_date": "2025-01-31",    # required
                "download_files": true
            }

        Returns:
            Scan results
        """
        from datetime import datetime, timedelta

        user_id = arguments.get("user_id", "kimghw")
        start_date_str = arguments.get("start_date")
        end_date_str = arguments.get("end_date")
        download_files = arguments.get("download_files", True)

        if not start_date_str or not end_date_str:
            return "❌ Error: start_date and end_date are required"

        try:
            logger.info(f"🔍 Starting subscription scan for {user_id}")

            # Parse dates
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            # Add 1 day to end_date to include the entire end day
            end_date = end_date + timedelta(days=1)
            days_back = (end_date - start_date).days

            logger.info(f"📅 Date range: {start_date_str} to {end_date_str} ({days_back} days)")

            # Scan emails
            emails = await self.scanner.scan_emails(user_id, days_back)

            if not emails:
                return f"""ℹ️  No subscription emails found

User: {user_id}
Days scanned: {days_back}
Monitored senders: {len(self.config.subscription_senders)}

Try:
  • Increasing days_back
  • Adding more senders with add_subscription_sender"""

            # Download files if requested
            collection_results = []
            if download_files:
                logger.info(f"📥 Downloading {len(emails)} subscription emails...")

                # Get access token for this user
                from infra.core.token_service import get_token_service
                token_service = get_token_service()
                access_token = await token_service.get_valid_access_token(user_id)

                if not access_token:
                    return f"❌ Error: No valid access token found for user: {user_id}"

                # Create orchestrator and get graph client
                orchestrator = MailQueryOrchestrator()
                async with orchestrator:
                    # Set access token on graph client
                    orchestrator.graph_client.access_token = access_token
                    orchestrator.graph_client.user_id = user_id

                    # Collect attachments for each email
                    for email in emails:
                        result = await self.collector.collect_attachments(
                            orchestrator.graph_client,
                            email["email_id"],
                            email["sender"],
                            email["received_datetime"],
                            email["attachments"]
                        )
                        collection_results.append(result)

                # Get summary
                summary = self.collector.get_collection_summary(collection_results)

                return f"""✅ Subscription scan complete

User: {user_id}
Days scanned: {days_back}

📊 Results:
  • Emails found: {len(emails)}
  • Files downloaded: {summary['total_files']}
  • Total size: {summary['total_size_mb']} MB
  • Errors: {summary['total_errors']}

💾 Files saved to:
  Windows: {self.config._to_windows_path(self.config.save_path)}
  WSL: {self.config.save_path}

📧 Emails by sender:
{self._format_sender_summary(emails)}"""

            else:
                # Just list found emails without downloading
                return f"""✅ Subscription scan complete (preview only)

User: {user_id}
Days scanned: {days_back}

📊 Results:
  • Emails found: {len(emails)}
  • Total attachments: {sum(len(e['attachments']) for e in emails)}

📧 Emails by sender:
{self._format_sender_summary(emails)}

💡 Run with download_files=true to save attachments"""

        except Exception as e:
            error_msg = f"Scan failed: {e}"
            logger.error(error_msg, exc_info=True)
            return f"❌ Error: {error_msg}"

    async def get_subscription_status(self, arguments: Dict[str, Any]) -> str:
        """
        Get subscription tracking status

        Returns:
            Status information
        """
        try:
            config_dict = self.config.to_dict()

            # Check folder accessibility
            folder_status = "✅ Accessible" if self.config.save_path.exists() else "❌ Not accessible"

            return f"""📊 Subscription Tracker Status

🪟 Windows Path: {config_dict['windows_path']}
   Status: {folder_status}

📧 Monitored Senders: {len(config_dict['subscription_senders'])}
🔍 Keywords: {len(config_dict['keywords'])}

⚙️  Configuration:
  • Server: {config_dict['server_host']}:{config_dict['server_port']}
  • Organize by date: {config_dict['organize_by_date']}
  • Date format: {config_dict['date_format']}

Use list_subscriptions tool for detailed configuration."""

        except Exception as e:
            error_msg = f"Failed to get status: {e}"
            logger.error(error_msg)
            return f"❌ Error: {error_msg}"

    def _format_sender_summary(self, emails: list) -> str:
        """Format sender summary"""
        sender_counts = {}
        for email in emails:
            sender = email["sender"]
            sender_counts[sender] = sender_counts.get(sender, 0) + 1

        lines = []
        for sender, count in sender_counts.items():
            lines.append(f"  • {sender}: {count} email(s)")

        return "\n".join(lines) if lines else "  (none)"
