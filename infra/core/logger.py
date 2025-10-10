"""
IACSGraph 프로젝트의 구조화된 로깅 시스템

프로젝트 전반에서 사용할 표준화된 로거를 제공합니다.
새로운 logging_config 모듈과 통합하여 일관된 로깅을 제공합니다.
"""

import logging
from typing import Optional

# 새로운 logging_config 모듈 사용
from .logging_config import get_logging_config, get_logger as get_configured_logger


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    IACSGraph 프로젝트용 로거를 반환합니다.

    새로운 logging_config 모듈을 사용하여 일관된 로깅을 제공합니다.

    Args:
        name: 로거 이름 (일반적으로 모듈명)
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        설정된 로거 인스턴스
    """
    return get_configured_logger(name, level)


def configure_root_logger(level: str = "INFO") -> None:
    """
    루트 로거 설정

    Args:
        level: 로그 레벨
    """
    config = get_logging_config()
    config.level = config._parse_level(level)
    config.configure_root_logger()


def update_all_loggers_level(level: str) -> None:
    """
    모든 기존 로거의 레벨을 업데이트

    Args:
        level: 새로운 로그 레벨
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # 루트 로거 업데이트
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    for handler in root_logger.handlers:
        handler.setLevel(log_level)

    # 모든 기존 로거 업데이트
    for name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(name)
        if logger.handlers:  # 핸들러가 있는 로거만 업데이트
            logger.setLevel(log_level)
            for handler in logger.handlers:
                handler.setLevel(log_level)


class LoggerMixin:
    """로거를 사용하는 클래스를 위한 믹스인"""

    @property
    def logger(self) -> logging.Logger:
        """클래스 전용 로거를 반환"""
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__module__)
        return self._logger

    def log_debug(self, message: str, **kwargs) -> None:
        """디버그 메시지 로깅"""
        self.logger.debug(message, **kwargs)

    def log_info(self, message: str, **kwargs) -> None:
        """정보 메시지 로깅"""
        self.logger.info(message, **kwargs)

    def log_warning(self, message: str, **kwargs) -> None:
        """경고 메시지 로깅"""
        self.logger.warning(message, **kwargs)

    def log_error(self, message: str, **kwargs) -> None:
        """오류 메시지 로깅"""
        self.logger.error(message, **kwargs)

    def log_critical(self, message: str, **kwargs) -> None:
        """치명적 오류 메시지 로깅"""
        self.logger.critical(message, **kwargs)