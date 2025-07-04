"""
Auth 모듈의 OAuth 전용 헬퍼 함수들

OAuth 플로우 관리를 위한 유틸리티 함수들을 제공합니다.
메모리 세션 관리, ID 생성, 상태 검증 등의 기능을 포함합니다.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from infra.core.logger import get_logger

logger = get_logger(__name__)


def auth_generate_session_id(user_id: str) -> str:
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
    logger.debug(f"세션 ID 생성: {session_id}")
    return session_id


def auth_generate_state_token() -> str:
    """
    CSRF 방지용 상태 토큰을 생성합니다.

    Returns:
        상태 토큰
    """
    state_token = secrets.token_urlsafe(32)
    logger.debug(f"상태 토큰 생성: {state_token[:10]}...")
    return state_token


def auth_validate_callback_url(callback_url: str, expected_redirect_uri: str) -> bool:
    """
    OAuth 콜백 URL의 유효성을 검증합니다.

    Args:
        callback_url: 수신된 콜백 URL
        expected_redirect_uri: 예상 리다이렉트 URI

    Returns:
        유효성 여부
    """
    try:
        callback_parsed = urlparse(callback_url)
        expected_parsed = urlparse(expected_redirect_uri)

        # 스키마, 호스트, 포트, 경로가 일치하는지 확인
        return (
            callback_parsed.scheme == expected_parsed.scheme
            and callback_parsed.netloc == expected_parsed.netloc
            and callback_parsed.path == expected_parsed.path
        )
    except Exception as e:
        logger.error(f"콜백 URL 검증 실패: {str(e)}")
        return False


def auth_parse_callback_params(callback_url: str) -> Dict[str, str]:
    """
    OAuth 콜백 URL에서 매개변수를 파싱합니다.

    Args:
        callback_url: 콜백 URL

    Returns:
        파싱된 매개변수 딕셔너리
    """
    try:
        parsed_url = urlparse(callback_url)
        params = parse_qs(parsed_url.query)

        # 단일 값으로 변환
        result = {}
        for key, value_list in params.items():
            if value_list:
                result[key] = value_list[0]

        logger.debug(f"콜백 매개변수 파싱: {list(result.keys())}")
        return result
    except Exception as e:
        logger.error(f"콜백 매개변수 파싱 실패: {str(e)}")
        return {}


def auth_sanitize_user_id(user_id: str) -> str:
    """
    사용자 ID를 정리하고 유효성을 검증합니다.

    Args:
        user_id: 원본 사용자 ID

    Returns:
        정리된 사용자 ID
    """
    if not user_id or not isinstance(user_id, str):
        raise ValueError("사용자 ID가 유효하지 않습니다")

    # 공백 제거 및 소문자 변환
    sanitized = user_id.strip().lower()

    # 이메일 형식인지 확인 (간단한 검증)
    if "@" in sanitized and "." in sanitized:
        return sanitized

    # 일반 문자열인 경우 영숫자와 일부 특수문자만 허용
    allowed_chars = set("abcdefghijklmnopqrstuvwxyz0123456789.-_")
    if all(c in allowed_chars for c in sanitized):
        return sanitized

    raise ValueError(f"사용자 ID 형식이 유효하지 않습니다: {user_id}")


def auth_create_session_expiry(minutes: int = 10) -> datetime:
    """
    세션 만료 시간을 생성합니다.

    Args:
        minutes: 만료까지의 분

    Returns:
        만료 시간
    """
    expiry_time = datetime.utcnow() + timedelta(minutes=minutes)
    logger.debug(f"세션 만료 시간 설정: {expiry_time.isoformat()}")
    return expiry_time


def auth_format_error_message(error: str, description: Optional[str] = None) -> str:
    """
    OAuth 오류 메시지를 포맷팅합니다.

    Args:
        error: 오류 코드
        description: 오류 설명

    Returns:
        포맷팅된 오류 메시지
    """
    error_messages = {
        "access_denied": "사용자가 인증을 거부했습니다",
        "invalid_request": "잘못된 인증 요청입니다",
        "unauthorized_client": "클라이언트 인증에 실패했습니다",
        "unsupported_response_type": "지원하지 않는 응답 타입입니다",
        "invalid_scope": "잘못된 권한 범위입니다",
        "server_error": "인증 서버 오류가 발생했습니다",
        "temporarily_unavailable": "인증 서비스가 일시적으로 사용할 수 없습니다",
    }

    base_message = error_messages.get(error, f"알 수 없는 오류: {error}")

    if description:
        return f"{base_message} - {description}"

    return base_message


def auth_validate_token_info(token_info: Dict[str, Any]) -> bool:
    """
    토큰 정보의 유효성을 검증합니다.

    Args:
        token_info: 토큰 정보

    Returns:
        유효성 여부
    """
    required_fields = ["access_token", "refresh_token", "expires_in"]

    for field in required_fields:
        if field not in token_info or not token_info[field]:
            logger.warning(f"토큰 정보에 필수 필드가 없음: {field}")
            return False

    # 만료 시간 검증
    expires_in = token_info.get("expires_in")
    if not isinstance(expires_in, int) or expires_in <= 0:
        logger.warning(f"잘못된 expires_in 값: {expires_in}")
        return False

    return True


def auth_mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    민감한 데이터를 마스킹합니다.

    Args:
        data: 원본 데이터

    Returns:
        마스킹된 데이터
    """
    masked = data.copy()
    sensitive_fields = ["access_token", "refresh_token", "client_secret", "password"]

    for field in sensitive_fields:
        if field in masked and masked[field]:
            value = str(masked[field])
            if len(value) > 8:
                masked[field] = f"{value[:4]}...{value[-4:]}"
            else:
                masked[field] = "***"

    return masked


def auth_calculate_session_timeout(user_count: int, base_timeout: int = 10) -> int:
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
    logger.debug(f"세션 타임아웃 계산: {user_count}명 → {calculated_timeout}분")
    return calculated_timeout


def auth_generate_callback_success_html(user_id: str, session_id: str) -> str:
    """
    OAuth 콜백 성공 페이지 HTML을 생성합니다.

    Args:
        user_id: 사용자 ID
        session_id: 세션 ID

    Returns:
        HTML 문자열
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>인증 완료</title>
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
            .success {{ color: #4CAF50; }}
            .info {{ color: #2196F3; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <h1 class="success">✓ 인증이 완료되었습니다</h1>
        <div class="info">
            <p><strong>사용자:</strong> {user_id}</p>
            <p><strong>세션:</strong> {session_id[:16]}...</p>
            <p>이제 이 창을 닫으셔도 됩니다.</p>
        </div>
        <script>
            // 3초 후 자동으로 창 닫기
            setTimeout(function() {{
                if (window.opener) {{
                    window.close();
                }}
            }}, 3000);
        </script>
    </body>
    </html>
    """


def auth_generate_callback_error_html(
    error: str, description: Optional[str] = None
) -> str:
    """
    OAuth 콜백 오류 페이지 HTML을 생성합니다.

    Args:
        error: 오류 코드
        description: 오류 설명

    Returns:
        HTML 문자열
    """
    error_message = auth_format_error_message(error, description)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>인증 실패</title>
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
            .error {{ color: #f44336; }}
            .info {{ color: #666; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <h1 class="error">✗ 인증에 실패했습니다</h1>
        <div class="info">
            <p><strong>오류:</strong> {error_message}</p>
            <p>다시 시도해 주세요.</p>
        </div>
        <script>
            // 5초 후 자동으로 창 닫기
            setTimeout(function() {{
                if (window.opener) {{
                    window.close();
                }}
            }}, 5000);
        </script>
    </body>
    </html>
    """


def auth_log_session_activity(
    session_id: str, activity: str, details: Optional[Dict[str, Any]] = None
):
    """
    세션 활동을 로깅합니다.

    Args:
        session_id: 세션 ID
        activity: 활동 타입
        details: 추가 세부 정보
    """
    masked_details = auth_mask_sensitive_data(details or {})
    logger.info(
        f"세션 활동 [{session_id[:16]}...]: {activity}",
        extra={
            "session_id": session_id,
            "activity": activity,
            "details": masked_details,
        },
    )
