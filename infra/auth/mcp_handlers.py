"""Common Authentication MCP Handlers

This module provides reusable MCP authentication handlers that can be inherited
by different MCP servers (IACS, mail_query, subscription_tracker, etc.)
"""

from typing import List
from mcp.types import Tool, TextContent

from infra.core.logger import get_logger
from .auth_manager import AuthManager

logger = get_logger(__name__)


class AuthHandlers:
    """Base authentication handlers for MCP servers"""

    def __init__(self):
        """Initialize authentication handlers"""
        self.auth_manager = AuthManager()
        logger.info("✅ AuthHandlers initialized")

    def get_auth_tools(self) -> List[Tool]:
        """
        Get list of authentication MCP tools

        Returns:
            List of authentication Tool objects
        """
        return [
            Tool(
                name="register_account",
                description="Register a new email account with OAuth credentials. Saves account to database for future authentication.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "User ID (e.g., 'kimghw')"
                        },
                        "email": {
                            "type": "string",
                            "description": "Email address (e.g., 'kimghw@krs.co.kr')"
                        },
                        "user_name": {
                            "type": "string",
                            "description": "User display name (optional, defaults to user_id)"
                        },
                        "oauth_client_id": {
                            "type": "string",
                            "description": "Microsoft Azure App OAuth Client ID"
                        },
                        "oauth_client_secret": {
                            "type": "string",
                            "description": "Microsoft Azure App OAuth Client Secret"
                        },
                        "oauth_tenant_id": {
                            "type": "string",
                            "description": "Microsoft Azure AD Tenant ID"
                        },
                        "oauth_redirect_uri": {
                            "type": "string",
                            "description": "OAuth redirect URI (optional, defaults to http://localhost:5000/auth/callback)"
                        },
                    },
                    "required": ["user_id", "email", "oauth_client_id", "oauth_client_secret", "oauth_tenant_id"]
                }
            ),
            Tool(
                name="get_account_status",
                description="Get detailed status and authentication information for a specific account. Shows token status, expiry time, and account details.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "User ID to query"
                        }
                    },
                    "required": ["user_id"]
                }
            ),
            Tool(
                name="start_authentication",
                description="Start OAuth authentication flow for a registered account. Returns an authentication URL that MUST be opened in a browser to complete Microsoft login.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "User ID (must be already registered)"
                        }
                    },
                    "required": ["user_id"]
                }
            ),
            Tool(
                name="list_active_accounts",
                description="List all active accounts with detailed information including token status and creation date.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
        ]

    async def handle_auth_tool(self, name: str, arguments: dict) -> List[TextContent]:
        """
        Handle authentication tool calls

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            List of TextContent with tool results
        """
        logger.info(f"🔐 [Auth Handler] Handling tool: {name}")

        try:
            if name == "register_account":
                result = await self.auth_manager.register_account(arguments)
                return [TextContent(type="text", text=result)]

            elif name == "get_account_status":
                result = await self.auth_manager.get_account_status(arguments)
                return [TextContent(type="text", text=result)]

            elif name == "start_authentication":
                result = await self.auth_manager.start_authentication(arguments)
                return [TextContent(type="text", text=result)]

            elif name == "list_active_accounts":
                result = await self.auth_manager.list_active_accounts()
                return [TextContent(type="text", text=result)]

            else:
                error_msg = f"Unknown authentication tool: {name}"
                logger.error(error_msg)
                return [TextContent(type="text", text=f"❌ Error: {error_msg}")]

        except Exception as e:
            error_msg = f"Authentication tool '{name}' failed: {str(e)}"
            logger.error(error_msg)
            return [TextContent(type="text", text=f"❌ Error: {error_msg}")]

    def is_auth_tool(self, tool_name: str) -> bool:
        """
        Check if tool name is an authentication tool

        Args:
            tool_name: Tool name to check

        Returns:
            True if authentication tool
        """
        auth_tool_names = [
            "register_account",
            "get_account_status",
            "start_authentication",
            "list_active_accounts"
        ]
        return tool_name in auth_tool_names
