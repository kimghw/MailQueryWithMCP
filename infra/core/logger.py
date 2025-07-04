"""
IACSGraph 프로젝트의 구조화된 로깅 시스템

프로젝트 전반에서 사용할 표준화된 로거를 제공합니다.
로그 레벨은 환경 설정에 따라 동적으로 조정됩니다.
"""

import logging
import sys
from datetime import datetime
from functools import lru_cache
from typing import Optional


class IACSGraphFormatter(logging.Formatter):
    """IACSGraph 프로젝트 전용 로그 포매터"""

    def __init__(self):
        super().__init__()
        self.fmt = "[{asctime}] {levelname:8} | {name:25} | {message}"
        self.style = "{"

    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드를 포맷팅"""
        # 타임스탬프 형식 설정
        record.asctime = datetime.fromtimestamp(record.created).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # 모듈명이 너무 길면 축약
        if len(record.name) > 25:
            parts = record.name.split(".")
            if len(parts) > 2:
                record.name = f"{parts[0]}...{parts[-1]}"

        return super().format(record)


@lru_cache(maxsize=None)
def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    IACSGraph 프로젝트용 로거를 반환합니다.

    Args:
        name: 로거 이름 (일반적으로 모듈명)
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        설정된 로거 인스턴스
    """
    logger = logging.getLogger(name)

    # 이미 핸들러가 설정되어 있으면 반환
    if logger.handlers:
        if level:
            logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        return logger

    # 로그 레벨 설정
    log_level = getattr(logging, (level or "INFO").upper(), logging.INFO)
    logger.setLevel(log_level)

    # 콘솔 핸들러 생성
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(IACSGraphFormatter())

    # 핸들러 추가
    logger.addHandler(console_handler)

    # 중복 로그 방지
    logger.propagate = False

    return logger


def configure_root_logger(level: str = "INFO") -> None:
    """
    루트 로거 설정

    Args:
        level: 로그 레벨
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 새 핸들러 추가
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    console_handler.setFormatter(IACSGraphFormatter())
    root_logger.addHandler(console_handler)


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
        """클래스명을 기반으로 로거를 반환"""
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__module__)
        return self._logger


# 기본 로거 설정
_default_logger = get_logger("iacsgraph")


def log_function_call(func_name: str, args: tuple = (), kwargs: dict = None) -> None:
    """함수 호출을 로그에 기록"""
    kwargs = kwargs or {}
    args_str = ", ".join([repr(arg) for arg in args])
    kwargs_str = ", ".join([f"{k}={repr(v)}" for k, v in kwargs.items()])

    all_args = []
    if args_str:
        all_args.append(args_str)
    if kwargs_str:
        all_args.append(kwargs_str)

    args_combined = ", ".join(all_args)
    _default_logger.debug(f"함수 호출: {func_name}({args_combined})")


def log_error(error: Exception, context: str = "") -> None:
    """에러를 구조화된 형태로 로그에 기록"""
    error_info = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context,
    }

    # IACSGraphError인 경우 추가 정보 포함
    if hasattr(error, "to_dict"):
        error_info.update(error.to_dict())

    _default_logger.error(f"오류 발생: {error_info}")


def log_performance(operation: str, duration: float, **kwargs) -> None:
    """성능 관련 정보를 로그에 기록"""
    perf_info = {
        "operation": operation,
        "duration_ms": round(duration * 1000, 2),
        **kwargs,
    }
    _default_logger.info(f"성능 측정: {perf_info}")
