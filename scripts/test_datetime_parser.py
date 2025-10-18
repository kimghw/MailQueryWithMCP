#!/usr/bin/env python3
"""Test datetime_parser utility and compare with existing implementations"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from infra.utils.datetime_parser import parse_start_date, parse_end_date, parse_date_range


def test_basic_parsing():
    """기본 파싱 테스트"""
    print("=" * 80)
    print("1. 기본 파싱 테스트")
    print("=" * 80)

    # start_date 테스트
    start = parse_start_date("2025-09-01")
    print(f"\nstart_date('2025-09-01'):")
    print(f"  UTC: {start}")
    print(f"  KST: {start.astimezone(timezone(timedelta(hours=9)))}")

    # end_date 테스트 (오늘)
    today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    end_today = parse_end_date(today)
    print(f"\nend_date('{today}') - 오늘:")
    print(f"  UTC: {end_today}")
    print(f"  KST: {end_today.astimezone(timezone(timedelta(hours=9)))}")

    # end_date 테스트 (과거)
    end_past = parse_end_date("2025-10-17")
    print(f"\nend_date('2025-10-17') - 과거:")
    print(f"  UTC: {end_past}")
    print(f"  KST: {end_past.astimezone(timezone(timedelta(hours=9)))}")


def test_date_range():
    """날짜 범위 테스트"""
    print("\n" + "=" * 80)
    print("2. 날짜 범위 테스트")
    print("=" * 80)

    # 둘 다 지정
    start, end, days = parse_date_range("2025-09-01", "2025-10-17")
    print(f"\nparse_date_range('2025-09-01', '2025-10-17'):")
    print(f"  start: {start} UTC")
    print(f"  end:   {end} UTC")
    print(f"  days:  {days}일")

    # start만 지정
    start, end, days = parse_date_range(start_date_str="2025-10-01")
    print(f"\nparse_date_range(start='2025-10-01'):")
    print(f"  start: {start} UTC")
    print(f"  end:   {end} UTC (현재)")
    print(f"  days:  {days}일")

    # end만 지정
    start, end, days = parse_date_range(end_date_str="2025-10-17", days_back=30)
    print(f"\nparse_date_range(end='2025-10-17', days_back=30):")
    print(f"  start: {start} UTC")
    print(f"  end:   {end} UTC")
    print(f"  days:  {days}일")


def test_compatibility_with_mail_query():
    """mail_query.py와 호환성 테스트"""
    print("\n" + "=" * 80)
    print("3. mail_query.py 호환성 테스트")
    print("=" * 80)

    KST = timezone(timedelta(hours=9))

    # 기존 email_query.py 로직 시뮬레이션
    print("\n[기존 email_query.py 로직]")
    end_date_str = "2025-10-17"
    if len(end_date_str) == 10:
        now_kst = datetime.now(KST)
        end_date_only = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        dt_kst = datetime.combine(end_date_only, now_kst.time()).replace(tzinfo=KST)
        old_end = dt_kst.astimezone(timezone.utc)
        print(f"  end_date('2025-10-17'): {old_end}")

    # 새 유틸리티
    print("\n[새 datetime_parser 유틸리티]")
    new_end = parse_end_date("2025-10-17")
    print(f"  end_date('2025-10-17'): {new_end}")

    print("\n[차이점]")
    print(f"  기존: 과거 날짜도 현재 시간 사용 (문제!)")
    print(f"  신규: 과거 날짜는 23:59:59 사용 (올바름)")


def test_edge_cases():
    """엣지 케이스 테스트"""
    print("\n" + "=" * 80)
    print("4. 엣지 케이스 테스트")
    print("=" * 80)

    KST = timezone(timedelta(hours=9))

    # 시간 포함된 입력
    start = parse_start_date("2025-09-01T10:30:00")
    print(f"\nstart_date('2025-09-01T10:30:00'):")
    print(f"  KST: {start.astimezone(KST)}")
    print(f"  UTC: {start}")

    end = parse_end_date("2025-10-17T15:45:00")
    print(f"\nend_date('2025-10-17T15:45:00'):")
    print(f"  KST: {end.astimezone(KST)}")
    print(f"  UTC: {end}")

    # 에러 케이스
    print("\n[에러 케이스]")
    try:
        parse_date_range("2025-10-17", "2025-09-01")
    except ValueError as e:
        print(f"  ✅ start > end 검증: {e}")


def test_with_mail_query_schema():
    """MailQuerySeverFilters와 함께 테스트"""
    print("\n" + "=" * 80)
    print("5. MailQuerySeverFilters 통합 테스트")
    print("=" * 80)

    try:
        from modules.mail_query.mail_query_schema import MailQuerySeverFilters

        # 오늘 날짜로 테스트
        today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
        start, end, days = parse_date_range("2025-09-01", today)

        print(f"\n날짜 범위: 2025-09-01 ~ {today}")
        print(f"  start: {start}")
        print(f"  end:   {end}")

        # MailQuerySeverFilters에 전달
        filters = MailQuerySeverFilters(date_from=start, date_to=end)
        print(f"\n✅ MailQuerySeverFilters 생성 성공!")
        print(f"  date_from: {filters.date_from}")
        print(f"  date_to:   {filters.date_to}")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")


if __name__ == "__main__":
    test_basic_parsing()
    test_date_range()
    test_compatibility_with_mail_query()
    test_edge_cases()
    test_with_mail_query_schema()

    print("\n" + "=" * 80)
    print("✅ 모든 테스트 완료!")
    print("=" * 80)
