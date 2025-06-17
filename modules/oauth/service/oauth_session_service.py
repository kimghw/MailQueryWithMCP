"""세션 관리 서비스"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from infra.core.logger import get_logger
from ..auth_schema import (
    AuthSession, AuthState, AuthStartResponse, 
    AuthStatusResponse, AuthBulkStatus, AuthBulkResponse,
    AuthCleanupResponse
)
from ..utilities.oauth_activity_logger import AuthActivityLogger
from ..utilities.session_manager import SessionManager


class AuthSessionService:
    """OAuth 세션 관리 서비스"""
    
    def __init__(self, session_manager: SessionManager):
        self.logger = get_logger(__name__)
        self.session_manager = session_manager
        self.activity_logger = AuthActivityLogger()
    
    def create_new_session(self, user_id: str) -> AuthSession:
        """
        새로운 인증 세션을 생성합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            생성된 세션
        """
        session_id = self.session_manager.generate_session_id(user_id)
        state = self.session_manager.generate_state_token()
        expires_at = self.session_manager.create_session_expiry(10)  # 10분
        
        session = AuthSession(
            session_id=session_id,
            user_id=user_id,
            state=state,
            auth_url="",  # OAuth 서비스에서 설정
            status=AuthState.PENDING,
            expires_at=expires_at
        )
        
        self.activity_logger.log_session_activity(
            session_id,
            "session_created",
            {"user_id": user_id}
        )
        
        return session
    
    def save_session(self, session: AuthSession) -> None:
        """
        세션을 저장합니다.
        
        Args:
            session: 저장할 세션
        """
        self.session_manager.save_session(session)
        self.logger.debug(f"세션 저장됨: {session.session_id}")
    
    def find_pending_session(self, user_id: str) -> Optional[AuthSession]:
        """
        사용자의 진행 중인 세션을 찾습니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            진행 중인 세션 또는 None
        """
        sessions = self.session_manager.get_all_sessions()
        
        for session in sessions.values():
            if session.user_id == user_id and session.is_pending():
                self.logger.info(f"기존 진행 중인 세션 발견: user_id={user_id}")
                return session
        
        return None
    
    def get_session_status(self, session_id: str) -> AuthStatusResponse:
        """
        세션 상태를 조회합니다.
        
        Args:
            session_id: 세션 ID
            
        Returns:
            세션 상태 응답
        """
        session = self.session_manager.find_by_session_id(session_id)
        if not session:
            raise ValueError(f"세션을 찾을 수 없습니다: {session_id}")
        
        # 만료된 세션 처리
        if session.is_expired():
            session.status = AuthState.EXPIRED
            self.session_manager.remove_session(session.state)
            auth_log_session_activity(
                session_id,
                "session_expired",
                {"user_id": session.user_id}
            )
        
        # 상태 메시지 생성
        status_messages = {
            AuthState.PENDING: "사용자 인증 대기 중입니다",
            AuthState.CALLBACK_RECEIVED: "콜백 수신됨, 토큰 교환 중입니다",
            AuthState.COMPLETED: "인증이 완료되었습니다",
            AuthState.FAILED: f"인증에 실패했습니다: {session.error_message}",
            AuthState.EXPIRED: "세션이 만료되었습니다"
        }
        
        return AuthStatusResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            status=session.status,
            message=status_messages.get(session.status, "알 수 없는 상태"),
            created_at=session.created_at,
            expires_at=session.expires_at,
            error_message=session.error_message,
            is_completed=(session.status == AuthState.COMPLETED)
        )
    
    def create_response_from_session(self, session: AuthSession) -> AuthStartResponse:
        """
        세션으로부터 인증 시작 응답을 생성합니다.
        
        Args:
            session: 세션 객체
            
        Returns:
            인증 시작 응답
        """
        return AuthStartResponse(
            session_id=session.session_id,
            auth_url=session.auth_url,
            state=session.state,
            expires_at=session.expires_at
        )
    
    def create_bulk_status(
        self, 
        user_id: str, 
        auth_response: AuthStartResponse
    ) -> AuthBulkStatus:
        """
        일괄 인증 상태를 생성합니다.
        
        Args:
            user_id: 사용자 ID
            auth_response: 인증 시작 응답
            
        Returns:
            일괄 인증 상태
        """
        return AuthBulkStatus(
            user_id=user_id,
            session_id=auth_response.session_id,
            status=AuthState.PENDING,
            auth_url=auth_response.auth_url
        )
    
    def create_completed_status(self, user_id: str) -> AuthBulkStatus:
        """
        완료된 인증 상태를 생성합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            완료된 인증 상태
        """
        return AuthBulkStatus(
            user_id=user_id,
            status=AuthState.COMPLETED
        )
    
    def create_failed_status(self, user_id: str, error: str) -> AuthBulkStatus:
        """
        실패한 인증 상태를 생성합니다.
        
        Args:
            user_id: 사용자 ID
            error: 오류 메시지
            
        Returns:
            실패한 인증 상태
        """
        return AuthBulkStatus(
            user_id=user_id,
            status=AuthState.FAILED,
            error_message=error
        )
    
    def create_bulk_response(self, user_statuses: List[AuthBulkStatus]) -> AuthBulkResponse:
        """
        일괄 인증 응답을 생성합니다.
        
        Args:
            user_statuses: 사용자별 상태 목록
            
        Returns:
            일괄 인증 응답
        """
        pending_count = sum(1 for s in user_statuses if s.status == AuthState.PENDING)
        completed_count = sum(1 for s in user_statuses if s.status == AuthState.COMPLETED)
        failed_count = sum(1 for s in user_statuses if s.status == AuthState.FAILED)
        
        return AuthBulkResponse(
            total_users=len(user_statuses),
            pending_count=pending_count,
            completed_count=completed_count,
            failed_count=failed_count,
            user_statuses=user_statuses
        )
    
    def cleanup_sessions(
        self, 
        expire_threshold_minutes: int, 
        force_cleanup: bool
    ) -> AuthCleanupResponse:
        """
        만료된 세션을 정리합니다.
        
        Args:
            expire_threshold_minutes: 만료 기준 시간(분)
            force_cleanup: 강제 정리 여부
            
        Returns:
            정리 결과
        """
        initial_count = self.session_manager.get_session_count()
        cutoff_time = datetime.utcnow() - timedelta(minutes=expire_threshold_minutes)
        
        cleaned_count = 0
        sessions = self.session_manager.get_all_sessions()
        
        for state, session in list(sessions.items()):
            should_remove = False
            
            if force_cleanup:
                should_remove = True
            elif session.is_expired() or session.created_at < cutoff_time:
                should_remove = True
            elif session.status in [AuthState.COMPLETED, AuthState.FAILED]:
                if session.created_at < cutoff_time:
                    should_remove = True
            
            if should_remove:
                self.session_manager.remove_session(state)
                cleaned_count += 1
                auth_log_session_activity(
                    session.session_id,
                    "session_cleaned",
                    {"reason": "expired" if session.is_expired() else "cleanup"}
                )
        
        active_count = self.session_manager.get_session_count()
        
        self.logger.info(f"세션 정리 완료: {cleaned_count}개 정리, {active_count}개 활성")
        
        return AuthCleanupResponse(
            cleaned_sessions=cleaned_count,
            active_sessions=active_count,
            total_sessions_before=initial_count
        )
    
    def clear_all_sessions(self) -> int:
        """
        모든 세션을 정리합니다.
        
        Returns:
            정리된 세션 수
        """
        count = self.session_manager.get_session_count()
        self.session_manager.clear_all()
        self.logger.info(f"모든 세션 정리됨: {count}개")
        return count