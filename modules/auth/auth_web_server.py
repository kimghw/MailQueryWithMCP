"""
Auth 모듈의 OAuth 콜백 처리 웹서버

OAuth 2.0 인증 콜백을 처리하는 임시 웹서버입니다.
메모리 세션과 연동하여 인증 코드를 토큰으로 교환하고 결과를 저장합니다.
"""

import asyncio
import threading
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from aiohttp import web, ClientSession
from urllib.parse import parse_qs

from infra.core.logger import get_logger
from infra.core.config import get_config
from infra.core.oauth_client import get_oauth_client
from infra.core.token_service import get_token_service
from infra.core.database import get_database_manager
from .auth_schema import AuthCallback, AuthState
from ._auth_helpers import (
    auth_parse_callback_params,
    auth_generate_callback_success_html,
    auth_generate_callback_error_html,
    auth_log_session_activity,
    auth_validate_token_info
)

logger = get_logger(__name__)


class AuthWebServer:
    """OAuth 콜백 처리를 위한 임시 웹서버"""

    def __init__(self):
        """웹서버 초기화"""
        self.config = get_config()
        self.oauth_client = get_oauth_client()
        self.token_service = get_token_service()
        
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False
        
        # 세션 저장소 참조 (외부에서 주입)
        self.session_store: Optional[Dict[str, Any]] = None
        self.callback_handlers: Dict[str, Callable] = {}

    def set_session_store(self, session_store: Dict[str, Any]):
        """세션 저장소 설정"""
        self.session_store = session_store
        logger.debug("세션 저장소 설정됨")

    def register_callback_handler(self, state: str, handler: Callable):
        """콜백 핸들러 등록"""
        self.callback_handlers[state] = handler
        logger.debug(f"콜백 핸들러 등록: state={state[:10]}...")

    async def auth_web_server_start(self, port: int = 5000) -> str:
        """
        웹서버를 시작합니다.
        
        Args:
            port: 포트 번호
            
        Returns:
            서버 URL
        """
        try:
            self.app = web.Application()
            
            # 라우트 설정
            self.app.router.add_get('/auth/callback', self._handle_oauth_callback)
            self.app.router.add_get('/health', self._handle_health_check)
            
            # 서버 시작
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, 'localhost', port)
            await self.site.start()
            
            self.is_running = True
            server_url = f"http://localhost:{port}"
            
            logger.info(f"OAuth 콜백 웹서버 시작됨: {server_url}")
            return server_url
            
        except Exception as e:
            logger.error(f"웹서버 시작 실패: {str(e)}")
            await self._cleanup()
            raise

    async def auth_web_server_stop(self):
        """웹서버를 중지합니다."""
        try:
            self.is_running = False
            await self._cleanup()
            logger.info("OAuth 콜백 웹서버 중지됨")
        except Exception as e:
            logger.error(f"웹서버 중지 실패: {str(e)}")

    async def _handle_oauth_callback(self, request: web.Request) -> web.Response:
        """OAuth 콜백 요청을 처리합니다."""
        try:
            # 쿼리 매개변수 파싱
            query_params = dict(request.query)
            logger.debug(f"OAuth 콜백 수신: {list(query_params.keys())}")
            
            # 콜백 데이터 생성
            callback_data = AuthCallback(
                code=query_params.get('code', ''),
                state=query_params.get('state', ''),
                session_state=query_params.get('session_state'),
                error=query_params.get('error'),
                error_description=query_params.get('error_description')
            )
            
            # 오류가 있는 경우
            if callback_data.has_error():
                return await self._handle_callback_error(callback_data)
            
            # 정상적인 인증 코드 처리
            return await self._handle_callback_success(callback_data)
            
        except Exception as e:
            logger.error(f"OAuth 콜백 처리 실패: {str(e)}")
            error_html = auth_generate_callback_error_html(
                "server_error", 
                "콜백 처리 중 서버 오류가 발생했습니다"
            )
            return web.Response(text=error_html, content_type='text/html', status=500)

    async def _handle_callback_success(self, callback_data: AuthCallback) -> web.Response:
        """성공적인 OAuth 콜백을 처리합니다."""
        state = callback_data.state
        
        # 세션 저장소에서 해당 세션 찾기
        if not self.session_store or state not in self.session_store:
            logger.warning(f"유효하지 않은 state: {state[:10]}...")
            error_html = auth_generate_callback_error_html(
                "invalid_request",
                "유효하지 않은 인증 요청입니다"
            )
            return web.Response(text=error_html, content_type='text/html', status=400)
        
        session = self.session_store[state]
        
        try:
            # 세션 상태 업데이트
            session.status = AuthState.CALLBACK_RECEIVED
            session.callback_received_at = datetime.utcnow()
            
            auth_log_session_activity(
                session.session_id,
                "callback_received",
                {"code_length": len(callback_data.code)}
            )
            
            # 계정별 OAuth 설정 가져오기
            db = get_database_manager()
            account = db.fetch_one(
                """
                SELECT oauth_client_id, oauth_client_secret, oauth_tenant_id, oauth_redirect_uri
                FROM accounts 
                WHERE user_id = ? AND is_active = 1
                """,
                (session.user_id,)
            )
            
            token_info = None
            
            if account and account['oauth_client_id']:
                # 계정별 OAuth 설정으로 토큰 교환
                logger.info(f"계정별 OAuth 설정으로 토큰 교환: user_id={session.user_id}")
                token_info = await self._exchange_code_with_account_config(
                    callback_data.code,
                    account['oauth_client_id'],
                    account['oauth_client_secret'],
                    account['oauth_tenant_id'],
                    account['oauth_redirect_uri'] or self.config.oauth_redirect_uri
                )
            else:
                # 전역 설정으로 토큰 교환 (fallback)
                logger.info(f"전역 OAuth 설정으로 토큰 교환: user_id={session.user_id}")
                token_info = await self.oauth_client.exchange_code_for_tokens(callback_data.code)
            
            # 토큰 유효성 검증
            if not auth_validate_token_info(token_info):
                raise ValueError("유효하지 않은 토큰 정보")
            
            # 토큰을 데이터베이스에 저장
            account_id = await self.token_service.store_tokens(
                user_id=session.user_id,
                token_info=token_info
            )
            
            # 세션 완료 처리
            session.status = AuthState.COMPLETED
            session.token_info = token_info
            
            auth_log_session_activity(
                session.session_id,
                "authentication_completed",
                {"account_id": account_id}
            )
            
            # 등록된 콜백 핸들러 호출
            if state in self.callback_handlers:
                try:
                    await self.callback_handlers[state](session, token_info)
                except Exception as e:
                    logger.warning(f"콜백 핸들러 실행 실패: {str(e)}")
            
            # 성공 페이지 반환
            success_html = auth_generate_callback_success_html(
                session.user_id,
                session.session_id
            )
            
            logger.info(f"OAuth 인증 완료: user_id={session.user_id}")
            return web.Response(text=success_html, content_type='text/html')
            
        except Exception as e:
            logger.error(f"토큰 교환 실패: {str(e)}")
            
            # 세션 실패 처리
            session.status = AuthState.FAILED
            session.error_message = str(e)
            
            auth_log_session_activity(
                session.session_id,
                "token_exchange_failed",
                {"error": str(e)}
            )
            
            error_html = auth_generate_callback_error_html(
                "server_error",
                "토큰 교환 중 오류가 발생했습니다"
            )
            return web.Response(text=error_html, content_type='text/html', status=500)

    async def _handle_callback_error(self, callback_data: AuthCallback) -> web.Response:
        """OAuth 콜백 오류를 처리합니다."""
        state = callback_data.state
        error = callback_data.error or "unknown_error"
        description = callback_data.error_description
        
        logger.warning(f"OAuth 콜백 오류: {error} - {description}")
        
        # 세션이 있으면 오류 상태로 업데이트
        if self.session_store and state in self.session_store:
            session = self.session_store[state]
            session.status = AuthState.FAILED
            session.error_message = f"{error}: {description}" if description else error
            
            auth_log_session_activity(
                session.session_id,
                "callback_error",
                {"error": error, "description": description}
            )
        
        # 오류 페이지 반환
        error_html = auth_generate_callback_error_html(error, description)
        return web.Response(text=error_html, content_type='text/html', status=400)

    async def _handle_health_check(self, request: web.Request) -> web.Response:
        """서버 상태 확인 엔드포인트"""
        return web.json_response({
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "server": "oauth_callback_server"
        })

    async def _exchange_code_with_account_config(
        self, 
        code: str, 
        client_id: str, 
        client_secret: str,
        tenant_id: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """
        계정별 OAuth 설정을 사용하여 인증 코드를 토큰으로 교환합니다.
        
        Args:
            code: 인증 코드
            client_id: OAuth 클라이언트 ID
            client_secret: OAuth 클라이언트 시크릿
            tenant_id: Azure AD 테넌트 ID
            redirect_uri: 리다이렉트 URI
            
        Returns:
            토큰 정보 딕셔너리
        """
        import aiohttp
        from urllib.parse import urlencode
        
        # 토큰 엔드포인트 URL
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        
        # 토큰 요청 데이터
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "scope": "https://graph.microsoft.com/.default offline_access"
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        logger.debug(f"토큰 교환 요청: client_id={client_id[:8]}..., tenant_id={tenant_id}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                token_url, 
                data=urlencode(data),
                headers=headers
            ) as response:
                response_data = await response.json()
                
                if response.status != 200:
                    error = response_data.get("error", "unknown_error")
                    error_description = response_data.get("error_description", "")
                    logger.error(f"토큰 교환 실패: {error} - {error_description}")
                    raise Exception(f"토큰 교환 실패: {error} - {error_description}")
                
                # 만료 시간 계산
                expires_in = response_data.get("expires_in", 3600)
                expiry_time = datetime.utcnow() + timedelta(seconds=expires_in)
                response_data["expiry_time"] = expiry_time.isoformat()
                
                logger.info(f"계정별 설정으로 토큰 교환 성공: client_id={client_id[:8]}...")
                return response_data

    async def _cleanup(self):
        """리소스 정리"""
        try:
            if self.site:
                await self.site.stop()
                self.site = None
            
            if self.runner:
                await self.runner.cleanup()
                self.runner = None
            
            self.app = None
            self.callback_handlers.clear()
            
        except Exception as e:
            logger.error(f"웹서버 정리 실패: {str(e)}")

    def __del__(self):
        """소멸자"""
        if self.is_running:
            try:
                asyncio.create_task(self._cleanup())
            except:
                pass


class AuthWebServerManager:
    """웹서버 생명주기 관리 클래스"""
    
    def __init__(self):
        self.server: Optional[AuthWebServer] = None
        self.server_url: Optional[str] = None
    
    async def auth_web_server_manager_start(
        self, 
        session_store: Dict[str, Any], 
        port: int = 5000
    ) -> str:
        """
        웹서버를 시작하고 세션 저장소를 설정합니다.
        
        Args:
            session_store: 세션 저장소
            port: 포트 번호
            
        Returns:
            서버 URL
        """
        if self.server and self.server.is_running:
            logger.warning("웹서버가 이미 실행 중입니다")
            return self.server_url
        
        self.server = AuthWebServer()
        self.server.set_session_store(session_store)
        self.server_url = await self.server.auth_web_server_start(port)
        
        logger.info(f"웹서버 관리자 시작: {self.server_url}")
        return self.server_url
    
    async def auth_web_server_manager_stop(self):
        """웹서버를 중지합니다."""
        if self.server:
            await self.server.auth_web_server_stop()
            self.server = None
            self.server_url = None
            logger.info("웹서버 관리자 중지됨")
    
    def auth_web_server_manager_register_callback(self, state: str, handler: Callable):
        """콜백 핸들러를 등록합니다."""
        if self.server:
            self.server.register_callback_handler(state, handler)
    
    @property
    def is_running(self) -> bool:
        """실행 상태 확인"""
        return self.server is not None and self.server.is_running


# 전역 웹서버 관리자 인스턴스
_web_server_manager = AuthWebServerManager()


def get_auth_web_server_manager() -> AuthWebServerManager:
    """
    웹서버 관리자 인스턴스를 반환합니다.
    
    Returns:
        AuthWebServerManager 인스턴스
    """
    return _web_server_manager
