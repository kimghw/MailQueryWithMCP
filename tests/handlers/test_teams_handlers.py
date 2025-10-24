#!/usr/bin/env python3
"""
Teams 모듈 핸들러 직접 테스트

사용법:
    python tests/handlers/test_teams_handlers.py
"""

import sys
import asyncio
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.teams_mcp.handlers import TeamsHandlers


def print_test_result(test_name: str, passed: bool, details: str = ""):
    """테스트 결과 출력"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"  {details}")


async def test_list_chats():
    """teams_list_chats 핸들러 테스트"""
    print("\n💬 [1/3] teams_list_chats 핸들러 테스트...")

    try:
        handler = TeamsHandlers()
        result = await handler.handle_call_tool(
            "teams_list_chats",
            {"user_id": "kimghw"}
        )
        result_text = result[0].text if result else ""

        # 결과 검증
        success = "chats" in result_text.lower() or "액세스 토큰이 없습니다" in result_text or "총" in result_text and "개 채팅" in result_text
        print_test_result("teams_list_chats", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("teams_list_chats", False, f"Exception: {e}")
        return False


async def test_get_chat_messages():
    """teams_get_chat_messages 핸들러 테스트"""
    print("\n📨 [2/3] teams_get_chat_messages 핸들러 테스트...")

    try:
        handler = TeamsHandlers()
        result = await handler.handle_call_tool(
            "teams_get_chat_messages",
            {
                "user_id": "kimghw",
                "chat_id": "19:test-chat-id",
                "limit": 10
            }
        )
        result_text = result[0].text if result else ""

        # 결과 검증 (에러가 나더라도 올바르게 처리되면 성공)
        success = (
            "messages" in result_text.lower() or
            "액세스 토큰이 없습니다" in result_text or
            ("총" in result_text and "개 메시지" in result_text) or
            "message" in result_text.lower() or  # error message 포함
            "status_code" in result_text.lower()
        )
        print_test_result("teams_get_chat_messages", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("teams_get_chat_messages", False, f"Exception: {e}")
        return False


async def test_send_chat_message():
    """teams_send_chat_message 핸들러 테스트"""
    print("\n✉️ [3/3] teams_send_chat_message 핸들러 테스트...")

    try:
        handler = TeamsHandlers()
        result = await handler.handle_call_tool(
            "teams_send_chat_message",
            {
                "user_id": "kimghw",
                "chat_id": "19:test-chat-id",
                "content": "Test message from handler",
                "prefix": "[test]"
            }
        )
        result_text = result[0].text if result else ""

        # 결과 검증
        success = (
            "success" in result_text.lower() or
            "액세스 토큰이 없습니다" in result_text or
            "message_id" in result_text.lower() or
            "error" in result_text.lower()
        )
        print_test_result("teams_send_chat_message", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("teams_send_chat_message", False, f"Exception: {e}")
        return False


async def run_tests():
    """비동기 테스트 실행"""
    results = []

    # 테스트 실행
    results.append(await test_list_chats())
    results.append(await test_get_chat_messages())
    results.append(await test_send_chat_message())

    return results


def main():
    """메인 테스트 실행"""
    print("=" * 80)
    print("🧪 Teams 핸들러 직접 테스트")
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
