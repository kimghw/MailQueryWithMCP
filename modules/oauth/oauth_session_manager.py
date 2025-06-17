"""메모리 세션 저장소 관리 - 메인 컴포넌트"""

import secrets
import hashlib
from typing import Dict, Optional, List
from threading import Lock
from datetime import datetime, timedelta
from infra.core.logger import get_logger
from infra.core.database import get_database_manager
from .oauth_schema import (
    OAuthSession, OAuthState, OAuthStatusResponse,
    OAuthCleanupRequest, OAuthCleanupResponse
)


class OAuthSessionManager:
    """메모리 기반 OAuth 세션 저장소 관리자"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self._sessions: Dict[str, OAuthSession] = {}
        self._lock = Lock()  # 스레드 안전성을 위한 락
        self.db = get_database_manager()

    # ===== 세션 생성 관련 =====

    def generate_session_id(self, user_id: str) -> str:
        """
        OAuth 세션 고유 ID를 생성합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            세션 ID
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_part = secrets.token_hex(8)
        user_hash = hashlib.md5(user_id.encode()).hexdigest()[:8]
        
        session_id = f"auth_{timestamp}_{user_hash}_{random_part}"
        self.logger.debug(f"세션 ID 생성: {session_id}")
        return session_id

    def generate_state_token(self) -> str:
        """
        CSRF 방지용 상태 토큰을 생성합니다.
        
        Returns:
            상태 토큰
        """
        state_token = secrets.token_urlsafe(32)
        self.logger.debug(f"상태 토큰 생성: {state_token[:10]}...")
        return state_token
    
    def create_session_expiry(self, minutes: int = 10) -> datetime:
        """
        세션 만료 시간을 생성합니다.
        
        Args:
            minutes: 만료까지의 분
            
        Returns:
            만료 시간
        """
        expiry_time = datetime.utcnow() + timedelta(minutes=minutes)
        self.logger.debug(f"세션 만료 시간 설정: {expiry_time.isoformat()}")
        return expiry_time
    
    # ===== 세션 저장/조회 =====

    def save_session(self, session: OAuthSession) -> None:
        """
        세션을 저장합니다.

        Args:
            session: 저장할 세션
        """
        with self._lock:
            self._sessions[session.state] = session
            self.logger.debug(f"세션 저장: session_id={session.session_id}, state={session.state[:10]}...")

    def get_session_by_state(self, state: str) -> Optional[OAuthSession]:
        """
        state로 세션을 조회합니다.

        Args:
            state: 상태값

        Returns:
            세션 또는 None
        """
        with self._lock:
            return self._sessions.get(state)

    def find_by_session_id(self, session_id: str) -> Optional[OAuthSession]:
        """
        세션 ID로 세션을 찾습니다.
        
        Args:
            session_id: 세션 ID

        Returns:
            세션 또는 None
        """
        with self._lock:
            for session in self._sessions.values():
                if session.session_id == session_id:
                    return session
            return None

    # ===== 외부 API (오케스트레이터에서 이동) =====

    def get_session_status(self, session_id: str) -> OAuthStatusResponse:
        """
        세션 상태를 조회합니다. (외부 API)
        
        Args:
            session_id: 세션 ID
            
        Returns:
            세션 상태 응답
        """
        session = self.find_by_session_id(session_id)
        if not session:
            raise ValueError(f"세션을 찾을 수 없습니다: {session_id}")

        # 만료된 세션 처리
        if session.is_expired():
            session.status = OAuthState.EXPIRED
            self.remove_session(session.state)
            self.logger.info(f"만료된 세션 제거: {session_id}")

        # 상태 메시지 생성
        status_messages = {
            OAuthState.PENDING: "사용자 인증 대기 중입니다",
            OAuthState.CALLBACK_RECEIVED: "콜백 수신됨, 토큰 교환 중입니다",
            OAuthState.COMPLETED: "인증이 완료되었습니다",
            OAuthState.FAILED: f"인증에 실패했습니다: {session.error_message}",
            OAuthState.EXPIRED: "세션이 만료되었습니다"
        }

        return OAuthStatusResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            status=session.status,
            message=status_messages.get(session.status, "알 수 없는 상태"),
            created_at=session.created_at,
            expires_at=session.expires_at,
            error_message=session.error_message,
            is_completed=(session.status == OAuthState.COMPLETED)
        )

    def cleanup_sessions(self, request: OAuthCleanupRequest) -> OAuthCleanupResponse:
        """
        만료된 세션을 정리합니다. (외부 API)
        
        Args:
            request: 세션 정리 요청
            
        Returns:
            세션 정리 응답
        """
        initial_count = self.get_session_count()
        cutoff_time = datetime.utcnow() - timedelta(minutes=request.expire_threshold_minutes)
        
        cleaned_count = 0
        
        with self._lock:
            sessions_to_remove = []
            
            for state, session in self._sessions.items():
                should_remove = False

                if request.force_cleanup:
                    should_remove = True
                elif session.is_expired() or session.created_at < cutoff_time:
                    should_remove = True
                elif session.status in [OAuthState.COMPLETED, OAuthState.FAILED]:
                    if session.created_at < cutoff_time:
                        should_remove = True

                if should_remove:
                    sessions_to_remove.append(state)
                    self.logger.debug(f"세션 정리 대상: {session.session_id}")
            
            # 세션 제거
            for state in sessions_to_remove:
                del self._sessions[state]
                cleaned_count += 1
        
        active_count = self.get_session_count()

        self.logger.info(f"세션 정리 완료: {cleaned_count}개 정리, {active_count}개 활성")

        return OAuthCleanupResponse(
            cleaned_sessions=cleaned_count,
            active_sessions=active_count,
            total_sessions_before=initial_count
        )

    async def get_all_accounts_with_session_status(self) -> List[Dict[str, Any]]:
        """
        모든 계정의 인증 상태를 세션 정보와 함께 조회합니다. (외부 API)
        
        Returns:
            계정 상태 목록
        """
        try:
            # 데이터베이스에서 모든 계정 조회
            accounts = self.db.fetch_all(
                """
                SELECT user_id, user_name, status, token_expiry, 
                       last_sync_time, is_active, created_at, updated_at
                FROM accounts 
                ORDER BY updated_at DESC
                """
            )
            
            account_statuses = []
            for account in accounts:
                account_dict = dict(account)
                
                # 토큰 만료 상태 확인
                expiry_time = account_dict.get("token_expiry")
                if expiry_time:
                    if isinstance(expiry_time, str):
                        expiry_time = datetime.fromisoformat(expiry_time)
                    account_dict["token_expired"] = datetime.utcnow() >= expiry_time
                else:
                    account_dict["token_expired"] = True
                
                # 현재 진행 중인 세션 확인
                pending_session = self.find_pending_session_by_user(account_dict["user_id"])
                account_dict["has_pending_session"] = pending_session is not None
                if pending_session:
                    account_dict["pending_session_id"] = pending_session.session_id
                    account_dict["session_status"] = pending_session.status.value
                    account_dict["session_expires_at"] = pending_session.expires_at
                
                account_statuses.append(account_dict)
            
            return account_statuses
            
        except Exception as e:
            self.logger.error(f"전체 계정 상태 조회 실패: {str(e)}")
            return []
    
    def shutdown(self) -> int:
        """
        OAuthSessionManager를 종료하고 모든 세션을 정리합니다. (외부 API)

        Returns:
            정리된 세션 수
        """
        session_count = self.get_session_count()
        with self._lock:
            self._sessions.clear()

        self.logger.info(f"OAuthSessionManager 종료: {session_count}개 세션 정리됨")
        return session_count

    # ===== 내부 메서드 =====
    
    def remove_session(self, state: str) -> bool:
        """
        세션을 제거합니다.
        
        Args:
            state: 상태값
            
        Returns:
            제거 성공 여부
        """
        with self._lock:
            if state in self._sessions:
                session = self._sessions[state]
                del self._sessions[state]
                self.logger.debug(f"세션 제거: session_id={session.session_id}")
                return True
            return False

    def get_all_sessions(self) -> Dict[str, OAuthSession]:
        """
        모든 세션을 반환합니다.

        Returns:
            세션 딕셔너리의 복사본
        """
        with self._lock:
            return self._sessions.copy()

    def get_session_count(self) -> int:
        """
        저장된 세션 수를 반환합니다.
        
        Returns:
            세션 수
        """
        with self._lock:
            return len(self._sessions)
    
    def clear_all(self) -> None:
        """모든 세션을 제거합니다."""
        with self._lock:
            count = len(self._sessions)
            self._sessions.clear()
            self.logger.info(f"모든 세션 제거: {count}개")

    def get_session_store(self) -> Dict[str, OAuthSession]:
        """
        웹서버와 공유할 세션 저장소 참조를 반환합니다.

        Returns:
            세션 저장소 참조
        """
        return self._sessions

    def find_pending_session_by_user(self, user_id: str) -> Optional[OAuthSession]:
        """
        사용자의 진행 중인 세션을 찾습니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            진행 중인 세션 또는 None
        """
        with self._lock:
            for session in self._sessions.values():
                if session.user_id == user_id and session.is_pending():
                    return session
            return None

    def get_sessions_by_user(self, user_id: str) -> List[OAuthSession]:
        """
        특정 사용자의 모든 세션을 조회합니다.

        Args:
            user_id: 사용자 ID

        Returns:
            세션 목록
        """
        with self._lock:
            return [
                session for session in self._sessions.values()
                if session.user_id == user_id
            ]

    def cleanup_expired_sessions(self) -> int:
        """
        만료된 세션을 정리합니다.
        
        Returns:
            정리된 세션 수
        """
        with self._lock:
            expired_states = []
            
            for state, session in self._sessions.items():
                if session.is_expired():
                    expired_states.append(state)
            
            for state in expired_states:
                del self._sessions[state]
            
            if expired_states:
                self.logger.info(f"만료된 세션 {len(expired_states)}개 정리됨")
            
            return len(expired_states)


# 전역 OAuthSessionManager 인스턴스
_session_manager = None


def get_oauth_session_manager() -> OAuthSessionManager:
    """
    OAuthSessionManager 인스턴스를 반환합니다.

    Returns:
        OAuthSessionManager 인스턴스
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = OAuthSessionManager()
    return _session_manager
>>>>>>> REPLACE
