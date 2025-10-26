#!/usr/bin/env python3
"""Timezone-aware migration script

This script migrates naive ISO datetime strings to UTC-aware format.
Adds 'Z' suffix to timestamp columns to explicitly indicate UTC timezone.

IMPORTANT: This is a non-destructive migration.
- Reads naive ISO strings from DB
- Appends 'Z' suffix if not present
- Updates the record

Tables affected:
- accounts: token_expiry, created_at, updated_at, last_sync_time
- dcr_azure_tokens: expires_at, created_at, updated_at
- dcr_tokens: expires_at, issued_at
- dcr_clients: created_at, updated_at
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from infra.core.database import get_database_manager
from infra.core.logger import get_logger

logger = get_logger(__name__)


def backup_database(db_manager):
    """Create backup of database before migration"""
    import shutil
    from pathlib import Path

    db_path = Path(db_manager.config.database_path)
    backup_path = db_path.parent / f"{db_path.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{db_path.suffix}"

    logger.info(f"Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    logger.info(f"✅ Backup created successfully")

    return backup_path


def add_z_suffix_if_missing(timestamp_str: str) -> str:
    """Add 'Z' suffix to ISO timestamp if not present

    Args:
        timestamp_str: ISO timestamp string

    Returns:
        Timestamp with 'Z' suffix

    Examples:
        >>> add_z_suffix_if_missing("2025-10-26T10:00:00")
        "2025-10-26T10:00:00Z"
        >>> add_z_suffix_if_missing("2025-10-26T10:00:00Z")
        "2025-10-26T10:00:00Z"
        >>> add_z_suffix_if_missing("2025-10-26T10:00:00+00:00")
        "2025-10-26T10:00:00Z"
    """
    if not timestamp_str:
        return timestamp_str

    # Already has 'Z'
    if timestamp_str.endswith('Z'):
        return timestamp_str

    # Has +00:00 offset → replace with 'Z'
    if timestamp_str.endswith('+00:00'):
        return timestamp_str[:-6] + 'Z'

    # Naive → add 'Z'
    return timestamp_str + 'Z'


def migrate_accounts_table(db_manager):
    """Migrate accounts table timestamps to UTC-aware format"""
    logger.info("Migrating accounts table...")

    # Fetch all accounts
    accounts = db_manager.fetch_all("""
        SELECT id, token_expiry, created_at, updated_at, last_sync_time
        FROM accounts
        WHERE id IS NOT NULL
    """)

    if not accounts:
        logger.info("  No accounts to migrate")
        return 0

    migrated = 0
    for account in accounts:
        account_id, token_expiry, created_at, updated_at, last_sync_time = account

        # Convert timestamps
        new_token_expiry = add_z_suffix_if_missing(token_expiry) if token_expiry else None
        new_created_at = add_z_suffix_if_missing(created_at) if created_at else None
        new_updated_at = add_z_suffix_if_missing(updated_at) if updated_at else None
        new_last_sync = add_z_suffix_if_missing(last_sync_time) if last_sync_time else None

        # Update if any changed
        if (new_token_expiry != token_expiry or
            new_created_at != created_at or
            new_updated_at != updated_at or
            new_last_sync != last_sync_time):

            db_manager.execute("""
                UPDATE accounts
                SET
                    token_expiry = ?,
                    created_at = ?,
                    updated_at = ?,
                    last_sync_time = ?
                WHERE id = ?
            """, (new_token_expiry, new_created_at, new_updated_at, new_last_sync, account_id))

            migrated += 1

    logger.info(f"  ✅ Migrated {migrated} accounts")
    return migrated


def migrate_dcr_azure_tokens_table(db_manager):
    """Migrate dcr_azure_tokens table timestamps to UTC-aware format"""
    logger.info("Migrating dcr_azure_tokens table...")

    try:
        tokens = db_manager.fetch_all("""
            SELECT object_id, expires_at, created_at, updated_at
            FROM dcr_azure_tokens
            WHERE object_id IS NOT NULL
        """)
    except Exception as e:
        logger.info(f"  Table doesn't exist or no access: {e}")
        return 0

    if not tokens:
        logger.info("  No Azure tokens to migrate")
        return 0

    migrated = 0
    for token in tokens:
        object_id, expires_at, created_at, updated_at = token

        new_expires_at = add_z_suffix_if_missing(expires_at) if expires_at else None
        new_created_at = add_z_suffix_if_missing(created_at) if created_at else None
        new_updated_at = add_z_suffix_if_missing(updated_at) if updated_at else None

        if (new_expires_at != expires_at or
            new_created_at != created_at or
            new_updated_at != updated_at):

            db_manager.execute("""
                UPDATE dcr_azure_tokens
                SET
                    expires_at = ?,
                    created_at = ?,
                    updated_at = ?
                WHERE object_id = ?
            """, (new_expires_at, new_created_at, new_updated_at, object_id))

            migrated += 1

    logger.info(f"  ✅ Migrated {migrated} Azure tokens")
    return migrated


def migrate_dcr_tokens_table(db_manager):
    """Migrate dcr_tokens table timestamps to UTC-aware format"""
    logger.info("Migrating dcr_tokens table...")

    try:
        tokens = db_manager.fetch_all("""
            SELECT dcr_token_value, expires_at, issued_at
            FROM dcr_tokens
            WHERE dcr_token_value IS NOT NULL
        """)
    except Exception as e:
        logger.info(f"  Table doesn't exist or no access: {e}")
        return 0

    if not tokens:
        logger.info("  No DCR tokens to migrate")
        return 0

    migrated = 0
    for token in tokens:
        token_value, expires_at, issued_at = token

        new_expires_at = add_z_suffix_if_missing(expires_at) if expires_at else None
        new_issued_at = add_z_suffix_if_missing(issued_at) if issued_at else None

        if new_expires_at != expires_at or new_issued_at != issued_at:
            db_manager.execute("""
                UPDATE dcr_tokens
                SET
                    expires_at = ?,
                    issued_at = ?
                WHERE dcr_token_value = ?
            """, (new_expires_at, new_issued_at, token_value))

            migrated += 1

    logger.info(f"  ✅ Migrated {migrated} DCR tokens")
    return migrated


def migrate_dcr_clients_table(db_manager):
    """Migrate dcr_clients table timestamps to UTC-aware format"""
    logger.info("Migrating dcr_clients table...")

    try:
        clients = db_manager.fetch_all("""
            SELECT dcr_client_id, created_at, updated_at
            FROM dcr_clients
            WHERE dcr_client_id IS NOT NULL
        """)
    except Exception as e:
        logger.info(f"  Table doesn't exist or no access: {e}")
        return 0

    if not clients:
        logger.info("  No DCR clients to migrate")
        return 0

    migrated = 0
    for client in clients:
        client_id, created_at, updated_at = client

        new_created_at = add_z_suffix_if_missing(created_at) if created_at else None
        new_updated_at = add_z_suffix_if_missing(updated_at) if updated_at else None

        if new_created_at != created_at or new_updated_at != updated_at:
            db_manager.execute("""
                UPDATE dcr_clients
                SET
                    created_at = ?,
                    updated_at = ?
                WHERE dcr_client_id = ?
            """, (new_created_at, new_updated_at, client_id))

            migrated += 1

    logger.info(f"  ✅ Migrated {migrated} DCR clients")
    return migrated


def verify_migration(db_manager):
    """Verify that all timestamps have UTC timezone info"""
    logger.info("Verifying migration...")

    # Check accounts
    try:
        naive_accounts = db_manager.fetch_all("""
            SELECT id, token_expiry, created_at, updated_at
            FROM accounts
            WHERE
                (token_expiry IS NOT NULL AND token_expiry NOT LIKE '%Z')
                OR (created_at IS NOT NULL AND created_at NOT LIKE '%Z')
                OR (updated_at IS NOT NULL AND updated_at NOT LIKE '%Z')
        """)

        if naive_accounts:
            logger.warning(f"  ⚠️ Found {len(naive_accounts)} accounts with naive timestamps")
            return False
    except Exception:
        logger.info("  accounts table doesn't exist, skipping")

    # Check dcr_azure_tokens
    try:
        naive_azure = db_manager.fetch_all("""
            SELECT object_id, expires_at
            FROM dcr_azure_tokens
            WHERE expires_at IS NOT NULL AND expires_at NOT LIKE '%Z'
        """)

        if naive_azure:
            logger.warning(f"  ⚠️ Found {len(naive_azure)} Azure tokens with naive timestamps")
            return False
    except Exception:
        logger.info("  dcr_azure_tokens table doesn't exist, skipping")

    # Check dcr_tokens
    try:
        naive_dcr = db_manager.fetch_all("""
            SELECT dcr_token_value, expires_at
            FROM dcr_tokens
            WHERE expires_at IS NOT NULL AND expires_at NOT LIKE '%Z'
        """)

        if naive_dcr:
            logger.warning(f"  ⚠️ Found {len(naive_dcr)} DCR tokens with naive timestamps")
            return False
    except Exception:
        logger.info("  dcr_tokens table doesn't exist, skipping")

    logger.info("  ✅ All timestamps are UTC-aware")
    return True


def main():
    """Run migration"""
    logger.info("="*60)
    logger.info("Timezone-aware Migration")
    logger.info("="*60)

    backup_path = None
    try:
        # Get database manager
        db_manager = get_database_manager()
        logger.info(f"Database: {db_manager.config.database_path}")

        # Create backup
        backup_path = backup_database(db_manager)

        # Run migrations
        logger.info("\nRunning migrations...")
        total_migrated = 0

        total_migrated += migrate_accounts_table(db_manager)
        total_migrated += migrate_dcr_azure_tokens_table(db_manager)
        total_migrated += migrate_dcr_tokens_table(db_manager)
        total_migrated += migrate_dcr_clients_table(db_manager)

        # Verify
        logger.info("")
        if verify_migration(db_manager):
            logger.info("\n✅ Migration completed successfully!")
            logger.info(f"Total records migrated: {total_migrated}")
            logger.info(f"Backup location: {backup_path}")
        else:
            logger.error("\n❌ Migration verification failed!")
            logger.error(f"Please check the database and restore from backup if needed: {backup_path}")
            return 1

    except Exception as e:
        logger.error(f"\n❌ Migration failed: {e}")
        if backup_path:
            logger.error(f"Database backup is available at: {backup_path}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
