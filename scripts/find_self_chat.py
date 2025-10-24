#!/usr/bin/env python3
"""
kimghw 본인과의 채팅 찾기
"""

import asyncio
import httpx
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import importlib.util
spec = importlib.util.spec_from_file_location(
    "teams_handler",
    PROJECT_ROOT / "modules" / "teams_mcp" / "teams_handler.py"
)
teams_handler_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teams_handler_module)
TeamsHandler = teams_handler_module.TeamsHandler


async def main():
    """kimghw 본인과의 채팅 찾기"""
    user_id = "kimghw"
    kimghw_email = "kimghw@krs.co.kr"

    handler = TeamsHandler()

    # Get access token
    import sqlite3
    db_path = PROJECT_ROOT / "data" / "graphapi.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT access_token FROM accounts WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        print(f"❌ {user_id} 계정을 찾을 수 없습니다")
        return

    access_token = result[0]

    # Get all chats
    print("=" * 60)
    print("kimghw 본인과의 채팅 찾기")
    print("=" * 60)

    result = await handler.list_chats(user_id)
    if not result.get("success"):
        print(f"❌ 채팅 목록 조회 실패: {result.get('message')}")
        return

    chats = result.get("chats", [])
    print(f"총 {len(chats)}개 채팅 검색 중...\n")

    # Check each chat for self-chat (only kimghw in members)
    self_chat = None

    async with httpx.AsyncClient() as client:
        for idx, chat in enumerate(chats, 1):
            chat_id = chat.get("id")
            chat_type = chat.get("chatType")

            # Get members
            response = await client.get(
                f"https://graph.microsoft.com/v1.0/chats/{chat_id}/members",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code == 200:
                data = response.json()
                members = data.get("value", [])

                # Check if only kimghw is in the chat (self-chat)
                if len(members) == 1 and members[0].get("email") == kimghw_email:
                    self_chat = chat
                    print(f"✅ 자기 자신과의 채팅 발견!")
                    print(f"Chat ID: {chat_id}")
                    print(f"Chat Type: {chat_type}")
                    print(f"멤버: {members[0].get('displayName')} ({members[0].get('email')})")
                    break

                # Print progress
                if idx % 5 == 0:
                    print(f"검색 중... {idx}/{len(chats)}")

    if not self_chat:
        print("\n❌ 자기 자신과의 채팅을 찾을 수 없습니다.")
        print("\nTeams에서는 일반적으로 자기 자신과의 1:1 채팅을 만들 수 없습니다.")
        print("대신 그룹 채팅이나 다른 사용자와의 채팅에 메시지를 보낼 수 있습니다.")
        return

    # Send message to self
    print("\n" + "=" * 60)
    print("메시지 전송")
    print("=" * 60)

    chat_id = self_chat.get("id")
    message_result = await handler.send_chat_message(user_id, chat_id, "안녕")

    if message_result.get("success"):
        print(f"✅ 메시지 전송 성공!")
        print(f"Message ID: {message_result.get('message_id')}")
    else:
        print(f"❌ 메시지 전송 실패: {message_result.get('message')}")


if __name__ == "__main__":
    asyncio.run(main())
