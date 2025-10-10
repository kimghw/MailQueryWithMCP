"""
표준화된 에러 메시지 시스템

일관된 에러 메시지 형식과 사용자 친화적인 오류 보고를 제공합니다.
"""

from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(Enum):
    """표준 에러 코드"""

    # 설정 관련 (1000번대)
    CONFIG_MISSING = 1001
    CONFIG_INVALID = 1002
    ENV_VAR_MISSING = 1003
    ENV_VAR_INVALID = 1004

    # 인증 관련 (2000번대)
    AUTH_FAILED = 2001
    AUTH_TOKEN_EXPIRED = 2002
    AUTH_TOKEN_INVALID = 2003
    AUTH_REFRESH_FAILED = 2004
    AUTH_ACCOUNT_NOT_FOUND = 2005
    AUTH_ACCOUNT_INACTIVE = 2006

    # 데이터베이스 관련 (3000번대)
    DB_CONNECTION_FAILED = 3001
    DB_QUERY_FAILED = 3002
    DB_TRANSACTION_FAILED = 3003
    DB_INTEGRITY_ERROR = 3004
    DB_NOT_FOUND = 3005

    # API 관련 (4000번대)
    API_REQUEST_FAILED = 4001
    API_RESPONSE_INVALID = 4002
    API_RATE_LIMITED = 4003
    API_UNAUTHORIZED = 4004
    API_FORBIDDEN = 4005
    API_NOT_FOUND = 4006
    API_SERVER_ERROR = 4007

    # 파일 처리 관련 (5000번대)
    FILE_NOT_FOUND = 5001
    FILE_READ_ERROR = 5002
    FILE_WRITE_ERROR = 5003
    FILE_FORMAT_INVALID = 5004
    FILE_TOO_LARGE = 5005
    FILE_CONVERSION_FAILED = 5006

    # 메일 처리 관련 (6000번대)
    MAIL_QUERY_FAILED = 6001
    MAIL_PARSE_FAILED = 6002
    MAIL_ATTACHMENT_FAILED = 6003
    MAIL_FILTER_ERROR = 6004
    MAIL_SAVE_FAILED = 6005

    # MCP 서버 관련 (7000번대)
    MCP_INIT_FAILED = 7001
    MCP_HANDLER_ERROR = 7002
    MCP_TOOL_NOT_FOUND = 7003
    MCP_TOOL_EXECUTION_FAILED = 7004
    MCP_SESSION_ERROR = 7005

    # 일반 오류 (9000번대)
    UNKNOWN_ERROR = 9999
    VALIDATION_ERROR = 9001
    TIMEOUT_ERROR = 9002
    NETWORK_ERROR = 9003


class ErrorMessage:
    """표준화된 에러 메시지"""

    # 에러 메시지 템플릿
    TEMPLATES = {
        # 설정 관련
        ErrorCode.CONFIG_MISSING: "필수 설정이 누락되었습니다: {config_name}",
        ErrorCode.CONFIG_INVALID: "잘못된 설정값입니다: {config_name} = {value}",
        ErrorCode.ENV_VAR_MISSING: "필수 환경변수가 설정되지 않았습니다: {var_name}",
        ErrorCode.ENV_VAR_INVALID: "환경변수 값이 유효하지 않습니다: {var_name} = {value}",

        # 인증 관련
        ErrorCode.AUTH_FAILED: "인증에 실패했습니다: {reason}",
        ErrorCode.AUTH_TOKEN_EXPIRED: "토큰이 만료되었습니다. 재인증이 필요합니다.",
        ErrorCode.AUTH_TOKEN_INVALID: "유효하지 않은 토큰입니다.",
        ErrorCode.AUTH_REFRESH_FAILED: "토큰 갱신에 실패했습니다: {reason}",
        ErrorCode.AUTH_ACCOUNT_NOT_FOUND: "계정을 찾을 수 없습니다: {user_id}",
        ErrorCode.AUTH_ACCOUNT_INACTIVE: "비활성화된 계정입니다: {user_id}",

        # 데이터베이스 관련
        ErrorCode.DB_CONNECTION_FAILED: "데이터베이스 연결에 실패했습니다: {reason}",
        ErrorCode.DB_QUERY_FAILED: "쿼리 실행에 실패했습니다: {query}",
        ErrorCode.DB_TRANSACTION_FAILED: "트랜잭션 처리 중 오류가 발생했습니다",
        ErrorCode.DB_INTEGRITY_ERROR: "데이터 무결성 오류: {reason}",
        ErrorCode.DB_NOT_FOUND: "데이터를 찾을 수 없습니다: {entity}",

        # API 관련
        ErrorCode.API_REQUEST_FAILED: "API 요청에 실패했습니다: {endpoint}",
        ErrorCode.API_RESPONSE_INVALID: "잘못된 API 응답 형식입니다",
        ErrorCode.API_RATE_LIMITED: "API 요청 제한에 도달했습니다. 잠시 후 다시 시도해주세요.",
        ErrorCode.API_UNAUTHORIZED: "API 인증에 실패했습니다",
        ErrorCode.API_FORBIDDEN: "API 접근 권한이 없습니다",
        ErrorCode.API_NOT_FOUND: "API 엔드포인트를 찾을 수 없습니다: {endpoint}",
        ErrorCode.API_SERVER_ERROR: "API 서버 오류가 발생했습니다: {status_code}",

        # 파일 처리 관련
        ErrorCode.FILE_NOT_FOUND: "파일을 찾을 수 없습니다: {file_path}",
        ErrorCode.FILE_READ_ERROR: "파일 읽기에 실패했습니다: {file_path}",
        ErrorCode.FILE_WRITE_ERROR: "파일 쓰기에 실패했습니다: {file_path}",
        ErrorCode.FILE_FORMAT_INVALID: "지원하지 않는 파일 형식입니다: {format}",
        ErrorCode.FILE_TOO_LARGE: "파일 크기가 너무 큽니다: {size}MB (최대: {max_size}MB)",
        ErrorCode.FILE_CONVERSION_FAILED: "파일 변환에 실패했습니다: {file_name}",

        # 메일 처리 관련
        ErrorCode.MAIL_QUERY_FAILED: "메일 조회에 실패했습니다: {reason}",
        ErrorCode.MAIL_PARSE_FAILED: "메일 파싱에 실패했습니다: {mail_id}",
        ErrorCode.MAIL_ATTACHMENT_FAILED: "첨부파일 처리에 실패했습니다: {file_name}",
        ErrorCode.MAIL_FILTER_ERROR: "메일 필터링 중 오류가 발생했습니다",
        ErrorCode.MAIL_SAVE_FAILED: "메일 저장에 실패했습니다: {reason}",

        # MCP 서버 관련
        ErrorCode.MCP_INIT_FAILED: "MCP 서버 초기화에 실패했습니다: {reason}",
        ErrorCode.MCP_HANDLER_ERROR: "MCP 핸들러 처리 중 오류: {method}",
        ErrorCode.MCP_TOOL_NOT_FOUND: "MCP 도구를 찾을 수 없습니다: {tool_name}",
        ErrorCode.MCP_TOOL_EXECUTION_FAILED: "MCP 도구 실행에 실패했습니다: {tool_name}",
        ErrorCode.MCP_SESSION_ERROR: "MCP 세션 오류: {session_id}",

        # 일반 오류
        ErrorCode.UNKNOWN_ERROR: "알 수 없는 오류가 발생했습니다",
        ErrorCode.VALIDATION_ERROR: "입력값 검증에 실패했습니다: {field}",
        ErrorCode.TIMEOUT_ERROR: "요청 시간이 초과되었습니다",
        ErrorCode.NETWORK_ERROR: "네트워크 연결 오류가 발생했습니다",
    }

    # 사용자 친화적 메시지
    USER_FRIENDLY_MESSAGES = {
        ErrorCode.CONFIG_MISSING: "설정 파일을 확인해주세요.",
        ErrorCode.ENV_VAR_MISSING: ".env 파일을 확인하고 필요한 환경변수를 설정해주세요.",
        ErrorCode.AUTH_TOKEN_EXPIRED: "다시 로그인해주세요.",
        ErrorCode.DB_CONNECTION_FAILED: "데이터베이스 서버 상태를 확인해주세요.",
        ErrorCode.API_RATE_LIMITED: "너무 많은 요청을 보냈습니다. 잠시 후 다시 시도해주세요.",
        ErrorCode.FILE_TOO_LARGE: "더 작은 파일을 선택해주세요.",
        ErrorCode.MAIL_QUERY_FAILED: "메일 서버 연결을 확인해주세요.",
        ErrorCode.TIMEOUT_ERROR: "네트워크 연결을 확인하고 다시 시도해주세요.",
    }

    @classmethod
    def format(
        cls,
        code: ErrorCode,
        context: Optional[Dict[str, Any]] = None,
        include_code: bool = True,
        user_friendly: bool = False
    ) -> str:
        """
        에러 메시지 포맷팅

        Args:
            code: 에러 코드
            context: 메시지 포맷팅용 컨텍스트
            include_code: 에러 코드 포함 여부
            user_friendly: 사용자 친화적 메시지 사용 여부

        Returns:
            포맷된 에러 메시지
        """
        # 기본 메시지 가져오기
        template = cls.TEMPLATES.get(code, "오류가 발생했습니다")

        # 컨텍스트로 메시지 포맷팅
        try:
            message = template.format(**(context or {}))
        except KeyError:
            message = template

        # 에러 코드 포함
        if include_code:
            message = f"[{code.name}] {message}"

        # 사용자 친화적 메시지 추가
        if user_friendly and code in cls.USER_FRIENDLY_MESSAGES:
            message += f"\n💡 {cls.USER_FRIENDLY_MESSAGES[code]}"

        return message

    @classmethod
    def get_details(
        cls,
        code: ErrorCode,
        exception: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        상세한 에러 정보 생성

        Args:
            code: 에러 코드
            exception: 원본 예외
            context: 추가 컨텍스트

        Returns:
            에러 상세 정보 딕셔너리
        """
        details = {
            "code": code.value,
            "name": code.name,
            "message": cls.format(code, context, include_code=False),
            "category": cls._get_category(code),
        }

        if exception:
            details["exception"] = {
                "type": type(exception).__name__,
                "message": str(exception),
            }

        if context:
            details["context"] = context

        return details

    @staticmethod
    def _get_category(code: ErrorCode) -> str:
        """에러 코드의 카테고리 반환"""
        code_value = code.value

        if 1000 <= code_value < 2000:
            return "CONFIG"
        elif 2000 <= code_value < 3000:
            return "AUTH"
        elif 3000 <= code_value < 4000:
            return "DATABASE"
        elif 4000 <= code_value < 5000:
            return "API"
        elif 5000 <= code_value < 6000:
            return "FILE"
        elif 6000 <= code_value < 7000:
            return "MAIL"
        elif 7000 <= code_value < 8000:
            return "MCP"
        else:
            return "GENERAL"


class StandardError(Exception):
    """표준 에러 클래스"""

    def __init__(
        self,
        code: ErrorCode,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        표준 에러 초기화

        Args:
            code: 에러 코드
            context: 에러 컨텍스트
            original_exception: 원본 예외
        """
        self.code = code
        self.context = context or {}
        self.original_exception = original_exception

        # 메시지 생성
        message = ErrorMessage.format(code, context, include_code=True)
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """에러 정보를 딕셔너리로 변환"""
        return ErrorMessage.get_details(
            self.code,
            self.original_exception,
            self.context
        )

    def get_user_message(self) -> str:
        """사용자 친화적 메시지 반환"""
        return ErrorMessage.format(
            self.code,
            self.context,
            include_code=False,
            user_friendly=True
        )


# 특정 도메인별 에러 클래스
class ConfigError(StandardError):
    """설정 관련 에러"""

    def __init__(self, message: str, **context):
        super().__init__(ErrorCode.CONFIG_INVALID, context)


class AuthError(StandardError):
    """인증 관련 에러"""

    def __init__(self, code: ErrorCode = ErrorCode.AUTH_FAILED, **context):
        super().__init__(code, context)


class DatabaseError(StandardError):
    """데이터베이스 관련 에러"""

    def __init__(self, code: ErrorCode = ErrorCode.DB_QUERY_FAILED, **context):
        super().__init__(code, context)


class APIError(StandardError):
    """API 관련 에러"""

    def __init__(self, code: ErrorCode = ErrorCode.API_REQUEST_FAILED, **context):
        super().__init__(code, context)


class FileError(StandardError):
    """파일 처리 관련 에러"""

    def __init__(self, code: ErrorCode = ErrorCode.FILE_READ_ERROR, **context):
        super().__init__(code, context)


class MailError(StandardError):
    """메일 처리 관련 에러"""

    def __init__(self, code: ErrorCode = ErrorCode.MAIL_QUERY_FAILED, **context):
        super().__init__(code, context)


class MCPError(StandardError):
    """MCP 서버 관련 에러"""

    def __init__(self, code: ErrorCode = ErrorCode.MCP_HANDLER_ERROR, **context):
        super().__init__(code, context)