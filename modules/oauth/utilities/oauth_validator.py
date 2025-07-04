"""인증 관련 검증 유틸리티"""

from typing import Dict, Any
from infra.core.logger import get_logger


class AuthValidator:
    """인증 관련 검증 유틸리티"""

    def __init__(self):
        self.logger = get_logger(__name__)

    def validate_user_id(self, user_id: str) -> str:
        """
        사용자 ID를 검증하고 정리합니다.

        Args:
            user_id: 원본 사용자 ID

        Returns:
            정리된 사용자 ID

        Raises:
            ValueError: 유효하지 않은 사용자 ID
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("사용자 ID가 유효하지 않습니다")

        # 공백 제거 및 소문자 변환
        sanitized = user_id.strip().lower()

        if not sanitized:
            raise ValueError("사용자 ID가 비어있습니다")

        # 이메일 형식인지 확인
        if "@" in sanitized:
            if not self._is_valid_email(sanitized):
                raise ValueError(f"잘못된 이메일 형식: {user_id}")
        else:
            # 일반 문자열인 경우 영숫자와 일부 특수문자만 허용
            if not self._is_valid_username(sanitized):
                raise ValueError(f"잘못된 사용자 ID 형식: {user_id}")

        self.logger.debug(f"사용자 ID 검증 완료: {sanitized}")
        return sanitized

    def validate_session_id(self, session_id: str) -> bool:
        """
        세션 ID의 유효성을 검증합니다.

        Args:
            session_id: 세션 ID

        Returns:
            유효성 여부
        """
        if not session_id or not isinstance(session_id, str):
            return False

        # 세션 ID 형식: auth_YYYYMMDDHHMMSS_XXXXXXXX_YYYYYYYY
        parts = session_id.split("_")
        if len(parts) != 4:
            return False

        if parts[0] != "auth":
            return False

        # 타임스탬프 부분 검증
        if not parts[1].isdigit() or len(parts[1]) != 14:
            return False

        # 해시 부분 검증
        if len(parts[2]) != 8 or len(parts[3]) != 16:
            return False

        return True

    def validate_state_token(self, state: str) -> bool:
        """
        CSRF 상태 토큰의 유효성을 검증합니다.

        Args:
            state: 상태 토큰

        Returns:
            유효성 여부
        """
        if not state or not isinstance(state, str):
            return False

        # URL-safe base64 형식이어야 함
        # 최소 32자 이상
        if len(state) < 32:
            return False

        # URL-safe 문자만 포함
        valid_chars = set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        )
        return all(c in valid_chars for c in state)

    def validate_token_info(self, token_info: Dict[str, Any]) -> bool:
        """
        토큰 정보의 유효성을 검증합니다.

        Args:
            token_info: 토큰 정보

        Returns:
            유효성 여부
        """
        required_fields = ["access_token", "refresh_token", "expires_in"]

        for field in required_fields:
            if field not in token_info or not token_info[field]:
                self.logger.warning(f"토큰 정보에 필수 필드 누락: {field}")
                return False

        # 만료 시간 검증
        expires_in = token_info.get("expires_in")
        if not isinstance(expires_in, int) or expires_in <= 0:
            self.logger.warning(f"잘못된 expires_in 값: {expires_in}")
            return False

        # 토큰 형식 검증 (최소 길이)
        if len(token_info["access_token"]) < 10:
            self.logger.warning("액세스 토큰이 너무 짧습니다")
            return False

        if len(token_info["refresh_token"]) < 10:
            self.logger.warning("리프레시 토큰이 너무 짧습니다")
            return False

        return True

    def _is_valid_email(self, email: str) -> bool:
        """
        이메일 형식 검증 (간단한 버전)

        Args:
            email: 이메일 주소

        Returns:
            유효성 여부
        """
        parts = email.split("@")
        if len(parts) != 2:
            return False

        local, domain = parts
        if not local or not domain:
            return False

        # 도메인에 최소 하나의 점이 있어야 함
        if "." not in domain:
            return False

        # 허용된 문자만 포함
        allowed_chars = set("abcdefghijklmnopqrstuvwxyz0123456789.-_@")
        return all(c in allowed_chars for c in email)

    def _is_valid_username(self, username: str) -> bool:
        """
        사용자명 형식 검증

        Args:
            username: 사용자명

        Returns:
            유효성 여부
        """
        # 최소 2자 이상
        if len(username) < 2:
            return False

        # 허용된 문자만 포함
        allowed_chars = set("abcdefghijklmnopqrstuvwxyz0123456789.-_")
        return all(c in allowed_chars for c in username)
