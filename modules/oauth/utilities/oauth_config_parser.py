"""OAuth 설정 파싱 유틸리티"""

import json
from typing import List, Optional

from cryptography.fernet import Fernet

from infra.core.config import get_config
from infra.core.logger import get_logger


class OAuthConfigParser:
    """OAuth 설정 파싱 및 처리 유틸리티"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_config()

    def parse_scopes(self, delegated_permissions: Optional[str]) -> List[str]:
        """
        delegated_permissions 문자열을 스코프 리스트로 파싱합니다.

        Args:
            delegated_permissions: 권한 문자열

        Returns:
            스코프 리스트
        """
        if not delegated_permissions:
            # 기본 스코프
            return ["Mail.ReadWrite", "Mail.Send", "offline_access"]

        try:
            # JSON 배열 형태
            if delegated_permissions.strip().startswith("["):
                scopes = json.loads(delegated_permissions)
                if isinstance(scopes, list):
                    # offline_access 확인 및 추가
                    if "offline_access" not in scopes:
                        scopes.append("offline_access")
                    return scopes

            # 쉼표로 구분된 형태
            if "," in delegated_permissions:
                scopes = [
                    s.strip() for s in delegated_permissions.split(",") if s.strip()
                ]
            # 공백으로 구분된 형태
            elif " " in delegated_permissions:
                scopes = [s.strip() for s in delegated_permissions.split() if s.strip()]
            # 단일 스코프
            else:
                scopes = [delegated_permissions.strip()]

            # offline_access 확인 및 추가
            if "offline_access" not in scopes:
                scopes.append("offline_access")

            self.logger.debug(f"파싱된 스코프: {scopes}")
            return scopes

        except Exception as e:
            self.logger.warning(
                f"스코프 파싱 실패: {delegated_permissions}, error={str(e)}"
            )
            return ["Mail.ReadWrite", "Mail.Send", "offline_access"]

    def decrypt_client_secret(self, encrypted_secret: Optional[str]) -> str:
        """
        암호화된 클라이언트 시크릿을 복호화합니다.

        Args:
            encrypted_secret: 암호화된 시크릿

        Returns:
            복호화된 시크릿

        Raises:
            ValueError: 복호화 실패 시
        """
        if not encrypted_secret:
            raise ValueError("클라이언트 시크릿이 없습니다")

        try:
            # Fernet 암호화된 값인지 확인
            if encrypted_secret.startswith("gAAAAA"):
                fernet = Fernet(self.config.encryption_key.encode())
                decrypted = fernet.decrypt(encrypted_secret.encode()).decode()
                self.logger.debug("클라이언트 시크릿 복호화 성공")
                return decrypted
            else:
                # 평문인 경우 그대로 반환
                self.logger.debug("클라이언트 시크릿이 평문으로 저장됨")
                return encrypted_secret

        except Exception as e:
            self.logger.error(f"클라이언트 시크릿 복호화 실패: {str(e)}")
            raise ValueError("클라이언트 시크릿 복호화 실패")

    def validate_oauth_config(self, oauth_config: Dict[str, Any]) -> bool:
        """
        OAuth 설정의 유효성을 검증합니다.

        Args:
            oauth_config: OAuth 설정

        Returns:
            유효성 여부
        """
        required_fields = ["oauth_client_id", "oauth_tenant_id"]

        for field in required_fields:
            if not oauth_config.get(field):
                self.logger.warning(f"필수 OAuth 필드 누락: {field}")
                return False

        # 클라이언트 ID 형식 검증 (UUID 형식)
        client_id = oauth_config["oauth_client_id"]
        if len(client_id) != 36 or client_id.count("-") != 4:
            self.logger.warning(f"잘못된 클라이언트 ID 형식: {client_id}")
            return False

        return True

    def merge_with_defaults(self, oauth_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        OAuth 설정에 기본값을 병합합니다.

        Args:
            oauth_config: OAuth 설정

        Returns:
            병합된 설정
        """
        merged = oauth_config.copy()

        # 기본 리다이렉트 URI
        if not merged.get("oauth_redirect_uri"):
            merged["oauth_redirect_uri"] = self.config.oauth_redirect_uri

        # 기본 스코프
        if not merged.get("delegated_permissions"):
            merged["delegated_permissions"] = "Mail.ReadWrite,Mail.Send,offline_access"

        return merged
