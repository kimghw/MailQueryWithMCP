"""OAuth 콜백 처리 서비스"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from infra.core.logger import get_logger
from infra.core.token_service import get_token_service
from infra.core.oauth_client import get_oauth_client
from ..auth_schema import AuthCallback, AuthState, AuthSession
from .._auth_helpers import (
    auth_generate_callback_success_html,
    auth_generate_callback_error_html,
    auth_log_session_activity,
    auth_validate_token_info
)
from .account_service import AuthAccountService
from .oauth_service import AuthOAuthService


class AuthCallbackService:
    """OAuth 콜백 처리 서비스"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.token_service = get_token_service()
        self.oauth_client = get_oauth_client()
        self.account_service = AuthAccountService()
        self.oauth_service = AuthOAuthService()
    
    async def process_callback(
        self, 
        query_params: Dict[str, str],
        session_store: Dict[str, AuthSession]
    ) -> str:
        """
        OAuth 콜백을 처리합니다.
        
        Args:
            query_params: 쿼리 파라미터
            session_store: 세션 저장소
            
        Returns:
            HTML 응답
        """
        try:
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
                return await self._handle_callback_error(callback_data, session_store)
            
            # 정상적인 인증 코드 처리
            return await self._handle_callback_success(callback_data, session_store)
            
        except Exception as e:
            self.logger.error(f"OAuth 콜백 처리 실패: {str(e)}")
            return auth_generate_callback_error_html(
                "server_error", 
                "콜백 처리 중 서버 오류가 발생했습니다"
            )
    
    async def _handle_callback_success(
        self, 
        callback_data: AuthCallback,
        session_store: Dict[str, AuthSession]
    ) -> str:
        """
        성공적인 OAuth 콜백을 처리합니다.
        
        Args:
            callback_data: 콜백 데이터
            session_store: 세션 저장소
            
        Returns:
            성공 HTML
        """
        state = callback_data.state
        
        # 세션 검증
        if state not in session_store:
            self.logger.warning(f"유효하지 않은 state: {state[:10]}...")
            return auth_generate_callback_error_html(
                "invalid_request",
                "유효하지 않은 인증 요청입니다"
            )
        
        session = session_store[state]
        
        try:
            # 세션 상태 업데이트
            session.status = AuthState.CALLBACK_RECEIVED
            session.callback_received_at = datetime.utcnow()
            
            auth_log_session_activity(
                session.session_id,
                "callback_received",
                {"code_length": len(callback_data.code)}
            )
            
            # OAuth 설정 가져오기
            oauth_config = await self.account_service.get_oauth_config(session.user_id)
            
            if not oauth_config:
                raise ValueError("OAuth 설정을 찾을 수 없습니다")
            
            # 토큰 교환
            token_info = await self.oauth_service.exchange_code_for_tokens(
                callback_data.code,
                oauth_config
            )
            
            # 토큰 유효성 검증
            if not auth_validate_token_info(token_info):
                raise ValueError("유효하지 않은 토큰 정보")
            
            # 토큰 저장
            account_id = await self.account_service.update_account_tokens(
                session.user_id,
                token_info
            )
            
            # 세션 완료 처리
            session.status = AuthState.COMPLETED
            session.token_info = token_info
            
            auth_log_session_activity(
                session.session_id,
                "authentication_completed",
                {"account_id": account_id}
            )
            
            # 성공 페이지 반환
            return auth_generate_callback_success_html(
                session.user_id,
                session.session_id
            )
            
        except Exception as e:
            self.logger.error(f"토큰 교환 실패: {str(e)}")
            
            # 세션 실패 처리
            session.status = AuthState.FAILED
            session.error_message = str(e)
            
            auth_log_session_activity(
                session.session_id,
                "token_exchange_failed",
                {"error": str(e)}
            )
            
            return auth_generate_callback_error_html(
                "server_error",
                "토큰 교환 중 오류가 발생했습니다"
            )
    
    async def _handle_callback_error(
        self, 
        callback_data: AuthCallback,
        session_store: Dict[str, AuthSession]
    ) -> str:
        """
        OAuth 콜백 오류를 처리합니다.
        
        Args:
            callback_data: 콜백 데이터
            session_store: 세션 저장소
            
        Returns:
            오류 HTML
        """
        state = callback_data.state
        error = callback_data.error or "unknown_error"
        description = callback_data.error_description
        
        self.logger.warning(f"OAuth 콜백 오류: {error} - {description}")
        
        # 세션이 있으면 오류 상태로 업데이트
        if state in session_store:
            session = session_store[state]
            session.status = AuthState.FAILED
            session.error_message = f"{error}: {description}" if description else error
            
            auth_log_session_activity(
                session.session_id,
                "callback_error",
                {"error": error, "description": description}
            )
        
        return auth_generate_callback_error_html(error, description)