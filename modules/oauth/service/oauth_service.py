"""OAuth URL 생성 및 토큰 교환 서비스"""

from typing import Dict, Any, List, Optional
from infra.core.logger import get_logger
from infra.core.oauth_client import get_oauth_client
from infra.core.config import get_config
from ..utilities.oauth_config_parser import OAuthConfigParser


class AuthOAuthService:
    """OAuth URL 생성 및 토큰 교환 서비스"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.oauth_client = get_oauth_client()
        self.config = get_config()
        self.config_parser = OAuthConfigParser()

    def generate_auth_url(self, oauth_config: Dict[str, Any], state: str) -> str:
        """
        OAuth 인증 URL을 생성합니다.

        Args:
            oauth_config: OAuth 설정
            state: CSRF 방지용 상태값

        Returns:
            인증 URL
        """
        # 스코프 파싱
        scopes = self.config_parser.parse_scopes(
            oauth_config.get("delegated_permissions")
        )

        # 계정별 OAuth 설정 사용
        auth_url = self.oauth_client.generate_auth_url_with_account_config(
            client_id=oauth_config["oauth_client_id"],
            tenant_id=oauth_config["oauth_tenant_id"],
            redirect_uri=oauth_config.get(
                "oauth_redirect_uri", self.config.oauth_redirect_uri
            ),
            state=state,
            scopes=scopes,
        )

        self.logger.info(
            f"OAuth URL 생성: client_id={oauth_config['oauth_client_id'][:8]}..., "
            f"scopes={scopes}"
        )

        return auth_url

    async def exchange_code_for_tokens(
        self, code: str, oauth_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        인증 코드를 토큰으로 교환합니다.

        Args:
            code: 인증 코드
            oauth_config: OAuth 설정

        Returns:
            토큰 정보
        """
        # 클라이언트 시크릿 복호화
        client_secret = self.config_parser.decrypt_client_secret(
            oauth_config.get("oauth_client_secret")
        )

        # 스코프 파싱
        scopes = self.config_parser.parse_scopes(
            oauth_config.get("delegated_permissions")
        )

        # 토큰 교환 파라미터
        params = {
            "client_id": oauth_config["oauth_client_id"],
            "client_secret": client_secret,
            "tenant_id": oauth_config["oauth_tenant_id"],
            "redirect_uri": oauth_config.get(
                "oauth_redirect_uri", self.config.oauth_redirect_uri
            ),
            "scopes": scopes,
        }

        # 토큰 교환 실행
        token_info = await self.oauth_client.exchange_code_with_params(code, params)

        self.logger.info(
            f"토큰 교환 성공: client_id={oauth_config['oauth_client_id'][:8]}..."
        )

        return token_info

    def validate_redirect_uri(
        self, callback_url: str, expected_redirect_uri: str
    ) -> bool:
        """
        콜백 URL의 유효성을 검증합니다.

        Args:
            callback_url: 수신된 콜백 URL
            expected_redirect_uri: 예상 리다이렉트 URI

        Returns:
            유효성 여부
        """
        from urllib.parse import urlparse

        try:
            callback_parsed = urlparse(callback_url)
            expected_parsed = urlparse(expected_redirect_uri)

            # 스키마, 호스트, 포트, 경로가 일치하는지 확인
            return (
                callback_parsed.scheme == expected_parsed.scheme
                and callback_parsed.netloc == expected_parsed.netloc
                and callback_parsed.path == expected_parsed.path
            )
        except Exception as e:
            self.logger.error(f"콜백 URL 검증 실패: {str(e)}")
            return False
