"""File Collector for Subscription Attachments"""

import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from infra.core.logger import get_logger
from modules.mail_query_without_db.core.attachment_downloader import AttachmentDownloader
from ..config import get_subscription_config

logger = get_logger(__name__)


class SubscriptionFileCollector:
    """Collector for subscription attachment files"""

    def __init__(self):
        """Initialize file collector"""
        self.config = get_subscription_config()
        self.downloader = AttachmentDownloader(output_dir=str(self.config.save_path))

    async def collect_attachments(
        self,
        graph_client,
        email_id: str,
        sender_email: str,
        received_datetime: str,
        attachments: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Collect and save attachments from a subscription email

        Args:
            graph_client: Graph API client
            email_id: Email ID
            sender_email: Sender email address
            received_datetime: When email was received
            attachments: List of attachment metadata

        Returns:
            Collection results
        """
        results = {
            "email_id": email_id,
            "sender": sender_email,
            "total_attachments": len(attachments),
            "saved_files": [],
            "errors": []
        }

        # Use single folder (save_path directly)
        target_folder = self.config.save_path
        received_date = datetime.fromisoformat(received_datetime.replace("Z", "+00:00"))

        # Create folder
        try:
            target_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 Target folder: {target_folder}")
        except Exception as e:
            error_msg = f"Failed to create folder: {e}"
            logger.error(f"❌ {error_msg}")
            results["errors"].append(error_msg)
            return results

        # Download each attachment
        for attachment in attachments:
            try:
                file_path = await self._download_attachment(
                    graph_client,
                    email_id,
                    attachment,
                    target_folder,
                    received_date
                )

                if file_path:
                    results["saved_files"].append({
                        "filename": attachment["name"],
                        "path": str(file_path),
                        "size": attachment["size"]
                    })
                    logger.info(f"✅ Saved: {file_path.name}")

            except Exception as e:
                error_msg = f"Failed to download {attachment['name']}: {e}"
                logger.error(f"❌ {error_msg}")
                results["errors"].append(error_msg)

        return results

    async def _download_attachment(
        self,
        graph_client,
        email_id: str,
        attachment: Dict[str, str],
        target_folder: Path,
        received_date: datetime
    ) -> Path:
        """
        Download a single attachment

        Args:
            graph_client: Graph API client
            email_id: Email ID
            attachment: Attachment metadata
            target_folder: Target folder path
            received_date: Date email was received

        Returns:
            Path to saved file
        """
        attachment_id = attachment["id"]
        filename = attachment["name"]

        # Download attachment content using AttachmentDownloader
        content = await self.downloader.download_attachment(
            graph_client,
            email_id,
            attachment_id
        )

        if not content:
            raise ValueError(f"No content received for attachment: {filename}")

        # Generate unique filename if file exists
        file_path = self._get_unique_filepath(target_folder, filename, received_date)

        # Save file (content is already bytes from AttachmentDownloader)
        file_path.write_bytes(content)

        return file_path

    def _get_unique_filepath(self, folder: Path, filename: str, date: datetime) -> Path:
        """
        Get unique file path, adding date/number suffix if file exists

        Args:
            folder: Target folder
            filename: Original filename
            date: Date for suffix

        Returns:
            Unique file path
        """
        # Split filename and extension
        name_parts = filename.rsplit(".", 1)
        if len(name_parts) == 2:
            name, ext = name_parts
            ext = f".{ext}"
        else:
            name = filename
            ext = ""

        # Try original filename
        file_path = folder / filename
        if not file_path.exists():
            return file_path

        # Add date suffix
        date_suffix = date.strftime("%Y%m%d")
        file_path = folder / f"{name}_{date_suffix}{ext}"
        if not file_path.exists():
            return file_path

        # Add number suffix
        counter = 1
        while True:
            file_path = folder / f"{name}_{date_suffix}_{counter}{ext}"
            if not file_path.exists():
                return file_path
            counter += 1

    def get_collection_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get summary of collection results

        Args:
            results: List of collection results

        Returns:
            Summary statistics
        """
        total_emails = len(results)
        total_files = sum(len(r["saved_files"]) for r in results)
        total_errors = sum(len(r["errors"]) for r in results)
        total_size = sum(
            f["size"] for r in results for f in r["saved_files"]
        )

        return {
            "total_emails": total_emails,
            "total_files": total_files,
            "total_errors": total_errors,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
