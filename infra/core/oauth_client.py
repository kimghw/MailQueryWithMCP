"""
IACSGraph 프로젝트의 OAuth 2.0 클라이언트

Azure AD와의 OAuth 2.0 인증 플로우를 처리하는 비동기 클라이언트입니다.
Microsoft Graph API 접근을 위한 토큰 관리 기능을 제공합니다.
"""

import asyncio
import base64
import json
import urllib.parse
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from functools import lru_cache

import aiohttp

from .config import get_config
from .exceptions import AuthenticationError, TokenError, TokenExpiredError, TokenRefreshError, APIConnectionError
from .logger import get_logger

logger = get_logger(__name__)


class OAuthClient:
    """Azure AD OAuth 2.0 인증을 처리하는 클라이언트"""

    def __init__(self):
        """OAuth 클라이언트 초기화"""
        self.config = get_config()
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """HTTP 세션을 반환 (레이지 초기화)"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.http_timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": "IACSGraph/1.0",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            )
        return self._session

    def generate_auth_url(self, state: Optional[str] = None) -> str:
        """
        Azure AD 인증 URL을 생성합니다.
        
        Args:
            state: CSRF 방지를 위한 상태값
            
        Returns:
            인증 URL
        """
        if not self.config.is_oauth_configured():
            raise AuthenticationError(
                "OAuth 설정이 완료되지 않았습니다. AZURE_CLIENT_ID와 AZURE_CLIENT_SECRET을 확인하세요."
            )

        params = {
            "client_id": self.config.azure_client_id,
            "response_type": "code",
            "redirect_uri": self.config.oauth_redirect_uri,
            "scope": " ".join(self.config.azure_scopes),
            "response_mode": "query",
        }
        
        if state:
            params["state"] = state
            
        auth_url = f"{self.config.azure_authority}/oauth2/v2.0/authorize?" + urllib.parse.urlencode(params)
        
        logger.info(f"인증 URL 생성됨: {auth_url[:100]}...")
        return auth_url

    async def exchange_code_for_tokens(self, authorization_code: str) -> Dict[str, Any]:
        """
        인증 코드를 액세스 토큰과 리프레시 토큰으로 교환합니다.
        
        Args:
            authorization_code: 인증 코드
            
        Returns:
            토큰 정보 딕셔너리
        """
        if not self.config.is_oauth_configured():
            raise AuthenticationError(
                "OAuth 설정이 완료되지 않았습니다."
            )

        token_url = f"{self.config.azure_authority}/oauth2/v2.0/token"
        
        data = {
            "client_id": self.config.azure_client_id,
            "client_secret": self.config.azure_client_secret,
            "code": authorization_code,
            "redirect_uri": self.config.oauth_redirect_uri,
            "grant_type": "authorization_code",
            "scope": " ".join(self.config.azure_scopes),
        }

        try:
            session = await self._get_session()
            async with session.post(token_url, data=data) as response:
                response_data = await response.json()
                
                if response.status != 200:
                    error_msg = response_data.get("error_description", "토큰 교환 실패")
                    raise TokenError(
                        f"토큰 교환 실패: {error_msg}",
                        details={
                            "status_code": response.status,
                            "error": response_data.get("error"),
                            "error_description": response_data.get("error_description")
                        }
                    )

                # 토큰 정보 파싱
                token_info = self._parse_token_response(response_data)
                
                logger.info("토큰 교환 성공")
                return token_info

        except aiohttp.ClientError as e:
            raise APIConnectionError(
                f"토큰 교환 중 네트워크 오류: {str(e)}",
                api_endpoint=token_url
            ) from e
        except Exception as e:
            raise TokenError(
                f"토큰 교환 중 예상치 못한 오류: {str(e)}"
            ) from e

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        리프레시 토큰을 사용하여 새로운 액세스 토큰을 발급받습니다.
        
        Args:
            refresh_token: 리프레시 토큰
            
        Returns:
            새로운 토큰 정보 딕셔너리
        """
        if not self.config.is_oauth_configured():
            raise AuthenticationError(
                "OAuth 설정이 완료되지 않았습니다."
            )

        token_url = f"{self.config.azure_authority}/oauth2/v2.0/token"
        
        data = {
            "client_id": self.config.azure_client_id,
            "client_secret": self.config.azure_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": " ".join(self.config.azure_scopes),
        }

        try:
            session = await self._get_session()
            async with session.post(token_url, data=data) as response:
                response_data = await response.json()
                
                if response.status != 200:
                    error_msg = response_data.get("error_description", "토큰 갱신 실패")
                    
                    # 리프레시 토큰이 만료된 경우
                    if response_data.get("error") == "invalid_grant":
                        raise TokenExpiredError(
                            "리프레시 토큰이 만료되었습니다. 재인증이 필요합니다."
                        )
                    
                    raise TokenRefreshError(
                        f"토큰 갱신 실패: {error_msg}",
                        details={
                            "status_code": response.status,
                            "error": response_data.get("error"),
                            "error_description": response_data.get("error_description")
                        }
                    )

                # 토큰 정보 파싱
                token_info = self._parse_token_response(response_data)
                
                # 새로운 리프레시 토큰이 없으면 기존 토큰 유지
                if not token_info.get("refresh_token"):
                    token_info["refresh_token"] = refresh_token
                
                logger.info("토큰 갱신 성공")
                return token_info

        except aiohttp.ClientError as e:
            raise APIConnectionError(
                f"토큰 갱신 중 네트워크 오류: {str(e)}",
                api_endpoint=token_url
            ) from e
        except (TokenExpiredError, TokenRefreshError):
            raise
        except Exception as e:
            raise TokenRefreshError(
                f"토큰 갱신 중 예상치 못한 오류: {str(e)}"
            ) from e

    async def validate_token(self, access_token: str) -> Dict[str, Any]:
        """
        액세스 토큰의 유효성을 검증합니다.
        
        Args:
            access_token: 검증할 액세스 토큰
            
        Returns:
            사용자 정보 딕셔너리
        """
        user_info_url = f"{self.config.graph_api_endpoint}me"
        
        try:
            session = await self._get_session()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
            
            async with session.get(user_info_url, headers=headers) as response:
                if response.status == 401:
                    raise TokenExpiredError("액세스 토큰이 유효하지 않습니다.")
                
                if response.status != 200:
                    raise APIConnectionError(
                        f"토큰 검증 실패: HTTP {response.status}",
                        api_endpoint=user_info_url,
                        status_code=response.status
                    )
                
                user_info = await response.json()
                logger.debug(f"토큰 검증 성공: 사용자 {user_info.get('userPrincipalName', 'Unknown')}")
                return user_info

        except aiohttp.ClientError as e:
            raise APIConnectionError(
                f"토큰 검증 중 네트워크 오류: {str(e)}",
                api_endpoint=user_info_url
            ) from e
        except TokenExpiredError:
            raise
        except Exception as e:
            raise AuthenticationError(
                f"토큰 검증 중 예상치 못한 오류: {str(e)}"
            ) from e

    async def make_graph_request(
        self, 
        access_token: str, 
        endpoint: str, 
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Microsoft Graph API 요청을 수행합니다.
        
        Args:
            access_token: 액세스 토큰
            endpoint: API 엔드포인트 (예: "me/messages")
            method: HTTP 메서드
            params: 쿼리 매개변수
            json_data: JSON 데이터
            
        Returns:
            API 응답 데이터
        """
        if not endpoint.startswith("http"):
            url = f"{self.config.graph_api_endpoint}{endpoint.lstrip('/')}"
        else:
            url = endpoint

        try:
            session = await self._get_session()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
            
            if json_data:
                headers["Content-Type"] = "application/json"
            
            async with session.request(
                method, 
                url, 
                headers=headers, 
                params=params, 
                json=json_data
            ) as response:
                
                if response.status == 401:
                    raise TokenExpiredError("액세스 토큰이 만료되었습니다.")
                
                if response.status >= 400:
                    try:
                        error_data = await response.json()
                        error_msg = error_data.get("error", {}).get("message", "알 수 없는 오류")
                    except:
                        error_msg = f"HTTP {response.status}"
                    
                    raise APIConnectionError(
                        f"Graph API 요청 실패: {error_msg}",
                        api_endpoint=url,
                        status_code=response.status
                    )
                
                result = await response.json()
                logger.debug(f"Graph API 요청 성공: {method} {endpoint}")
                return result

        except aiohttp.ClientError as e:
            raise APIConnectionError(
                f"Graph API 요청 중 네트워크 오류: {str(e)}",
                api_endpoint=url
            ) from e
        except (TokenExpiredError, APIConnectionError):
            raise
        except Exception as e:
            raise APIConnectionError(
                f"Graph API 요청 중 예상치 못한 오류: {str(e)}",
                api_endpoint=url
            ) from e

    def _parse_token_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        토큰 응답 데이터를 파싱하고 만료 시간을 계산합니다.
        
        Args:
            response_data: 토큰 응답 데이터
            
        Returns:
            파싱된 토큰 정보
        """
        access_token = response_data.get("access_token")
        refresh_token = response_data.get("refresh_token")
        expires_in = response_data.get("expires_in", 3600)  # 기본 1시간
        token_type = response_data.get("token_type", "Bearer")
        scope = response_data.get("scope", "")

        # 만료 시간 계산 (버퍼 시간 적용)
        expiry_time = datetime.utcnow() + timedelta(
            seconds=expires_in - (self.config.token_refresh_buffer_minutes * 60)
        )

        token_info = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": token_type,
            "expires_in": expires_in,
            "expiry_time": expiry_time,
            "scope": scope,
            "created_at": datetime.utcnow()
        }

        # ID 토큰이 있으면 디코딩하여 사용자 정보 추출
        id_token = response_data.get("id_token")
        if id_token:
            try:
                user_info = self._decode_jwt_payload(id_token)
                token_info["user_info"] = user_info
            except Exception as e:
                logger.warning(f"ID 토큰 디코딩 실패: {str(e)}")

        return token_info

    def _decode_jwt_payload(self, jwt_token: str) -> Dict[str, Any]:
        """
        JWT 토큰의 페이로드를 디코딩합니다 (검증 없이).
        
        Args:
            jwt_token: JWT 토큰
            
        Returns:
            디코딩된 페이로드
        """
        try:
            # JWT는 header.payload.signature 형태
            parts = jwt_token.split(".")
            if len(parts) != 3:
                raise ValueError("잘못된 JWT 형식")
            
            # Base64 URL 디코딩
            payload = parts[1]
            # 패딩 추가
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += "=" * padding
            
            decoded_bytes = base64.urlsafe_b64decode(payload)
            decoded_payload = json.loads(decoded_bytes.decode("utf-8"))
            
            return decoded_payload
            
        except Exception as e:
            logger.error(f"JWT 디코딩 실패: {str(e)}")
            return {}

    def is_token_expired(self, token_info: Dict[str, Any]) -> bool:
        """
        토큰이 만료되었는지 확인합니다.
        
        Args:
            token_info: 토큰 정보
            
        Returns:
            만료 여부
        """
        expiry_time = token_info.get("expiry_time")
        if not expiry_time:
            return True
        
        if isinstance(expiry_time, str):
            expiry_time = datetime.fromisoformat(expiry_time.replace("Z", "+00:00"))
        
        return datetime.utcnow() >= expiry_time

    async def close(self) -> None:
        """HTTP 세션을 종료합니다."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("OAuth 클라이언트 세션 종료됨")

    def __del__(self):
        """소멸자에서 세션 정리"""
        if hasattr(self, '_session') and self._session and not self._session.closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._session.close())
                else:
                    asyncio.run(self._session.close())
            except:
                pass  # 소멸자에서는 예외를 무시


@lru_cache(maxsize=1)
def get_oauth_client() -> OAuthClient:
    """
    OAuth 클라이언트 인스턴스를 반환하는 레이지 싱글톤 함수
    
    Returns:
        OAuthClient: OAuth 클라이언트 인스턴스
    """
    return OAuthClient()


# 편의를 위한 전역 OAuth 클라이언트 인스턴스
oauth_client = get_oauth_client()
