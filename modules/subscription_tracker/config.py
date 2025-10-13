"""Configuration for Subscription Tracker MCP Server"""

import os
from pathlib import Path
from typing import List

from infra.core.logger import get_logger

logger = get_logger(__name__)


class SubscriptionConfig:
    """Configuration for subscription tracking"""

    def __init__(self):
        """Initialize subscription configuration"""
        # Server settings
        self.server_port = int(os.getenv("SUBSCRIPTION_SERVER_PORT", "8003"))
        self.server_host = os.getenv("SUBSCRIPTION_SERVER_HOST", "127.0.0.1")

        # File storage path (WSL-Windows compatible)
        self.save_path = Path(os.getenv(
            "SUBSCRIPTION_SAVE_PATH",
            "/mnt/c/Users/kimghw/Documents/Subscriptions"
        ))

        # Subscription senders
        senders_str = os.getenv("SUBSCRIPTION_SENDERS", "")
        self.subscription_senders = [
            s.strip() for s in senders_str.split(",") if s.strip()
        ]

        # Detection keywords
        keywords_str = os.getenv("SUBSCRIPTION_KEYWORDS", "invoice,receipt,bill,statement")
        self.keywords = [
            k.strip().lower() for k in keywords_str.split(",") if k.strip()
        ]

        # File organization
        self.organize_by_date = os.getenv("SUBSCRIPTION_ORGANIZE_BY_DATE", "true").lower() == "true"
        self.date_format = os.getenv("SUBSCRIPTION_DATE_FORMAT", "%Y-%m")

        # Validate and create paths
        self._validate_config()

    def _validate_config(self):
        """Validate configuration"""
        # Just log the save path, don't create it yet
        logger.info(f"📁 Subscription save path: {self.save_path}")

        # Check if it's a Windows path via WSL
        if str(self.save_path).startswith("/mnt/"):
            logger.info("🪟 Detected WSL-Windows path mapping")
            windows_path = self._to_windows_path(self.save_path)
            logger.info(f"🪟 Windows path: {windows_path}")

        # Log configuration
        logger.info(f"📊 Subscription senders: {len(self.subscription_senders)}")
        logger.info(f"🔍 Detection keywords: {', '.join(self.keywords)}")

    def _to_windows_path(self, wsl_path: Path) -> str:
        """
        Convert WSL path to Windows path for display

        /mnt/c/Users/kimghw/Documents -> C:\\Users\\kimghw\\Documents
        """
        path_str = str(wsl_path)
        if path_str.startswith("/mnt/"):
            # Extract drive letter and path
            parts = path_str[5:].split("/", 1)
            if len(parts) == 2:
                drive, rest = parts
                return f"{drive.upper()}:\\{rest.replace('/', '\\')}"
        return path_str

    def get_sender_folder(self, sender_email: str) -> Path:
        """
        Get folder path for a specific sender

        Args:
            sender_email: Email address of sender

        Returns:
            Path to sender's folder
        """
        # Extract company name from email (e.g., netflix@netflix.com -> netflix)
        sender_name = sender_email.split("@")[0].lower()
        return self.save_path / sender_name

    def get_date_folder(self, sender_folder: Path, date_str: str) -> Path:
        """
        Get date-organized folder path

        Args:
            sender_folder: Base sender folder
            date_str: Date string in configured format

        Returns:
            Path to date folder
        """
        if self.organize_by_date:
            return sender_folder / date_str
        return sender_folder

    def add_sender(self, email: str):
        """Add a new subscription sender"""
        if email not in self.subscription_senders:
            self.subscription_senders.append(email)
            logger.info(f"✅ Added subscription sender: {email}")

    def remove_sender(self, email: str):
        """Remove a subscription sender"""
        if email in self.subscription_senders:
            self.subscription_senders.remove(email)
            logger.info(f"🗑️  Removed subscription sender: {email}")

    def is_subscription_sender(self, email: str) -> bool:
        """Check if email is a subscription sender"""
        email_lower = email.lower()
        return any(
            sender.lower() in email_lower or email_lower in sender.lower()
            for sender in self.subscription_senders
        )

    def has_subscription_keyword(self, filename: str) -> bool:
        """Check if filename contains subscription keywords"""
        filename_lower = filename.lower()
        return any(keyword in filename_lower for keyword in self.keywords)

    def to_dict(self) -> dict:
        """Convert configuration to dictionary"""
        return {
            "server_port": self.server_port,
            "server_host": self.server_host,
            "save_path": str(self.save_path),
            "windows_path": self._to_windows_path(self.save_path),
            "subscription_senders": self.subscription_senders,
            "keywords": self.keywords,
            "organize_by_date": self.organize_by_date,
            "date_format": self.date_format
        }


# Singleton instance
_config_instance = None


def get_subscription_config() -> SubscriptionConfig:
    """Get subscription configuration singleton"""
    global _config_instance
    if _config_instance is None:
        _config_instance = SubscriptionConfig()
    return _config_instance
