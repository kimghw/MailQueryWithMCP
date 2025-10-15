#!/usr/bin/env python3
"""Production Deployment - IACS MCP HTTP Server Entry Point

Entry point for production deployment (Render.com, cloud platforms).
Starts the IACS mail management HTTP MCP server.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# MCP stdio 모드가 아님을 명시
os.environ.pop('MCP_STDIO_MODE', None)

from infra.core.logger import get_logger
from infra.core.database import get_database_manager
from modules.mail_iacs.db_service import IACSDBService

logger = get_logger(__name__)


def initialize_database():
    """Initialize IACS database schema and register accounts"""
    logger.info("📦 Initializing IACS database and accounts...")

    try:
        # Initialize IACS database
        db_service = IACSDBService()
        logger.info("✅ IACS database initialized successfully")

        # Log panel information if exists
        panels = db_service.get_all_panel_info()
        if panels:
            logger.info(f"📋 Found {len(panels)} panel(s) configured")
            for panel in panels:
                logger.info(f"  - {panel.panel_name}: {panel.chair_address}")
        else:
            logger.warning("⚠️  No panels configured yet")

        # Log default panel if set
        default_panel = db_service.get_default_panel_name()
        if default_panel:
            logger.info(f"🎯 Default panel: {default_panel}")
        else:
            logger.warning("⚠️  No default panel set")

        # Register accounts from environment variables
        logger.info("📝 Checking for account configurations...")
        db = get_database_manager()
        account_num = 1
        while True:
            prefix = f"ACCOUNT_{account_num}_"
            user_id = os.getenv(f"{prefix}USER_ID")

            if not user_id:
                break

            user_name = os.getenv(f"{prefix}USER_NAME")
            email = os.getenv(f"{prefix}EMAIL")
            tenant_id = os.getenv(f"{prefix}TENANT_ID")
            client_id = os.getenv(f"{prefix}CLIENT_ID")
            client_secret = os.getenv(f"{prefix}CLIENT_SECRET")

            # Render.com automatically sets RENDER environment variable
            default_redirect = (
                "https://iacs-mail-server.onrender.com/auth/callback"
                if os.getenv("RENDER")
                else "http://localhost:5000/auth/callback"
            )
            redirect_uri = os.getenv(f"{prefix}REDIRECT_URI", default_redirect)

            if all([user_name, email, tenant_id, client_id, client_secret]):
                logger.info(f"📝 Registering account {account_num}: {user_id} ({email})")

                # Check if account already exists
                existing = db.fetch_one("SELECT id FROM accounts WHERE user_id = ?", (user_id,))

                if existing:
                    logger.info(f"  ℹ️  Account already exists, updating...")
                    db.execute_query("""
                        UPDATE accounts
                        SET user_name = ?, email = ?,
                            oauth_client_id = ?, oauth_client_secret = ?,
                            oauth_tenant_id = ?, oauth_redirect_uri = ?,
                            updated_at = datetime('now')
                        WHERE user_id = ?
                    """, (user_name, email, client_id, client_secret, tenant_id, redirect_uri, user_id))
                    logger.info(f"  ✅ Account updated successfully")
                else:
                    db.execute_query("""
                        INSERT INTO accounts (
                            user_id, user_name, email,
                            oauth_client_id, oauth_client_secret, oauth_tenant_id, oauth_redirect_uri,
                            status, is_active, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', 1, datetime('now'), datetime('now'))
                    """, (user_id, user_name, email, client_id, client_secret, tenant_id, redirect_uri))
                    logger.info(f"  ✅ Account registered successfully")
            else:
                logger.warning(f"  ⚠️  Incomplete account configuration for {prefix}, skipping...")

            account_num += 1

        if account_num == 1:
            logger.warning("⚠️  No accounts found in environment variables")
            logger.info("   💡 To register accounts, set ACCOUNT_1_USER_ID, ACCOUNT_1_USER_NAME, etc.")
        else:
            logger.info(f"✅ Processed {account_num - 1} account(s)")

    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        # Don't exit - let the server start anyway


def main():
    """Main entry point for production IACS server"""
    logger.info("🚀 Starting PRODUCTION IACS MCP HTTP Server...")
    logger.info(f"📁 Project root: {PROJECT_ROOT}")

    # Create data directory for SQLite if it doesn't exist
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(exist_ok=True)

    # Get port and host from environment
    port = int(os.getenv("PORT") or os.getenv("IACS_SERVER_PORT") or "8002")
    host = os.getenv("IACS_SERVER_HOST") or "0.0.0.0"

    logger.info(f"🌐 Starting IACS HTTP MCP server...")
    logger.info(f"📍 Port: {port}")
    logger.info(f"📍 Host: {host}")

    # Initialize database
    initialize_database()

    # Set environment variables for http_server.py
    os.environ['IACS_SERVER_PORT'] = str(port)
    os.environ['IACS_SERVER_HOST'] = host
    os.environ['PYTHONPATH'] = str(PROJECT_ROOT)

    # Import and run MCP HTTP server
    from modules.mail_iacs.mcp_server import HTTPStreamingIACSServer

    logger.info("✅ Starting MCP HTTP Streaming server...")
    server = HTTPStreamingIACSServer(host=host, port=port)
    server.run()


if __name__ == "__main__":
    main()
