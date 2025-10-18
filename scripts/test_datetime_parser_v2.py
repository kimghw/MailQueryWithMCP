#!/usr/bin/env python3
"""Test enhanced datetime_parser with timezone options and dict output"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from infra.utils.datetime_parser import parse_start_date, parse_end_date, parse_date_range, Timezone
import json


def print_dict(title, data):
    """Pretty print dictionary"""
    print(f"\n{title}:")
    print(json.dumps(data, indent=2, default=str))


def test_timezone_options():
    """Timezone 옵션 테스트"""
    print("=" * 80)
    print("1. Timezone 옵션 테스트")
    print("=" * 80)

    date_str = "2025-10-17"

    # KST 입력 → UTC 출력 (기본)
    result = parse_end_date(date_str, input_tz=Timezone.KST, output_tz=Timezone.UTC, return_dict=True)
    print_dict(f"parse_end_date('{date_str}', KST→UTC)", result)

    # KST 입력 → KST 출력
    result = parse_end_date(date_str, input_tz=Timezone.KST, output_tz=Timezone.KST, return_dict=True)
    print_dict(f"parse_end_date('{date_str}', KST→KST)", result)

    # UTC 입력 → UTC 출력
    result = parse_end_date(date_str, input_tz=Timezone.UTC, output_tz=Timezone.UTC, return_dict=True)
    print_dict(f"parse_end_date('{date_str}', UTC→UTC)", result)

    # UTC 입력 → KST 출력
    result = parse_end_date(date_str, input_tz=Timezone.UTC, output_tz=Timezone.KST, return_dict=True)
    print_dict(f"parse_end_date('{date_str}', UTC→KST)", result)


def test_dict_output():
    """Dictionary 출력 테스트"""
    print("\n" + "=" * 80)
    print("2. Dictionary 출력 형식 테스트")
    print("=" * 80)

    # start_date
    result = parse_start_date("2025-09-01", return_dict=True)
    print_dict("parse_start_date('2025-09-01')", result)

    # end_date (오늘)
    today = "2025-10-18"
    result = parse_end_date(today, return_dict=True)
    print_dict(f"parse_end_date('{today}') - 오늘", result)

    # end_date (과거)
    past = "2025-10-17"
    result = parse_end_date(past, return_dict=True)
    print_dict(f"parse_end_date('{past}') - 과거", result)


def test_date_range_dict():
    """Date range dictionary 출력 테스트"""
    print("\n" + "=" * 80)
    print("3. Date Range Dictionary 테스트")
    print("=" * 80)

    # UTC 출력
    result = parse_date_range(
        "2025-09-01",
        "2025-10-17",
        input_tz=Timezone.KST,
        output_tz=Timezone.UTC,
        return_dict=True
    )
    print_dict("parse_date_range (KST→UTC)", result)

    # KST 출력
    result = parse_date_range(
        "2025-09-01",
        "2025-10-17",
        input_tz=Timezone.KST,
        output_tz=Timezone.KST,
        return_dict=True
    )
    print_dict("parse_date_range (KST→KST)", result)


def test_backward_compatibility():
    """기존 API 호환성 테스트"""
    print("\n" + "=" * 80)
    print("4. 기존 API 호환성 테스트")
    print("=" * 80)

    # 기본 사용법 (return_dict=False)
    start, end, days = parse_date_range("2025-09-01", "2025-10-17")
    print(f"\nparse_date_range('2025-09-01', '2025-10-17'):")
    print(f"  start: {start}")
    print(f"  end:   {end}")
    print(f"  days:  {days}")

    # datetime 객체 직접 반환
    dt = parse_start_date("2025-09-01")
    print(f"\nparse_start_date('2025-09-01'): {dt}")

    dt = parse_end_date("2025-10-17")
    print(f"parse_end_date('2025-10-17'): {dt}")


def test_comparison():
    """KST vs UTC 비교"""
    print("\n" + "=" * 80)
    print("5. KST vs UTC 비교")
    print("=" * 80)

    date_str = "2025-10-17"

    kst_result = parse_end_date(date_str, output_tz=Timezone.KST, return_dict=True)
    utc_result = parse_end_date(date_str, output_tz=Timezone.UTC, return_dict=True)

    print(f"\n입력: {date_str}")
    print(f"KST: {kst_result['formatted']} {kst_result['timezone']}")
    print(f"UTC: {utc_result['formatted']} {utc_result['timezone']}")
    print(f"시간 차이: 9시간 (KST = UTC+9)")
    print(f"Timestamp (동일): {kst_result['timestamp']} == {utc_result['timestamp']}")


if __name__ == "__main__":
    test_timezone_options()
    test_dict_output()
    test_date_range_dict()
    test_backward_compatibility()
    test_comparison()

    print("\n" + "=" * 80)
    print("✅ 모든 테스트 완료!")
    print("=" * 80)
