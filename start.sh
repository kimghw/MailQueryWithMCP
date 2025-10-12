#!/bin/bash
# Render deployment startup script

set -e

echo "🚀 Starting Mail Query MCP Server..."

# Load uv environment
export PATH="$HOME/.cargo/bin:$PATH"

# Create data directory for SQLite if it doesn't exist
mkdir -p ./data

# Initialize database and register accounts from environment variables
echo "📦 Initializing database and accounts..."
uv run python <<'EOF'
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path.cwd()))

from infra.core.database import get_database_manager
from infra.core.logger import get_logger

logger = get_logger(__name__)

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
        # Render.com에서는 자동으로 RENDER 환경변수가 설정됨
        default_redirect = "https://mailquerywithmcp.onrender.com/auth/callback" if os.getenv("RENDER") else "http://localhost:5000/auth/callback"
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
                # Insert account (simplified - you may need encryption for secrets)
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
EOF

echo "✅ Initialization complete"

# Start the HTTP MCP server
echo "🌐 Starting HTTP MCP server..."
echo "📍 Port: ${PORT:-8002}"
echo "📍 Host: 0.0.0.0"

# Export PORT for the server to use
export MCP_PORT="${PORT:-8002}"
export MCP_HOST="0.0.0.0"

exec uv run python -m modules.mail_query_without_db.mcp_server
