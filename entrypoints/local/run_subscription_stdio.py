#!/usr/bin/env python3
"""Local Development - Stdio-based Subscription Tracker MCP Server for Claude Desktop

Entry point for running the Subscription Tracker MCP server in STDIO mode for Claude Desktop integration.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# CRITICAL: Disable console logging BEFORE any imports that use logging
os.environ['ENABLE_CONSOLE_LOGGING'] = 'false'

from mcp.server import Server
from mcp.server.stdio import stdio_server

from modules.subscription_tracker.mcp_server.handlers import SubscriptionHandlers
from infra.core.database import get_database_manager
from infra.core.logger import get_logger

logger = get_logger(__name__)


async def main():
    """Main entry point for subscription tracker stdio MCP server"""

    # Setup logging - file only for stdio mode
    log_dir = PROJECT_ROOT / "logs" / "local"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "subscription_stdio.log"

    # Configure logging to file only (not stdout to avoid interfering with stdio communication)
    # Remove all existing handlers first
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add file handler with UTF-8 encoding
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)

    logger.info("🚀 Starting LOCAL stdio Subscription Tracker MCP Server")
    logger.info(f"📁 Project root: {PROJECT_ROOT}")
    logger.info(f"📝 Log file: {log_file}")

    # Initialize database
    db = get_database_manager()

    try:
        # Check authentication status
        query = "SELECT COUNT(*) FROM accounts WHERE is_active = 1"
        result = db.fetch_one(query)
        active_accounts = result[0] if result else 0

        logger.info(f"✅ Database connection successful")
        logger.info(f"📊 Active accounts found: {active_accounts}")

        if active_accounts > 0:
            auth_query = """
            SELECT user_id,
                   CASE
                       WHEN access_token IS NOT NULL AND token_expiry > datetime('now') THEN 'VALID'
                       WHEN refresh_token IS NOT NULL THEN 'REFRESH_NEEDED'
                       ELSE 'EXPIRED'
                   END as auth_status
            FROM accounts
            WHERE is_active = 1
            ORDER BY user_id
            """
            auth_results = db.fetch_all(auth_query)

            valid_count = sum(1 for row in auth_results if row[1] == "VALID")
            refresh_count = sum(1 for row in auth_results if row[1] == "REFRESH_NEEDED")
            expired_count = sum(1 for row in auth_results if row[1] == "EXPIRED")

            for row in auth_results:
                user_id, status = row
                logger.info(f"   {user_id}: {status}")

            logger.info(f"📊 Auth summary: {valid_count} valid, {refresh_count} need refresh, {expired_count} expired")
        else:
            logger.warning("⚠️ No active accounts found in database")

    except Exception as e:
        logger.error(f"❌ Failed to initialize database or check auth: {str(e)}")
        raise

    # Create MCP server
    server = Server("subscription-tracker-server")
    handlers = SubscriptionHandlers()

    # Register handlers
    @server.list_tools()
    async def list_tools():
        return await handlers.handle_list_tools()

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        return await handlers.handle_call_tool(name, arguments)

    logger.info("✅ Subscription Tracker stdio server initialized")

    # Run stdio server
    async with stdio_server() as (read_stream, write_stream):
        logger.info("📡 Stdio server running")
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {str(e)}", exc_info=True)
        sys.exit(1)
