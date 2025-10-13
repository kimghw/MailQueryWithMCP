#!/usr/bin/env python3
"""Production Deployment - MCP Server Entry Point

Entry point for production deployment (Render.com, cloud platforms).
Handles database initialization, account registration from environment variables,
and starts the HTTP MCP server.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from infra.core.database import get_database_manager
from infra.core.logger import get_logger
from modules.mail_query_without_db.mcp_server.http_server import HTTPStreamingMailAttachmentServer

logger = get_logger(__name__)


def initialize_database():
    """Initialize database and register accounts from environment variables"""
    logger.info("📦 Initializing database and accounts...")

    try:
        # Initialize database
        db = get_database_manager()
        logger.info("✅ Database initialized successfully")

        # Register accounts from environment variables
        # Check for ACCOUNT_1_*, ACCOUNT_2_*, etc.
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
                "https://mailquerywithmcp.onrender.com/auth/callback"
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
                    # Update existing account with new redirect_uri and credentials
                    db.execute_query("""
                        UPDATE accounts
                        SET user_name = ?, email = ?,
                            oauth_client_id = ?, oauth_client_secret = ?,
                            oauth_tenant_id = ?, oauth_redirect_uri = ?,
                            updated_at = datetime('now')
                        WHERE user_id = ?
                    """, (user_name, email, client_id, client_secret, tenant_id, redirect_uri, user_id))
                    logger.info(f"  ✅ Account updated successfully (redirect_uri: {redirect_uri})")
                else:
                    # Insert account
                    db.execute_query("""
                        INSERT INTO accounts (
                            user_id, user_name, email,
                            oauth_client_id, oauth_client_secret, oauth_tenant_id, oauth_redirect_uri,
                            status, is_active, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', 1, datetime('now'), datetime('now'))
                    """, (user_id, user_name, email, client_id, client_secret, tenant_id, redirect_uri))
                    logger.info(f"  ✅ Account registered successfully (redirect_uri: {redirect_uri})")
            else:
                logger.warning(f"  ⚠️  Incomplete account configuration for {prefix}, skipping...")

            account_num += 1

        if account_num == 1:
            logger.warning("⚠️  No accounts found in environment variables")
        else:
            logger.info(f"✅ Processed {account_num - 1} account(s)")

    except Exception as e:
        logger.error(f"❌ Failed to initialize: {e}")
        sys.exit(1)


def main():
    """Main entry point for production server"""
    logger.info("🚀 Starting PRODUCTION Mail Query MCP Server...")
    logger.info(f"📁 Project root: {PROJECT_ROOT}")

    # Create data directory for SQLite if it doesn't exist
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(exist_ok=True)

    # Get port and host from environment
    port = int(os.getenv("PORT") or os.getenv("MCP_PORT") or "8002")
    host = os.getenv("MCP_HOST") or "0.0.0.0"

    logger.info(f"🌐 Starting HTTP MCP server...")
    logger.info(f"📍 Port: {port}")
    logger.info(f"📍 Host: {host}")

    # Initialize database and accounts in background
    import threading
    init_thread = threading.Thread(target=initialize_database, daemon=True)
    init_thread.start()

    # Create and run server (starts immediately for Render health check)
    server = HTTPStreamingMailAttachmentServer(host=host, port=port)
    server.run()


if __name__ == "__main__":
    main()
