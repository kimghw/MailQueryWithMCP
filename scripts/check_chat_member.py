#!/usr/bin/env python3
"""
채팅 멤버 정보 조회
"""

import asyncio
import httpx
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import TeamsHandler directly
import importlib.util
spec = importlib.util.spec_from_file_location(
    "teams_handler",
    PROJECT_ROOT / "modules" / "teams_mcp" / "teams_handler.py"
)
teams_handler_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teams_handler_module)
TeamsHandler = teams_handler_module.TeamsHandler


async def main():
    """채팅 멤버 조회"""
    user_id = "kimghw"
    chat_id = "19:554c2a38-7b29-4527-9dda-21273b159882_8824239d-ed13-4a38-8c93-cb9ea07095f6@unq.gbl.spaces"

    handler = TeamsHandler()

    # Get access token using handler's internal method
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

    # Get chat members
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://graph.microsoft.com/v1.0/chats/{chat_id}/members",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        print("=" * 60)
        print("채팅 멤버 정보")
        print("=" * 60)

        if response.status_code == 200:
            data = response.json()
            members = data.get("value", [])
            print(f"총 {len(members)}명 참여 중\n")

            for idx, member in enumerate(members, 1):
                display_name = member.get("displayName", "N/A")
                email = member.get("email", "N/A")
                user_id_val = member.get("userId", "N/A")
                roles = member.get("roles", [])

                print(f"{idx}. {display_name}")
                print(f"   이메일: {email}")
                print(f"   User ID: {user_id_val}")
                print(f"   역할: {roles if roles else '일반 멤버'}")
                print()
        else:
            print(f"❌ 오류: {response.status_code}")
            print(response.text)


if __name__ == "__main__":
    asyncio.run(main())
