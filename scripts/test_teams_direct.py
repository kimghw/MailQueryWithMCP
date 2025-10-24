#!/usr/bin/env python3
"""
Teams Handler 직접 테스트 (mcp 의존성 없이)
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import TeamsHandler directly (teams_handler.py는 mcp에 의존하지 않음)
import importlib.util
spec = importlib.util.spec_from_file_location(
    "teams_handler",
    PROJECT_ROOT / "modules" / "teams_mcp" / "teams_handler.py"
)
teams_handler_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teams_handler_module)
TeamsHandler = teams_handler_module.TeamsHandler


async def test_list_chats(user_id: str):
    """채팅 목록 조회 테스트"""
    print(f"\n📋 채팅 목록 조회 중...")
    print(f"사용자: {user_id}\n")

    handler = TeamsHandler()
    result = await handler.list_chats(user_id)

    if result.get("success"):
        chats = result.get("chats", [])
        print(f"✅ 총 {len(chats)}개 채팅 조회 완료\n")

        for idx, chat in enumerate(chats, 1):
            chat_type = chat.get("chatType", "unknown")
            chat_id = chat.get("id")
            topic = chat.get("topic", "(제목 없음)")

            type_emoji = "👤" if chat_type == "oneOnOne" else "👥"
            print(f"{idx}. {type_emoji} [{chat_type}] {topic}")
            print(f"   ID: {chat_id}\n")

        return chats
    else:
        print(f"❌ 실패: {result.get('message')}")
        print(f"상태 코드: {result.get('status_code', 'N/A')}")
        return None


async def test_send_message(user_id: str, chat_id: str, message: str):
    """메시지 전송 테스트"""
    print(f"\n📤 메시지 전송 중...")
    print(f"사용자: {user_id}")
    print(f"채팅 ID: {chat_id}")
    print(f"메시지: {message}\n")

    handler = TeamsHandler()
    result = await handler.send_chat_message(user_id, chat_id, message)

    if result.get("success"):
        print(f"✅ 메시지 전송 성공!")
        print(f"Message ID: {result.get('message_id')}")
    else:
        print(f"❌ 실패: {result.get('message')}")
        print(f"상태 코드: {result.get('status_code', 'N/A')}")

    return result


async def main():
    """메인 함수"""
    print("=" * 60)
    print("Teams Chat Handler 직접 테스트")
    print("=" * 60)

    # kimghw 계정으로 테스트
    user_id = "kimghw@example.com"  # 실제 이메일로 변경 필요

    # 1. 채팅 목록 조회
    chats = await test_list_chats(user_id)

    if not chats:
        print("\n⚠️  채팅 목록을 가져올 수 없습니다.")
        print("가능한 원인:")
        print("  1. 액세스 토큰이 없거나 만료됨")
        print("  2. 사용자가 DB에 등록되지 않음")
        print("  3. Azure AD 권한 부족 (Chat.Read 필요)")
        return

    # 2. 첫 번째 채팅에 메시지 전송
    if chats:
        first_chat = chats[0]
        chat_id = first_chat.get("id")

        print("\n" + "=" * 60)
        print(f"첫 번째 채팅에 '안녕' 메시지 전송 시도...")
        print("=" * 60)

        await test_send_message(user_id, chat_id, "안녕")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  중단됨")
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
