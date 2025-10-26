"""Unit tests for datetime_utils module

이 테스트는 datetime_utils의 모든 함수가 올바르게 동작하는지 검증합니다.
"""

import pytest
from datetime import datetime, timezone, timedelta
from infra.utils.datetime_utils import (
    utc_now,
    utc_now_iso,
    from_timestamp,
    ensure_utc,
    parse_iso_to_utc,
    to_local_filename,
    format_for_display,
    is_expired,
    time_until_expiry,
)


class TestUtcNow:
    """utc_now() 함수 테스트"""

    def test_returns_datetime(self):
        """datetime 객체 반환 확인"""
        result = utc_now()
        assert isinstance(result, datetime)

    def test_has_utc_timezone(self):
        """UTC timezone 포함 확인"""
        result = utc_now()
        assert result.tzinfo == timezone.utc

    def test_is_aware(self):
        """aware datetime 확인"""
        result = utc_now()
        assert result.tzinfo is not None


class TestUtcNowIso:
    """utc_now_iso() 함수 테스트"""

    def test_returns_string(self):
        """문자열 반환 확인"""
        result = utc_now_iso()
        assert isinstance(result, str)

    def test_ends_with_z(self):
        """'Z' suffix 확인"""
        result = utc_now_iso()
        assert result.endswith('Z')

    def test_contains_t_separator(self):
        """ISO 8601 형식 확인"""
        result = utc_now_iso()
        assert 'T' in result

    def test_parseable(self):
        """생성된 문자열이 파싱 가능한지 확인"""
        iso_str = utc_now_iso()
        parsed = parse_iso_to_utc(iso_str)
        assert parsed.tzinfo == timezone.utc


class TestFromTimestamp:
    """from_timestamp() 함수 테스트"""

    def test_converts_int_timestamp(self):
        """정수 timestamp 변환"""
        # 2025-10-26 00:00:00 UTC
        ts = 1761436800
        result = from_timestamp(ts)
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 26

    def test_converts_float_timestamp(self):
        """실수 timestamp 변환"""
        ts = 1761436800.5
        result = from_timestamp(ts)
        assert result.microsecond > 0

    def test_has_utc_timezone(self):
        """UTC timezone 포함 확인"""
        result = from_timestamp(1761436800)
        assert result.tzinfo == timezone.utc


class TestEnsureUtc:
    """ensure_utc() 함수 테스트"""

    def test_converts_naive_to_utc(self):
        """naive datetime을 UTC aware로 변환"""
        naive = datetime(2025, 10, 26, 10, 0, 0)
        result = ensure_utc(naive)
        assert result.tzinfo == timezone.utc
        assert result.hour == 10

    def test_converts_other_timezone_to_utc(self):
        """다른 timezone을 UTC로 변환"""
        kst = timezone(timedelta(hours=9))
        kst_dt = datetime(2025, 10, 26, 11, 0, 0, tzinfo=kst)
        result = ensure_utc(kst_dt)
        assert result.tzinfo == timezone.utc
        assert result.hour == 2  # 11:00 KST = 02:00 UTC

    def test_preserves_utc_datetime(self):
        """이미 UTC인 경우 그대로 반환"""
        utc_dt = datetime(2025, 10, 26, 2, 0, 0, tzinfo=timezone.utc)
        result = ensure_utc(utc_dt)
        assert result == utc_dt


class TestParseIsoToUtc:
    """parse_iso_to_utc() 함수 테스트"""

    def test_parses_iso_with_z_suffix(self):
        """'Z' suffix ISO 문자열 파싱"""
        iso_str = "2025-10-26T02:00:00Z"
        result = parse_iso_to_utc(iso_str)
        assert result.tzinfo == timezone.utc
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 26
        assert result.hour == 2

    def test_parses_iso_with_offset(self):
        """timezone offset ISO 문자열 파싱"""
        iso_str = "2025-10-26T11:00:00+09:00"
        result = parse_iso_to_utc(iso_str)
        assert result.tzinfo == timezone.utc
        assert result.hour == 2  # 11:00 +09:00 = 02:00 UTC

    def test_parses_iso_without_timezone(self):
        """timezone 없는 ISO 문자열 파싱 (UTC로 가정)"""
        iso_str = "2025-10-26T02:00:00"
        result = parse_iso_to_utc(iso_str)
        assert result.tzinfo == timezone.utc
        assert result.hour == 2


class TestToLocalFilename:
    """to_local_filename() 함수 테스트"""

    def test_returns_string(self):
        """문자열 반환 확인"""
        result = to_local_filename()
        assert isinstance(result, str)

    def test_format_without_milliseconds(self):
        """밀리초 없는 포맷"""
        result = to_local_filename()
        assert len(result) == 15
        assert '_' in result

    def test_format_with_milliseconds(self):
        """밀리초 포함 포맷"""
        result = to_local_filename(include_ms=True)
        assert len(result) == 19
        assert result.count('_') == 2

    def test_custom_datetime(self):
        """특정 datetime으로 파일명 생성"""
        dt = datetime(2025, 10, 26, 15, 30, 45, tzinfo=timezone.utc)
        result = to_local_filename(dt)
        assert result == "20251026_153045"

    def test_filename_is_sortable(self):
        """파일명이 정렬 가능한지 확인"""
        dt1 = datetime(2025, 10, 26, 10, 0, 0, tzinfo=timezone.utc)
        dt2 = datetime(2025, 10, 26, 11, 0, 0, tzinfo=timezone.utc)
        fn1 = to_local_filename(dt1)
        fn2 = to_local_filename(dt2)
        assert fn1 < fn2


class TestFormatForDisplay:
    """format_for_display() 함수 테스트"""

    def test_includes_utc_suffix(self):
        """UTC suffix 포함 확인"""
        dt = datetime(2025, 10, 26, 15, 30, 45, tzinfo=timezone.utc)
        result = format_for_display(dt)
        assert result.endswith(' UTC')

    def test_excludes_utc_suffix_when_requested(self):
        """UTC suffix 제외 옵션"""
        dt = datetime(2025, 10, 26, 15, 30, 45, tzinfo=timezone.utc)
        result = format_for_display(dt, include_tz=False)
        assert not result.endswith(' UTC')

    def test_format(self):
        """포맷 형식 확인"""
        dt = datetime(2025, 10, 26, 15, 30, 45, tzinfo=timezone.utc)
        result = format_for_display(dt)
        assert result == "2025-10-26 15:30:45 UTC"


class TestIsExpired:
    """is_expired() 함수 테스트"""

    def test_future_time_not_expired(self):
        """미래 시각은 만료되지 않음"""
        future = utc_now() + timedelta(hours=1)
        assert is_expired(future) is False

    def test_past_time_expired(self):
        """과거 시각은 만료됨"""
        past = utc_now() - timedelta(hours=1)
        assert is_expired(past) is True

    def test_iso_string_future(self):
        """ISO 문자열 (미래)"""
        future = utc_now() + timedelta(hours=1)
        iso_str = future.isoformat().replace('+00:00', 'Z')
        assert is_expired(iso_str) is False

    def test_iso_string_past(self):
        """ISO 문자열 (과거)"""
        past = utc_now() - timedelta(hours=1)
        iso_str = past.isoformat().replace('+00:00', 'Z')
        assert is_expired(iso_str) is True

    def test_buffer_seconds(self):
        """버퍼 시간 적용"""
        # 30초 후 만료
        near_future = utc_now() + timedelta(seconds=30)
        # 60초 버퍼 → 만료로 판정
        assert is_expired(near_future, buffer_seconds=60) is True
        # 10초 버퍼 → 만료 안됨
        assert is_expired(near_future, buffer_seconds=10) is False


class TestTimeUntilExpiry:
    """time_until_expiry() 함수 테스트"""

    def test_future_time_positive_delta(self):
        """미래 시각은 양수 delta"""
        future = utc_now() + timedelta(hours=2)
        remaining = time_until_expiry(future)
        assert remaining.total_seconds() > 7000  # ~2 hours = 7200s

    def test_past_time_negative_delta(self):
        """과거 시각은 음수 delta"""
        past = utc_now() - timedelta(hours=1)
        remaining = time_until_expiry(past)
        assert remaining.total_seconds() < 0

    def test_iso_string(self):
        """ISO 문자열로 계산"""
        future = utc_now() + timedelta(minutes=30)
        iso_str = future.isoformat().replace('+00:00', 'Z')
        remaining = time_until_expiry(iso_str)
        assert remaining.total_seconds() > 1700  # ~30 minutes = 1800s


class TestIntegration:
    """통합 테스트 - 실제 사용 시나리오"""

    def test_token_expiry_scenario(self):
        """토큰 만료 시나리오"""
        # 토큰 발급 (1시간 후 만료)
        issued_at = utc_now()
        expires_at = issued_at + timedelta(hours=1)
        expires_at_str = expires_at.isoformat().replace('+00:00', 'Z')

        # DB 저장 시뮬레이션
        stored_iso = expires_at_str

        # 30분 후 체크
        # (실제로는 시간이 흐르지 않으므로 바로 체크)
        assert is_expired(stored_iso) is False

        # 만료 시각 이후 체크
        past_expiry = expires_at - timedelta(hours=2)  # 과거로 설정
        past_iso = past_expiry.isoformat().replace('+00:00', 'Z')
        assert is_expired(past_iso) is True

    def test_file_naming_scenario(self):
        """파일명 생성 시나리오"""
        # 현재 시각으로 파일명 생성
        filename = f"backup_{to_local_filename()}.json"
        assert filename.startswith("backup_")
        assert filename.endswith(".json")
        assert len(filename) > 20

    def test_log_display_scenario(self):
        """로그 표시 시나리오"""
        now = utc_now()
        log_message = f"Token refreshed at {format_for_display(now)}"
        assert "UTC" in log_message
        assert str(now.year) in log_message


def test_datetime_utils_import():
    """모듈 import 테스트"""
    from infra.utils import datetime_utils
    assert hasattr(datetime_utils, 'utc_now')
    assert hasattr(datetime_utils, 'utc_now_iso')
    assert hasattr(datetime_utils, 'ensure_utc')


if __name__ == "__main__":
    # pytest가 없을 경우 직접 실행
    pytest.main([__file__, "-v"])
