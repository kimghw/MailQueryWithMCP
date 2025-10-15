"""Authentication Manager

Handles OAuth authentication logic, account registration, and token management.
"""

import os
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from infra.core.database import get_database_manager
from infra.core.logger import get_logger
from modules.auth import get_auth_orchestrator, AuthStartRequest

logger = get_logger(__name__)


class AuthManager:
    """Manages authentication operations for accounts"""

    def __init__(self):
        """Initialize authentication manager"""
        self.db = get_database_manager()
        self.project_root = Path(__file__).parent.parent.parent
        self.enrollment_dir = self.project_root / "enrollment"
        logger.info("✅ AuthManager initialized")

    async def register_account(self, arguments: Dict[str, Any]) -> str:
        """
        Register a new account with OAuth credentials

        Args:
            arguments: Dict containing user_id, email, oauth_* credentials

        Returns:
            Registration result message
        """
        try:
            # Extract arguments
            user_id = arguments.get("user_id")
            email = arguments.get("email")
            oauth_client_id = arguments.get("oauth_client_id")
            oauth_client_secret = arguments.get("oauth_client_secret")
            oauth_tenant_id = arguments.get("oauth_tenant_id")
            user_name = arguments.get("user_name", user_id if user_id else "")

            # Set default redirect URI
            default_redirect = (
                "https://iacs-mail-server.onrender.com/auth/callback"
                if os.getenv("RENDER")
                else "http://localhost:5000/auth/callback"
            )
            oauth_redirect_uri = arguments.get("oauth_redirect_uri", default_redirect)

            # Validate required fields
            if not all([user_id, email, oauth_client_id, oauth_client_secret, oauth_tenant_id]):
                return "❌ Error: Missing required fields (user_id, email, oauth_client_id, oauth_client_secret, oauth_tenant_id)"

            logger.info(f"Registering account: {user_id} ({email})")

            # Check if account exists
            existing = self.db.fetch_one(
                "SELECT id, user_id FROM accounts WHERE user_id = ?",
                (user_id,)
            )

            # Create enrollment file
            enrollment_file = self.enrollment_dir / f"{user_id}.yaml"
            default_permissions = ["Mail.ReadWrite", "Mail.Send", "offline_access"]

            enrollment_data = {
                "account": {
                    "email": email,
                    "name": user_name,
                    "user_id": user_id
                },
                "microsoft_graph": {
                    "client_id": oauth_client_id,
                    "client_secret": oauth_client_secret,
                    "tenant_id": oauth_tenant_id
                },
                "oauth": {
                    "auth_type": "Authorization Code Flow",
                    "redirect_uri": oauth_redirect_uri,
                    "delegated_permissions": default_permissions
                }
            }

            # Save enrollment file
            self.enrollment_dir.mkdir(parents=True, exist_ok=True)
            with open(enrollment_file, 'w', encoding='utf-8') as f:
                yaml.dump(enrollment_data, f, default_flow_style=False, allow_unicode=True)

            logger.info(f"Enrollment file created: {enrollment_file}")

            # Encrypt client secret
            from modules.account._account_helpers import AccountCryptoHelpers
            crypto_helper = AccountCryptoHelpers()
            encrypted_secret = crypto_helper.account_encrypt_sensitive_data(oauth_client_secret)

            # Permissions JSON
            default_permissions_json = '["Mail.ReadWrite", "Mail.Send", "offline_access"]'

            if existing:
                # Update existing account
                self.db.execute_query("""
                    UPDATE accounts
                    SET user_name = ?, email = ?,
                        oauth_client_id = ?, oauth_client_secret = ?,
                        oauth_tenant_id = ?, oauth_redirect_uri = ?,
                        enrollment_file_path = ?,
                        delegated_permissions = COALESCE(delegated_permissions, ?),
                        auth_type = COALESCE(auth_type, 'Authorization Code Flow'),
                        updated_at = datetime('now')
                    WHERE user_id = ?
                """, (user_name, email, oauth_client_id, encrypted_secret, oauth_tenant_id,
                      oauth_redirect_uri, str(enrollment_file), default_permissions_json, user_id))

                logger.info(f"Account updated: {user_id}")

                return f"""✅ 계정 업데이트 완료

사용자 ID: {user_id}
이메일: {email}
Enrollment 파일: {enrollment_file}
상태: 업데이트됨

다음 단계:
start_authentication 도구로 OAuth 인증을 진행하세요."""

            else:
                # Insert new account
                self.db.execute_query("""
                    INSERT INTO accounts (
                        user_id, user_name, email,
                        oauth_client_id, oauth_client_secret, oauth_tenant_id, oauth_redirect_uri,
                        enrollment_file_path, delegated_permissions, auth_type,
                        status, is_active, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Authorization Code Flow', 'ACTIVE', 1, datetime('now'), datetime('now'))
                """, (user_id, user_name, email, oauth_client_id, encrypted_secret, oauth_tenant_id,
                      oauth_redirect_uri, str(enrollment_file), default_permissions_json))

                logger.info(f"New account registered: {user_id}")

                return f"""✅ 계정 등록 완료

사용자 ID: {user_id}
이메일: {email}
Enrollment 파일: {enrollment_file}
권한: Mail.ReadWrite, Mail.Send, offline_access
상태: 새로 생성됨

다음 단계:
start_authentication 도구로 OAuth 인증을 진행하세요."""

        except Exception as e:
            error_msg = f"계정 등록 실패: {str(e)}"
            logger.error(error_msg)
            return f"❌ Error: {error_msg}"

    async def get_account_status(self, arguments: Dict[str, Any]) -> str:
        """
        Get detailed status of specific account

        Args:
            arguments: Dict containing user_id

        Returns:
            Account status information
        """
        try:
            user_id = arguments.get("user_id")
            if not user_id:
                return "❌ Error: user_id is required"

            account = self.db.fetch_one(
                """
                SELECT user_id, user_name, email, status, is_active,
                       token_expiry, last_sync_time, created_at, updated_at
                FROM accounts
                WHERE user_id = ?
                """,
                (user_id,)
            )

            if not account:
                return f"❌ 계정을 찾을 수 없습니다: {user_id}"

            account_dict = dict(account)

            # Token status
            token_expiry = account_dict.get('token_expiry')
            if token_expiry:
                expiry_dt = datetime.fromisoformat(token_expiry)
                if expiry_dt.tzinfo is not None:
                    expiry_dt = expiry_dt.replace(tzinfo=None)
                now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
                if expiry_dt < now_utc:
                    token_status = f"❌ 만료됨 ({token_expiry})"
                else:
                    token_status = f"✅ 유효 (만료: {token_expiry})"
            else:
                token_status = "❌ 토큰 없음"

            # Active status
            is_active = account_dict.get('is_active', False)
            active_status = "✅ 활성" if is_active else "❌ 비활성"

            result = f"""📊 계정 상태 상세 정보

사용자 ID: {account_dict.get('user_id', 'N/A')}
이름: {account_dict.get('user_name', 'N/A')}
이메일: {account_dict.get('email', 'N/A')}

상태: {account_dict.get('status', 'N/A')}
활성 상태: {active_status}
토큰 상태: {token_status}

마지막 동기화: {account_dict.get('last_sync_time', 'N/A')}
생성일: {account_dict.get('created_at', 'N/A')}
수정일: {account_dict.get('updated_at', 'N/A')}"""

            return result

        except Exception as e:
            error_msg = f"계정 상태 조회 실패: {str(e)}"
            logger.error(error_msg)
            return f"❌ Error: {error_msg}"

    async def start_authentication(self, arguments: Dict[str, Any]) -> str:
        """
        Start OAuth authentication process

        Args:
            arguments: Dict containing user_id

        Returns:
            Authentication URL or error message
        """
        try:
            user_id = arguments.get("user_id")
            if not user_id:
                return "❌ Error: user_id is required"

            # Check if account is registered
            account = self.db.fetch_one(
                "SELECT user_id, email FROM accounts WHERE user_id = ?",
                (user_id,)
            )

            if not account:
                return f"❌ Error: 계정이 등록되지 않았습니다: {user_id}\n\nregister_account 도구를 먼저 사용하세요."

            # Use AuthOrchestrator
            orchestrator = get_auth_orchestrator()
            request = AuthStartRequest(user_id=user_id)
            response = await orchestrator.auth_orchestrator_start_authentication(request)

            return f"""🔐 OAuth 인증 시작

사용자 ID: {user_id}
세션 ID: {response.session_id}
만료 시간: {response.expires_at}

🌐 인증 URL (아래 링크를 클릭하세요):
{response.auth_url}

⚠️  중요: 위 URL을 반드시 브라우저에서 열어 Microsoft 로그인을 완료해야 합니다.
브라우저에서 로그인 후 권한 승인을 완료하면 자동으로 인증이 완료됩니다.

✅ 인증 완료 후 get_account_status 도구로 상태를 확인할 수 있습니다."""

        except Exception as e:
            error_msg = f"인증 시작 실패: {str(e)}"
            logger.error(error_msg)
            return f"❌ Error: {error_msg}"

    async def list_active_accounts(self) -> str:
        """
        List all active accounts

        Returns:
            Formatted list of active accounts
        """
        try:
            query = """
                SELECT user_id, user_name, email, status,
                       oauth_tenant_id, oauth_client_id,
                       token_expiry, created_at
                FROM accounts
                WHERE is_active = 1
                ORDER BY user_id
            """

            accounts = self.db.fetch_all(query)

            if not accounts:
                return "활성화된 계정이 없습니다."

            account_list = ["📊 활성 계정 목록:\n", "=" * 50 + "\n"]

            for idx, account in enumerate(accounts, 1):
                account_dict = dict(account)
                user_id = account_dict.get('user_id', 'N/A')
                email = account_dict.get('email', 'N/A')
                tenant_id = account_dict.get('oauth_tenant_id', '')
                client_id = account_dict.get('oauth_client_id', '')
                created_at = account_dict.get('created_at', 'N/A')

                account_list.append(f"\n{idx}. {user_id} ({email})\n")

                if tenant_id:
                    account_list.append(f"   Tenant: {tenant_id}\n")
                if client_id:
                    account_list.append(f"   Client: {client_id[:8]}...\n")
                if created_at:
                    account_list.append(f"   Created: {created_at}\n")

                # Token status
                token_expiry = account_dict.get('token_expiry')
                if token_expiry:
                    expiry_dt = datetime.fromisoformat(token_expiry)
                    if expiry_dt.tzinfo is not None:
                        expiry_dt = expiry_dt.replace(tzinfo=None)
                    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
                    token_status = "만료" if expiry_dt < now_utc else "유효"
                    account_list.append(f"   Token: {token_status}\n")
                else:
                    account_list.append(f"   Token: 없음\n")

            return "".join(account_list)

        except Exception as e:
            logger.error(f"Error listing active accounts: {str(e)}")
            return f"❌ Error: Failed to list accounts - {str(e)}"
