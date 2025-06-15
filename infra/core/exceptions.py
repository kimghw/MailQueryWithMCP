"""
IACSGraph 프로젝트의 표준 예외 클래스 정의

프로젝트 전반에서 사용할 구조화된 예외 계층을 제공합니다.
모든 사용자 정의 예외는 IACSGraphError를 상속받습니다.
"""

from typing import Optional, Dict, Any


class IACSGraphError(Exception):
    """IACSGraph 프로젝트의 최상위 예외 클래스"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """예외 정보를 딕셔너리로 반환"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
        }


class DatabaseError(IACSGraphError):
    """데이터베이스 관련 오류"""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        table: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if operation:
            details["operation"] = operation
        if table:
            details["table"] = table
        
        super().__init__(
            message=message,
            error_code=kwargs.get("error_code", "DB_ERROR"),
            details=details,
        )


class ConnectionError(DatabaseError):
    """데이터베이스 연결 오류"""

    def __init__(self, message: str = "데이터베이스 연결에 실패했습니다", **kwargs):
        super().__init__(
            message=message,
            error_code=kwargs.get("error_code", "DB_CONNECTION_ERROR"),
            **kwargs
        )


class KafkaError(IACSGraphError):
    """Kafka 관련 오류"""

    def __init__(
        self,
        message: str,
        topic: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if topic:
            details["topic"] = topic
        if operation:
            details["operation"] = operation
            
        super().__init__(
            message=message,
            error_code=kwargs.get("error_code", "KAFKA_ERROR"),
            details=details,
        )


class KafkaConnectionError(KafkaError):
    """Kafka 연결 오류"""

    def __init__(self, message: str = "Kafka 클러스터에 연결할 수 없습니다", **kwargs):
        super().__init__(
            message=message,
            error_code=kwargs.get("error_code", "KAFKA_CONNECTION_ERROR"),
            **kwargs
        )


class KafkaProducerError(KafkaError):
    """Kafka Producer 오류"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=kwargs.get("error_code", "KAFKA_PRODUCER_ERROR"),
            operation="produce",
            **kwargs
        )


class KafkaConsumerError(KafkaError):
    """Kafka Consumer 오류"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=kwargs.get("error_code", "KAFKA_CONSUMER_ERROR"),
            operation="consume",
            **kwargs
        )


class APIConnectionError(IACSGraphError):
    """외부 API 연결 오류"""

    def __init__(
        self,
        message: str,
        api_endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if api_endpoint:
            details["api_endpoint"] = api_endpoint
        if status_code:
            details["status_code"] = status_code
            
        super().__init__(
            message=message,
            error_code=kwargs.get("error_code", "API_CONNECTION_ERROR"),
            details=details,
        )


class AuthenticationError(IACSGraphError):
    """인증 관련 오류"""

    def __init__(
        self,
        message: str,
        auth_type: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if auth_type:
            details["auth_type"] = auth_type
            
        super().__init__(
            message=message,
            error_code=kwargs.get("error_code", "AUTH_ERROR"),
            details=details,
        )


class TokenError(AuthenticationError):
    """토큰 관련 오류"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=kwargs.get("error_code", "TOKEN_ERROR"),
            auth_type="oauth",
            **kwargs
        )


class TokenExpiredError(TokenError):
    """토큰 만료 오류"""

    def __init__(self, message: str = "액세스 토큰이 만료되었습니다", **kwargs):
        super().__init__(
            message=message,
            error_code=kwargs.get("error_code", "TOKEN_EXPIRED"),
            **kwargs
        )


class TokenRefreshError(TokenError):
    """토큰 갱신 오류"""

    def __init__(self, message: str = "토큰 갱신에 실패했습니다", **kwargs):
        super().__init__(
            message=message,
            error_code=kwargs.get("error_code", "TOKEN_REFRESH_ERROR"),
            **kwargs
        )


class ConfigurationError(IACSGraphError):
    """설정 관련 오류"""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if config_key:
            details["config_key"] = config_key
            
        super().__init__(
            message=message,
            error_code=kwargs.get("error_code", "CONFIG_ERROR"),
            details=details,
        )


class ValidationError(IACSGraphError):
    """데이터 검증 오류"""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
            
        super().__init__(
            message=message,
            error_code=kwargs.get("error_code", "VALIDATION_ERROR"),
            details=details,
        )


class BusinessLogicError(IACSGraphError):
    """비즈니스 로직 관련 오류"""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if operation:
            details["operation"] = operation
            
        super().__init__(
            message=message,
            error_code=kwargs.get("error_code", "BUSINESS_LOGIC_ERROR"),
            details=details,
        )
