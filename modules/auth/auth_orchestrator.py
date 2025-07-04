"""
Auth 모듈의 OAuth 플로우 조정 오케스트레이터

OAuth 2.0 인증 플로우를 조정하고 메모리 세션을 관리하는 메인 API입니다.
infra 서비스들을 활용하여 토큰 저장/갱신/상태확인을 수행합니다.
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from infra.core.logger import get_logger
from infra.core.database import get_database_manager
from infra.core.token_service import get_token_service
from infra.core.oauth_client import get_oauth_client
from infra.core.config import get_config
from .auth_schema import (
    AuthSession,
    AuthState,
    AuthStartRequest,
    AuthStartResponse,
    AuthStatusResponse,
    AuthBulkRequest,
    AuthBulkResponse,
    AuthBulkStatus,
    AuthCleanupRequest,
    AuthCleanupResponse,
)
from .auth_web_server import get_auth_web_server_manager
from ._auth_helpers import (
    auth_generate_session_id,
    auth_generate_state_token,
    auth_sanitize_user_id,
    auth_create_session_expiry,
    auth_calculate_session_timeout,
    auth_log_session_activity,
)
from modules.account._account_helpers import AccountCryptoHelpers

logger = get_logger(__name__)


class AuthOrchestrator:
    """OAuth 플로우 조정 오케스트레이터"""

    def __init__(self):
        """오케스트레이터 초기화"""
        self.config = get_config()
        self.db = get_database_manager()
        self.token_service = get_token_service()
        self.oauth_client = get_oauth_client()
        self.web_server_manager = get_auth_web_server_manager()

        # 메모리 기반 세션 저장소 (state를 키로 사용)
        self.auth_sessions: Dict[str, AuthSession] = {}

    async def auth_orchestrator_start_authentication(
        self, request: AuthStartRequest
    ) -> AuthStartResponse:
        """
        OAuth 인증을 시작합니다.

        Args:
            request: 인증 시작 요청

        Returns:
            인증 시작 응답
        """
        try:
            # 사용자 ID 검증 및 정리
            user_id = auth_sanitize_user_id(request.user_id)

            # 기존 진행 중인 세션 확인
            existing_session = self._find_pending_session_by_user(user_id)
            if existing_session and not existing_session.is_expired():
                logger.info(f"기존 진행 중인 세션 발견: user_id={user_id}")
                return AuthStartResponse(
                    session_id=existing_session.session_id,
                    auth_url=existing_session.auth_url,
                    state=existing_session.state,
                    expires_at=existing_session.expires_at,
                )

            # 새 세션 생성, generate session ID and state
            session_id = auth_generate_session_id(user_id)
            state = auth_generate_state_token()
            expires_at = auth_create_session_expiry(10)  # 10분

            # 계정별 OAuth 설정 가져오기
            oauth_config = await self._get_account_oauth_config(user_id)

            # OAuth 인증 URL 생성
            if oauth_config:
                # 계정별 OAuth 설정 사용
                scopes = self._parse_delegated_permissions(
                    oauth_config.get("delegated_permissions")
                )
                auth_url = self.oauth_client.generate_auth_url_with_account_config(
                    client_id=oauth_config["oauth_client_id"],
                    tenant_id=oauth_config["oauth_tenant_id"],
                    redirect_uri=oauth_config.get("oauth_redirect_uri"),
                    state=state,
                    scopes=scopes,
                )
                logger.info(
                    f"계정별 OAuth 설정 사용: user_id={user_id}, scopes={scopes}"
                )
            else:
                # 계정별 OAuth 설정이 없는 경우
                logger.error(f"계정별 OAuth 설정이 없습니다: user_id={user_id}")
                raise ValueError(
                    f"계정 '{user_id}'에 대한 OAuth 설정이 없습니다. enrollment 파일을 확인하고 계정을 등록해주세요."
                )

            # 세션 객체 생성
            session = AuthSession(
                session_id=session_id,
                user_id=user_id,
                state=state,
                auth_url=auth_url,
                status=AuthState.PENDING,
                expires_at=expires_at,
            )

            # 메모리에 세션 저장
            self.auth_sessions[state] = session

            # 웹서버 시작 (아직 실행 중이 아닌 경우)
            if not self.web_server_manager.is_running:
                await self.web_server_manager.auth_web_server_manager_start(
                    self.auth_sessions
                )

            auth_log_session_activity(
                session_id,
                "authentication_started",
                {
                    "user_id": user_id,
                    "oauth_config_type": "account" if oauth_config else "global",
                },
            )

            logger.info(f"OAuth 인증 시작: user_id={user_id}, session_id={session_id}")

            return AuthStartResponse(
                session_id=session_id,
                auth_url=auth_url,
                state=state,
                expires_at=expires_at,
            )

        except Exception as e:
            logger.error(f"인증 시작 실패: user_id={request.user_id}, error={str(e)}")
            raise

    async def auth_orchestrator_get_session_status(
        self, session_id: str
    ) -> AuthStatusResponse:
        """
        세션 상태를 조회합니다.

        Args:
            session_id: 세션 ID

        Returns:
            인증 상태 응답
        """
        # 세션 찾기
        session = self._find_session_by_id(session_id)
        if not session:
            raise ValueError(f"세션을 찾을 수 없습니다: {session_id}")

        # 만료된 세션 처리
        if session.is_expired():
            session.status = AuthState.EXPIRED
            self._cleanup_session(session.state)

        # 상태 메시지 생성
        status_messages = {
            AuthState.PENDING: "사용자 인증 대기 중입니다",
            AuthState.CALLBACK_RECEIVED: "콜백 수신됨, 토큰 교환 중입니다",
            AuthState.COMPLETED: "인증이 완료되었습니다",
            AuthState.FAILED: f"인증에 실패했습니다: {session.error_message}",
            AuthState.EXPIRED: "세션이 만료되었습니다",
        }

        return AuthStatusResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            status=session.status,
            message=status_messages.get(session.status, "알 수 없는 상태"),
            created_at=session.created_at,
            expires_at=session.expires_at,
            error_message=session.error_message,
            is_completed=(session.status == AuthState.COMPLETED),
        )

    async def auth_orchestrator_bulk_authentication(
        self, request: AuthBulkRequest
    ) -> AuthBulkResponse:
        """
        여러 사용자의 일괄 인증을 조정합니다.

        Args:
            request: 일괄 인증 요청

        Returns:
            일괄 인증 응답
        """
        user_statuses = []
        timeout_minutes = auth_calculate_session_timeout(
            len(request.user_ids), request.timeout_minutes
        )

        # 먼저 모든 사용자의 현재 토큰 상태 확인
        for user_id in request.user_ids:
            try:
                sanitized_user_id = auth_sanitize_user_id(user_id)

                # 토큰 서비스를 통해 인증 상태 확인
                auth_status = await self.token_service.check_authentication_status(
                    sanitized_user_id
                )

                if auth_status.get("requires_reauth", True):
                    # 재인증 필요 - 새 세션 생성
                    auth_request = AuthStartRequest(user_id=sanitized_user_id)
                    auth_response = await self.auth_orchestrator_start_authentication(
                        auth_request
                    )

                    user_statuses.append(
                        AuthBulkStatus(
                            user_id=sanitized_user_id,
                            session_id=auth_response.session_id,
                            status=AuthState.PENDING,
                            auth_url=auth_response.auth_url,
                        )
                    )
                else:
                    # 이미 유효한 토큰 보유
                    user_statuses.append(
                        AuthBulkStatus(
                            user_id=sanitized_user_id, status=AuthState.COMPLETED
                        )
                    )

            except Exception as e:
                logger.error(f"일괄 인증 처리 실패: user_id={user_id}, error={str(e)}")
                user_statuses.append(
                    AuthBulkStatus(
                        user_id=user_id, status=AuthState.FAILED, error_message=str(e)
                    )
                )

        # 통계 계산
        pending_count = sum(
            1 for status in user_statuses if status.status == AuthState.PENDING
        )
        completed_count = sum(
            1 for status in user_statuses if status.status == AuthState.COMPLETED
        )
        failed_count = sum(
            1 for status in user_statuses if status.status == AuthState.FAILED
        )

        logger.info(
            f"일괄 인증 시작: 총 {len(request.user_ids)}명, "
            f"대기 {pending_count}명, 완료 {completed_count}명, 실패 {failed_count}명"
        )

        return AuthBulkResponse(
            total_users=len(request.user_ids),
            pending_count=pending_count,
            completed_count=completed_count,
            failed_count=failed_count,
            user_statuses=user_statuses,
        )

    async def auth_orchestrator_cleanup_sessions(
        self, request: AuthCleanupRequest
    ) -> AuthCleanupResponse:
        """
        만료된 세션을 정리합니다.

        Args:
            request: 세션 정리 요청

        Returns:
            세션 정리 응답
        """
        initial_count = len(self.auth_sessions)
        cutoff_time = datetime.utcnow() - timedelta(
            minutes=request.expire_threshold_minutes
        )

        cleaned_sessions = 0
        sessions_to_remove = []

        for state, session in self.auth_sessions.items():
            should_remove = False

            if request.force_cleanup:
                should_remove = True
            elif session.is_expired() or session.created_at < cutoff_time:
                should_remove = True
            elif session.status in [AuthState.COMPLETED, AuthState.FAILED]:
                # 완료/실패된 세션도 일정 시간 후 정리
                if session.created_at < cutoff_time:
                    should_remove = True

            if should_remove:
                sessions_to_remove.append(state)
                auth_log_session_activity(
                    session.session_id,
                    "session_cleaned",
                    {"reason": "expired" if session.is_expired() else "cleanup"},
                )

        # 세션 제거
        for state in sessions_to_remove:
            del self.auth_sessions[state]
            cleaned_sessions += 1

        active_sessions = len(self.auth_sessions)

        logger.info(
            f"세션 정리 완료: {cleaned_sessions}개 정리, {active_sessions}개 활성"
        )

        return AuthCleanupResponse(
            cleaned_sessions=cleaned_sessions,
            active_sessions=active_sessions,
            total_sessions_before=initial_count,
        )

    async def auth_orchestrator_get_all_accounts_status(self) -> List[Dict[str, Any]]:
        """
        모든 계정의 인증 상태를 조회합니다.

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
                pending_session = self._find_pending_session_by_user(
                    account_dict["user_id"]
                )
                account_dict["has_pending_session"] = pending_session is not None
                if pending_session:
                    account_dict["pending_session_id"] = pending_session.session_id

                account_statuses.append(account_dict)

            return account_statuses

        except Exception as e:
            logger.error(f"전체 계정 상태 조회 실패: {str(e)}")
            return []

    async def auth_orchestrator_shutdown(self):
        """오케스트레이터를 종료하고 리소스를 정리합니다."""
        try:
            # 웹서버 중지
            if self.web_server_manager.is_running:
                await self.web_server_manager.auth_web_server_manager_stop()

            # 모든 세션 정리
            session_count = len(self.auth_sessions)
            self.auth_sessions.clear()

            logger.info(f"Auth 오케스트레이터 종료: {session_count}개 세션 정리됨")

        except Exception as e:
            logger.error(f"오케스트레이터 종료 실패: {str(e)}")

    def _find_session_by_id(self, session_id: str) -> Optional[AuthSession]:
        """세션 ID로 세션을 찾습니다."""
        for session in self.auth_sessions.values():
            if session.session_id == session_id:
                return session
        return None

    def _find_pending_session_by_user(self, user_id: str) -> Optional[AuthSession]:
        """사용자 ID로 진행 중인 세션을 찾습니다."""
        for session in self.auth_sessions.values():
            if session.user_id == user_id and session.is_pending():
                return session
        return None

    def _cleanup_session(self, state: str):
        """세션을 정리합니다."""
        if state in self.auth_sessions:
            session = self.auth_sessions[state]
            auth_log_session_activity(
                session.session_id, "session_expired", {"user_id": session.user_id}
            )
            del self.auth_sessions[state]

    def _parse_delegated_permissions(
        self, delegated_permissions: Optional[str]
    ) -> List[str]:
        """
        데이터베이스의 delegated_permissions 문자열을 파싱하여 스코프 리스트로 변환합니다.

        Args:
            delegated_permissions: 데이터베이스의 delegated_permissions 문자열

        Returns:
            스코프 리스트
        """
        if not delegated_permissions:
            # 기본 스코프 반환 - 간단한 권한만 요청
            return ["Mail.ReadWrite", "Mail.Send", "offline_access"]

        try:
            # JSON 형태로 저장된 경우
            import json

            if delegated_permissions.strip().startswith("["):
                scopes = json.loads(delegated_permissions)
                if isinstance(scopes, list):
                    # offline_access가 없으면 추가
                    if "offline_access" not in scopes:
                        scopes.append("offline_access")
                    return scopes

            # 쉼표로 구분된 문자열인 경우
            if "," in delegated_permissions:
                scopes = [scope.strip() for scope in delegated_permissions.split(",")]
                scopes = [scope for scope in scopes if scope]
            # 공백으로 구분된 문자열인 경우
            elif " " in delegated_permissions:
                scopes = [scope.strip() for scope in delegated_permissions.split()]
                scopes = [scope for scope in scopes if scope]
            # 단일 스코프인 경우
            else:
                scopes = [delegated_permissions.strip()]

            # offline_access가 없으면 추가
            if "offline_access" not in scopes:
                scopes.append("offline_access")

            return scopes

        except Exception as e:
            logger.warning(
                f"delegated_permissions 파싱 실패: {delegated_permissions}, error={str(e)}"
            )
            # 파싱 실패 시 기본 스코프 반환
            return ["Mail.ReadWrite", "Mail.Send", "offline_access"]

    async def _get_account_oauth_config(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        계정별 OAuth 설정을 데이터베이스에서 가져옵니다.

        Args:
            user_id: 사용자 ID

        Returns:
            OAuth 설정 딕셔너리 또는 None
        """
        try:
            logger.debug(f"계정별 OAuth 설정 조회 시도: user_id={user_id}")

            account = self.db.fetch_one(
                """
                SELECT oauth_client_id, oauth_client_secret, oauth_tenant_id, oauth_redirect_uri, delegated_permissions
                FROM accounts 
                WHERE user_id = ? AND is_active = 1
                """,
                (user_id,),
            )

            if not account:
                logger.debug(f"계정을 찾을 수 없음: user_id={user_id}")
                return None

            account_dict = dict(account)
            logger.debug(f"조회된 계정 정보: {list(account_dict.keys())}")

            # OAuth 클라이언트 ID가 있는지 확인
            oauth_client_id = account_dict.get("oauth_client_id")
            oauth_client_secret = account_dict.get("oauth_client_secret")

            if not oauth_client_id:
                logger.debug(f"계정별 OAuth 설정이 없음: user_id={user_id}")
                return None

            # 필수 필드 검증
            if not oauth_client_id.strip():
                logger.debug(f"oauth_client_id가 비어있음: user_id={user_id}")
                return None

            # oauth_client_secret 복호화
            if oauth_client_secret:
                try:
                    crypto_helper = AccountCryptoHelpers()
                    decrypted_secret = crypto_helper.account_decrypt_sensitive_data(
                        oauth_client_secret
                    )
                    account_dict["oauth_client_secret"] = decrypted_secret
                    logger.debug(f"oauth_client_secret 복호화 완료: user_id={user_id}")
                except Exception as decrypt_error:
                    logger.error(
                        f"oauth_client_secret 복호화 실패: user_id={user_id}, error={str(decrypt_error)}"
                    )
                    return None

            logger.info(
                f"계정별 OAuth 설정 발견: user_id={user_id}, client_id={oauth_client_id[:8]}..."
            )
            return account_dict

        except Exception as e:
            logger.error(
                f"계정별 OAuth 설정 조회 실패: user_id={user_id}, error={str(e)}"
            )
            import traceback

            traceback.print_exc()
            return None


# 전역 오케스트레이터 인스턴스
_auth_orchestrator = None


def get_auth_orchestrator() -> AuthOrchestrator:
    """
    Auth 오케스트레이터 인스턴스를 반환합니다.

    Returns:
        AuthOrchestrator 인스턴스
    """
    global _auth_orchestrator
    if _auth_orchestrator is None:
        _auth_orchestrator = AuthOrchestrator()
    return _auth_orchestrator
