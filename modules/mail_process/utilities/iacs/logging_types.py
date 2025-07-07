"""
로깅 타입 및 포맷 정의
modules/mail_process/utilities/logging_types.py
"""

from enum import Enum
from typing import Dict, Any


class LogLevel(Enum):
    """로그 레벨"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """로그 카테고리"""

    PARSING = "parsing"
    PROCESSING = "processing"
    DATABASE = "database"
    EVENT = "event"
    FILTER = "filter"
    EXTRACTION = "extraction"
    PERFORMANCE = "performance"


class LogFormat:
    """표준화된 로그 포맷"""

    @staticmethod
    def mail_processing(
        category: LogCategory, action: str, mail_id: str, details: Dict[str, Any] = None
    ) -> str:
        """메일 처리 로그 포맷"""
        base_msg = f"[{category.value}] {action} - mail_id: {mail_id}"
        if details:
            detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
            return f"{base_msg}, {detail_str}"
        return base_msg

    @staticmethod
    def batch_processing(
        category: LogCategory,
        action: str,
        account_id: str,
        count: int,
        details: Dict[str, Any] = None,
    ) -> str:
        """배치 처리 로그 포맷"""
        base_msg = (
            f"[{category.value}] {action} - account: {account_id}, count: {count}"
        )
        if details:
            detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
            return f"{base_msg}, {detail_str}"
        return base_msg

    @staticmethod
    def performance(
        operation: str,
        duration_ms: int,
        count: int = None,
        details: Dict[str, Any] = None,
    ) -> str:
        """성능 로그 포맷"""
        base_msg = (
            f"[{LogCategory.PERFORMANCE.value}] {operation} - duration: {duration_ms}ms"
        )
        if count is not None:
            base_msg += f", items: {count}"
        if details:
            detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
            return f"{base_msg}, {detail_str}"
        return base_msg
