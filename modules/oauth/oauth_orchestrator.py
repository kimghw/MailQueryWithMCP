"""
OAuth 플로우 조정 오케스트레이터
"""

from infra.core.logger import get_logger

# 스키마
from .oauth_schema import (
    OAuthStartRequest, OAuthStartResponse,
    OAuthBulkRequest, OAuthBulkResponse
)

# 서비스
from .service.oauth_session_service import OAuthSessionService
from .service.oauth_service import OAuthService
from .service.oauth_account_service import OAuthAccountService

# 세션 관리자
from .oauth_session_manager import get_oauth_session_manager

# 유틸리티
from .utilities.oauth_validator import OAuthValidator

# 웹서버
from .oauth_web_server import get_auth_web_server_manager

logger = get_logger(__name__)


class OAuthOrchestrator:
    """OAuth 플로우 조정 오케스트레이터"""

    def __init__(self):
        """오케스트레이터 초기화"""
        self.logger = get_logger(__name__)
        
        # 세션 관리자
        self.session_manager = get_oauth_session_manager()
        
        # 유틸리티
        self.validator = OAuthValidator()
        
        # 서비스 초기화
        self.session_service = OAuthSessionService(self.session_manager)
        self.oauth_service = OAuthService()
        self.account_service = OAuthAccountService()
        
        # 웹서버 매니저
        self.web_server_manager = get_auth_web_server_manager()

    async def start_authentication(
        self, 
        request: OAuthStartRequest
    ) -> OAuthStartResponse:
        """
        OAuth 인증을 시작합니다.
        """
        try:
            # 1. 사용자 ID 검증
            user_id = self.validator.validate_user_id(request.user_id)
            
            # 2. 기존 진행 중인 세션 확인
            existing_session = self.session_manager.find_pending_session_by_user(user_id)
            if existing_session:
                self.logger.info(f"기존 인증 세션 사용: user_id={user_id}")
                return self.session_service.create_start_response(existing_session)

            # 3. 새 세션 생성
            session = self.session_service.create_session(user_id)

            # 4. OAuth 설정 가져오기
            oauth_config = await self.account_service.get_oauth_config(user_id)
            
            # 5. 인증 URL 생성
            auth_url = self.oauth_service.generate_auth_url(oauth_config, session.state)
            
            # 6. 세션 업데이트 및 저장
            session.auth_url = auth_url
            self.session_manager.save_session(session)
            
            # 7. 웹서버 시작 (필요시)
            if not self.web_server_manager.is_running:
                await self.web_server_manager.start_server(
                    self.session_manager.get_session_store()
                )
            
            self.logger.info(f"OAuth 인증 시작: user_id={user_id}, session_id={session.session_id}")
            
            return self.session_service.create_start_response(session)
            
        except Exception as e:
            self.logger.error(f"인증 시작 실패: user_id={request.user_id}, error={str(e)}")
            raise

    async def bulk_authentication(
        self, 
        request: OAuthBulkRequest
    ) -> OAuthBulkResponse:
        """
        여러 사용자의 일괄 인증을 조정합니다.
        """
        results = []
        
        for user_id in request.user_ids:
            try:
                # 1. 사용자 ID 검증
                sanitized_user_id = self.validator.validate_user_id(user_id)
                
                # 2. 토큰 유효성 검사
                if await self.account_service.is_token_valid(sanitized_user_id):
                    results.append(self.session_service.create_completed_status(sanitized_user_id))
                    continue

                # 3. 인증 시작
                auth_request = OAuthStartRequest(user_id=sanitized_user_id)
                auth_response = await self.start_authentication(auth_request)
                results.append(self.session_service.create_bulk_status(sanitized_user_id, auth_response))
                    
            except Exception as e:
                self.logger.error(f"일괄 인증 처리 실패: user_id={user_id}, error={str(e)}")
                results.append(self.session_service.create_failed_status(user_id, str(e)))
        
        return OAuthBulkResponse(results=results)

    async def shutdown(self):
        """오케스트레이터를 종료하고 리소스를 정리합니다."""
        try:
            if self.web_server_manager.is_running:
                await self.web_server_manager.stop_server()
            
            self.session_manager.shutdown()
            self.logger.info("OAuth 오케스트레이터 종료 완료")
            
        except Exception as e:
            self.logger.error(f"오케스트레이터 종료 실패: {str(e)}")


# 전역 오케스트레이터 인스턴스
_oauth_orchestrator = None


def get_oauth_orchestrator() -> OAuthOrchestrator:
    """
    OAuth 오케스트레이터 싱글톤 인스턴스를 반환합니다.
    
    Returns:
        OAuthOrchestrator 인스턴스
    """
    global _oauth_orchestrator
    if _oauth_orchestrator is None:
        _oauth_orchestrator = OAuthOrchestrator()
    return _oauth_orchestrator
