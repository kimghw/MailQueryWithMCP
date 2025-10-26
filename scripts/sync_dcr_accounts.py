#!/usr/bin/env python3
"""
DCR OAuth로 인증된 계정을 graphapi.db의 accounts 테이블로 동기화하는 스크립트
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from datetime import datetime, timezone
from modules.enrollment.account import AccountCryptoHelpers
from infra.core.database import get_database_manager
from infra.core.logger import get_logger

logger = get_logger(__name__)

def sync_dcr_accounts():
    """claudedcr.db의 Azure 토큰을 graphapi.db의 accounts 테이블로 동기화"""

    crypto = AccountCryptoHelpers()
    db_manager = get_database_manager()

    # claudedcr.db에서 Azure 토큰 조회
    dcr_conn = sqlite3.connect('./data/claudedcr.db')
    dcr_conn.row_factory = sqlite3.Row
    dcr_cursor = dcr_conn.cursor()

    dcr_cursor.execute('''
        SELECT
            dat.object_id,
            dat.user_email,
            dat.user_name,
            dat.access_token,
            dat.refresh_token,
            dat.expires_at,
            dat.scope,
            daa.application_id,
            daa.tenant_id,
            daa.redirect_uri,
            daa.client_secret
        FROM dcr_azure_tokens dat
        JOIN dcr_azure_auth daa ON dat.application_id = daa.application_id
        WHERE dat.user_email IS NOT NULL
    ''')

    azure_tokens = dcr_cursor.fetchall()
    logger.info(f"📋 Found {len(azure_tokens)} accounts in claudedcr.db")

    for token in azure_tokens:
        user_email = token['user_email']
        user_name = token['user_name'] or user_email.split('@')[0]
        auto_user_id = user_email.split('@')[0] if '@' in user_email else user_email

        logger.info(f"🔄 Processing account: {user_email}")

        # Check if account exists in graphapi.db
        existing = db_manager.fetch_one(
            "SELECT id, user_id, email FROM accounts WHERE user_id = ? OR email = ?",
            (auto_user_id, user_email)
        )

        if not existing:
            # Create new account
            logger.info(f"  ✨ Creating new account: {auto_user_id}")

            # Note: tokens are already encrypted in claudedcr.db
            account_data = {
                'user_id': auto_user_id,
                'user_name': user_name,
                'email': user_email,
                'oauth_client_id': token['application_id'],
                'oauth_client_secret': crypto.account_encrypt_sensitive_data(token['client_secret']),
                'oauth_tenant_id': token['tenant_id'],
                'oauth_redirect_uri': token['redirect_uri'],
                'delegated_permissions': '["Mail.ReadWrite", "Mail.Send", "offline_access"]',
                'auth_type': 'Authorization Code Flow',
                'access_token': token['access_token'],  # Already encrypted
                'refresh_token': token['refresh_token'],  # Already encrypted
                'token_expiry': token['expires_at'],
                'status': 'ACTIVE',
                'is_active': 1,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'last_used_at': datetime.now(timezone.utc).isoformat()
            }

            account_id = db_manager.insert('accounts', account_data)
            logger.info(f"  ✅ Created account ID: {account_id}")

        else:
            # Update existing account
            existing_user_id = existing['user_id']
            logger.info(f"  🔄 Updating existing account: {existing_user_id}")

            db_manager.execute_query('''
                UPDATE accounts
                SET access_token = ?,
                    refresh_token = ?,
                    token_expiry = ?,
                    status = 'ACTIVE',
                    is_active = 1,
                    last_used_at = datetime('now'),
                    updated_at = datetime('now')
                WHERE user_id = ?
            ''', (
                token['access_token'],  # Already encrypted
                token['refresh_token'],  # Already encrypted
                token['expires_at'],
                existing_user_id
            ))
            logger.info(f"  ✅ Updated account: {existing_user_id}")

    # Checkpoint to ensure DB file is written
    db_manager.checkpoint()

    dcr_conn.close()

    # Verify sync
    count = db_manager.fetch_one("SELECT COUNT(*) as count FROM accounts")[0]
    logger.info(f"✅ Sync complete. Total accounts in graphapi.db: {count}")

if __name__ == "__main__":
    sync_dcr_accounts()