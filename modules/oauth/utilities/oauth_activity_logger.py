"""인증 활동 로깅 유틸리티"""

from typing import Optional, Dict, Any
from infra.core.logger import get_logger
from .response_generator import AuthResponseGenerator


class AuthActivityLogger:
    """인증 관련 활동 로깅 유틸리티"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.response_generator = AuthResponseGenerator()

    def log_session_activity(
        self, session_id: str, activity: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        세션 활동을 로깅합니다.

        Args:
            session_id: 세션 ID
            activity: 활동 타입
            details: 추가 세부 정보
        """
        masked_details = self.response_generator.mask_sensitive_data(details or {})

        self.logger.info(
            f"세션 활동 [{session_id[:16]}...]: {activity}",
            extra={
                "session_id": session_id,
                "activity": activity,
                "details": masked_details,
            },
        )

    def calculate_session_timeout(self, user_count: int, base_timeout: int = 10) -> int:
        """
        사용자 수에 따른 적절한 세션 타임아웃을 계산합니다.

        Args:
            user_count: 사용자 수
            base_timeout: 기본 타임아웃(분)

        Returns:
            계산된 타임아웃(분)
        """
        # 사용자가 많을수록 타임아웃을 늘림 (최대 30분)
        calculated_timeout = min(base_timeout + (user_count * 2), 30)
        self.logger.debug(
            f"세션 타임아웃 계산: {user_count}명 → {calculated_timeout}분"
        )
        return calculated_timeout
