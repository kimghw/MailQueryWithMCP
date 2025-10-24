#!/usr/bin/env python3
"""
kimghw만 있는 모든 채팅 찾기
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
    """모든 채팅 확인"""
    user_id = "kimghw"
    kimghw_user_id = "8824239d-ed13-4a38-8c93-cb9ea07095f6"

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
    print("모든 채팅 확인 - kimghw만 있는 채팅 찾기")
    print("=" * 60)

    result = await handler.list_chats(user_id)
    if not result.get("success"):
        print(f"❌ 채팅 목록 조회 실패: {result.get('message')}")
        return

    chats = result.get("chats", [])
    print(f"총 {len(chats)}개 채팅 검색 중...\n")

    found_chats = []

    async with httpx.AsyncClient() as client:
        for idx, chat in enumerate(chats, 1):
            chat_id = chat.get("id")
            chat_type = chat.get("chatType")
            topic = chat.get("topic", "(제목 없음)")

            # Get members
            response = await client.get(
                f"https://graph.microsoft.com/v1.0/chats/{chat_id}/members",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code == 200:
                data = response.json()
                members = data.get("value", [])

                # Check if kimghw is the only REAL user (excluding bots)
                real_members = [m for m in members if m.get("userId")]

                print(f"{idx}. [{chat_type}] {topic}")
                print(f"   멤버 수: {len(members)} (실제 사용자: {len(real_members)})")

                for m in members:
                    display_name = m.get("displayName", "N/A")
                    email = m.get("email", "N/A")
                    user_id_val = m.get("userId", "N/A")
                    print(f"   - {display_name} ({email}) [ID: {user_id_val}]")

                # 실제 사용자가 kimghw 1명뿐인 경우
                if len(real_members) == 1 and real_members[0].get("userId") == kimghw_user_id:
                    found_chats.append({
                        "chat": chat,
                        "members": members
                    })
                    print(f"   ⭐ kimghw만 있는 채팅 발견!")

                print()

    print("=" * 60)
    print(f"결과: kimghw만 있는 채팅 {len(found_chats)}개 발견")
    print("=" * 60)

    for i, item in enumerate(found_chats, 1):
        chat = item["chat"]
        members = item["members"]
        print(f"{i}. ID: {chat.get('id')}")
        print(f"   Type: {chat.get('chatType')}")
        print(f"   Topic: {chat.get('topic', '(제목 없음)')}")
        print(f"   Members: {[m.get('displayName') for m in members]}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
