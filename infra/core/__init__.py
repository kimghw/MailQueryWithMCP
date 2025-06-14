"""
IACSGraph 프로젝트의 핵심 인프라 컴포넌트

이 모듈은 프로젝트 전반에서 사용되는 핵심 인프라 컴포넌트들을 제공합니다:
- 설정 관리 (Config)
- 데이터베이스 관리 (DatabaseManager)
- Kafka 클라이언트 (KafkaClient)
- OAuth 클라이언트 (OAuthClient)
- 토큰 서비스 (TokenService)
- 로깅 시스템 (Logger)
- 예외 클래스들 (Exceptions)
"""

# 설정 관리
from .config import Config, get_config, config

# 데이터베이스 관리
from .database import DatabaseManager, get_database_manager, db

# Kafka 클라이언트
from .kafka_client import KafkaClient, get_kafka_client, kafka_client

# OAuth 클라이언트
from .oauth_client import OAuthClient, get_oauth_client, oauth_client

# 토큰 서비스
from .token_service import TokenService, get_token_service, token_service

# 로깅 시스템
from .logger import (
    get_logger,
    configure_root_logger,
    update_all_loggers_level,
    LoggerMixin,
    log_function_call,
    log_error,
    log_performance
)

# 예외 클래스들
from .exceptions import (
    # 기본 예외
    IACSGraphError,
    
    # 데이터베이스 예외
    DatabaseError,
    ConnectionError,
    
    # Kafka 예외
    KafkaError,
    KafkaConnectionError,
    KafkaProducerError,
    KafkaConsumerError,
    
    # API 연결 예외
    APIConnectionError,
    
    # 인증 예외
    AuthenticationError,
    TokenError,
    TokenExpiredError,
    TokenRefreshError,
    
    # 설정 예외
    ConfigurationError,
    
    # 검증 예외
    ValidationError
)

# 편의를 위한 전역 인스턴스들
__all__ = [
    # 설정
    "Config",
    "get_config", 
    "config",
    
    # 데이터베이스
    "DatabaseManager",
    "get_database_manager",
    "db",
    
    # Kafka
    "KafkaClient",
    "get_kafka_client", 
    "kafka_client",
    
    # OAuth
    "OAuthClient",
    "get_oauth_client",
    "oauth_client",
    
    # 토큰 서비스
    "TokenService",
    "get_token_service",
    "token_service",
    
    # 로깅
    "get_logger",
    "configure_root_logger",
    "update_all_loggers_level",
    "LoggerMixin",
    "log_function_call",
    "log_error", 
    "log_performance",
    
    # 예외
    "IACSGraphError",
    "DatabaseError",
    "ConnectionError",
    "KafkaError",
    "KafkaConnectionError", 
    "KafkaProducerError",
    "KafkaConsumerError",
    "APIConnectionError",
    "AuthenticationError",
    "TokenError",
    "TokenExpiredError",
    "TokenRefreshError",
    "ConfigurationError",
    "ValidationError"
]

# 모듈 정보
__version__ = "1.0.0"
__author__ = "IACSGraph Team"
__description__ = "IACSGraph 프로젝트의 핵심 인프라 컴포넌트"

# 모듈 로드 시 기본 설정 적용
try:
    # 설정 로드 및 검증
    _config = get_config()
    
    # 로그 레벨 설정
    configure_root_logger(_config.log_level)
    
    # 로거 생성
    _logger = get_logger(__name__)
    _logger.info(f"IACSGraph 핵심 인프라 모듈 로드 완료 (v{__version__})")
    _logger.debug(f"환경: {_config.environment}, 로그 레벨: {_config.log_level}")
    
except Exception as e:
    # 기본 로깅으로 폴백
    import logging
    logging.basicConfig(level=logging.INFO)
    logging.getLogger(__name__).error(f"인프라 모듈 초기화 실패: {e}")
