#!/usr/bin/env python3
"""
kimghw 계정으로 Teams 채팅에 '안녕' 메시지 전송
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import TeamsHandler directly (without MCP dependencies)
import importlib.util
spec = importlib.util.spec_from_file_location(
    "teams_handler",
    PROJECT_ROOT / "modules" / "teams_mcp" / "teams_handler.py"
)
teams_handler_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teams_handler_module)
TeamsHandler = teams_handler_module.TeamsHandler

from infra.core.logger import get_logger

logger = get_logger(__name__)


async def main():
    """메인 함수"""
    user_id = "kimghw"

    print("=" * 60)
    print("Teams Chat - kimghw 계정으로 '안녕' 메시지 전송")
    print("=" * 60)

    # TeamsHandler 인스턴스 생성
    handler = TeamsHandler()

    # 1. 채팅 목록 조회
    print(f"\n📋 Step 1: 채팅 목록 조회 중...")
    print(f"사용자: {user_id}\n")

    result = await handler.list_chats(user_id)

    if not result.get("success"):
        print(f"❌ 채팅 목록 조회 실패: {result.get('message')}")
        print(f"상태 코드: {result.get('status_code', 'N/A')}")
        return

    chats = result.get("chats", [])
    print(f"✅ 총 {len(chats)}개 채팅 조회 완료\n")

    if not chats:
        print("⚠️  활성 채팅이 없습니다.")
        return

    # 채팅 목록 출력
    for idx, chat in enumerate(chats, 1):
        chat_type = chat.get("chatType", "unknown")
        chat_id = chat.get("id")
        topic = chat.get("topic", "(제목 없음)")

        type_emoji = "👤" if chat_type == "oneOnOne" else "👥"
        print(f"{idx}. {type_emoji} [{chat_type}] {topic}")
        print(f"   ID: {chat_id}\n")

    # 2. 첫 번째 채팅에 메시지 전송
    first_chat = chats[0]
    chat_id = first_chat.get("id")
    chat_topic = first_chat.get("topic", "(제목 없음)")

    print("=" * 60)
    print(f"📤 Step 2: 메시지 전송")
    print("=" * 60)
    print(f"대상 채팅: {chat_topic}")
    print(f"채팅 ID: {chat_id}")
    print(f"메시지: 안녕\n")

    result = await handler.send_chat_message(user_id, chat_id, "안녕")

    if result.get("success"):
        print(f"✅ 메시지 전송 성공!")
        print(f"Message ID: {result.get('message_id')}")
    else:
        print(f"❌ 메시지 전송 실패: {result.get('message')}")
        print(f"상태 코드: {result.get('status_code', 'N/A')}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}", exc_info=True)
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
