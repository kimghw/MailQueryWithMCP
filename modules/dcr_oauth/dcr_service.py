"""DCR (Dynamic Client Registration) Service V2
RFC 7591 준수 동적 클라이언트 등록 서비스
단일 테이블 스키마로 최적화
"""

import json
import os
import secrets
import time
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Tuple
from enum import Enum

from infra.core.database import get_database_manager
from infra.core.logger import get_logger
from modules.enrollment.account import AccountCryptoHelpers

logger = get_logger(__name__)


class TokenType(Enum):
    """토큰 타입"""
    CLIENT = "client"           # DCR 클라이언트 등록
    AUTH_CODE = "auth_code"      # Authorization code (임시, 10분)
    ACCESS_TOKEN = "access"      # Access token (1시간)
    REFRESH_TOKEN = "refresh"    # Refresh token (30일)


class DCRServiceV2:
    """
    Dynamic Client Registration Service V2

    단일 테이블(dcr_oauth)로 모든 OAuth 데이터 관리:
    - 클라이언트 등록 정보
    - Authorization codes
    - Access/Refresh tokens
    """

    def __init__(self):
        self.db = get_database_manager()
        self.crypto = AccountCryptoHelpers()

        # Azure AD 설정 (환경변수 또는 기본 계정에서 가져옴)
        # DCR_ 접두사 우선, 기존 이름도 호환성을 위해 지원
        self.azure_client_id = os.getenv("DCR_AZURE_CLIENT_ID") or os.getenv("AZURE_CLIENT_ID")
        self.azure_client_secret = os.getenv("DCR_AZURE_CLIENT_SECRET") or os.getenv("AZURE_CLIENT_SECRET")
        self.azure_tenant_id = os.getenv("DCR_AZURE_TENANT_ID") or os.getenv("AZURE_TENANT_ID") or "common"

        # 허용된 사용자 목록 (쉼표로 구분된 이메일)
        allowed_users_str = os.getenv("DCR_ALLOWED_USERS", "").strip()
        self.allowed_users = [email.strip().lower() for email in allowed_users_str.split(",") if email.strip()] if allowed_users_str else []

        if self.allowed_users:
            logger.info(f"✅ DCR access restricted to {len(self.allowed_users)} users")
        else:
            logger.warning("⚠️ DCR access allowed for ALL Azure users (no DCR_ALLOWED_USERS set)")

        # DCR 설정이 없으면 기본 계정에서 가져오기
        if not all([self.azure_client_id, self.azure_client_secret]):
            self._load_default_azure_config()

        # 스키마 초기화
        self._ensure_dcr_schema()

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
            self.azure_tenant_id = result[2] or "common"
            logger.info("✅ Loaded Azure AD config from default account")
        else:
            logger.warning("⚠️ No Azure AD config found. DCR will not work.")

    def _ensure_dcr_schema(self):
        """DCR 3-테이블 스키마 초기화 (Claude vs Azure 데이터 분리)"""
        schema_sql = """
        -- 1) DCR 클라이언트 (Claude가 보는 정보)
        CREATE TABLE IF NOT EXISTS dcr_clients (
            client_id        TEXT PRIMARY KEY,
            client_secret    TEXT NOT NULL,
            client_name      TEXT,
            redirect_uris    TEXT,                  -- JSON string
            grant_types      TEXT,                  -- JSON string
            requested_scope  TEXT,
            azure_client_id  TEXT NOT NULL,
            created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- 2) DCR 토큰 (토큰 회전 추적)
        CREATE TABLE IF NOT EXISTS dcr_tokens (
            token_value   TEXT PRIMARY KEY,
            client_id     TEXT NOT NULL,
            token_type    TEXT DEFAULT 'Bearer',
            issued_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at    DATETIME NOT NULL,
            status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked','expired')),
            rotated_from  TEXT,
            metadata      TEXT,                     -- JSON string (PKCE, redirect_uri 등)
            FOREIGN KEY (client_id) REFERENCES dcr_clients(client_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_dcrt_expires_at ON dcr_tokens(expires_at);
        CREATE INDEX IF NOT EXISTS idx_dcrt_client_active ON dcr_tokens(client_id, status);

        -- 3) Azure 토큰 (Claude는 접근 불가)
        CREATE TABLE IF NOT EXISTS azure_tokens (
            azure_token_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id          TEXT NOT NULL,
            azure_tenant_id    TEXT,
            principal_type     TEXT NOT NULL DEFAULT 'delegated' CHECK (principal_type IN ('application','delegated')),
            principal_id       TEXT,
            resource           TEXT NOT NULL DEFAULT 'https://graph.microsoft.com',
            granted_scope      TEXT,
            azure_access_token TEXT NOT NULL,
            azure_refresh_token TEXT,
            azure_token_expiry DATETIME NOT NULL,
            user_email         TEXT,
            user_name          TEXT,
            created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES dcr_clients(client_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_azt_client ON azure_tokens(client_id);
        CREATE INDEX IF NOT EXISTS idx_azt_expiry ON azure_tokens(azure_token_expiry);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_azt_ctx
            ON azure_tokens (client_id, resource, COALESCE(azure_tenant_id,''), COALESCE(principal_id,''));
        """

        try:
            import sqlite3
            from infra.core.config import get_config
            config = get_config()
            conn = sqlite3.connect(config.database_path)
            conn.executescript(schema_sql)
            conn.commit()
            conn.close()
            logger.info("✅ DCR V3 schema initialized (3-table structure)")
        except Exception as e:
            logger.error(f"❌ DCR V3 schema initialization failed: {e}")
            raise

    async def register_client(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        RFC 7591: 동적 클라이언트 등록 (dcr_clients 테이블)
        """
        # Azure AD 설정 확인
        if not all([self.azure_client_id, self.azure_client_secret]):
            raise ValueError("Azure AD configuration not available for DCR")

        # 고유한 client_id와 secret 생성
        client_id = f"dcr_{secrets.token_urlsafe(16)}"
        client_secret = secrets.token_urlsafe(32)

        # 현재 시각 (Unix timestamp)
        issued_at = int(time.time())

        # 요청 데이터 추출
        client_name = request_data.get("client_name", "Claude Connector")
        redirect_uris = request_data.get("redirect_uris", ["https://claude.ai/api/mcp/auth_callback"])
        grant_types = request_data.get("grant_types", ["authorization_code", "refresh_token"])
        scope = request_data.get("scope", "Mail.Read User.Read")

        # dcr_clients 테이블에 클라이언트 정보 저장
        query = """
        INSERT INTO dcr_clients (
            client_id, client_secret, client_name,
            redirect_uris, grant_types, requested_scope, azure_client_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        self.db.execute_query(
            query,
            (
                client_id,
                self.crypto.account_encrypt_sensitive_data(client_secret),
                client_name,
                json.dumps(redirect_uris),
                json.dumps(grant_types),
                scope,
                self.azure_client_id,
            ),
        )

        logger.info(f"✅ DCR client registered: {client_id}")

        # RFC 7591 응답
        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "client_id_issued_at": issued_at,
            "client_secret_expires_at": 0,  # Never expires
            "grant_types": grant_types,
            "client_name": client_name,
            "redirect_uris": redirect_uris,
            "scope": scope,
        }

    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """클라이언트 정보 조회 (dcr_clients 테이블)"""
        query = """
        SELECT client_id, client_secret, client_name, redirect_uris, grant_types,
               requested_scope, azure_client_id
        FROM dcr_clients
        WHERE client_id = ?
        """

        result = self.db.fetch_one(query, (client_id,))

        if not result:
            return None

        # Azure 설정은 환경변수에서 가져오기 (dcr_clients에는 저장 안 함)
        return {
            "client_id": result[0],
            "client_secret": self.crypto.account_decrypt_sensitive_data(result[1]) if result[1] else None,
            "client_name": result[2],
            "redirect_uris": json.loads(result[3]) if result[3] else [],
            "grant_types": json.loads(result[4]) if result[4] else [],
            "scope": result[5],
            "azure_client_id": result[6],
            "azure_client_secret": self.azure_client_secret,  # 환경변수에서
            "azure_tenant_id": self.azure_tenant_id,  # 환경변수에서
        }

    def verify_client_credentials(self, client_id: str, client_secret: str) -> bool:
        """클라이언트 인증 정보 검증"""
        client = self.get_client(client_id)
        if not client:
            return False

        return secrets.compare_digest(client.get("client_secret", ""), client_secret)

    def create_authorization_code(
        self,
        client_id: str,
        redirect_uri: str,
        scope: str,
        state: Optional[str] = None,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None
    ) -> str:
        """Authorization code 생성 (10분 유효, PKCE 지원)

        Args:
            client_id: 클라이언트 ID
            redirect_uri: 리다이렉트 URI
            scope: 요청 스코프
            state: CSRF 방지용 state
            code_challenge: PKCE code challenge (RFC 7636)
            code_challenge_method: PKCE method ('S256' or 'plain')

        Returns:
            생성된 authorization code
        """
        code = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(minutes=10)

        # metadata에 PKCE 정보 저장
        metadata = {
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": scope
        }

        if code_challenge:
            metadata["code_challenge"] = code_challenge
            metadata["code_challenge_method"] = code_challenge_method or "plain"
            logger.info(f"📝 PKCE enabled for auth code: method={metadata['code_challenge_method']}")

        # dcr_tokens 테이블에 auth_code 저장
        query = """
        INSERT INTO dcr_tokens (
            token_value, client_id, token_type, expires_at, status, metadata
        ) VALUES (?, ?, 'authorization_code', ?, 'active', ?)
        """

        self.db.execute_query(
            query,
            (code, client_id, expires_at, json.dumps(metadata))
        )

        return code

    def verify_authorization_code(
        self,
        code: str,
        client_id: str,
        redirect_uri: str = None,
        code_verifier: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Authorization code 검증 (일회용, PKCE 지원)

        Args:
            code: Authorization code
            client_id: 클라이언트 ID
            redirect_uri: 리다이렉트 URI
            code_verifier: PKCE code verifier (RFC 7636)

        Returns:
            검증 성공 시 스코프와 상태 정보, 실패 시 None
        """
        # dcr_tokens 테이블에서 auth_code 조회
        query = """
        SELECT client_id, metadata, expires_at, status
        FROM dcr_tokens
        WHERE token_value = ? AND token_type = 'authorization_code'
        """

        result = self.db.fetch_one(query, (code,))

        if not result:
            logger.warning(f"❌ Authorization code not found")
            return None

        stored_client_id, metadata_str, expires_at, status = result

        # metadata 파싱
        metadata = json.loads(metadata_str) if metadata_str else {}
        scope = metadata.get("scope")

        # 기본 검증
        if stored_client_id != client_id:
            logger.warning(f"❌ Client ID mismatch")
            return None

        if status != 'active':
            logger.warning(f"❌ Authorization code already used or revoked")
            return None

        if datetime.fromisoformat(expires_at) < datetime.now():
            logger.warning(f"❌ Authorization code expired")
            # 만료된 코드 상태 업데이트
            self.db.execute_query("UPDATE dcr_tokens SET status = 'expired' WHERE token_value = ?", (code,))
            return None

        # Redirect URI 검증 (metadata에서)
        if redirect_uri and metadata.get("redirect_uri") != redirect_uri:
            logger.warning(f"❌ Redirect URI mismatch")
            return None

        # PKCE 검증 (RFC 7636)
        if "code_challenge" in metadata:
            if not code_verifier:
                logger.warning(f"❌ PKCE required but no code_verifier provided")
                return None

            if not self._verify_pkce(
                code_verifier,
                metadata["code_challenge"],
                metadata.get("code_challenge_method", "plain")
            ):
                logger.warning(f"❌ PKCE verification failed")
                return None

            logger.info(f"✅ PKCE verification successful")

        # Mark as used (status = 'expired' 로 변경)
        update_query = """
        UPDATE dcr_tokens
        SET status = 'expired'
        WHERE token_value = ?
        """
        self.db.execute_query(update_query, (code,))

        return {"scope": scope, "state": metadata.get("state")}

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
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
        principal_id: Optional[str] = None,
    ):
        """DCR 토큰 + Azure 토큰 분리 저장 (dcr_tokens + azure_tokens)"""
        expires_at = datetime.now() + timedelta(seconds=expires_in)

        # 1) dcr_tokens 테이블에 DCR access token 저장
        dcr_query = """
        INSERT INTO dcr_tokens (
            token_value, client_id, token_type, expires_at, status
        ) VALUES (?, ?, 'Bearer', ?, 'active')
        """

        self.db.execute_query(
            dcr_query,
            (
                self.crypto.account_encrypt_sensitive_data(access_token),
                client_id,
                expires_at,
            ),
        )

        # 2) azure_tokens 테이블에 Azure 토큰 저장
        azure_query = """
        INSERT OR REPLACE INTO azure_tokens (
            client_id, azure_tenant_id, principal_type, principal_id, resource,
            granted_scope, azure_access_token, azure_refresh_token, azure_token_expiry,
            user_email, user_name
        ) VALUES (?, ?, 'delegated', ?, 'https://graph.microsoft.com', ?, ?, ?, ?, ?, ?)
        """

        self.db.execute_query(
            azure_query,
            (
                client_id,
                self.azure_tenant_id,
                principal_id,
                scope,
                self.crypto.account_encrypt_sensitive_data(azure_access_token),
                self.crypto.account_encrypt_sensitive_data(azure_refresh_token) if azure_refresh_token else None,
                azure_token_expiry,
                user_email,
                user_name,
            ),
        )

        logger.info(f"✅ Stored DCR token + Azure token for client: {client_id}, user: {user_email}")

        # 3) DCR refresh token 저장 (있으면)
        if refresh_token:
            refresh_expires = datetime.now() + timedelta(days=30)
            refresh_query = """
            INSERT INTO dcr_tokens (
                token_value, client_id, token_type, expires_at, status
            ) VALUES (?, ?, 'refresh_token', ?, 'active')
            """
            self.db.execute_query(
                refresh_query,
                (
                    self.crypto.account_encrypt_sensitive_data(refresh_token),
                    client_id,
                    refresh_expires,
                ),
            )

    def verify_bearer_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Bearer 토큰 검증 및 Azure AD 토큰 반환 (dcr_tokens + azure_tokens 조인)"""
        # dcr_tokens 테이블에서 활성 토큰 조회
        query = """
        SELECT d.client_id, d.token_value, d.expires_at,
               a.azure_access_token, a.azure_token_expiry, a.granted_scope, a.user_email
        FROM dcr_tokens d
        LEFT JOIN azure_tokens a ON d.client_id = a.client_id
        WHERE d.token_type = 'Bearer' AND d.status = 'active' AND d.expires_at > CURRENT_TIMESTAMP
        """

        results = self.db.fetch_all(query)

        if not results:
            return None

        # 암호화된 토큰 비교
        for row in results:
            client_id, encrypted_token, expires_at, encrypted_azure_token, azure_expiry, scope, user_email = row

            try:
                decrypted_token = self.crypto.account_decrypt_sensitive_data(encrypted_token)
                if secrets.compare_digest(decrypted_token, token):
                    # 토큰 매치!
                    if not encrypted_azure_token:
                        logger.warning(f"⚠️ DCR token found but no Azure token for client: {client_id}")
                        return None

                    azure_access_token = self.crypto.account_decrypt_sensitive_data(encrypted_azure_token)
                    return {
                        "client_id": client_id,
                        "azure_access_token": azure_access_token,
                        "azure_token_expiry": azure_expiry,
                        "scope": scope,
                        "user_email": user_email,
                    }
            except Exception as e:
                logger.error(f"Token decryption error: {e}")
                continue

        return None

    def get_azure_tokens_by_client_id(self, client_id: str) -> Optional[Dict[str, Any]]:
        """client_id로 Azure 토큰 조회 (azure_tokens 테이블)"""
        query = """
        SELECT azure_access_token, azure_refresh_token, granted_scope, azure_token_expiry, user_email
        FROM azure_tokens
        WHERE client_id = ?
        """

        result = self.db.fetch_one(query, (client_id,))

        if not result:
            return None

        azure_access_token, azure_refresh_token, scope, expiry, user_email = result

        # 만료 시간 계산
        if expiry:
            expires_in = int((datetime.fromisoformat(expiry) - datetime.now()).total_seconds())
            if expires_in < 0:
                expires_in = 0
        else:
            expires_in = 3600

        return {
            "access_token": self.crypto.account_decrypt_sensitive_data(azure_access_token),
            "refresh_token": self.crypto.account_decrypt_sensitive_data(azure_refresh_token) if azure_refresh_token else None,
            "scope": scope,
            "expires_in": expires_in,
            "user_email": user_email,
        }

    # PKCE Helper Methods (RFC 7636)
    def _generate_code_verifier(self) -> str:
        """PKCE code_verifier 생성 (43-128 문자)"""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

    def _generate_code_challenge(self, code_verifier: str, method: str = "S256") -> str:
        """PKCE code_challenge 생성

        Args:
            code_verifier: 원본 verifier
            method: 'plain' 또는 'S256'

        Returns:
            code_challenge 값
        """
        if method == "plain":
            return code_verifier
        elif method == "S256":
            digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
            return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
        else:
            raise ValueError(f"Unsupported PKCE method: {method}")

    def _verify_pkce(self, code_verifier: str, code_challenge: str, method: str = "plain") -> bool:
        """PKCE 검증

        Args:
            code_verifier: 클라이언트가 제공한 verifier
            code_challenge: 저장된 challenge
            method: 'plain' 또는 'S256'

        Returns:
            검증 성공 여부
        """
        if method == "plain":
            # plain 방식: verifier와 challenge가 같아야 함
            return secrets.compare_digest(code_verifier, code_challenge)
        elif method == "S256":
            # S256 방식: SHA256(verifier) == challenge
            calculated_challenge = self._generate_code_challenge(code_verifier, "S256")
            return secrets.compare_digest(calculated_challenge, code_challenge)
        else:
            logger.warning(f"Unsupported PKCE method: {method}")
            return False

    def generate_pkce_pair(self) -> Tuple[str, str]:
        """PKCE code_verifier와 code_challenge 쌍 생성 (S256 방식)

        Returns:
            (code_verifier, code_challenge) 튜플
        """
        code_verifier = self._generate_code_verifier()
        code_challenge = self._generate_code_challenge(code_verifier, "S256")
        return code_verifier, code_challenge

    def update_auth_code_with_azure_tokens(
        self, auth_code: str, azure_code: str, azure_access_token: str, azure_refresh_token: str
    ):
        """Authorization code에 Azure 토큰 연결"""
        query = """
        UPDATE dcr_oauth
        SET azure_access_token = ?, azure_refresh_token = ?, azure_token_expiry = ?, updated_at = CURRENT_TIMESTAMP
        WHERE token_type = ? AND token_value = ?
        """

        azure_expiry = datetime.now() + timedelta(hours=1)  # Azure 토큰 기본 1시간

        self.db.execute_query(
            query,
            (
                azure_access_token,  # 이미 암호화되어 있다고 가정
                azure_refresh_token,
                azure_expiry,
                TokenType.AUTH_CODE.value,
                auth_code,
            ),
        )

    def cleanup_expired_tokens(self):
        """만료된 토큰 정리 (주기적으로 실행)"""
        query = """
        UPDATE dcr_oauth
        SET revoked_at = CURRENT_TIMESTAMP
        WHERE expires_at < CURRENT_TIMESTAMP AND revoked_at IS NULL
        """

        self.db.execute_query(query)
        logger.info("✅ Cleaned up expired tokens")

    def is_user_allowed(self, user_email: str) -> bool:
        """
        사용자가 허용된 사용자 목록에 있는지 확인

        Args:
            user_email: Azure AD에서 가져온 사용자 이메일

        Returns:
            허용된 사용자면 True, 아니면 False
        """
        # 허용 목록이 비어있으면 모든 사용자 허용
        if not self.allowed_users:
            return True

        # 이메일을 소문자로 변환하여 비교
        user_email_lower = user_email.lower().strip()

        # 허용 목록에 있는지 확인
        is_allowed = user_email_lower in self.allowed_users

        if not is_allowed:
            logger.warning(f"❌ Access denied for user: {user_email} (not in allowed users list)")
        else:
            logger.info(f"✅ Access granted for user: {user_email}")

        return is_allowed


# 기존 DCRService와의 호환성을 위한 별칭
DCRService = DCRServiceV2