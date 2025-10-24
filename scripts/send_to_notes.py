#!/usr/bin/env python3
"""
Teams Notes 채팅에 메시지 전송
"""

import asyncio
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
    """Notes 채팅에 메시지 전송"""
    user_id = "kimghw"
    notes_chat_id = "48:notes"  # Teams Notes 특별 채팅 ID

    handler = TeamsHandler()

    print("=" * 60)
    print("Teams Notes 채팅에 '안녕' 메시지 전송")
    print("=" * 60)
    print(f"Chat ID: {notes_chat_id}\n")

    # Send message to Notes
    result = await handler.send_chat_message(user_id, notes_chat_id, "안녕")

    if result.get("success"):
        print(f"✅ Notes 채팅에 메시지 전송 성공!")
        print(f"Message ID: {result.get('message_id')}")
    else:
        print(f"❌ 메시지 전송 실패: {result.get('message')}")
        print(f"상태 코드: {result.get('status_code', 'N/A')}")
        if result.get("error"):
            print(f"오류 상세: {result.get('error')}")


if __name__ == "__main__":
    asyncio.run(main())
