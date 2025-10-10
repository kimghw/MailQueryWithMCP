"""
Email Dashboard 모듈

이메일 아젠다 및 응답 관리를 위한 대시보드 기능을 제공합니다.
- 의장 발송 아젠다 관리
- 멤버 기관 응답 관리
- 대시보드 통계 및 현황 조회
- 자동 테이블 초기화
- 이벤트 구독 및 처리

주요 컴포넌트:
- EmailDashboardOrchestrator: 메인 오케스트레이터
- EmailDashboardEventProcessor: 이벤트 처리
- EmailDashboardRepository: 데이터베이스 접근
- EmailDashboardQuery: 대시보드 조회 기능
- EmailDashboardService: 모듈 서비스 관리
"""

from infra.core.logger import get_logger



logger = get_logger(__name__)

# 안전한 import를 위한 예외 처리
try:
    # 핵심 인프라 컴포넌트 import
    from .config import config, get_config
    from .database import db, get_database_manager
    from .exceptions import (
        APIConnectionError,
        AuthenticationError,
        BusinessLogicError,
        ConfigurationError,
        ConnectionError,
        DatabaseError,
        IACSGraphError,
        KafkaConnectionError,
        KafkaConsumerError,
        KafkaError,
        KafkaProducerError,
        TokenError,
        TokenExpiredError,
        TokenRefreshError,
        ValidationError,
    )
    from .kafka_client import get_kafka_client, kafka_client
    from .logger import get_logger
    from .oauth_client import get_oauth_client, oauth_client
    from .token_service import get_token_service, token_service

except ImportError as e:
    logger.info(f"Infra core 모듈 import 오류: {e}")
    logger.info("의존성 확인:")
    logger.info("1. infra.core 모듈이 올바르게 설정되었는지 확인")
    logger.info("2. 프로젝트 루트에서 실행하고 있는지 확인")
    logger.info("3. PYTHONPATH가 올바르게 설정되었는지 확인")
    raise

__all__ = [
    # Configuration
    "get_config",
    "config",
    # Database
    "get_database_manager",
    "db",
    # Logging
    "get_logger",
    # Exceptions
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
    "ValidationError",
    "BusinessLogicError",
    # Kafka
    "get_kafka_client",
    "kafka_client",
    # OAuth
    "get_oauth_client",
    "oauth_client",
    # Token Service
    "get_token_service",
    "token_service",
]
