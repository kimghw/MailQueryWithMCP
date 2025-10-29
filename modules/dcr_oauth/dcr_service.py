"""DCR (Dynamic Client Registration) Service V3
RFC 7591 준수 동적 클라이언트 등록 서비스
명확한 Azure/DCR 분리 및 Azure Portal 용어 사용
"""

import json
import os
import secrets
import hashlib
import base64
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any, Tuple

from infra.core.database import get_database_manager
from infra.core.logger import get_logger
from modules.enrollment.account import AccountCryptoHelpers
from . import db_utils
from .azure_config import (
    ensure_dcr_schema as _ensure_dcr_schema_helper,
    load_azure_config as _load_azure_config_helper,
    save_azure_config_to_db as _save_azure_config_helper,
    revoke_active_dcr_tokens_on_config_change as _revoke_tokens_helper,
)
from .pkce import verify_pkce as _verify_pkce_helper

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

        # DCR Bearer 토큰 TTL (초)
        ttl_seconds = int(self.config.dcr_access_token_ttl_seconds)
        if ttl_seconds <= 0:
            logger.warning("⚠️ DCR_ACCESS_TOKEN_TTL_SECONDS가 0 이하입니다. 기본값 3600초를 사용합니다.")
            ttl_seconds = 3600
        self.dcr_bearer_ttl_seconds = ttl_seconds

        if self.allowed_users:
            logger.info(f"✅ DCR access restricted to {len(self.allowed_users)} users")
        else:
            logger.warning("⚠️ DCR access allowed for ALL Azure users")

    def _execute_query(self, query: str, params: tuple = ()): 
        """SQL 쿼리 실행 헬퍼 (위임)"""
        return db_utils.execute_query(self.db_path, query, params)

    def _fetch_one(self, query: str, params: tuple = ()): 
        """단일 행 조회 헬퍼 (위임)"""
        return db_utils.fetch_one(self.db_path, query, params)

    def _fetch_all(self, query: str, params: tuple = ()): 
        """여러 행 조회 헬퍼 (위임)"""
        return db_utils.fetch_all(self.db_path, query, params)

    def _load_azure_config(self):
        """dcr_azure_auth 테이블 또는 환경변수에서 Azure 설정 로드 (위임)"""
        _load_azure_config_helper(self)

    def _revoke_active_dcr_tokens_on_config_change(self):
        """Azure 설정 변경 시 활성화된 DCR Bearer/refresh 토큰을 revoke 처리 (위임)"""
        _revoke_tokens_helper(self)

    def _ensure_dcr_schema(self):
        """DCR V3 스키마 초기화 (위임)"""
        _ensure_dcr_schema_helper(self)

    def _save_azure_config_to_db(self):
        """환경변수에서 읽은 Azure 설정을 DB에 저장 (위임)"""
        _save_azure_config_helper(self)

    async def register_client(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """RFC 7591: 동적 클라이언트 등록 (통합 클라이언트 재사용)"""
        if not all([self.azure_application_id, self.azure_client_secret]):
            raise ValueError("Azure AD configuration not available")

        # 요청 데이터
        client_name = request_data.get("client_name", "Claude Connector")
        redirect_uris = request_data.get("redirect_uris", ["https://claude.ai/api/mcp/auth_callback"])
        grant_types = request_data.get("grant_types", ["authorization_code", "refresh_token"])
        scope = request_data.get("scope", "Mail.Read User.Read")

        # 기존 클라이언트 확인 (같은 scope와 redirect_uri를 가진 클라이언트 재사용)
        existing_query = """
        SELECT dcr_client_id, dcr_client_secret, created_at
        FROM dcr_clients
        WHERE azure_application_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """

        existing_client = self._fetch_one(
            existing_query,
            (self.azure_application_id,)
        )

        if existing_client:
            # 기존 클라이언트 재사용 (tuple로 반환됨)
            dcr_client_id = existing_client[0]  # dcr_client_id
            dcr_client_secret = self.crypto.account_decrypt_sensitive_data(
                existing_client[1]  # dcr_client_secret
            )
            issued_at = int(datetime.fromisoformat(existing_client[2]).timestamp())  # created_at

            logger.info(f"♻️ Reusing existing DCR client: {dcr_client_id}")
        else:
            # 새 클라이언트 생성
            dcr_client_id = f"dcr_{secrets.token_urlsafe(16)}"
            dcr_client_secret = secrets.token_urlsafe(32)
            issued_at = int(datetime.now(timezone.utc).timestamp())

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

            logger.info(f"✅ New DCR client registered: {dcr_client_id}")

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

    def save_azure_tokens_and_sync(
        self,
        *,
        azure_object_id: str,
        azure_access_token: str,
        azure_refresh_token: Optional[str],
        scope: str,
        user_email: Optional[str],
        user_name: Optional[str],
        azure_expires_at: datetime,
        sync_accounts: bool = True,
    ) -> None:
        """Persist Azure tokens to dcr_azure_tokens and sync to accounts table.

        This centralizes the path for saving Azure tokens so any caller
        (e.g., OAuth callback) can ensure graphapi accounts are updated.
        """
        if not azure_object_id:
            raise ValueError("azure_object_id is required")

        # Store in dcr_azure_tokens (encrypted)
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

        if sync_accounts:
            # Sync to accounts table using encrypted values
            encrypted_access = self.crypto.account_encrypt_sensitive_data(azure_access_token)
            encrypted_refresh = (
                self.crypto.account_encrypt_sensitive_data(azure_refresh_token)
                if azure_refresh_token
                else None
            )

            self._sync_with_accounts_table(
                azure_object_id=azure_object_id,
                user_email=user_email,
                user_name=user_name,
                encrypted_access_token=encrypted_access,
                encrypted_refresh_token=encrypted_refresh,
                azure_expires_at=azure_expires_at,
            )

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
        """Authorization code 생성 (PKCE 지원)

        Note: authorization_code는 사용자 로그인 후 리다이렉트 시 전달되는 일회성 코드입니다.
        10분 후 만료되며, 토큰 교환 시 즉시 'expired' 상태로 변경됩니다.
        임시 사용 후 즉시 폐기되므로 암호화하지 않습니다.
        """
        code = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        metadata = {
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": scope
        }

        if code_challenge:
            metadata["code_challenge"] = code_challenge
            metadata["code_challenge_method"] = code_challenge_method or "plain"

        # Delete old authorization codes for this client (keep only the newest)
        delete_query = """
        DELETE FROM dcr_tokens
        WHERE dcr_client_id = ?
          AND dcr_token_type = 'authorization_code'
        """
        self._execute_query(delete_query, (dcr_client_id,))

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

        # timezone-aware 비교
        expiry_dt = datetime.fromisoformat(expires_at)
        if expiry_dt.tzinfo is None:
            expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
        if expiry_dt < datetime.now(timezone.utc):
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
        """DCR 토큰 + Azure 토큰 저장 + accounts 테이블 연동"""
        dcr_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

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

            # accounts 테이블 연동 (암호화된 토큰 전달)
            encrypted_access = self.crypto.account_encrypt_sensitive_data(azure_access_token)
            encrypted_refresh = self.crypto.account_encrypt_sensitive_data(azure_refresh_token) if azure_refresh_token else None

            self._sync_with_accounts_table(
                azure_object_id=azure_object_id,
                user_email=user_email,
                user_name=user_name,
                encrypted_access_token=encrypted_access,
                encrypted_refresh_token=encrypted_refresh,
                azure_expires_at=azure_expires_at
            )

        # 2) 기존 active Bearer 토큰을 무효화 (같은 클라이언트 & 사용자)
        invalidate_query = """
        UPDATE dcr_tokens
        SET dcr_status = 'revoked'
        WHERE dcr_client_id = ?
          AND azure_object_id = ?
          AND dcr_token_type = 'Bearer'
          AND dcr_status = 'active'
        """
        self._execute_query(invalidate_query, (dcr_client_id, azure_object_id))

        # 3) dcr_tokens에 새 DCR access token 저장
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

        logger.info(f"✅ Stored DCR token for client: {dcr_client_id} (revoked old tokens)")

        # 4) DCR refresh token 저장
        if dcr_refresh_token:
            # 기존 refresh 토큰 무효화
            invalidate_refresh = """
            UPDATE dcr_tokens
            SET dcr_status = 'revoked'
            WHERE dcr_client_id = ?
              AND dcr_token_type = 'refresh'
              AND dcr_status = 'active'
            """
            self._execute_query(invalidate_refresh, (dcr_client_id,))

            # 새 refresh 토큰 저장
            refresh_expires = datetime.now(timezone.utc) + timedelta(days=30)
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
        """DCR Bearer 토큰 검증 (Azure 토큰 조회 없음)"""
        query = """
        SELECT dcr_client_id, dcr_token_value, azure_object_id
        FROM dcr_tokens
        WHERE dcr_token_type = 'Bearer'
          AND dcr_status = 'active'
          AND expires_at > CURRENT_TIMESTAMP
        """

        results = self._fetch_all(query)

        if not results:
            return None

        for row in results:
            dcr_client_id, encrypted_dcr_token, azure_object_id = row

            try:
                # DCR 토큰 복호화 후 비교
                decrypted_dcr_token = self.crypto.account_decrypt_sensitive_data(encrypted_dcr_token)
                if secrets.compare_digest(decrypted_dcr_token, token):
                    return {
                        "dcr_client_id": dcr_client_id,
                        "azure_object_id": azure_object_id,
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

        # timezone-aware 계산
        if expires_at:
            expiry_dt = datetime.fromisoformat(expires_at)
            if expiry_dt.tzinfo is None:
                expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
        else:
            expiry_dt = None

        return {
            "access_token": self.crypto.account_decrypt_sensitive_data(access_token),
            "refresh_token": self.crypto.account_decrypt_sensitive_data(refresh_token) if refresh_token else None,
            "scope": scope,
            "user_email": user_email,
            "azure_expires_at": expiry_dt,
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

    def _sync_with_accounts_table(
        self,
        azure_object_id: str,
        user_email: Optional[str],
        user_name: Optional[str],
        encrypted_access_token: str,
        encrypted_refresh_token: Optional[str],
        azure_expires_at: datetime
    ):
        """DCR 인증 완료 시 graphapi.db의 accounts 테이블과 자동 연동 (암호화된 토큰 복사)"""
        try:
            # 이메일 필수 확인
            if not user_email:
                logger.warning(f"User email missing, cannot sync to accounts table")
                return

            # graphapi.db 연결 (get_database_manager가 자동으로 DB와 테이블 생성)
            db_manager = get_database_manager()

            # user_id는 이메일의 로컬 파트 사용 (예: kimghw@krs.co.kr -> kimghw)
            auto_user_id = user_email.split('@')[0] if '@' in user_email else user_email

            # user_id로 계정 조회 (이메일로도 확인)
            existing = db_manager.fetch_one(
                "SELECT id, user_id, email FROM accounts WHERE user_id = ? OR email = ?",
                (auto_user_id, user_email)
            )

            if not existing:
                # 계정이 없으면 생성
                logger.info(f"🆕 Creating new account for user_id: {auto_user_id}, email: {user_email}")

                # OAuth 정보: DCR 설정 사용
                oauth_client_id = self.azure_application_id
                oauth_tenant_id = self.azure_tenant_id
                oauth_redirect_uri = self.azure_redirect_uri
                oauth_client_secret = self.azure_client_secret

                # DCR 테이블에서 실제 사용자의 scope 가져오기
                azure_token = self._fetch_one(
                    "SELECT scope FROM dcr_azure_tokens WHERE object_id = ?",
                    (azure_object_id,)
                )

                # DCR 테이블의 scope를 그대로 사용 (OAuth 2.0 표준: 공백 구분)
                # 없으면 환경변수 기본값 사용
                if azure_token and azure_token[0]:
                    delegated_permissions = azure_token[0]
                else:
                    delegated_permissions = os.getenv("DCR_OAUTH_SCOPE", "offline_access User.Read Mail.ReadWrite")

                # 계정 생성 (이미 암호화된 토큰 그대로 복사)
                db_manager.execute_query("""
                    INSERT INTO accounts (
                        user_id, user_name, email,
                        oauth_client_id, oauth_client_secret, oauth_tenant_id, oauth_redirect_uri,
                        delegated_permissions, auth_type,
                        access_token, refresh_token, token_expiry,
                        status, is_active, created_at, updated_at, last_used_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Authorization Code Flow', ?, ?, ?, 'ACTIVE', 1, datetime('now'), datetime('now'), datetime('now'))
                """, (
                    auto_user_id,
                    user_name or auto_user_id,
                    user_email,
                    oauth_client_id,
                    self.crypto.account_encrypt_sensitive_data(oauth_client_secret),
                    oauth_tenant_id,
                    oauth_redirect_uri,
                    delegated_permissions,  # 공백 구분 문자열 그대로 저장
                    encrypted_access_token,  # 이미 암호화됨
                    encrypted_refresh_token,  # 이미 암호화됨
                    azure_expires_at.isoformat() if azure_expires_at else None
                ))
                logger.info(f"✅ Created new account in graphapi.db for {auto_user_id} ({user_email})")
            else:
                # 기존 계정 업데이트 (이미 암호화된 토큰 그대로 복사)
                existing_user_id = existing["user_id"]
                db_manager.execute_query("""
                    UPDATE accounts
                    SET access_token = ?, refresh_token = ?, token_expiry = ?,
                        status = 'ACTIVE', last_used_at = datetime('now'), updated_at = datetime('now')
                    WHERE user_id = ?
                """, (
                    encrypted_access_token,  # 이미 암호화됨
                    encrypted_refresh_token,  # 이미 암호화됨
                    azure_expires_at.isoformat() if azure_expires_at else None,
                    existing_user_id
                ))
                logger.info(f"✅ Updated account tokens in graphapi.db for {existing_user_id} ({user_email})")

        except Exception as e:
            logger.error(f"Failed to sync with accounts table: {e}")
            # 실패해도 DCR 인증은 계속 진행

    # PKCE Helper Methods
    def _verify_pkce(self, code_verifier: str, code_challenge: str, method: str = "plain") -> bool:
        """PKCE 검증 (위임)"""
        return _verify_pkce_helper(code_verifier, code_challenge, method)
