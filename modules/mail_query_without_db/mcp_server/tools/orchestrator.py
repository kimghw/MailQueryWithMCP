"""Tool orchestrator for MCP server"""

import logging
from typing import Any, Dict

from .email_query import EmailQueryTool
from .export import ExportTool
from .account import AccountManagementTool
from .help_content import get_tool_help

logger = logging.getLogger(__name__)


class ToolOrchestrator:
    """
    Orchestrator that manages all MCP tools
    Maintains backward compatibility with MailAttachmentTools
    """

    def __init__(self):
        """Initialize all tools"""
        # Load configuration
        from ..config import Config
        self.config = Config()

        # Initialize individual tools
        self.email_tool = EmailQueryTool(self.config)
        self.export_tool = ExportTool(self.config)
        self.account_tool = AccountManagementTool(self.config)

        logger.info("ToolOrchestrator initialized with all tools")

    # Email query methods
    async def query_email(self, arguments: Dict[str, Any]) -> str:
        """Handle mail query with attachments"""
        return await self.email_tool.query_email(arguments)

    # Export methods
    def save_emails_to_csv(self, emails: list[Dict[str, Any]], user_id: str):
        """Save email data to CSV file"""
        return self.export_tool.save_emails_to_csv(emails, user_id)

    def save_emails_to_json(self, emails: list[Dict[str, Any]], user_id: str):
        """Save email data to JSON file"""
        return self.export_tool.save_emails_to_json(emails, user_id)

    def export_email_summary(self, emails: list[Dict[str, Any]], user_id: str, format: str = "markdown"):
        """Export email summary in specified format"""
        return self.export_tool.export_email_summary(emails, user_id, format)

    # Account management methods
    async def list_active_accounts(self) -> str:
        """List all active accounts"""
        return await self.account_tool.list_active_accounts()

    async def create_enrollment_file(self, arguments: Dict[str, Any]) -> str:
        """Create enrollment file"""
        return await self.account_tool.create_enrollment_file(arguments)

    async def list_enrollments(self, arguments: Dict[str, Any]) -> str:
        """List enrollment files"""
        return await self.account_tool.list_enrollments(arguments)

    async def enroll_account(self, arguments: Dict[str, Any]) -> str:
        """Enroll account"""
        return await self.account_tool.enroll_account(arguments)

    async def list_accounts(self, arguments: Dict[str, Any]) -> str:
        """List accounts"""
        return await self.account_tool.list_accounts(arguments)

    async def get_account_status(self, arguments: Dict[str, Any]) -> str:
        """Get account status"""
        return await self.account_tool.get_account_status(arguments)

    async def start_authentication(self, arguments: Dict[str, Any]) -> str:
        """Start authentication"""
        return await self.account_tool.start_authentication(arguments)

    async def check_auth_status(self, arguments: Dict[str, Any]) -> str:
        """Check authentication status"""
        return await self.account_tool.check_auth_status(arguments)

    # Help method
    async def help(self, arguments: Dict[str, Any]) -> str:
        """
        Get help information for tools

        Args:
            arguments: Dictionary with optional 'tool_name' parameter

        Returns:
            Formatted help text
        """
        tool_name = arguments.get("tool_name")
        return get_tool_help(tool_name)

    # Additional utility methods
    def get_config(self):
        """Get configuration object"""
        return self.config

    def get_tool_status(self) -> Dict[str, bool]:
        """
        Get status of all tools

        Returns:
            Dictionary with tool availability status
        """
        return {
            "email_query": self.email_tool is not None,
            "export": self.export_tool is not None,
            "account_management": self.account_tool is not None,
            "config_loaded": self.config is not None
        }

    def get_supported_operations(self) -> list[str]:
        """
        Get list of supported operations

        Returns:
            List of operation names
        """
        return [
            "query_email",
            "save_emails_to_csv",
            "save_emails_to_json",
            "export_email_summary",
            "list_active_accounts",
            "create_enrollment_file",
            "list_enrollments",
            "enroll_account",
            "list_accounts",
            "get_account_status",
            "start_authentication",
            "check_auth_status"
        ]