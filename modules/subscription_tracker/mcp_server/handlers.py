"""MCP Protocol handlers for Subscription Tracker"""

import json
import logging
from typing import Any, Dict, List

from mcp.types import Prompt, PromptMessage, TextContent, Tool

from infra.core.logger import get_logger
from .tools.subscription_monitor import SubscriptionMonitorTool

logger = get_logger(__name__)


class SubscriptionHandlers:
    """MCP Protocol handlers for subscription tracking"""

    def __init__(self):
        self.tool = SubscriptionMonitorTool()

    async def handle_list_tools(self) -> List[Tool]:
        """List available tools"""
        logger.info("🔧 [Subscription Handler] list_tools() called")

        return [
            Tool(
                name="add_subscription_sender",
                title="➕ Add Subscription Sender",
                description="Add a new email sender to monitor for subscription invoices/receipts",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sender_email": {
                            "type": "string",
                            "description": "Email address of subscription service (e.g., 'netflix@netflix.com')"
                        }
                    },
                    "required": ["sender_email"]
                }
            ),
            Tool(
                name="list_subscriptions",
                title="📋 List Subscriptions",
                description="List all monitored subscription senders and configuration",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="scan_subscription_emails",
                title="🔍 Scan Subscription Emails",
                description="Scan for subscription emails and automatically download invoice/receipt attachments to Windows folder",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "User ID (must be registered in main mail query server)",
                            "default": "kimghw"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM-DD format (e.g., '2025-01-01')"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in YYYY-MM-DD format (e.g., '2025-01-31')"
                        },
                        "download_files": {
                            "type": "boolean",
                            "description": "Download and save attachments to disk",
                            "default": True
                        }
                    },
                    "required": ["start_date", "end_date"]
                }
            ),
            Tool(
                name="get_subscription_status",
                title="📊 Get Status",
                description="Get subscription tracker status and configuration",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="help",
                title="❓ Help",
                description="Get help and usage information for subscription tracker tools",
                inputSchema={"type": "object", "properties": {}}
            ),
        ]

    async def handle_call_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle tool calls"""
        logger.info(f"🛠️ [Subscription Handler] call_tool() called with tool: {name}")
        logger.info(f"📝 [Subscription Handler] Arguments: {json.dumps(arguments, indent=2, ensure_ascii=False)}")

        try:
            if name == "add_subscription_sender":
                result = await self.tool.add_subscription_sender(arguments)
                return [TextContent(type="text", text=result)]

            elif name == "list_subscriptions":
                result = await self.tool.list_subscriptions(arguments)
                return [TextContent(type="text", text=result)]

            elif name == "scan_subscription_emails":
                result = await self.tool.scan_subscription_emails(arguments)
                return [TextContent(type="text", text=result)]

            elif name == "get_subscription_status":
                result = await self.tool.get_subscription_status(arguments)
                return [TextContent(type="text", text=result)]

            elif name == "help":
                result = self._get_help()
                return [TextContent(type="text", text=result)]

            else:
                error_msg = f"Unknown tool: {name}"
                logger.error(error_msg)
                return [TextContent(type="text", text=f"❌ Error: {error_msg}")]

        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return [TextContent(type="text", text=f"❌ Error: {error_msg}")]

    async def handle_list_prompts(self) -> List[Prompt]:
        """List available prompts"""
        logger.info("📋 [Subscription Handler] list_prompts() called")
        return []

    async def handle_get_prompt(self, name: str, arguments: Dict[str, Any]) -> PromptMessage:
        """Get specific prompt"""
        logger.info(f"📝 [Subscription Handler] get_prompt() called with prompt: {name}")
        raise ValueError(f"Prompt not found: {name}")

    def _get_help(self) -> str:
        """Get help information"""
        return """
============================================================
💳 Subscription Tracker MCP Server - Help
============================================================

📖 Overview:
Automatically tracks subscription-related emails and saves
invoice/receipt attachments to your Windows folder.

🔧 Available Tools:

1. ➕ add_subscription_sender
   Add a new subscription service to monitor
   Example: add_subscription_sender(sender_email="netflix@netflix.com")

2. 📋 list_subscriptions
   View all monitored subscriptions and configuration
   Example: list_subscriptions()

3. 🔍 scan_subscription_emails
   Scan emails and download invoice/receipt attachments
   Example: scan_subscription_emails(
       user_id="kimghw",
       days_back=30,
       download_files=true
   )

4. 📊 get_subscription_status
   Check server status and folder accessibility
   Example: get_subscription_status()

5. ❓ help
   Display this help information
   Example: help()

📖 Usage Flow:
  1️⃣ Register account in main mail query server (port 8002)
  2️⃣ Add subscription senders: add_subscription_sender()
  3️⃣ Scan and collect: scan_subscription_emails()
  4️⃣ Check files in Windows folder

🪟 File Organization:
  C:\\Users\\kimghw\\Documents\\Subscriptions\\
  ├── netflix/
  │   └── 2024-10/
  │       ├── invoice_2024-10-15.pdf
  │       └── receipt_2024-10-15.pdf
  ├── spotify/
  └── adobe/

🔍 Detection Keywords:
  invoice, receipt, bill, statement, 청구서, 영수증, 결제, 구독

⚙️  Configuration:
  Edit .env file to customize:
    - SUBSCRIPTION_SAVE_PATH (Windows folder path)
    - SUBSCRIPTION_SENDERS (comma-separated)
    - SUBSCRIPTION_KEYWORDS (detection keywords)

============================================================
"""
