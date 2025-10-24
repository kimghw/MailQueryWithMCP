"""
Account 모듈의 헬퍼 클래스들

350줄 제한 규칙 준수를 위해 분리된 유틸리티 클래스들을 정의합니다.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from cryptography.fernet import Fernet

from infra.core.config import get_config
from infra.core.logger import get_logger

logger = get_logger(__name__)
config = get_config()


class AccountFileHelpers:
    """파일 관련 헬퍼 클래스"""

    @staticmethod
    def account_read_enrollment_file(file_path: str) -> Dict[str, Any]:
        """
        Enrollment YAML 파일을 읽어서 딕셔너리로 반환

        Args:
            file_path: YAML 파일 경로

        Returns:
            Dict[str, Any]: 파일 내용

        Raises:
            FileNotFoundError: 파일이 없는 경우
            yaml.YAMLError: YAML 파싱 오류
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file)
                logger.debug(f"enrollment 파일 읽기 성공: {file_path}")
                return data
        except FileNotFoundError:
            logger.error(f"enrollment 파일을 찾을 수 없습니다: {file_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"YAML 파싱 오류: {file_path}, {e}")
            raise
        except Exception as e:
            logger.error(f"enrollment 파일 읽기 오류: {file_path}, {e}")
            raise

    @staticmethod
    def account_calculate_file_hash(file_path: str) -> str:
        """
        파일의 SHA256 해시를 계산

        Args:
            file_path: 파일 경로

        Returns:
            str: SHA256 해시값
        """
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as file:
                for chunk in iter(lambda: file.read(4096), b""):
                    hash_sha256.update(chunk)

            hash_value = hash_sha256.hexdigest()
            logger.debug(f"파일 해시 계산 완료: {file_path} -> {hash_value[:8]}...")
            return hash_value
        except Exception as e:
            logger.error(f"파일 해시 계산 오류: {file_path}, {e}")
            raise

    @staticmethod
    def account_validate_enrollment_structure(data: Dict[str, Any]) -> bool:
        """
        Enrollment 파일 구조 검증

        Args:
            data: YAML에서 읽은 데이터

        Returns:
            bool: 구조가 유효한지 여부
        """
        required_sections = ["account", "microsoft_graph", "oauth"]
        required_account_fields = ["email", "name"]
        required_graph_fields = ["client_id", "client_secret", "tenant_id"]
        required_oauth_fields = ["redirect_uri", "auth_type", "delegated_permissions"]

        try:
            # 필수 섹션 확인
            for section in required_sections:
                if section not in data:
                    logger.error(f"필수 섹션 누락: {section}")
                    return False

            # account 섹션 필드 확인
            for field in required_account_fields:
                if field not in data["account"]:
                    logger.error(f"account 섹션의 필수 필드 누락: {field}")
                    return False

            # microsoft_graph 섹션 필드 확인
            for field in required_graph_fields:
                if field not in data["microsoft_graph"]:
                    logger.error(f"microsoft_graph 섹션의 필수 필드 누락: {field}")
                    return False

            # oauth 섹션 필드 확인
            for field in required_oauth_fields:
                if field not in data["oauth"]:
                    logger.error(f"oauth 섹션의 필수 필드 누락: {field}")
                    return False

            # delegated_permissions가 리스트인지 확인
            if not isinstance(data["oauth"]["delegated_permissions"], list):
                logger.error("delegated_permissions는 리스트여야 합니다")
                return False

            # delegated_permissions scope 검증 및 필터링
            from ._scope_validator import validate_delegated_scope, format_scopes_for_storage

            permissions = data["oauth"]["delegated_permissions"]
            permissions_str = ' '.join(permissions) if isinstance(permissions, list) else str(permissions)

            is_valid, valid_scopes, invalid_scopes = validate_delegated_scope(permissions_str)

            if invalid_scopes:
                logger.warning(
                    f"⚠️  YAML 파일에 허용되지 않은 scope 발견: {invalid_scopes}\n"
                    f"   허용된 scope만 사용합니다: {valid_scopes}"
                )
                # 허용된 scope만 유지
                data["oauth"]["delegated_permissions"] = valid_scopes

            logger.debug("enrollment 파일 구조 검증 성공")
            return True

        except Exception as e:
            logger.error(f"enrollment 파일 구조 검증 오류: {e}")
            return False

    @staticmethod
    def account_list_enrollment_files(directory: str) -> list:
        """
        디렉터리에서 enrollment YAML 파일 목록을 반환

        Args:
            directory: 검색할 디렉터리 경로

        Returns:
            list: 파일 경로 목록
        """
        try:
            directory_path = Path(directory)
            if not directory_path.exists():
                logger.warning(f"enrollment 디렉터리가 존재하지 않습니다: {directory}")
                return []

            yaml_files = list(directory_path.glob("*.yaml")) + list(
                directory_path.glob("*.yml")
            )
            file_paths = [str(file) for file in yaml_files]

            logger.debug(f"enrollment 파일 {len(file_paths)}개 발견: {directory}")
            return file_paths

        except Exception as e:
            logger.error(f"enrollment 파일 목록 조회 오류: {directory}, {e}")
            return []


class AccountCryptoHelpers:
    """암호화 관련 헬퍼 클래스"""

    def __init__(self):
        self._cipher_suite: Optional[Fernet] = None

    def _get_cipher_suite(self) -> Fernet:
        """레이지 로딩으로 암호화 객체 반환"""
        if self._cipher_suite is None:
            try:
                encryption_key = config.encryption_key
                self._cipher_suite = Fernet(encryption_key.encode())
                logger.debug("암호화 객체 초기화 완료")
            except Exception as e:
                logger.error(f"암호화 객체 초기화 실패: {e}")
                raise
        return self._cipher_suite

    def account_encrypt_sensitive_data(self, data: str) -> str:
        """
        민감한 데이터를 암호화

        Args:
            data: 암호화할 문자열

        Returns:
            str: 암호화된 문자열 (base64)
        """
        try:
            cipher_suite = self._get_cipher_suite()
            encrypted_data = cipher_suite.encrypt(data.encode())
            result = encrypted_data.decode()
            logger.debug("데이터 암호화 완료")
            return result
        except Exception as e:
            logger.error(f"데이터 암호화 오류: {e}")
            raise

    def account_decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """
        암호화된 데이터를 복호화

        Args:
            encrypted_data: 암호화된 문자열 (base64)

        Returns:
            str: 복호화된 문자열
        """
        try:
            cipher_suite = self._get_cipher_suite()
            decrypted_data = cipher_suite.decrypt(encrypted_data.encode())
            result = decrypted_data.decode()
            logger.debug("데이터 복호화 완료")
            return result
        except Exception as e:
            logger.error(f"데이터 복호화 오류: {e}")
            raise


class AccountAuditHelpers:
    """감사 로그 관련 헬퍼 클래스"""

    @staticmethod
    def account_create_audit_message(
        action: str,
        account_id: int,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        감사 로그 메시지 생성

        Args:
            action: 수행된 액션
            account_id: 계정 ID
            old_values: 이전 값들
            new_values: 새로운 값들

        Returns:
            Dict[str, Any]: 감사 로그 데이터
        """
        return {
            "account_id": account_id,
            "action": action,
            "old_values": AccountAuditHelpers._account_sanitize_values(old_values),
            "new_values": AccountAuditHelpers._account_sanitize_values(new_values),
            "changed_by": "system",  # 현재는 시스템으로 고정
            "timestamp": datetime.now(timezone.utc),
        }

    @staticmethod
    def _account_sanitize_values(values: Optional[Dict]) -> Optional[Dict]:
        """
        민감한 정보를 제거하고 JSON 직렬화 가능한 안전한 값들 반환

        Args:
            values: 원본 값들

        Returns:
            Dict: 민감한 정보가 제거되고 JSON 직렬화 가능한 값들
        """
        if values is None:
            return None

        sanitized = values.copy()
        sensitive_fields = [
            "oauth_client_secret",
            "access_token",
            "refresh_token",
            "client_secret",
            "password",
        ]

        # 민감한 정보 제거
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = "***REDACTED***"

        # datetime 객체를 ISO 형식 문자열로 변환
        for key, value in sanitized.items():
            if isinstance(value, datetime):
                sanitized[key] = value.isoformat()

        return sanitized

    @staticmethod
    def account_format_audit_log(audit_data: Dict[str, Any]) -> str:
        """
        감사 로그를 읽기 쉬운 문자열로 포맷

        Args:
            audit_data: 감사 로그 데이터

        Returns:
            str: 포맷된 로그 메시지
        """
        action = audit_data.get("action", "UNKNOWN")
        account_id = audit_data.get("account_id", "N/A")
        timestamp = audit_data.get("timestamp", datetime.now(timezone.utc))

        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        base_message = f"[{timestamp.isoformat()}] Account {account_id}: {action}"

        # 변경사항이 있는 경우 추가 정보 포함
        new_values = audit_data.get("new_values")
        if new_values:
            changes = []
            for key, value in new_values.items():
                if key not in ["created_at", "updated_at", "id"]:
                    changes.append(f"{key}={value}")

            if changes:
                base_message += f" - Changes: {', '.join(changes)}"

        return base_message
