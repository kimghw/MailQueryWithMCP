"""DCR (Dynamic Client Registration) Service V3
RFC 7591 준수 동적 클라이언트 등록 서비스
명확한 Azure/DCR 분리 및 Azure Portal 용어 사용
"""

import json
import os
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Tuple

from infra.core.database import get_database_manager
from infra.core.logger import get_logger
from modules.enrollment.account import AccountCryptoHelpers

logger = get_logger(__name__)


class DCRService:
    """
    Dynamic Client Registration Service V3

    테이블 구조:
    - dcr_azure_auth: Azure 앱 인증 정보 (Portal에서 생성)
    - dcr_azure_tokens: Azure 사용자 토큰 (Azure AD에서 받음)
    - dcr_clients: Claude 클라이언트 등록 (DCR이 생성)
    - dcr_tokens: Claude 토큰 (DCR이 발급)
    """

    def __init__(self):
        from infra.core.config import get_config
        self.config = get_config()
        self.db_path = self.config.dcr_database_path
        self.crypto = AccountCryptoHelpers()

        # 스키마 초기화 (가장 먼저 실행)
        self._ensure_dcr_schema()

        # Azure AD 설정 로드
        self._load_azure_config()

        # 허용된 사용자 목록
        allowed_users_str = os.getenv("DCR_ALLOWED_USERS", "").strip()
        self.allowed_users = [email.strip().lower() for email in allowed_users_str.split(",") if email.strip()] if allowed_users_str else []

        if self.allowed_users:
            logger.info(f"✅ DCR access restricted to {len(self.allowed_users)} users")
        else:
            logger.warning("⚠️ DCR access allowed for ALL Azure users")

    def _execute_query(self, query: str, params: tuple = ()):
        """SQL 쿼리 실행 헬퍼"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def _fetch_one(self, query: str, params: tuple = ()):
        """단일 행 조회 헬퍼"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()
        finally:
            conn.close()

    def _fetch_all(self, query: str, params: tuple = ()):
        """여러 행 조회 헬퍼"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            conn.close()

    def _load_azure_config(self):
        """dcr_azure_auth 테이블 또는 환경변수에서 Azure 설정 로드"""
        # 1순위: dcr_azure_auth 테이블
        query = "SELECT application_id, client_secret, tenant_id, redirect_uri FROM dcr_azure_auth LIMIT 1"
        result = self._fetch_one(query)

        if result:
            self.azure_application_id = result[0]
            self.azure_client_secret = self.crypto.account_decrypt_sensitive_data(result[1])
            self.azure_tenant_id = result[2] or "common"
            self.azure_redirect_uri = result[3] or "http://localhost:8000/oauth/azure_callback"
            logger.info(f"✅ Loaded Azure config from dcr_azure_auth: {self.azure_application_id}")
        else:
            # 2순위: 환경변수
            self.azure_application_id = os.getenv("AZURE_CLIENT_ID")
            self.azure_client_secret = os.getenv("AZURE_CLIENT_SECRET")
            self.azure_tenant_id = os.getenv("AZURE_TENANT_ID", "common")
            self.azure_redirect_uri = os.getenv("AZURE_REDIRECT_URI", "http://localhost:8000/oauth/azure_callback")

            if self.azure_application_id and self.azure_client_secret:
                logger.info(f"✅ Loaded Azure config from environment: {self.azure_application_id}")
            else:
                logger.warning("⚠️ No Azure config found. DCR will not work.")

    def _ensure_dcr_schema(self):
        """DCR V3 스키마 초기화"""
        import sqlite3
        from infra.core.config import get_config

        try:
            config = get_config()
            conn = sqlite3.connect(config.dcr_database_path)

            # 스키마 파일 읽기
            schema_path = os.path.join(os.path.dirname(__file__), "../../infra/migrations/dcr_schema_v3.sql")
            with open(schema_path, 'r') as f:
                schema_sql = f.read()

            conn.executescript(schema_sql)
            conn.commit()
            conn.close()
            logger.info("✅ DCR V3 schema initialized")
        except Exception as e:
            logger.error(f"❌ DCR V3 schema initialization failed: {e}")
            raise

    async def register_client(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """RFC 7591: 동적 클라이언트 등록"""
        if not all([self.azure_application_id, self.azure_client_secret]):
            raise ValueError("Azure AD configuration not available")

        # DCR 클라이언트 ID/Secret 생성
        dcr_client_id = f"dcr_{secrets.token_urlsafe(16)}"
        dcr_client_secret = secrets.token_urlsafe(32)
        issued_at = int(datetime.now().timestamp())

        # 요청 데이터
        client_name = request_data.get("client_name", "Claude Connector")
        redirect_uris = request_data.get("redirect_uris", ["https://claude.ai/api/mcp/auth_callback"])
        grant_types = request_data.get("grant_types", ["authorization_code", "refresh_token"])
        scope = request_data.get("scope", "Mail.Read User.Read")

        # dcr_clients 테이블에 저장
        query = """
        INSERT INTO dcr_clients (
            dcr_client_id, dcr_client_secret, dcr_client_name,
            dcr_redirect_uris, dcr_grant_types, dcr_requested_scope, azure_application_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        self._execute_query(
            query,
            (
                dcr_client_id,
                self.crypto.account_encrypt_sensitive_data(dcr_client_secret),
                client_name,
                json.dumps(redirect_uris),
                json.dumps(grant_types),
                scope,
                self.azure_application_id,
            ),
        )

        logger.info(f"✅ DCR client registered: {dcr_client_id}")

        return {
            "client_id": dcr_client_id,
            "client_secret": dcr_client_secret,
            "client_id_issued_at": issued_at,
            "client_secret_expires_at": 0,
            "grant_types": grant_types,
            "client_name": client_name,
            "redirect_uris": redirect_uris,
            "scope": scope,
        }

    def get_client(self, dcr_client_id: str) -> Optional[Dict[str, Any]]:
        """DCR 클라이언트 정보 조회"""
        query = """
        SELECT dcr_client_id, dcr_client_secret, dcr_client_name, dcr_redirect_uris,
               dcr_grant_types, dcr_requested_scope, azure_application_id
        FROM dcr_clients
        WHERE dcr_client_id = ?
        """

        result = self._fetch_one(query, (dcr_client_id,))

        if not result:
            return None

        return {
            "dcr_client_id": result[0],
            "dcr_client_secret": self.crypto.account_decrypt_sensitive_data(result[1]) if result[1] else None,
            "dcr_client_name": result[2],
            "dcr_redirect_uris": json.loads(result[3]) if result[3] else [],
            "dcr_grant_types": json.loads(result[4]) if result[4] else [],
            "dcr_requested_scope": result[5],
            "azure_application_id": result[6],
            # Azure 설정 추가
            "azure_client_secret": self.azure_client_secret,
            "azure_tenant_id": self.azure_tenant_id,
            "azure_redirect_uri": self.azure_redirect_uri,
        }

    def verify_client_credentials(self, dcr_client_id: str, dcr_client_secret: str) -> bool:
        """클라이언트 인증 정보 검증"""
        client = self.get_client(dcr_client_id)
        if not client:
            return False
        return secrets.compare_digest(client.get("dcr_client_secret", ""), dcr_client_secret)

    def create_authorization_code(
        self,
        dcr_client_id: str,
        redirect_uri: str,
        scope: str,
        state: Optional[str] = None,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None
    ) -> str:
        """Authorization code 생성 (PKCE 지원)"""
        code = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(minutes=10)

        metadata = {
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": scope
        }

        if code_challenge:
            metadata["code_challenge"] = code_challenge
            metadata["code_challenge_method"] = code_challenge_method or "plain"

        query = """
        INSERT INTO dcr_tokens (
            dcr_token_value, dcr_client_id, dcr_token_type, expires_at, dcr_status, metadata
        ) VALUES (?, ?, 'authorization_code', ?, 'active', ?)
        """

        self._execute_query(
            query,
            (code, dcr_client_id, expires_at, json.dumps(metadata))
        )

        return code

    def verify_authorization_code(
        self,
        code: str,
        dcr_client_id: str,
        redirect_uri: str = None,
        code_verifier: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Authorization code 검증 (PKCE 지원)"""
        query = """
        SELECT dcr_client_id, metadata, expires_at, dcr_status, azure_object_id
        FROM dcr_tokens
        WHERE dcr_token_value = ? AND dcr_token_type = 'authorization_code'
        """

        result = self._fetch_one(query, (code,))

        if not result:
            logger.warning(f"❌ Authorization code not found")
            return None

        stored_client_id, metadata_str, expires_at, status, azure_object_id = result
        metadata = json.loads(metadata_str) if metadata_str else {}

        # 검증
        if stored_client_id != dcr_client_id:
            logger.warning(f"❌ Client ID mismatch")
            return None

        if status != 'active':
            logger.warning(f"❌ Authorization code already used")
            return None

        if datetime.fromisoformat(expires_at) < datetime.now():
            logger.warning(f"❌ Authorization code expired")
            self._execute_query("UPDATE dcr_tokens SET dcr_status = 'expired' WHERE dcr_token_value = ?", (code,))
            return None

        if redirect_uri and metadata.get("redirect_uri") != redirect_uri:
            logger.warning(f"❌ Redirect URI mismatch")
            return None

        # PKCE 검증
        if "code_challenge" in metadata:
            if not code_verifier:
                logger.warning(f"❌ PKCE required but no code_verifier")
                return None

            if not self._verify_pkce(code_verifier, metadata["code_challenge"], metadata.get("code_challenge_method", "plain")):
                logger.warning(f"❌ PKCE verification failed")
                return None

        # Mark as used
        self._execute_query("UPDATE dcr_tokens SET dcr_status = 'expired' WHERE dcr_token_value = ?", (code,))

        return {"scope": metadata.get("scope"), "state": metadata.get("state"), "azure_object_id": azure_object_id}

    def store_tokens(
        self,
        dcr_client_id: str,
        dcr_access_token: str,
        dcr_refresh_token: Optional[str],
        expires_in: int,
        scope: str,
        azure_object_id: str,
        azure_access_token: str,
        azure_refresh_token: Optional[str],
        azure_expires_at: datetime,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
    ):
        """DCR 토큰 + Azure 토큰 저장"""
        dcr_expires_at = datetime.now() + timedelta(seconds=expires_in)

        # 1) dcr_azure_tokens에 Azure 토큰 저장
        if azure_object_id:
            azure_query = """
            INSERT OR REPLACE INTO dcr_azure_tokens (
                object_id, application_id, access_token, refresh_token, expires_at,
                scope, user_email, user_name, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """

            self._execute_query(
                azure_query,
                (
                    azure_object_id,
                    self.azure_application_id,
                    self.crypto.account_encrypt_sensitive_data(azure_access_token),
                    self.crypto.account_encrypt_sensitive_data(azure_refresh_token) if azure_refresh_token else None,
                    azure_expires_at,
                    scope,
                    user_email,
                    user_name,
                ),
            )
            logger.info(f"✅ Stored Azure token for object_id: {azure_object_id}, user: {user_email}")

        # 2) dcr_tokens에 DCR access token 저장
        dcr_query = """
        INSERT INTO dcr_tokens (
            dcr_token_value, dcr_client_id, dcr_token_type, azure_object_id, expires_at, dcr_status
        ) VALUES (?, ?, 'Bearer', ?, ?, 'active')
        """

        self._execute_query(
            dcr_query,
            (
                self.crypto.account_encrypt_sensitive_data(dcr_access_token),
                dcr_client_id,
                azure_object_id,
                dcr_expires_at,
            ),
        )

        logger.info(f"✅ Stored DCR token for client: {dcr_client_id}")

        # 3) DCR refresh token 저장
        if dcr_refresh_token:
            refresh_expires = datetime.now() + timedelta(days=30)
            refresh_query = """
            INSERT INTO dcr_tokens (
                dcr_token_value, dcr_client_id, dcr_token_type, expires_at, dcr_status
            ) VALUES (?, ?, 'refresh', ?, 'active')
            """
            self._execute_query(
                refresh_query,
                (
                    self.crypto.account_encrypt_sensitive_data(dcr_refresh_token),
                    dcr_client_id,
                    refresh_expires,
                ),
            )

    def verify_bearer_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Bearer 토큰 검증 및 Azure 토큰 반환"""
        query = """
        SELECT d.dcr_client_id, d.dcr_token_value, d.expires_at, d.azure_object_id,
               a.access_token, a.expires_at, a.scope, a.user_email
        FROM dcr_tokens d
        LEFT JOIN dcr_azure_tokens a ON d.azure_object_id = a.object_id
        WHERE d.dcr_token_type = 'Bearer' AND d.dcr_status = 'active' AND d.expires_at > CURRENT_TIMESTAMP
        """

        results = self._fetch_all(query)

        if not results:
            return None

        for row in results:
            dcr_client_id, encrypted_token, dcr_expires_at, azure_object_id, encrypted_azure_token, azure_expires_at, scope, user_email = row

            try:
                decrypted_token = self.crypto.account_decrypt_sensitive_data(encrypted_token)
                if secrets.compare_digest(decrypted_token, token):
                    if not encrypted_azure_token:
                        logger.warning(f"⚠️ DCR token found but no Azure token for object_id: {azure_object_id}")
                        return None

                    azure_access_token = self.crypto.account_decrypt_sensitive_data(encrypted_azure_token)
                    return {
                        "dcr_client_id": dcr_client_id,
                        "azure_object_id": azure_object_id,
                        "azure_access_token": azure_access_token,
                        "azure_expires_at": azure_expires_at,
                        "scope": scope,
                        "user_email": user_email,
                    }
            except Exception as e:
                logger.error(f"Token decryption error: {e}")
                continue

        return None

    def get_azure_tokens_by_object_id(self, azure_object_id: str) -> Optional[Dict[str, Any]]:
        """Azure Object ID로 Azure 토큰 조회"""
        query = """
        SELECT access_token, refresh_token, scope, expires_at, user_email
        FROM dcr_azure_tokens
        WHERE object_id = ?
        """

        result = self._fetch_one(query, (azure_object_id,))

        if not result:
            return None

        access_token, refresh_token, scope, expires_at, user_email = result

        expires_in = int((datetime.fromisoformat(expires_at) - datetime.now()).total_seconds()) if expires_at else 3600
        if expires_in < 0:
            expires_in = 0

        return {
            "access_token": self.crypto.account_decrypt_sensitive_data(access_token),
            "refresh_token": self.crypto.account_decrypt_sensitive_data(refresh_token) if refresh_token else None,
            "scope": scope,
            "expires_in": expires_in,
            "user_email": user_email,
        }

    def update_auth_code_with_object_id(self, auth_code: str, azure_object_id: str):
        """Authorization code에 Azure Object ID 연결"""
        query = """
        UPDATE dcr_tokens
        SET azure_object_id = ?
        WHERE dcr_token_value = ? AND dcr_token_type = 'authorization_code'
        """
        self._execute_query(query, (azure_object_id, auth_code))

    def is_user_allowed(self, user_email: str) -> bool:
        """사용자 허용 여부 확인"""
        if not self.allowed_users:
            return True

        user_email_lower = user_email.lower().strip()
        is_allowed = user_email_lower in self.allowed_users

        if not is_allowed:
            logger.warning(f"❌ Access denied for user: {user_email}")
        else:
            logger.info(f"✅ Access granted for user: {user_email}")

        return is_allowed

    # PKCE Helper Methods
    def _verify_pkce(self, code_verifier: str, code_challenge: str, method: str = "plain") -> bool:
        """PKCE 검증"""
        if method == "plain":
            return secrets.compare_digest(code_verifier, code_challenge)
        elif method == "S256":
            digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
            calculated_challenge = base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
            return secrets.compare_digest(calculated_challenge, code_challenge)
        else:
            return False
