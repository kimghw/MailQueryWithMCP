"""DCR (Dynamic Client Registration) Service
RFC 7591 준수 동적 클라이언트 등록 서비스
"""

import json
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

from infra.core.database import get_database_manager
from infra.core.logger import get_logger
from modules.enrollment.account import AccountCryptoHelpers

logger = get_logger(__name__)


class DCRService:
    """Dynamic Client Registration Service"""

    def __init__(self):
        self.db = get_database_manager()
        self.crypto = AccountCryptoHelpers()

        # Azure AD 설정 (환경변수 또는 기본 계정에서 가져옴)
        self.azure_client_id = os.getenv("AZURE_CLIENT_ID")
        self.azure_client_secret = os.getenv("AZURE_CLIENT_SECRET")
        self.azure_tenant_id = os.getenv("AZURE_TENANT_ID")

        # DCR 설정이 없으면 기본 계정에서 가져오기
        if not all([self.azure_client_id, self.azure_client_secret, self.azure_tenant_id]):
            self._load_default_azure_config()

    def _load_default_azure_config(self):
        """기본 계정에서 Azure AD 설정 로드"""
        query = """
        SELECT oauth_client_id, oauth_client_secret, oauth_tenant_id
        FROM accounts
        WHERE is_active = 1
        ORDER BY created_at
        LIMIT 1
        """
        result = self.db.fetch_one(query)

        if result:
            self.azure_client_id = result[0]
            # Decrypt client secret
            encrypted_secret = result[1]
            self.azure_client_secret = self.crypto.account_decrypt_sensitive_data(encrypted_secret)
            self.azure_tenant_id = result[2]
            logger.info("✅ Loaded Azure AD config from default account")
        else:
            logger.warning("⚠️ No Azure AD config found. DCR will not work.")

    def _ensure_dcr_schema(self):
        """DCR 스키마 초기화"""
        schema_path = "infra/migrations/dcr_schema.sql"

        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()

            # Remove comments and split by semicolons
            statements = []
            for line in schema_sql.split('\n'):
                line = line.strip()
                if line and not line.startswith('--'):
                    statements.append(line)

            # Join back and split by semicolons
            full_sql = ' '.join(statements)
            for statement in full_sql.split(';'):
                statement = statement.strip()
                if statement:
                    try:
                        self.db.execute_query(statement)
                    except Exception as e:
                        # Ignore table already exists errors
                        if 'already exists' not in str(e):
                            logger.debug(f"Schema execution note: {e}")

            logger.info("✅ DCR schema initialized")

    async def register_client(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        RFC 7591: 동적 클라이언트 등록

        Args:
            request_data: DCR 요청 데이터

        Returns:
            클라이언트 등록 응답 (client_id, client_secret 등)
        """
        # DCR 스키마 확인
        self._ensure_dcr_schema()

        # 고유한 client_id 생성
        client_id = f"dcr_{secrets.token_urlsafe(16)}"
        client_secret = secrets.token_urlsafe(32)
        registration_access_token = secrets.token_urlsafe(32)

        # 현재 시각 (Unix timestamp)
        issued_at = int(time.time())

        # 요청 데이터 추출
        client_name = request_data.get("client_name", "Claude Connector")
        redirect_uris = request_data.get("redirect_uris", ["https://claude.ai/api/mcp/auth_callback"])
        grant_types = request_data.get("grant_types", ["authorization_code", "refresh_token"])
        response_types = request_data.get("response_types", ["code"])
        scope = request_data.get("scope", "Mail.Read User.Read")
        token_endpoint_auth_method = request_data.get("token_endpoint_auth_method", "client_secret_post")

        # Azure AD 설정 확인
        if not all([self.azure_client_id, self.azure_client_secret, self.azure_tenant_id]):
            raise ValueError("Azure AD configuration not available for DCR")

        # DB에 저장
        query = """
        INSERT INTO dcr_clients (
            client_id, client_secret, client_id_issued_at,
            client_name, redirect_uris, token_endpoint_auth_method,
            grant_types, response_types, scope,
            azure_client_id, azure_client_secret, azure_tenant_id,
            registration_access_token
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        # Encrypt Azure client secret
        encrypted_azure_secret = self.crypto.account_encrypt_sensitive_data(self.azure_client_secret)

        self.db.execute_query(
            query,
            (
                client_id,
                self.crypto.account_encrypt_sensitive_data(client_secret),  # Encrypt client secret
                issued_at,
                client_name,
                json.dumps(redirect_uris),
                token_endpoint_auth_method,
                json.dumps(grant_types),
                json.dumps(response_types),
                scope,
                self.azure_client_id,
                encrypted_azure_secret,
                self.azure_tenant_id,
                self.crypto.account_encrypt_sensitive_data(registration_access_token),
            ),
        )

        logger.info(f"✅ DCR client registered: {client_id} (mapped to Azure AD)")

        # RFC 7591 응답
        response = {
            "client_id": client_id,
            "client_secret": client_secret,
            "client_id_issued_at": issued_at,
            "client_secret_expires_at": 0,  # Never expires
            "registration_access_token": registration_access_token,
            "registration_client_uri": f"/oauth/register/{client_id}",
            "token_endpoint_auth_method": token_endpoint_auth_method,
            "grant_types": grant_types,
            "response_types": response_types,
            "client_name": client_name,
            "redirect_uris": redirect_uris,
            "scope": scope,
        }

        return response

    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """클라이언트 정보 조회"""
        query = """
        SELECT client_id, client_name, redirect_uris, grant_types, response_types, scope,
               azure_client_id, azure_client_secret, azure_tenant_id,
               token_endpoint_auth_method, is_active
        FROM dcr_clients
        WHERE client_id = ? AND is_active = 1
        """

        result = self.db.fetch_one(query, (client_id,))

        if not result:
            return None

        return {
            "client_id": result[0],
            "client_name": result[1],
            "redirect_uris": json.loads(result[2]) if result[2] else [],
            "grant_types": json.loads(result[3]) if result[3] else [],
            "response_types": json.loads(result[4]) if result[4] else [],
            "scope": result[5],
            "azure_client_id": result[6],
            "azure_client_secret": self.crypto.account_decrypt_sensitive_data(result[7]),
            "azure_tenant_id": result[8],
            "token_endpoint_auth_method": result[9],
            "is_active": bool(result[10]),
        }

    def verify_client_credentials(self, client_id: str, client_secret: str) -> bool:
        """클라이언트 인증 정보 검증"""
        query = """
        SELECT client_secret
        FROM dcr_clients
        WHERE client_id = ? AND is_active = 1
        """

        result = self.db.fetch_one(query, (client_id,))

        if not result:
            return False

        stored_secret = self.crypto.account_decrypt_sensitive_data(result[0])
        return secrets.compare_digest(stored_secret, client_secret)

    async def delete_client(self, client_id: str, registration_access_token: str) -> bool:
        """클라이언트 삭제 (RFC 7591)"""
        # Verify registration access token
        query = """
        SELECT registration_access_token
        FROM dcr_clients
        WHERE client_id = ? AND is_active = 1
        """

        result = self.db.fetch_one(query, (client_id,))

        if not result:
            return False

        stored_token = self.crypto.account_decrypt_sensitive_data(result[0])

        if not secrets.compare_digest(stored_token, registration_access_token):
            return False

        # Soft delete
        update_query = """
        UPDATE dcr_clients
        SET is_active = 0, updated_at = CURRENT_TIMESTAMP
        WHERE client_id = ?
        """

        self.db.execute_query(update_query, (client_id,))
        logger.info(f"✅ DCR client deleted: {client_id}")

        return True

    def create_authorization_code(
        self, client_id: str, redirect_uri: str, scope: str, state: Optional[str] = None
    ) -> str:
        """Authorization code 생성"""
        code = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(minutes=10)

        query = """
        INSERT INTO dcr_auth_codes (code, client_id, redirect_uri, scope, state, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """

        self.db.execute_query(query, (code, client_id, redirect_uri, scope, state, expires_at))

        return code

    def verify_authorization_code(
        self, code: str, client_id: str, redirect_uri: str
    ) -> Optional[Dict[str, Any]]:
        """Authorization code 검증"""
        query = """
        SELECT client_id, redirect_uri, scope, state, expires_at, used_at
        FROM dcr_auth_codes
        WHERE code = ?
        """

        result = self.db.fetch_one(query, (code,))

        if not result:
            return None

        stored_client_id, stored_redirect_uri, scope, state, expires_at, used_at = result

        # 검증
        if stored_client_id != client_id:
            logger.warning(f"❌ Client ID mismatch: {client_id} != {stored_client_id}")
            return None

        if stored_redirect_uri != redirect_uri:
            logger.warning(f"❌ Redirect URI mismatch: {redirect_uri} != {stored_redirect_uri}")
            return None

        if used_at:
            logger.warning(f"❌ Authorization code already used")
            return None

        if datetime.fromisoformat(expires_at) < datetime.now():
            logger.warning(f"❌ Authorization code expired")
            return None

        # Mark as used
        update_query = """
        UPDATE dcr_auth_codes
        SET used_at = CURRENT_TIMESTAMP
        WHERE code = ?
        """
        self.db.execute_query(update_query, (code,))

        return {
            "scope": scope,
            "state": state,
        }

    def store_token(
        self,
        client_id: str,
        access_token: str,
        refresh_token: Optional[str],
        expires_in: int,
        scope: str,
        azure_access_token: str,
        azure_refresh_token: Optional[str],
        azure_token_expiry: datetime,
    ):
        """토큰 저장"""
        expires_at = datetime.now() + timedelta(seconds=expires_in)

        query = """
        INSERT INTO dcr_tokens (
            client_id, access_token, refresh_token, expires_at, scope,
            azure_access_token, azure_refresh_token, azure_token_expiry
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        self.db.execute_query(
            query,
            (
                client_id,
                self.crypto.account_encrypt_sensitive_data(access_token),
                self.crypto.account_encrypt_sensitive_data(refresh_token) if refresh_token else None,
                expires_at,
                scope,
                self.crypto.account_encrypt_sensitive_data(azure_access_token),
                self.crypto.account_encrypt_sensitive_data(azure_refresh_token) if azure_refresh_token else None,
                azure_token_expiry,
            ),
        )

    def verify_bearer_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Bearer 토큰 검증 및 Azure AD 토큰 반환"""
        # Get all active tokens and decrypt to compare
        query = """
        SELECT client_id, access_token, azure_access_token, azure_token_expiry, scope, expires_at
        FROM dcr_tokens
        WHERE revoked_at IS NULL
        """

        results = self.db.fetch_all(query)

        if not results:
            return None

        # Find matching token by decrypting each one
        for row in results:
            client_id, encrypted_token, encrypted_azure_token, azure_expiry, scope, expires_at = row

            try:
                decrypted_token = self.crypto.account_decrypt_sensitive_data(encrypted_token)

                if secrets.compare_digest(decrypted_token, token):
                    # 토큰 만료 확인
                    if datetime.fromisoformat(expires_at) < datetime.now():
                        logger.warning(f"❌ Token expired")
                        return None

                    azure_access_token = self.crypto.account_decrypt_sensitive_data(encrypted_azure_token)

                    return {
                        "client_id": client_id,
                        "azure_access_token": azure_access_token,
                        "azure_token_expiry": azure_expiry,
                        "scope": scope,
                    }
            except Exception:
                # Skip invalid tokens
                continue

        return None
