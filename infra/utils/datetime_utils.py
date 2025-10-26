"""Timezone-aware datetime utilities for consistent UTC handling

이 모듈은 프로젝트 전역에서 일관된 UTC 기준 시간 처리를 위한 헬퍼 함수를 제공합니다.

사용 원칙:
1. datetime.now() 사용 금지 → utc_now() 사용
2. DB 저장 시 ISO format with 'Z' → utc_now_iso() 사용
3. 파일명 생성 시 → to_local_filename() 사용
4. naive datetime 발견 시 → ensure_utc() 사용

Examples:
    >>> from infra.utils.datetime_utils import utc_now, utc_now_iso
    >>>
    >>> # 현재 UTC 시각
    >>> now = utc_now()
    >>> print(now.tzinfo)
    datetime.timezone.utc
    >>>
    >>> # DB 저장용 ISO 문자열
    >>> iso_str = utc_now_iso()
    >>> print(iso_str)
    '2025-10-26T02:00:00Z'
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Union


def utc_now() -> datetime:
    """Get current UTC time (timezone-aware)

    Returns:
        datetime with UTC timezone

    Example:
        >>> now = utc_now()
        >>> now.tzinfo
        datetime.timezone.utc
        >>> isinstance(now, datetime)
        True

    Note:
        이 함수는 datetime.now()를 대체합니다.
        항상 UTC timezone이 포함된 aware datetime을 반환합니다.
    """
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """Get current UTC time as ISO format string with 'Z' suffix

    Returns:
        ISO format string (e.g., '2025-10-26T02:00:00Z')

    Example:
        >>> iso = utc_now_iso()
        >>> iso.endswith('Z')
        True
        >>> 'T' in iso
        True

    Note:
        DB 저장 시 이 형식을 사용하세요.
        'Z' suffix는 UTC를 명시적으로 나타냅니다.
    """
    return utc_now().isoformat().replace('+00:00', 'Z')


def from_timestamp(ts: Union[int, float]) -> datetime:
    """Convert UNIX timestamp to UTC datetime

    Args:
        ts: UNIX timestamp (seconds since epoch)

    Returns:
        datetime with UTC timezone

    Example:
        >>> dt = from_timestamp(1698307200)
        >>> dt.tzinfo
        datetime.timezone.utc

    Raises:
        ValueError: If timestamp is invalid
        OSError: If timestamp is out of range
    """
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime has UTC timezone

    Args:
        dt: datetime (naive or aware)

    Returns:
        datetime with UTC timezone

    Example:
        >>> # naive datetime (timezone 없음)
        >>> naive = datetime(2025, 10, 26, 2, 0, 0)
        >>> aware = ensure_utc(naive)
        >>> aware.tzinfo
        datetime.timezone.utc
        >>>
        >>> # 다른 timezone의 datetime
        >>> from datetime import timezone, timedelta
        >>> kst = timezone(timedelta(hours=9))
        >>> kst_dt = datetime(2025, 10, 26, 11, 0, 0, tzinfo=kst)
        >>> utc_dt = ensure_utc(kst_dt)
        >>> utc_dt.hour
        2

    Note:
        - naive datetime → UTC로 가정하고 tzinfo 추가
        - aware datetime → UTC로 변환
        - 이미 UTC인 경우 → 그대로 반환
    """
    if dt.tzinfo is None:
        # naive → UTC로 가정
        return dt.replace(tzinfo=timezone.utc)
    # aware → UTC로 변환
    return dt.astimezone(timezone.utc)


def parse_iso_to_utc(iso_str: str) -> datetime:
    """Parse ISO format string to UTC datetime

    Args:
        iso_str: ISO format string (with or without timezone)

    Returns:
        datetime with UTC timezone

    Example:
        >>> # With 'Z' suffix
        >>> dt = parse_iso_to_utc('2025-10-26T02:00:00Z')
        >>> dt.tzinfo
        datetime.timezone.utc
        >>>
        >>> # Without timezone (assume UTC)
        >>> dt = parse_iso_to_utc('2025-10-26T02:00:00')
        >>> dt.tzinfo
        datetime.timezone.utc
        >>>
        >>> # With offset
        >>> dt = parse_iso_to_utc('2025-10-26T11:00:00+09:00')
        >>> dt.hour
        2

    Note:
        - 'Z' suffix → UTC
        - '+00:00' offset → UTC
        - timezone 없음 → UTC로 가정
        - 다른 offset → UTC로 변환
    """
    # Replace 'Z' with '+00:00' for fromisoformat
    iso_str_normalized = iso_str.replace('Z', '+00:00')
    dt = datetime.fromisoformat(iso_str_normalized)
    return ensure_utc(dt)


def to_local_filename(dt: Optional[datetime] = None, include_ms: bool = False) -> str:
    """Generate filename timestamp (YYYYmmdd_HHMMSS)

    Args:
        dt: datetime to format (default: utc_now())
        include_ms: Include milliseconds (default: False)

    Returns:
        Filename-safe timestamp string

    Example:
        >>> filename = to_local_filename()
        >>> len(filename)
        15
        >>> '_' in filename
        True
        >>>
        >>> # With milliseconds
        >>> filename_ms = to_local_filename(include_ms=True)
        >>> len(filename_ms)
        19

    Note:
        이 함수는 파일명/폴더명 생성 전용입니다.
        UTC 기준으로 생성되므로 서버 시간대에 관계없이 일관성이 보장됩니다.

        사용 예시:
        - 백업 파일: f"backup_{to_local_filename()}.json"
        - 로그 폴더: f"logs/{to_local_filename()}"
        - 임시 파일: f"temp_{to_local_filename(include_ms=True)}.tmp"
    """
    if dt is None:
        dt = utc_now()

    if include_ms:
        return dt.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # microseconds → milliseconds
    return dt.strftime("%Y%m%d_%H%M%S")


def format_for_display(dt: datetime, include_tz: bool = True) -> str:
    """Format datetime for human-readable display

    Args:
        dt: datetime to format
        include_tz: Include timezone suffix (default: True)

    Returns:
        Formatted string (e.g., '2025-10-26 02:00:00 UTC')

    Example:
        >>> dt = utc_now()
        >>> display = format_for_display(dt)
        >>> 'UTC' in display
        True
        >>>
        >>> display_no_tz = format_for_display(dt, include_tz=False)
        >>> 'UTC' in display_no_tz
        False

    Note:
        로그, HTTP 응답, 문서 내용 등에 사용하세요.
        사용자가 timezone을 명확히 알 수 있도록 'UTC' suffix 포함 권장.
    """
    dt_utc = ensure_utc(dt)
    formatted = dt_utc.strftime("%Y-%m-%d %H:%M:%S")

    if include_tz:
        return f"{formatted} UTC"
    return formatted


def is_expired(expires_at: Union[str, datetime], buffer_seconds: int = 0) -> bool:
    """Check if a datetime has expired

    Args:
        expires_at: Expiry time (ISO string or datetime)
        buffer_seconds: Additional buffer time in seconds (default: 0)

    Returns:
        True if expired, False otherwise

    Example:
        >>> from datetime import timedelta
        >>>
        >>> # Future time
        >>> future = utc_now() + timedelta(hours=1)
        >>> is_expired(future)
        False
        >>>
        >>> # Past time
        >>> past = utc_now() - timedelta(hours=1)
        >>> is_expired(past)
        True
        >>>
        >>> # With buffer
        >>> near_future = utc_now() + timedelta(seconds=30)
        >>> is_expired(near_future, buffer_seconds=60)
        True

    Note:
        토큰 만료 검사 등에 사용하세요.
        buffer_seconds를 사용하면 만료 전에 미리 갱신할 수 있습니다.
    """
    if isinstance(expires_at, str):
        expiry_dt = parse_iso_to_utc(expires_at)
    else:
        expiry_dt = ensure_utc(expires_at)

    now = utc_now()

    if buffer_seconds > 0:
        # 버퍼 시간만큼 일찍 만료로 판정
        now = now + timedelta(seconds=buffer_seconds)

    return expiry_dt <= now


def time_until_expiry(expires_at: Union[str, datetime]) -> timedelta:
    """Calculate time remaining until expiry

    Args:
        expires_at: Expiry time (ISO string or datetime)

    Returns:
        timedelta (negative if already expired)

    Example:
        >>> from datetime import timedelta
        >>>
        >>> future = utc_now() + timedelta(hours=2)
        >>> remaining = time_until_expiry(future)
        >>> remaining.total_seconds() > 7000  # ~2 hours
        True
        >>>
        >>> past = utc_now() - timedelta(hours=1)
        >>> remaining = time_until_expiry(past)
        >>> remaining.total_seconds() < 0
        True

    Note:
        로그나 모니터링에서 토큰 만료까지 남은 시간을 표시할 때 사용하세요.
    """
    if isinstance(expires_at, str):
        expiry_dt = parse_iso_to_utc(expires_at)
    else:
        expiry_dt = ensure_utc(expires_at)

    return expiry_dt - utc_now()


# Deprecated 함수 (하위 호환성)
def get_utc_now() -> datetime:
    """Deprecated: Use utc_now() instead"""
    import warnings
    warnings.warn(
        "get_utc_now() is deprecated, use utc_now() instead",
        DeprecationWarning,
        stacklevel=2
    )
    return utc_now()
