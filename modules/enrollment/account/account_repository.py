"""
Account Repository - 계정 데이터 CRUD 및 암호화 처리

데이터베이스와의 모든 계정 관련 상호작용을 담당합니다.
"""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from infra.core.database import get_database_manager
from infra.core.exceptions import DatabaseError, ValidationError
from infra.core.logger import get_logger

from ._account_helpers import AccountAuditHelpers, AccountCryptoHelpers
from .account_schema import (
    AccountAuditLog,
    AccountCreate,
    AccountListFilter,
    AccountResponse,
    AccountStatus,
    AccountUpdate,
    AuthType,
)

logger = get_logger(__name__)


class AccountRepository:
    """계정 데이터 저장소"""

    def __init__(self):
        self.db = get_database_manager()
        self.crypto = AccountCryptoHelpers()
        self.audit_helper = AccountAuditHelpers()

    def account_create_from_enrollment(self, account_data: AccountCreate) -> int:
        """
        Enrollment 데이터로부터 계정 생성

        Args:
            account_data: 계정 생성 데이터

        Returns:
            int: 생성된 계정 ID
        """
        try:
            # Delegated scope 검증
            from ._scope_validator import validate_delegated_scope

            permissions_str = account_data.delegated_permissions
            if isinstance(account_data.delegated_permissions, list):
                permissions_str = ' '.join(account_data.delegated_permissions)

            is_valid, valid_scopes, invalid_scopes = validate_delegated_scope(permissions_str)

            if not is_valid:
                logger.error(
                    f"❌ 계정 생성 실패: 허용되지 않은 scope 발견\n"
                    f"   User ID: {account_data.user_id}\n"
                    f"   거부된 scope: {invalid_scopes}"
                )
                raise ValidationError(
                    f"허용되지 않은 scope가 포함되어 있습니다: {invalid_scopes}"
                )

            # 클라이언트 시크릿 암호화
            encrypted_secret = self.crypto.account_encrypt_sensitive_data(
                account_data.oauth_client_secret
            )

            # 검증된 권한 목록을 JSON 문자열로 변환
            permissions_json = json.dumps(valid_scopes)

            query = """
                INSERT INTO accounts (
                    user_id, user_name, email, enrollment_file_path, enrollment_file_hash,
                    oauth_client_id, oauth_client_secret, oauth_tenant_id, oauth_redirect_uri,
                    status, auth_type, delegated_permissions, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            current_time = datetime.now(timezone.utc)
            params = (
                account_data.user_id,
                account_data.user_name,
                str(account_data.email),
                account_data.enrollment_file_path,
                account_data.enrollment_file_hash,
                account_data.oauth_client_id,
                encrypted_secret,
                account_data.oauth_tenant_id,
                account_data.oauth_redirect_uri,
                account_data.status.value,
                account_data.auth_type.value,
                permissions_json,
                account_data.status == AccountStatus.ACTIVE,
                current_time.isoformat(),
                current_time.isoformat(),
            )

            with self.db.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                account_id = cursor.lastrowid

                # 감사 로그 생성
                audit_data = self.audit_helper.account_create_audit_message(
                    "ACCOUNT_CREATED", account_id, None, account_data.dict()
                )
                self._account_create_audit_log(cursor, audit_data)

                logger.info(
                    f"계정 생성 완료: ID={account_id}, user_id={account_data.user_id}"
                )
                return account_id

        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise ValidationError(f"이미 존재하는 계정: {account_data.user_id}")
            raise DatabaseError(f"계정 생성 중 무결성 오류: {e}")
        except Exception as e:
            logger.error(f"계정 생성 오류: {e}")
            raise DatabaseError(f"계정 생성 실패: {e}")

    def account_get_by_user_id(self, user_id: str) -> Optional[AccountResponse]:
        """
        사용자 ID로 계정 조회

        Args:
            user_id: 사용자 ID

        Returns:
            Optional[AccountResponse]: 계정 정보
        """
        try:
            query = """
                SELECT id, user_id, user_name, email, enrollment_file_path, enrollment_file_hash,
                       oauth_client_id, oauth_tenant_id, oauth_redirect_uri, status, auth_type,
                       delegated_permissions, access_token, refresh_token, token_expiry,
                       last_sync_time, is_active, created_at, updated_at
                FROM accounts WHERE user_id = ?
            """

            row = self.db.fetch_one(query, (user_id,))

            if not row:
                return None

            return self._account_row_to_response(row)

        except Exception as e:
            logger.error(f"계정 조회 오류: user_id={user_id}, {e}")
            raise DatabaseError(f"계정 조회 실패: {e}")

    def account_update_by_id(self, account_id: int, update_data: AccountUpdate) -> bool:
        """
        계정 ID로 계정 정보 업데이트

        Args:
            account_id: 계정 ID
            update_data: 업데이트할 데이터

        Returns:
            bool: 업데이트 성공 여부
        """
        try:
            # 기존 데이터 조회 (감사 로그용)
            existing_account = self.account_get_by_id(account_id)
            if not existing_account:
                return False

            # 업데이트할 필드 수집
            update_fields = []
            params = []

            if update_data.user_name is not None:
                update_fields.append("user_name = ?")
                params.append(update_data.user_name)

            if update_data.status is not None:
                update_fields.append("status = ?")
                params.append(update_data.status.value)
                update_fields.append("is_active = ?")
                params.append(update_data.status == AccountStatus.ACTIVE)

            if update_data.enrollment_file_path is not None:
                update_fields.append("enrollment_file_path = ?")
                params.append(update_data.enrollment_file_path)

            if update_data.enrollment_file_hash is not None:
                update_fields.append("enrollment_file_hash = ?")
                params.append(update_data.enrollment_file_hash)

            if update_data.oauth_client_id is not None:
                update_fields.append("oauth_client_id = ?")
                params.append(update_data.oauth_client_id)

            if update_data.oauth_client_secret is not None:
                encrypted_secret = self.crypto.account_encrypt_sensitive_data(
                    update_data.oauth_client_secret
                )
                update_fields.append("oauth_client_secret = ?")
                params.append(encrypted_secret)

            if update_data.oauth_tenant_id is not None:
                update_fields.append("oauth_tenant_id = ?")
                params.append(update_data.oauth_tenant_id)

            if update_data.oauth_redirect_uri is not None:
                update_fields.append("oauth_redirect_uri = ?")
                params.append(update_data.oauth_redirect_uri)

            if update_data.delegated_permissions is not None:
                # Delegated scope 검증
                from ._scope_validator import validate_delegated_scope

                permissions_str = update_data.delegated_permissions
                if isinstance(update_data.delegated_permissions, list):
                    permissions_str = ' '.join(update_data.delegated_permissions)

                is_valid, valid_scopes, invalid_scopes = validate_delegated_scope(permissions_str)

                if not is_valid:
                    logger.error(
                        f"❌ 계정 업데이트 실패: 허용되지 않은 scope 발견\n"
                        f"   Account ID: {account_id}\n"
                        f"   거부된 scope: {invalid_scopes}"
                    )
                    raise ValidationError(
                        f"허용되지 않은 scope가 포함되어 있습니다: {invalid_scopes}"
                    )

                # 검증된 권한 목록만 저장
                permissions_json = json.dumps(valid_scopes)
                update_fields.append("delegated_permissions = ?")
                params.append(permissions_json)

            if update_data.access_token is not None:
                update_fields.append("access_token = ?")
                params.append(update_data.access_token)

            if update_data.refresh_token is not None:
                update_fields.append("refresh_token = ?")
                params.append(update_data.refresh_token)

            if update_data.token_expiry is not None:
                update_fields.append("token_expiry = ?")
                params.append(update_data.token_expiry)

            if update_data.last_sync_time is not None:
                update_fields.append("last_sync_time = ?")
                params.append(update_data.last_sync_time)

            if not update_fields:
                return True  # 업데이트할 필드가 없음

            # updated_at 추가
            update_fields.append("updated_at = ?")
            params.append(datetime.now(timezone.utc).isoformat())
            params.append(account_id)

            query = f"UPDATE accounts SET {', '.join(update_fields)} WHERE id = ?"

            with self.db.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)

                if cursor.rowcount > 0:
                    # 감사 로그 생성
                    audit_data = self.audit_helper.account_create_audit_message(
                        "ACCOUNT_UPDATED",
                        account_id,
                        existing_account.dict(),
                        update_data.dict(exclude_unset=True),
                    )
                    self._account_create_audit_log(cursor, audit_data)

                    logger.info(f"계정 업데이트 완료: ID={account_id}")
                    return True

                return False

        except Exception as e:
            logger.error(f"계정 업데이트 오류: account_id={account_id}, {e}")
            raise DatabaseError(f"계정 업데이트 실패: {e}")

    def account_get_by_id(self, account_id: int) -> Optional[AccountResponse]:
        """계정 ID로 계정 조회"""
        try:
            query = """
                SELECT id, user_id, user_name, email, enrollment_file_path, enrollment_file_hash,
                       oauth_client_id, oauth_tenant_id, oauth_redirect_uri, status, auth_type,
                       delegated_permissions, access_token, refresh_token, token_expiry,
                       last_sync_time, is_active, created_at, updated_at
                FROM accounts WHERE id = ?
            """

            row = self.db.fetch_one(query, (account_id,))

            if not row:
                return None

            return self._account_row_to_response(row)

        except Exception as e:
            logger.error(f"계정 조회 오류: account_id={account_id}, {e}")
            raise DatabaseError(f"계정 조회 실패: {e}")

    def _account_row_to_response(self, row: sqlite3.Row) -> AccountResponse:
        """데이터베이스 행을 AccountResponse로 변환"""
        permissions = (
            json.loads(row["delegated_permissions"])
            if row["delegated_permissions"]
            else []
        )

        return AccountResponse(
            id=row["id"],
            user_id=row["user_id"],
            user_name=row["user_name"],
            email=row["email"],
            status=AccountStatus(row["status"]),
            enrollment_file_path=row["enrollment_file_path"],
            enrollment_file_hash=row["enrollment_file_hash"],
            oauth_client_id=row["oauth_client_id"],
            oauth_tenant_id=row["oauth_tenant_id"],
            oauth_redirect_uri=row["oauth_redirect_uri"],
            auth_type=AuthType(row["auth_type"]),
            delegated_permissions=permissions,
            has_valid_token=self._account_check_token_validity(row),
            token_expiry=row["token_expiry"],
            last_sync_time=row["last_sync_time"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _account_check_token_validity(self, row: sqlite3.Row) -> bool:
        """토큰 유효성 확인"""
        if not row["access_token"] or not row["token_expiry"]:
            return False

        try:
            expiry_time = datetime.fromisoformat(
                row["token_expiry"].replace("Z", "+00:00")
            )
            now_utc = datetime.now(timezone.utc)
            return expiry_time > now_utc
        except Exception as e:
            logger.error(f"토큰 유효성 확인 오류: {e}")
            return False

    def _account_create_audit_log(self, cursor, audit_data: Dict[str, Any]) -> None:
        """감사 로그 생성"""
        query = """
            INSERT INTO account_audit_logs (account_id, action, old_values, new_values, changed_by, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """

        params = (
            audit_data["account_id"],
            audit_data["action"],
            json.dumps(audit_data["old_values"]) if audit_data["old_values"] else None,
            json.dumps(audit_data["new_values"]) if audit_data["new_values"] else None,
            audit_data["changed_by"],
            audit_data["timestamp"],
        )

        cursor.execute(query, params)
