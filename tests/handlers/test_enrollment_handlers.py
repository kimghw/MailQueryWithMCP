#!/usr/bin/env python3
"""
Enrollment 모듈 핸들러 직접 테스트

사용법:
    python tests/handlers/test_enrollment_handlers.py
"""

import sys
import asyncio
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.enrollment.mcp_server.handlers import AuthAccountHandlers


def print_test_result(test_name: str, passed: bool, details: str = ""):
    """테스트 결과 출력"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"  {details}")


async def test_register_account():
    """register_account 핸들러 테스트"""
    print("\n🔐 [1/4] register_account 핸들러 테스트...")

    try:
        handler = AuthAccountHandlers()

        # handle_call_tool을 통해 호출
        result = await handler.handle_call_tool("register_account", {"use_env_vars": True})
        result_text = result[0].text if result else ""

        # 결과 검증
        success = "계정 등록 완료" in result_text or "계정 업데이트 완료" in result_text
        print_test_result("register_account", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("register_account", False, f"Exception: {e}")
        return False


async def test_list_active_accounts():
    """list_active_accounts 핸들러 테스트"""
    print("\n📋 [2/4] list_active_accounts 핸들러 테스트...")

    try:
        handler = AuthAccountHandlers()
        result = await handler.handle_call_tool("list_active_accounts", {})
        result_text = result[0].text if result else ""

        # 결과 검증
        success = "활성 계정 목록" in result_text or "kimghw" in result_text
        print_test_result("list_active_accounts", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("list_active_accounts", False, f"Exception: {e}")
        return False


async def test_get_account_status():
    """get_account_status 핸들러 테스트"""
    print("\n📊 [3/4] get_account_status 핸들러 테스트...")

    try:
        handler = AuthAccountHandlers()
        result = await handler.handle_call_tool("get_account_status", {"user_id": "kimghw"})
        result_text = result[0].text if result else ""

        # 결과 검증
        success = "계정 상태 상세 정보" in result_text
        print_test_result("get_account_status", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("get_account_status", False, f"Exception: {e}")
        return False


async def test_start_authentication():
    """start_authentication 핸들러 테스트"""
    print("\n🔑 [4/4] start_authentication 핸들러 테스트...")

    try:
        handler = AuthAccountHandlers()
        result = await handler.handle_call_tool("start_authentication", {"user_id": "kimghw"})
        result_text = result[0].text if result else ""

        # 결과 검증
        success = "https://login.microsoftonline.com" in result_text
        print_test_result("start_authentication", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("start_authentication", False, f"Exception: {e}")
        return False


async def run_tests():
    """비동기 테스트 실행"""
    results = []

    # 테스트 실행
    results.append(await test_register_account())
    results.append(await test_list_active_accounts())
    results.append(await test_get_account_status())
    results.append(await test_start_authentication())

    return results


def main():
    """메인 테스트 실행"""
    print("=" * 80)
    print("🧪 Enrollment 핸들러 직접 테스트")
    print("=" * 80)

    # 비동기 테스트 실행
    results = asyncio.run(run_tests())

    # 결과 요약
    print("\n" + "=" * 80)
    print("📊 테스트 결과 요약")
    print("=" * 80)

    total = len(results)
    passed = sum(results)
    failed = total - passed

    print(f"총 테스트: {total}개")
    print(f"✅ 성공: {passed}개")
    print(f"❌ 실패: {failed}개")

    if failed == 0:
        print("\n✅ 모든 테스트 통과!")
        return 0
    else:
        print(f"\n❌ {failed}개의 테스트 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())
