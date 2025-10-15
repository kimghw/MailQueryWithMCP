#!/usr/bin/env python3
"""
Client-side blocking 기능 테스트
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules"))

from mail_query.clientblock import ClientBlocker
from mail_query.mail_query_schema import GraphMailItem


def test_blocker_basic():
    """기본 blocking 테스트"""
    print("=" * 60)
    print("Test 1: 기본 blocking 테스트")
    print("=" * 60)

    blocker = ClientBlocker(["noreply@", "spam.com", "block@krs.co.kr"])

    # Test cases
    test_cases = [
        ("noreply@github.com", True, "noreply@ 패턴 매칭"),
        ("user@spam.com", True, "spam.com 도메인 매칭"),
        ("block@krs.co.kr", True, "정확한 주소 매칭"),
        ("valid@example.com", False, "정상 메일"),
        ("NOREPLY@GITHUB.COM", True, "대소문자 무시"),
    ]

    passed = 0
    for email, expected_blocked, description in test_cases:
        result = blocker.is_blocked(email)
        status = "✓" if result == expected_blocked else "✗"
        print(f"{status} {description}: {email} -> {'차단' if result else '허용'}")
        if result == expected_blocked:
            passed += 1

    print(f"\n결과: {passed}/{len(test_cases)} 통과\n")
    return passed == len(test_cases)


def test_blocker_filter_messages():
    """메시지 필터링 테스트"""
    print("=" * 60)
    print("Test 2: 메시지 필터링 테스트")
    print("=" * 60)

    blocker = ClientBlocker(["noreply@", "spam.com"])

    # Create mock messages
    messages = [
        GraphMailItem(
            id="1",
            subject="Normal email",
            from_address={"emailAddress": {"address": "user@example.com"}},
            received_date_time="2024-01-01T00:00:00Z",
            body_preview="Normal content"
        ),
        GraphMailItem(
            id="2",
            subject="Spam email",
            from_address={"emailAddress": {"address": "noreply@spam.com"}},
            received_date_time="2024-01-01T00:00:00Z",
            body_preview="Spam content"
        ),
        GraphMailItem(
            id="3",
            subject="Another normal",
            from_address={"emailAddress": {"address": "friend@example.com"}},
            received_date_time="2024-01-01T00:00:00Z",
            body_preview="Friend content"
        ),
        GraphMailItem(
            id="4",
            subject="GitHub notification",
            from_address={"emailAddress": {"address": "noreply@github.com"}},
            received_date_time="2024-01-01T00:00:00Z",
            body_preview="GitHub content"
        ),
    ]

    print(f"원본 메시지 수: {len(messages)}")
    for msg in messages:
        sender = msg.from_address.get("emailAddress", {}).get("address", "")
        print(f"  - {msg.subject} ({sender})")

    filtered = blocker.filter_messages(messages)

    print(f"\n필터링 후 메시지 수: {len(filtered)}")
    for msg in filtered:
        sender = msg.from_address.get("emailAddress", {}).get("address", "")
        print(f"  - {msg.subject} ({sender})")

    expected_count = 2  # Only normal emails should remain
    passed = len(filtered) == expected_count

    print(f"\n결과: {'✓ 통과' if passed else '✗ 실패'}")
    print(f"기대값: {expected_count}개, 실제값: {len(filtered)}개\n")

    return passed


def test_blocker_empty():
    """빈 blocker 테스트"""
    print("=" * 60)
    print("Test 3: 빈 blocker 테스트")
    print("=" * 60)

    blocker = ClientBlocker([])

    test_email = "any@example.com"
    result = blocker.is_blocked(test_email)

    print(f"차단 패턴: 없음")
    print(f"테스트 메일: {test_email}")
    print(f"결과: {'차단' if result else '허용'}")

    passed = not result  # Should not be blocked
    print(f"\n결과: {'✓ 통과' if passed else '✗ 실패'}\n")

    return passed


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Client-side Blocking 기능 테스트")
    print("=" * 60 + "\n")

    tests = [
        test_blocker_basic,
        test_blocker_filter_messages,
        test_blocker_empty,
    ]

    results = []
    for test_func in tests:
        try:
            results.append(test_func())
        except Exception as e:
            print(f"✗ 테스트 실패: {e}\n")
            results.append(False)

    # Summary
    print("=" * 60)
    print("테스트 요약")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"통과: {passed}/{total}")
    print(f"실패: {total - passed}/{total}")

    if passed == total:
        print("\n✓ 모든 테스트 통과!")
        return 0
    else:
        print(f"\n✗ {total - passed}개 테스트 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())
