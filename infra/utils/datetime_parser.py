"""DateTime parsing utilities for consistent date handling across the project

This module provides standardized date/time parsing with timezone handling.

규칙:
- start_date: 항상 00:00:00 (해당 날짜의 시작)
- end_date: 오늘 날짜면 현재 시간, 과거 날짜면 23:59:59
- 입력 timezone 지정 가능 (KST/UTC)
- 출력 timezone 선택 가능 (KST/UTC)
- 결과는 dictionary 형태로 반환 가능 (시간 기준 포함)
"""

from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional, Dict, Any, Union
from enum import Enum

# Timezone 정의
KST = timezone(timedelta(hours=9))
UTC = timezone.utc


class Timezone(str, Enum):
    """Supported timezones"""
    KST = "KST"
    UTC = "UTC"


def parse_start_date(
    date_str: str,
    input_tz: Timezone = Timezone.KST,
    output_tz: Timezone = Timezone.UTC,
    return_dict: bool = False
) -> Union[Dict[str, Any], datetime]:
    """
    Parse start date string with timezone support

    항상 00:00:00으로 설정 (시간 정보 없는 경우)

    Args:
        date_str: Date string (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        input_tz: Input timezone (KST or UTC)
        output_tz: Output timezone (KST or UTC)
        return_dict: If True, return dictionary with metadata

    Returns:
        datetime object or dict with timezone info

    Examples:
        >>> parse_start_date("2025-09-01")
        datetime(2025, 8, 31, 15, 0, 0, tzinfo=timezone.utc)

        >>> parse_start_date("2025-09-01", return_dict=True)
        {
            'datetime': datetime(2025, 8, 31, 15, 0, 0, tzinfo=timezone.utc),
            'formatted': '2025-08-31 15:00:00',
            'timezone': 'UTC',
            'iso': '2025-08-31T15:00:00+00:00'
        }
    """
    # 시간 정보가 없으면 00:00:00 추가
    if 'T' not in date_str:
        date_str += 'T00:00:00'

    # 파싱
    dt = datetime.fromisoformat(date_str)

    # timezone 설정
    if dt.tzinfo is None:
        input_timezone = KST if input_tz == Timezone.KST else UTC
        dt = dt.replace(tzinfo=input_timezone)

    # 출력 timezone으로 변환
    output_timezone = KST if output_tz == Timezone.KST else UTC
    dt_converted = dt.astimezone(output_timezone)

    if return_dict:
        return {
            'datetime': dt_converted,
            'formatted': dt_converted.strftime('%Y-%m-%d %H:%M:%S'),
            'timezone': output_tz.value,
            'iso': dt_converted.isoformat(),
            'timestamp': int(dt_converted.timestamp())
        }

    return dt_converted


def parse_end_date(
    date_str: str,
    input_tz: Timezone = Timezone.KST,
    output_tz: Timezone = Timezone.UTC,
    return_dict: bool = False
) -> Union[Dict[str, Any], datetime]:
    """
    Parse end date string with timezone support

    규칙:
    - 오늘 날짜: 현재 시간 사용
    - 과거 날짜: 23:59:59 사용
    - 미래 날짜: 23:59:59 사용

    Args:
        date_str: Date string (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        input_tz: Input timezone (KST or UTC)
        output_tz: Output timezone (KST or UTC)
        return_dict: If True, return dictionary with metadata

    Returns:
        datetime object or dict with timezone info

    Examples:
        >>> # 오늘이 2025-10-18 08:30:00 KST라고 가정
        >>> parse_end_date("2025-10-18", return_dict=True)
        {
            'datetime': datetime(2025, 10, 17, 23, 30, 0, tzinfo=timezone.utc),
            'formatted': '2025-10-17 23:30:00',
            'timezone': 'UTC',
            'iso': '2025-10-17T23:30:00+00:00',
            'is_today': True,
            'time_used': 'current'
        }
    """
    # 시간 정보가 포함된 경우
    if 'T' in date_str:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            input_timezone = KST if input_tz == Timezone.KST else UTC
            dt = dt.replace(tzinfo=input_timezone)

        output_timezone = KST if output_tz == Timezone.KST else UTC
        dt_converted = dt.astimezone(output_timezone)

        if return_dict:
            return {
                'datetime': dt_converted,
                'formatted': dt_converted.strftime('%Y-%m-%d %H:%M:%S'),
                'timezone': output_tz.value,
                'iso': dt_converted.isoformat(),
                'timestamp': int(dt_converted.timestamp()),
                'is_today': False,
                'time_used': 'specified'
            }
        return dt_converted

    # 날짜만 있는 경우
    input_timezone = KST if input_tz == Timezone.KST else UTC
    now_in_tz = datetime.now(input_timezone)
    today_in_tz = now_in_tz.date()

    # 입력 날짜 파싱
    end_date_only = datetime.strptime(date_str, "%Y-%m-%d").date()

    # 오늘 날짜면 현재 시간, 그 외는 23:59:59
    is_today = end_date_only == today_in_tz

    if is_today:
        # 오늘 → 현재 시간 사용
        dt = datetime.combine(end_date_only, now_in_tz.time()).replace(tzinfo=input_timezone)
        time_used = 'current'
    else:
        # 과거/미래 → 23:59:59 사용
        dt = datetime.combine(end_date_only, datetime.max.time()).replace(microsecond=0, tzinfo=input_timezone)
        time_used = '23:59:59'

    # 출력 timezone으로 변환
    output_timezone = KST if output_tz == Timezone.KST else UTC
    dt_converted = dt.astimezone(output_timezone)

    if return_dict:
        return {
            'datetime': dt_converted,
            'formatted': dt_converted.strftime('%Y-%m-%d %H:%M:%S'),
            'timezone': output_tz.value,
            'iso': dt_converted.isoformat(),
            'timestamp': int(dt_converted.timestamp()),
            'is_today': is_today,
            'time_used': time_used
        }

    return dt_converted


def parse_date_range(
    start_date_str: Optional[str] = None,
    end_date_str: Optional[str] = None,
    days_back: int = 30,
    input_tz: Timezone = Timezone.KST,
    output_tz: Timezone = Timezone.UTC,
    return_dict: bool = False
) -> Union[Tuple[datetime, datetime, int], Dict[str, Any]]:
    """
    Parse date range with flexible input options and timezone support

    Args:
        start_date_str: Start date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS), optional
        end_date_str: End date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS), optional
        days_back: Number of days to look back if dates not specified
        input_tz: Input timezone (KST or UTC)
        output_tz: Output timezone (KST or UTC)
        return_dict: If True, return dictionary with metadata

    Returns:
        Tuple of (start_date, end_date, calculated_days_back) or dict

    Examples:
        >>> # 둘 다 지정
        >>> result = parse_date_range("2025-09-01", "2025-10-17", return_dict=True)
        {
            'start_date': datetime(...),
            'end_date': datetime(...),
            'days': 46,
            'timezone': 'UTC',
            'start_formatted': '2025-08-31 15:00:00',
            'end_formatted': '2025-10-17 14:59:59'
        }
    """
    # 둘 다 지정된 경우
    if start_date_str and end_date_str:
        start_date = parse_start_date(start_date_str, input_tz=input_tz, output_tz=output_tz)
        end_date = parse_end_date(end_date_str, input_tz=input_tz, output_tz=output_tz)

        if start_date >= end_date:
            raise ValueError(f"start_date ({start_date_str}) must be before end_date ({end_date_str})")

        calculated_days = (end_date - start_date).days

    # start만 지정
    elif start_date_str:
        start_date = parse_start_date(start_date_str, input_tz=input_tz, output_tz=output_tz)
        output_timezone = KST if output_tz == Timezone.KST else UTC
        end_date = datetime.now(output_timezone)
        calculated_days = (end_date - start_date).days + 1

    # end만 지정
    elif end_date_str:
        end_date = parse_end_date(end_date_str, input_tz=input_tz, output_tz=output_tz)
        start_date = end_date - timedelta(days=days_back)
        calculated_days = days_back

    # 둘 다 없음
    else:
        output_timezone = KST if output_tz == Timezone.KST else UTC
        end_date = datetime.now(output_timezone)
        start_date = end_date - timedelta(days=days_back - 1)
        calculated_days = days_back

    if return_dict:
        return {
            'start_date': start_date,
            'end_date': end_date,
            'days': calculated_days,
            'timezone': output_tz.value,
            'start_formatted': start_date.strftime('%Y-%m-%d %H:%M:%S'),
            'end_formatted': end_date.strftime('%Y-%m-%d %H:%M:%S'),
            'start_iso': start_date.isoformat(),
            'end_iso': end_date.isoformat(),
        }

    return start_date, end_date, calculated_days
