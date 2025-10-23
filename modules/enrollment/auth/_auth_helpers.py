"""
Auth 모듈의 OAuth 전용 헬퍼 함수들

OAuth 플로우 관리를 위한 유틸리티 함수들을 제공합니다.
메모리 세션 관리, ID 생성, 상태 검증 등의 기능을 포함합니다.
"""

import hashlib
import platform
import re
import secrets
import socket
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
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
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    random_part = secrets.token_hex(8)
    user_hash = hashlib.md5(user_id.encode()).hexdigest()[:8]

    session_id = f"auth_{timestamp}_{user_hash}_{random_part}"
    logger.debug(f"세션 ID 생성: {session_id}")
    return session_id


def auth_generate_state_token(user_id: Optional[str] = None) -> str:
    """
    CSRF 방지용 상태 토큰을 생성합니다.

    Args:
        user_id: 사용자 ID (선택사항, 제공 시 state에 인코딩됨)

    Returns:
        상태 토큰
    """
    random_token = secrets.token_urlsafe(32)

    # user_id가 제공되면 state에 인코딩
    if user_id:
        import base64
        # user_id를 base64로 인코딩하고 random_token과 결합
        encoded_user_id = base64.urlsafe_b64encode(user_id.encode()).decode()
        state_token = f"{random_token}:{encoded_user_id}"
        logger.debug(f"상태 토큰 생성 (user_id 포함): {state_token[:20]}...")
    else:
        state_token = random_token
        logger.debug(f"상태 토큰 생성: {state_token[:10]}...")

    return state_token


def auth_decode_state_token(state: str) -> tuple[str, Optional[str]]:
    """
    상태 토큰에서 user_id를 디코딩합니다.

    Args:
        state: 상태 토큰

    Returns:
        (state, user_id) 튜플. user_id가 없으면 None
    """
    try:
        if ":" in state:
            import base64
            random_token, encoded_user_id = state.split(":", 1)
            user_id = base64.urlsafe_b64decode(encoded_user_id).decode()
            logger.debug(f"상태 토큰에서 user_id 디코딩: {user_id}")
            return state, user_id
        else:
            return state, None
    except Exception as e:
        logger.warning(f"상태 토큰 디코딩 실패: {str(e)}")
        return state, None


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
    expiry_time = datetime.now(timezone.utc) + timedelta(minutes=minutes)
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


def auth_check_port_accessibility(port: int, host: str = "0.0.0.0") -> Tuple[bool, str]:
    """
    포트 접근성 확인 (관리자 권한 불필요)

    Args:
        port: 확인할 포트 번호
        host: 바인딩 호스트 (기본값: "0.0.0.0")

    Returns:
        (접근 가능 여부, 상태 메시지) 튜플
    """
    try:
        # 포트가 이미 사용 중인지 확인
        result = subprocess.run(
            ["ss", "-tuln"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            # 해당 포트가 리스닝 중인지 확인
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTEN" in line:
                    # 127.0.0.1로만 바인딩되어 있는지 확인
                    if "127.0.0.1" in line and host == "0.0.0.0":
                        return False, f"⚠️  포트 {port}이(가) localhost(127.0.0.1)로만 바인딩되어 외부 접근 불가"
                    elif "0.0.0.0" in line or "::" in line:
                        return True, f"✅ 포트 {port} 사용 가능 (모든 인터페이스에서 접근 가능)"
                    else:
                        return True, f"✅ 포트 {port} 리스닝 중"

            # 포트가 리스닝 중이 아님
            return True, f"✅ 포트 {port} 사용 가능"

        # ss 명령 실패 시 socket으로 재시도
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host if host != "0.0.0.0" else "127.0.0.1", port))
        sock.close()

        if result == 0:
            return True, f"✅ 포트 {port} 사용 가능"
        else:
            return False, f"❌ 포트 {port} 접근 불가"

    except subprocess.TimeoutExpired:
        logger.warning(f"포트 {port} 확인 시간 초과")
        return False, f"⚠️  포트 {port} 확인 시간 초과"
    except Exception as e:
        logger.warning(f"포트 {port} 확인 실패: {str(e)}")
        return False, f"⚠️  포트 {port} 확인 실패: {str(e)}"


def auth_check_firewall_status() -> Dict[str, Any]:
    """
    OS별 방화벽 상태 확인 (관리자 권한 불필요)

    Returns:
        방화벽 상태 정보 딕셔너리
    """
    status = {
        "os": platform.system(),
        "firewall_enabled": None,
        "firewall_status": "unknown",
        "requires_sudo": False,
        "message": ""
    }

    os_type = platform.system()

    try:
        if os_type == "Linux":
            # Linux: UFW 우선 체크, 없으면 iptables 체크
            try:
                result = subprocess.run(
                    ["ufw", "status"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if "Status: active" in result.stdout:
                    status["firewall_enabled"] = True
                    status["firewall_status"] = "active"
                    status["message"] = "⚠️  UFW 방화벽이 활성화되어 있습니다"
                elif "Status: inactive" in result.stdout:
                    status["firewall_enabled"] = False
                    status["firewall_status"] = "inactive"
                    status["message"] = "✅ UFW 방화벽 비활성화 상태"
                elif "must be run as root" in result.stderr or "permission denied" in result.stderr.lower():
                    status["requires_sudo"] = True
                    status["message"] = "⚠️  방화벽 상태 확인에 관리자 권한 필요"
                else:
                    status["message"] = "ℹ️  UFW 방화벽 미설치 또는 비활성"
            except FileNotFoundError:
                # UFW 없으면 iptables 체크
                try:
                    result = subprocess.run(
                        ["iptables", "-L", "-n"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        # 기본 정책이 ACCEPT가 아니거나 규칙이 있으면 활성화로 간주
                        if "DROP" in result.stdout or "REJECT" in result.stdout:
                            status["firewall_enabled"] = True
                            status["message"] = "⚠️  iptables 방화벽 규칙이 설정되어 있습니다"
                        else:
                            status["firewall_enabled"] = False
                            status["message"] = "✅ iptables 방화벽 기본 정책 (제한 없음)"
                    else:
                        status["requires_sudo"] = True
                        status["message"] = "⚠️  iptables 확인에 관리자 권한 필요"
                except FileNotFoundError:
                    status["message"] = "ℹ️  방화벽 도구 미설치 (UFW, iptables 없음)"

        elif os_type == "Darwin":  # macOS
            # macOS: Application Firewall 상태 체크
            try:
                result = subprocess.run(
                    ["/usr/libexec/ApplicationFirewall/socketfilterfw", "--getglobalstate"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if "enabled" in result.stdout.lower():
                    status["firewall_enabled"] = True
                    status["firewall_status"] = "active"
                    status["message"] = "⚠️  macOS 방화벽이 활성화되어 있습니다"
                elif "disabled" in result.stdout.lower():
                    status["firewall_enabled"] = False
                    status["firewall_status"] = "inactive"
                    status["message"] = "✅ macOS 방화벽 비활성화 상태"
                else:
                    status["message"] = "ℹ️  macOS 방화벽 상태 확인 실패"
            except FileNotFoundError:
                status["message"] = "ℹ️  macOS 방화벽 도구를 찾을 수 없음"
            except Exception as e:
                if "operation not permitted" in str(e).lower():
                    status["requires_sudo"] = True
                    status["message"] = "⚠️  macOS 방화벽 확인에 관리자 권한 필요"
                else:
                    status["message"] = f"ℹ️  macOS 방화벽 확인 실패: {str(e)}"

        elif os_type == "Windows":
            # Windows: netsh 명령으로 방화벽 상태 체크
            try:
                result = subprocess.run(
                    ["netsh", "advfirewall", "show", "allprofiles", "state"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if "ON" in result.stdout:
                    status["firewall_enabled"] = True
                    status["firewall_status"] = "active"
                    status["message"] = "⚠️  Windows 방화벽이 활성화되어 있습니다"
                elif "OFF" in result.stdout:
                    status["firewall_enabled"] = False
                    status["firewall_status"] = "inactive"
                    status["message"] = "✅ Windows 방화벽 비활성화 상태"
                else:
                    status["message"] = "ℹ️  Windows 방화벽 상태 확인 실패"
            except FileNotFoundError:
                status["message"] = "ℹ️  Windows netsh 명령을 찾을 수 없음"
            except Exception as e:
                if "access denied" in str(e).lower():
                    status["requires_sudo"] = True
                    status["message"] = "⚠️  Windows 방화벽 확인에 관리자 권한 필요"
                else:
                    status["message"] = f"ℹ️  Windows 방화벽 확인 실패: {str(e)}"

        else:
            status["message"] = f"ℹ️  지원하지 않는 OS: {os_type}"

    except subprocess.TimeoutExpired:
        status["message"] = "⚠️  방화벽 상태 확인 시간 초과"
    except Exception as e:
        status["message"] = f"⚠️  방화벽 상태 확인 실패: {str(e)}"

    return status


def auth_validate_oauth_credentials(
    client_id: Optional[str],
    client_secret: Optional[str],
    tenant_id: Optional[str]
) -> Tuple[bool, Optional[str]]:
    """
    Microsoft Azure OAuth 자격 증명 포맷 검증

    Args:
        client_id: Azure App Client ID (Application ID)
        client_secret: Azure App Client Secret
        tenant_id: Azure AD Tenant ID (Directory ID)

    Returns:
        (검증 성공 여부, 에러 메시지) 튜플
    """
    # UUID 포맷 (8-4-4-4-12 형식)
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)

    # 1. Client ID 검증 (UUID 포맷)
    if not client_id:
        return False, "❌ client_id가 비어있습니다"

    if not uuid_pattern.match(client_id):
        return False, f"❌ client_id 포맷이 올바르지 않습니다: {client_id[:20]}...\n   예상 포맷: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx (UUID)"

    # 2. Client Secret 검증
    # client_id와 client_secret을 헷갈리지 않도록만 검증
    if not client_secret:
        return False, "❌ client_secret이 비어있습니다"

    # ⚠️ client_secret에 UUID를 입력한 경우 (client_id와 혼동)
    if uuid_pattern.match(client_secret):
        return False, (
            f"❌ client_secret에 UUID가 입력되었습니다\n"
            f"   입력값: {client_secret}\n"
            f"   → client_id와 client_secret을 바꿔서 입력하신 것 같습니다\n"
            f"   → client_secret은 UUID가 아닌 영숫자+특수문자 조합입니다"
        )

    # 3. Tenant ID 검증 (UUID 포맷)
    if not tenant_id:
        return False, "❌ tenant_id가 비어있습니다"

    if not uuid_pattern.match(tenant_id):
        return False, f"❌ tenant_id 포맷이 올바르지 않습니다: {tenant_id[:20]}...\n   예상 포맷: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx (UUID)"

    # 모든 검증 통과
    logger.info(f"OAuth 자격 증명 검증 성공: client_id={client_id[:8]}..., tenant_id={tenant_id[:8]}...")
    return True, None
