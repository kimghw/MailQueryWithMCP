"""
Azure AD configuration loading/saving for DCR OAuth module.

These helpers operate with a DCRService-like instance that exposes:
- db_path, crypto, allowed_users, dcr_bearer_ttl_seconds
- _execute_query, _fetch_one methods (delegates are fine)
"""

import os
from infra.core.logger import get_logger

logger = get_logger(__name__)


def ensure_dcr_schema(service) -> None:
    """Initialize DCR V3 schema using the current module's SQL file."""
    import sqlite3
    try:
        conn = sqlite3.connect(service.config.dcr_database_path)
        schema_path = os.path.join(os.path.dirname(__file__), "migrations/dcr_schema_v3.sql")
        with open(schema_path, "r") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        conn.commit()
        conn.close()
        logger.info("✅ DCR V3 schema initialized")
    except Exception as e:
        logger.error(f"❌ DCR V3 schema initialization failed: {e}")
        raise


def revoke_active_dcr_tokens_on_config_change(service) -> None:
    """Revoke active DCR Bearer/refresh tokens when Azure config changes."""
    try:
        count_row = service._fetch_one(
            """
            SELECT COUNT(*) FROM dcr_tokens
            WHERE dcr_status = 'active'
              AND dcr_token_type IN ('Bearer', 'refresh')
            """
        )
        active_count = int(count_row[0]) if count_row and count_row[0] is not None else 0

        service._execute_query(
            """
            UPDATE dcr_tokens
            SET dcr_status = 'revoked'
            WHERE dcr_status = 'active'
              AND dcr_token_type IN ('Bearer', 'refresh')
            """
        )
        logger.info(f"🔒 Revoked {active_count} active DCR tokens due to Azure config change")
    except Exception as e:
        logger.error(f"❌ Failed to revoke DCR tokens on config change: {e}")


def save_azure_config_to_db(service) -> None:
    """Persist Azure config from service fields to DB if present."""
    if not all([service.azure_application_id, service.azure_client_secret]):
        return
    try:
        existing = service._fetch_one(
            "SELECT application_id FROM dcr_azure_auth WHERE application_id = ?",
            (service.azure_application_id,),
        )
        if existing:
            service._execute_query(
                """
                UPDATE dcr_azure_auth
                SET client_secret = ?, tenant_id = ?, redirect_uri = ?
                WHERE application_id = ?
                """,
                (
                    service.crypto.account_encrypt_sensitive_data(service.azure_client_secret),
                    service.azure_tenant_id,
                    service.azure_redirect_uri,
                    service.azure_application_id,
                ),
            )
            logger.info(f"✅ Updated Azure config in dcr_azure_auth: {service.azure_application_id}")
        else:
            service._execute_query(
                """
                INSERT INTO dcr_azure_auth (application_id, client_secret, tenant_id, redirect_uri)
                VALUES (?, ?, ?, ?)
                """,
                (
                    service.azure_application_id,
                    service.crypto.account_encrypt_sensitive_data(service.azure_client_secret),
                    service.azure_tenant_id,
                    service.azure_redirect_uri,
                ),
            )
            logger.info(f"✅ Saved Azure config to dcr_azure_auth: {service.azure_application_id}")
    except Exception as e:
        logger.error(f"❌ Failed to save Azure config to DB: {e}")


def load_azure_config(service) -> None:
    """Load Azure config from DB or environment and keep DB in sync.

    Priority:
    1) dcr_azure_auth table; if env overrides present (client_id and secret), update
       DB and revoke active tokens.
    2) Environment variables, then persist to DB if complete.
    """
    # 1) Load from DB first
    result = service._fetch_one(
        "SELECT application_id, client_secret, tenant_id, redirect_uri FROM dcr_azure_auth LIMIT 1"
    )

    env_app_id = os.getenv("DCR_AZURE_CLIENT_ID")
    env_secret = os.getenv("DCR_AZURE_CLIENT_SECRET")
    env_tenant = os.getenv("DCR_AZURE_TENANT_ID", "common")
    env_redirect = os.getenv("DCR_OAUTH_REDIRECT_URI")

    if result:
        current_app_id = result[0]
        current_secret = service.crypto.account_decrypt_sensitive_data(result[1]) if result[1] else None
        current_tenant = result[2] or "common"
        current_redirect = result[3]

        service.azure_application_id = current_app_id
        service.azure_client_secret = current_secret
        service.azure_tenant_id = current_tenant
        service.azure_redirect_uri = current_redirect

        # Apply env overrides if both id and secret are present
        if env_app_id and env_secret:
            def _norm(v: str | None) -> str:
                return (v or "").strip()

            changes = []
            if _norm(env_app_id) != _norm(current_app_id):
                changes.append("application_id")
            if _norm(env_secret) != _norm(current_secret):
                changes.append("client_secret")
            if env_tenant is not None and _norm(env_tenant) != _norm(current_tenant):
                changes.append("tenant_id")
            if env_redirect is not None and _norm(env_redirect) != _norm(current_redirect):
                changes.append("redirect_uri")

            if changes:
                try:
                    set_clauses = []
                    params = []
                    set_clauses.append("application_id = ?")
                    params.append(env_app_id)
                    set_clauses.append("client_secret = ?")
                    params.append(service.crypto.account_encrypt_sensitive_data(env_secret))
                    if env_tenant is not None:
                        set_clauses.append("tenant_id = ?")
                        params.append(env_tenant)
                    if env_redirect is not None:
                        set_clauses.append("redirect_uri = ?")
                        params.append(env_redirect)

                    update_sql = f"UPDATE dcr_azure_auth SET {', '.join(set_clauses)} WHERE application_id = ?"
                    params.append(current_app_id)
                    service._execute_query(update_sql, tuple(params))

                    # Update in-memory
                    service.azure_application_id = env_app_id
                    service.azure_client_secret = env_secret
                    service.azure_tenant_id = env_tenant if env_tenant is not None else current_tenant
                    service.azure_redirect_uri = env_redirect if env_redirect is not None else current_redirect

                    revoke_active_dcr_tokens_on_config_change(service)
                    logger.info(
                        f"♻️ Updated dcr_azure_auth from environment and revoked active DCR tokens (changed: {', '.join(changes)})"
                    )
                except Exception as e:
                    logger.error(f"❌ Failed to update dcr_azure_auth from environment: {e}")
            else:
                logger.info(f"✅ Loaded Azure config from dcr_azure_auth: {service.azure_application_id}")
        else:
            logger.info(f"✅ Loaded Azure config from dcr_azure_auth: {service.azure_application_id}")
    else:
        # 2) Fallback to environment and persist if complete
        service.azure_application_id = env_app_id
        service.azure_client_secret = env_secret
        service.azure_tenant_id = env_tenant
        service.azure_redirect_uri = env_redirect

        if service.azure_application_id and service.azure_client_secret:
            logger.info(f"✅ Loaded Azure config from environment: {service.azure_application_id}")
            save_azure_config_to_db(service)
        else:
            logger.warning("⚠️ No Azure config found. DCR will not work.")

