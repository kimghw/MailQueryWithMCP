"""DCR (Dynamic Client Registration) Service V2
RFC 7591 준수 동적 클라이언트 등록 서비스
단일 테이블 스키마로 최적화
"""

import json
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
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
        """DCR 단일 테이블 스키마 초기화"""
        schema_sql = """
        -- 통합 DCR OAuth 테이블
        CREATE TABLE IF NOT EXISTS dcr_oauth (
            -- 공통 필드
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_type TEXT NOT NULL,           -- 'client', 'auth_code', 'access', 'refresh'
            token_value TEXT NOT NULL,          -- client_id, code, or token (암호화)
            secret_value TEXT,                   -- client_secret (암호화)

            -- 클라이언트 정보 (token_type='client')
            client_id TEXT,                     -- 참조용 client_id
            client_name TEXT,
            redirect_uris TEXT,                 -- JSON array
            grant_types TEXT,                   -- JSON array
            scope TEXT,

            -- Azure 매핑 정보
            azure_client_id TEXT,
            azure_client_secret TEXT,            -- 암호화
            azure_tenant_id TEXT,
            azure_access_token TEXT,             -- 암호화
            azure_refresh_token TEXT,            -- 암호화
            azure_token_expiry DATETIME,

            -- 메타데이터
            expires_at DATETIME,
            used_at DATETIME,                    -- auth_code 사용 시점
            revoked_at DATETIME,                 -- 토큰 무효화 시점
            state TEXT,                          -- OAuth state parameter

            -- 타임스탬프
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

            -- 인덱스를 위한 제약
            UNIQUE(token_type, token_value)
        );

        -- 성능 최적화 인덱스
        CREATE INDEX IF NOT EXISTS idx_dcr_oauth_token_type ON dcr_oauth (token_type);
        CREATE INDEX IF NOT EXISTS idx_dcr_oauth_token_value ON dcr_oauth (token_value);
        CREATE INDEX IF NOT EXISTS idx_dcr_oauth_client_id ON dcr_oauth (client_id);
        CREATE INDEX IF NOT EXISTS idx_dcr_oauth_expires_at ON dcr_oauth (expires_at);
        CREATE INDEX IF NOT EXISTS idx_dcr_oauth_revoked_at ON dcr_oauth (revoked_at);
        """

        try:
            # Use executescript for multiple statements
            import sqlite3
            from infra.core.config import get_config
            config = get_config()
            conn = sqlite3.connect(config.database_path)
            conn.executescript(schema_sql)
            conn.commit()
            conn.close()
            logger.info("✅ DCR V2 schema initialized (single table)")
        except Exception as e:
            logger.error(f"❌ DCR V2 schema initialization failed: {e}")
            raise

    async def register_client(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        RFC 7591: 동적 클라이언트 등록
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

        # 단일 테이블에 클라이언트 정보 저장
        query = """
        INSERT INTO dcr_oauth (
            token_type, token_value, secret_value,
            client_id, client_name, redirect_uris, grant_types, scope,
            azure_client_id, azure_client_secret, azure_tenant_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        self.db.execute_query(
            query,
            (
                TokenType.CLIENT.value,
                client_id,  # token_value = client_id
                self.crypto.account_encrypt_sensitive_data(client_secret),
                client_id,  # client_id 필드에도 저장 (참조용)
                client_name,
                json.dumps(redirect_uris),
                json.dumps(grant_types),
                scope,
                self.azure_client_id,
                self.crypto.account_encrypt_sensitive_data(self.azure_client_secret),
                self.azure_tenant_id,
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
        """클라이언트 정보 조회"""
        query = """
        SELECT token_value, secret_value, client_name, redirect_uris, grant_types, scope,
               azure_client_id, azure_client_secret, azure_tenant_id
        FROM dcr_oauth
        WHERE token_type = ? AND token_value = ? AND revoked_at IS NULL
        """

        result = self.db.fetch_one(query, (TokenType.CLIENT.value, client_id))

        if not result:
            return None

        return {
            "client_id": result[0],
            "client_secret": self.crypto.account_decrypt_sensitive_data(result[1]) if result[1] else None,
            "client_name": result[2],
            "redirect_uris": json.loads(result[3]) if result[3] else [],
            "grant_types": json.loads(result[4]) if result[4] else [],
            "scope": result[5],
            "azure_client_id": result[6],
            "azure_client_secret": self.crypto.account_decrypt_sensitive_data(result[7]) if result[7] else None,
            "azure_tenant_id": result[8],
        }

    def verify_client_credentials(self, client_id: str, client_secret: str) -> bool:
        """클라이언트 인증 정보 검증"""
        client = self.get_client(client_id)
        if not client:
            return False

        return secrets.compare_digest(client.get("client_secret", ""), client_secret)

    def create_authorization_code(
        self, client_id: str, redirect_uri: str, scope: str, state: Optional[str] = None
    ) -> str:
        """Authorization code 생성 (10분 유효)"""
        code = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(minutes=10)

        query = """
        INSERT INTO dcr_oauth (
            token_type, token_value, client_id, scope, state, expires_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """

        self.db.execute_query(
            query,
            (TokenType.AUTH_CODE.value, code, client_id, scope, state, expires_at)
        )

        return code

    def verify_authorization_code(
        self, code: str, client_id: str, redirect_uri: str = None
    ) -> Optional[Dict[str, Any]]:
        """Authorization code 검증 (일회용)"""
        query = """
        SELECT client_id, scope, state, expires_at, used_at
        FROM dcr_oauth
        WHERE token_type = ? AND token_value = ?
        """

        result = self.db.fetch_one(query, (TokenType.AUTH_CODE.value, code))

        if not result:
            return None

        stored_client_id, scope, state, expires_at, used_at = result

        # 검증
        if stored_client_id != client_id:
            logger.warning(f"❌ Client ID mismatch")
            return None

        if used_at:
            logger.warning(f"❌ Authorization code already used")
            return None

        if datetime.fromisoformat(expires_at) < datetime.now():
            logger.warning(f"❌ Authorization code expired")
            return None

        # Mark as used
        update_query = """
        UPDATE dcr_oauth
        SET used_at = CURRENT_TIMESTAMP
        WHERE token_type = ? AND token_value = ?
        """
        self.db.execute_query(update_query, (TokenType.AUTH_CODE.value, code))

        return {"scope": scope, "state": state}

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
        """액세스 토큰 저장"""
        expires_at = datetime.now() + timedelta(seconds=expires_in)

        # Access token 저장
        query = """
        INSERT INTO dcr_oauth (
            token_type, token_value, client_id, scope, expires_at,
            azure_access_token, azure_refresh_token, azure_token_expiry
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        self.db.execute_query(
            query,
            (
                TokenType.ACCESS_TOKEN.value,
                self.crypto.account_encrypt_sensitive_data(access_token),
                client_id,
                scope,
                expires_at,
                self.crypto.account_encrypt_sensitive_data(azure_access_token),
                self.crypto.account_encrypt_sensitive_data(azure_refresh_token) if azure_refresh_token else None,
                azure_token_expiry,
            ),
        )

        # Refresh token 저장 (있으면)
        if refresh_token:
            refresh_expires = datetime.now() + timedelta(days=30)
            self.db.execute_query(
                query,
                (
                    TokenType.REFRESH_TOKEN.value,
                    self.crypto.account_encrypt_sensitive_data(refresh_token),
                    client_id,
                    scope,
                    refresh_expires,
                    None, None, None,  # Refresh token에는 Azure 토큰 연결 안 함
                ),
            )

    def verify_bearer_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Bearer 토큰 검증 및 Azure AD 토큰 반환"""
        query = """
        SELECT client_id, azure_access_token, azure_token_expiry, scope, expires_at
        FROM dcr_oauth
        WHERE token_type = ? AND revoked_at IS NULL AND expires_at > CURRENT_TIMESTAMP
        """

        # 모든 활성 액세스 토큰 조회
        results = self.db.fetch_all(query, (TokenType.ACCESS_TOKEN.value,))

        if not results:
            return None

        # 암호화된 토큰 비교
        for row in results:
            client_id, encrypted_azure_token, azure_expiry, scope, expires_at = row

            # token_value는 이미 암호화되어 저장됨
            # 각 토큰을 복호화해서 비교해야 함
            token_query = """
            SELECT token_value FROM dcr_oauth
            WHERE token_type = ? AND client_id = ? AND expires_at = ?
            """
            token_result = self.db.fetch_one(
                token_query,
                (TokenType.ACCESS_TOKEN.value, client_id, expires_at)
            )

            if token_result:
                try:
                    decrypted_token = self.crypto.account_decrypt_sensitive_data(token_result[0])
                    if secrets.compare_digest(decrypted_token, token):
                        # 토큰 매치!
                        azure_access_token = self.crypto.account_decrypt_sensitive_data(encrypted_azure_token)
                        return {
                            "client_id": client_id,
                            "azure_access_token": azure_access_token,
                            "azure_token_expiry": azure_expiry,
                            "scope": scope,
                        }
                except Exception:
                    continue

        return None

    def get_azure_tokens_by_auth_code(self, auth_code: str) -> Optional[Dict[str, Any]]:
        """Authorization code로 저장된 Azure 토큰 조회"""
        query = """
        SELECT azure_access_token, azure_refresh_token, scope
        FROM dcr_oauth
        WHERE token_type = ? AND token_value = ? AND azure_access_token IS NOT NULL
        """

        result = self.db.fetch_one(query, (TokenType.AUTH_CODE.value, auth_code))

        if not result:
            return None

        azure_access_token, azure_refresh_token, scope = result

        return {
            "access_token": azure_access_token,
            "refresh_token": azure_refresh_token,
            "scope": scope,
            "expires_in": 3600  # Default expiry
        }

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