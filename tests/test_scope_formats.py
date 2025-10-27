#!/usr/bin/env python3
"""
delegated_permissions 형식 호환성 테스트
"""

import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.enrollment.account._scope_validator import parse_scopes_from_storage

def test_scope_formats():
    """다양한 형식의 scope 문자열을 테스트"""

    print("\n=== Scope 형식 파싱 테스트 ===\n")

    test_cases = [
        {
            "name": "JSON 배열 (sync_dcr_accounts.py 형식)",
            "input": '["offline_access", "User.Read", "Mail.ReadWrite", "Files.ReadWrite"]',
            "expected": ["offline_access", "User.Read", "Mail.ReadWrite", "Files.ReadWrite"]
        },
        {
            "name": "쉼표 구분 (이전 dcr_service.py 형식)",
            "input": "offline_access,User.Read,Mail.ReadWrite,Files.ReadWrite",
            "expected": ["offline_access", "User.Read", "Mail.ReadWrite", "Files.ReadWrite"]
        },
        {
            "name": "공백 구분 (OAuth 2.0 표준)",
            "input": "offline_access User.Read Mail.ReadWrite Files.ReadWrite",
            "expected": ["offline_access", "User.Read", "Mail.ReadWrite", "Files.ReadWrite"]
        },
        {
            "name": "빈 문자열",
            "input": "",
            "expected": []
        },
        {
            "name": "None",
            "input": None,
            "expected": []
        },
        {
            "name": "단일 스코프",
            "input": "User.Read",
            "expected": ["User.Read"]
        },
        {
            "name": "쉼표와 공백 혼합 (공백 우선)",
            "input": "offline_access User.Read, Mail.ReadWrite",
            "expected": ["offline_access", "User.Read,", "Mail.ReadWrite"]  # 공백으로 분리됨
        }
    ]

    all_passed = True

    for i, test in enumerate(test_cases, 1):
        print(f"{i}. {test['name']}")
        print(f"   입력: {repr(test['input'])}")

        try:
            result = parse_scopes_from_storage(test['input'])
            print(f"   결과: {result}")

            if result == test['expected']:
                print(f"   ✅ 성공")
            else:
                print(f"   ❌ 실패 - 기대값: {test['expected']}")
                all_passed = False

        except Exception as e:
            print(f"   ❌ 예외 발생: {e}")
            all_passed = False

        print()

    # 실제 DB 데이터 테스트
    print("=== 실제 DB 데이터 테스트 ===\n")

    try:
        import sqlite3
        import json

        # GraphAPI DB의 실제 데이터 확인
        conn = sqlite3.connect('data/graphapi.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, delegated_permissions FROM accounts WHERE delegated_permissions IS NOT NULL LIMIT 3")

        for row in cursor.fetchall():
            user_id, perms = row
            print(f"사용자: {user_id}")
            print(f"저장된 값: {repr(perms)}")
            parsed = parse_scopes_from_storage(perms)
            print(f"파싱 결과: {parsed}")
            print(f"개수: {len(parsed)}개 스코프")
            print()

        conn.close()

    except Exception as e:
        print(f"DB 테스트 실패: {e}")

    # 결과 요약
    print("\n=== 테스트 요약 ===")
    if all_passed:
        print("✅ 모든 형식이 정상적으로 파싱됩니다!")
        print("\n지원 형식:")
        print("1. JSON 배열: [\"scope1\", \"scope2\"]")
        print("2. 쉼표 구분: scope1,scope2")
        print("3. 공백 구분: scope1 scope2")
    else:
        print("❌ 일부 테스트가 실패했습니다.")

    return all_passed

if __name__ == "__main__":
    success = test_scope_formats()
    exit(0 if success else 1)