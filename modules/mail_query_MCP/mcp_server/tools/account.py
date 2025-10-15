"""Account and Authentication Tools for MCP Server"""

import asyncio
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from infra.core.database import get_database_manager
from infra.core.logger import get_logger
from modules.account import AccountOrchestrator
from modules.auth import get_auth_orchestrator, AuthStartRequest
from .account_validator import AccountValidator

logger = get_logger(__name__)


class AccountManagementTool:
    """Tool for managing user accounts and authentication"""

    def __init__(self, config=None):
        """
        Initialize account management tool

        Args:
            config: Configuration object
        """
        self.config = config
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.enrollment_dir = self.project_root / "enrollment"
        self.db = get_database_manager()

    async def register_account(self, arguments: Dict[str, Any]) -> str:
        """
        Register a new account directly to database (no enrollment file needed)

        Args:
            arguments: Tool arguments containing:
                - user_id: User ID
                - email: Email address
                - user_name: User display name (optional)
                - oauth_client_id: OAuth Client ID
                - oauth_client_secret: OAuth Client Secret
                - oauth_tenant_id: OAuth Tenant ID
                - oauth_redirect_uri: OAuth Redirect URI (optional)

        Returns:
            Result message
        """
        try:
            # Extract and validate inputs
            user_id = arguments.get("user_id")
            email = arguments.get("email")
            oauth_client_id = arguments.get("oauth_client_id")
            oauth_client_secret = arguments.get("oauth_client_secret")
            oauth_tenant_id = arguments.get("oauth_tenant_id")
            user_name = arguments.get("user_name", user_id if user_id else "")

            # Set default redirect URI
            import os
            default_redirect = "https://mailquerywithmcp.onrender.com/auth/callback" if os.getenv("RENDER") else "http://localhost:5000/auth/callback"
            oauth_redirect_uri = arguments.get("oauth_redirect_uri", default_redirect)

            # Validate all input data
            validation_data = {
                "user_id": user_id,
                "email": email,
                "oauth_client_id": oauth_client_id,
                "oauth_client_secret": oauth_client_secret,
                "oauth_tenant_id": oauth_tenant_id,
                "oauth_redirect_uri": oauth_redirect_uri,
            }

            is_valid, errors = AccountValidator.validate_enrollment_data(validation_data)
            if not is_valid:
                error_messages = "\n".join([f"  - {err}" for err in errors])
                return f"❌ Validation Error:\n{error_messages}"

            # Check if account already exists
            existing = self.db.fetch_one("SELECT id, user_id FROM accounts WHERE user_id = ?", (user_id,))

            # Create enrollment file first
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

            # Encrypt client secret before storing
            from modules.account._account_helpers import AccountCryptoHelpers
            crypto_helper = AccountCryptoHelpers()
            encrypted_secret = crypto_helper.account_encrypt_sensitive_data(oauth_client_secret)

            # Convert permissions list to JSON string
            default_permissions_json = '["Mail.ReadWrite", "Mail.Send", "offline_access"]'

            if existing:
                # Update existing account with enrollment file path and permissions
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
                """, (user_name, email, oauth_client_id, encrypted_secret, oauth_tenant_id, oauth_redirect_uri, str(enrollment_file), default_permissions_json, user_id))

                logger.info(f"Account updated: {user_id}")

                return f"""✅ 계정 업데이트 완료

사용자 ID: {user_id}
이메일: {email}
Enrollment 파일: {enrollment_file}
상태: 업데이트됨

다음 단계:
start_authentication 툴로 OAuth 인증을 진행하세요."""
            else:
                # Insert new account with enrollment file path and permissions
                self.db.execute_query("""
                    INSERT INTO accounts (
                        user_id, user_name, email,
                        oauth_client_id, oauth_client_secret, oauth_tenant_id, oauth_redirect_uri,
                        enrollment_file_path, delegated_permissions, auth_type,
                        status, is_active, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Authorization Code Flow', 'ACTIVE', 1, datetime('now'), datetime('now'))
                """, (user_id, user_name, email, oauth_client_id, encrypted_secret, oauth_tenant_id, oauth_redirect_uri, str(enrollment_file), default_permissions_json))

                logger.info(f"New account registered: {user_id}")

                return f"""✅ 계정 등록 완료

사용자 ID: {user_id}
이메일: {email}
Enrollment 파일: {enrollment_file}
권한: Mail.ReadWrite, Mail.Send, offline_access
상태: 새로 생성됨

다음 단계:
start_authentication 툴로 OAuth 인증을 진행하세요."""

        except Exception as e:
            error_msg = f"계정 등록 실패: {str(e)}"
            logger.error(error_msg)
            return f"❌ Error: {error_msg}"

    async def create_enrollment_file(self, arguments: Dict[str, Any]) -> str:
        """
        Create enrollment YAML file for user

        Args:
            arguments: Tool arguments containing:
                - user_id: User ID
                - email: Email address
                - user_name: User display name (optional)
                - oauth_client_id: OAuth Client ID
                - oauth_client_secret: OAuth Client Secret
                - oauth_tenant_id: OAuth Tenant ID
                - oauth_redirect_uri: OAuth Redirect URI (optional)
                - delegated_permissions: List of permissions (optional)

        Returns:
            Result message
        """
        try:
            # Set defaults first
            user_id = arguments.get("user_id")
            email = arguments.get("email")
            oauth_client_id = arguments.get("oauth_client_id")
            oauth_client_secret = arguments.get("oauth_client_secret")
            oauth_tenant_id = arguments.get("oauth_tenant_id")
            user_name = arguments.get("user_name", user_id if user_id else "")

            # Render.com에서는 자동으로 RENDER 환경변수가 설정됨
            import os
            default_redirect = "https://mailquerywithmcp.onrender.com/auth/callback" if os.getenv("RENDER") else "http://localhost:5000/auth/callback"
            oauth_redirect_uri = arguments.get("oauth_redirect_uri", default_redirect)
            delegated_permissions = arguments.get("delegated_permissions", [
                "Mail.ReadWrite",
                "Mail.Send",
                "offline_access",
                "Files.ReadWrite.All",
                "Sites.ReadWrite.All"
            ])

            # Validate all input data
            validation_data = {
                "user_id": user_id,
                "email": email,
                "oauth_client_id": oauth_client_id,
                "oauth_client_secret": oauth_client_secret,
                "oauth_tenant_id": oauth_tenant_id,
                "oauth_redirect_uri": oauth_redirect_uri,
                "delegated_permissions": delegated_permissions
            }

            is_valid, errors = AccountValidator.validate_enrollment_data(validation_data)
            if not is_valid:
                error_messages = "\n".join([f"  - {err}" for err in errors])
                return f"❌ Validation Error:\n{error_messages}"

            # Enrollment file path
            enrollment_file = self.enrollment_dir / f"{user_id}.yaml"

            # YAML data structure
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
                    "delegated_permissions": delegated_permissions
                }
            }

            # Save YAML file
            self.enrollment_dir.mkdir(parents=True, exist_ok=True)
            with open(enrollment_file, 'w', encoding='utf-8') as f:
                yaml.dump(enrollment_data, f, default_flow_style=False, allow_unicode=True)

            logger.info(f"Enrollment file created: {enrollment_file}")

            return f"""✅ Enrollment 파일 생성 완료

파일 경로: {enrollment_file}
사용자 ID: {user_id}
이메일: {email}
권한: {', '.join(delegated_permissions)}

다음 단계:
1. enroll_account tool을 사용하여 DB에 등록
2. start_authentication tool을 사용하여 OAuth 인증"""

        except Exception as e:
            error_msg = f"Enrollment 파일 생성 실패: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def list_enrollments(self, arguments: Dict[str, Any]) -> str:
        """
        List all enrollment files

        Args:
            arguments: Tool arguments (unused)

        Returns:
            List of enrollment files
        """
        try:
            if not self.enrollment_dir.exists():
                return "Enrollment 디렉토리가 없습니다."

            yaml_files = list(self.enrollment_dir.glob("*.yaml"))

            if not yaml_files:
                return "등록된 enrollment 파일이 없습니다."

            result = ["📋 Enrollment 파일 목록:\n"]

            for yaml_file in sorted(yaml_files):
                try:
                    with open(yaml_file, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)

                    # Handle both old and new structure
                    if 'account' in data:
                        user_id = data['account'].get('user_id', yaml_file.stem)
                        email = data['account'].get('email', 'N/A')
                    else:
                        user_id = data.get('user_id', yaml_file.stem)
                        email = data.get('email', 'N/A')

                    result.append(f"• {user_id}")
                    result.append(f"  - 파일: {yaml_file.name}")
                    result.append(f"  - 이메일: {email}")
                    result.append("")

                except Exception as e:
                    result.append(f"• {yaml_file.name} (읽기 실패: {str(e)})")

            return "\n".join(result)

        except Exception as e:
            error_msg = f"Enrollment 목록 조회 실패: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def enroll_account(self, arguments: Dict[str, Any]) -> str:
        """
        Enroll a user account into database

        Args:
            arguments: Tool arguments containing user_id

        Returns:
            Enrollment result
        """
        try:
            user_id = arguments.get("user_id")
            if not user_id:
                return "Error: user_id is required"

            # Check enrollment file
            enrollment_file = self.enrollment_dir / f"{user_id}.yaml"
            if not enrollment_file.exists():
                return f"Error: Enrollment 파일이 없습니다: {enrollment_file}\n\ncreate_enrollment_file tool을 먼저 사용하세요."

            # Use AccountOrchestrator
            orchestrator = AccountOrchestrator()
            result = orchestrator.account_sync_single_file(str(enrollment_file))

            if result.get("success"):
                action = result.get("action")

                if action == "created":
                    msg = f"""✅ 계정 등록 완료

사용자 ID: {user_id}
상태: 새로 생성됨

다음 단계:
start_authentication tool을 사용하여 OAuth 인증을 진행하세요."""
                elif action == "updated":
                    msg = f"""✅ 계정 업데이트 완료

사용자 ID: {user_id}
상태: 업데이트됨"""
                else:
                    msg = f"""ℹ️  계정이 이미 최신 상태입니다

사용자 ID: {user_id}"""

                return msg
            else:
                error = result.get("error", "알 수 없는 오류")
                return f"Error: 계정 등록 실패 - {error}"

        except Exception as e:
            error_msg = f"계정 등록 실패: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def list_accounts(self, arguments: Dict[str, Any]) -> str:
        """
        List all enrolled accounts

        Args:
            arguments: Tool arguments with optional 'status' filter

        Returns:
            List of enrolled accounts
        """
        try:
            status_filter = arguments.get("status", "all")

            query = """
                SELECT user_id, user_name, email, status, is_active,
                       token_expiry, last_sync_time, created_at
                FROM accounts
            """

            if status_filter == "active":
                query += " WHERE is_active = 1 AND status = 'active'"
            elif status_filter == "inactive":
                query += " WHERE is_active = 0 OR status != 'active'"

            query += " ORDER BY user_id"

            accounts = self.db.fetch_all(query)

            if not accounts:
                return "등록된 계정이 없습니다."

            result = [f"📋 등록된 계정 목록 (총 {len(accounts)}개):\n"]

            for account in accounts:
                account_dict = dict(account)
                user_id = account_dict.get('user_id', 'N/A')
                email = account_dict.get('email', 'N/A')
                status = account_dict.get('status', 'N/A')
                is_active = account_dict.get('is_active', False)

                # Token expiry status
                token_expiry = account_dict.get('token_expiry')
                if token_expiry:
                    expiry_dt = datetime.fromisoformat(token_expiry)
                    # Ensure both are timezone-naive for comparison
                    if expiry_dt.tzinfo is not None:
                        expiry_dt = expiry_dt.replace(tzinfo=None)
                    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
                    token_status = "만료" if expiry_dt < now_utc else "유효"
                else:
                    token_status = "토큰 없음"

                active_mark = "✅" if is_active else "❌"

                result.append(f"{active_mark} {user_id}")
                result.append(f"  - 이메일: {email}")
                result.append(f"  - 상태: {status}")
                result.append(f"  - 토큰: {token_status}")
                result.append("")

            return "\n".join(result)

        except Exception as e:
            error_msg = f"계정 목록 조회 실패: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def get_account_status(self, arguments: Dict[str, Any]) -> str:
        """
        Get detailed status of specific account

        Args:
            arguments: Tool arguments containing user_id

        Returns:
            Account status information
        """
        try:
            user_id = arguments.get("user_id")
            if not user_id:
                return "Error: user_id is required"

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
                return f"계정을 찾을 수 없습니다: {user_id}"

            account_dict = dict(account)

            # Token status
            token_expiry = account_dict.get('token_expiry')
            if token_expiry:
                expiry_dt = datetime.fromisoformat(token_expiry)
                # Ensure both are timezone-naive for comparison
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
            return f"Error: {error_msg}"

    async def list_active_accounts(self) -> str:
        """
        List all active accounts with detailed information

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

            account_list = ["📊 활성 계정 목록:\n", "="*50 + "\n"]

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
                    from datetime import datetime, timezone
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
            return f"Error: Failed to list accounts - {str(e)}"

    async def start_authentication(self, arguments: Dict[str, Any]) -> str:
        """
        Start OAuth authentication process for user

        Args:
            arguments: Tool arguments containing user_id

        Returns:
            Authentication URL or error message
        """
        try:
            user_id = arguments.get("user_id")
            if not user_id:
                return "Error: user_id is required"

            # Check if account is registered
            account = self.db.fetch_one(
                "SELECT user_id, email FROM accounts WHERE user_id = ?",
                (user_id,)
            )

            if not account:
                return f"Error: 계정이 등록되지 않았습니다: {user_id}\n\nenroll_account tool을 먼저 사용하세요."

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

✅ 인증 완료 후 get_account_status 툴로 상태를 확인할 수 있습니다."""

        except Exception as e:
            error_msg = f"인증 시작 실패: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def check_auth_status(self, arguments: Dict[str, Any]) -> str:
        """
        Check authentication status

        Args:
            arguments: Tool arguments containing session_id

        Returns:
            Authentication status
        """
        try:
            session_id = arguments.get("session_id")
            if not session_id:
                return "Error: session_id is required"

            # Get orchestrator and check session
            orchestrator = get_auth_orchestrator()
            if session_id not in orchestrator.auth_sessions:
                return f"Error: 유효하지 않은 세션 ID입니다: {session_id}"

            session = orchestrator.auth_sessions[session_id]
            user_id = session.user_id

            # Check token status in database
            from infra.core.token_service import get_token_service

            token_service = get_token_service()
            token = await token_service.get_valid_access_token(user_id)

            if token:
                # Get token expiry
                user_data = self.db.fetch_one(
                    "SELECT token_expiry FROM accounts WHERE user_id = ?",
                    (user_id,)
                )

                expiry = "Unknown"
                if user_data:
                    token_expiry = dict(user_data).get('token_expiry')
                    if token_expiry:
                        expiry = token_expiry

                return f"""✅ 인증 상태: 유효

사용자 ID: {user_id}
토큰 만료: {expiry}
상태: 인증됨, 메일 조회 가능"""
            else:
                return f"""❌ 인증 상태: 만료 또는 없음

사용자 ID: {user_id}
상태: 재인증 필요

start_authentication tool을 사용하여 다시 인증하세요."""

        except Exception as e:
            error_msg = f"인증 상태 확인 실패: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def refresh_token(self, user_id: str) -> bool:
        """
        Refresh authentication token for user

        Args:
            user_id: User ID

        Returns:
            True if refresh successful
        """
        try:
            from infra.core.token_service import TokenService

            token_service = TokenService()
            result = await token_service.refresh_token(user_id)

            if result:
                logger.info(f"Token refreshed successfully for {user_id}")
                return True
            else:
                logger.warning(f"Token refresh failed for {user_id}")
                return False

        except Exception as e:
            logger.error(f"Error refreshing token for {user_id}: {str(e)}")
            return False

    async def remove_account(self, user_id: str) -> bool:
        """
        Remove user account

        Args:
            user_id: User ID to remove

        Returns:
            True if removal successful
        """
        try:
            await self.db.delete_user_data(user_id)
            logger.info(f"Account removed: {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error removing account {user_id}: {str(e)}")
            return False

    def get_account_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get detailed account information

        Args:
            user_id: User ID

        Returns:
            Account information dictionary
        """
        try:
            user_data = self.db.get_user_data_sync(user_id)

            if not user_data:
                return {"error": f"Account not found: {user_id}"}

            # Sanitize sensitive data
            account_info = {
                "user_id": user_id,
                "tenant_id": user_data.get("tenant_id"),
                "client_id": user_data.get("client_id", "")[:8] + "..." if user_data.get("client_id") else None,
                "created_at": user_data.get("created_at"),
                "updated_at": user_data.get("updated_at"),
                "token_expires": user_data.get("token_expires_at"),
                "is_authenticated": bool(user_data.get("access_token"))
            }

            return account_info

        except Exception as e:
            logger.error(f"Error getting account info for {user_id}: {str(e)}")
            return {"error": str(e)}