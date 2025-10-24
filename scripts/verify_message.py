#!/usr/bin/env python3
"""
전송한 메시지 확인
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
    """메시지 확인"""
    user_id = "kimghw"
    chat_id = "19:8824239d-ed13-4a38-8c93-cb9ea07095f6_358f0194-6b0e-4dd3-af35-c24fe8a9ec87@unq.gbl.spaces"

    handler = TeamsHandler()

    print("=" * 60)
    print("최근 메시지 조회")
    print("=" * 60)

    # Get recent messages from the chat
    result = await handler.get_chat_messages(user_id, chat_id, limit=10)

    if result.get("success"):
        messages = result.get("messages", [])
        print(f"총 {len(messages)}개 메시지\n")

        for idx, msg in enumerate(messages, 1):
            msg_id = msg.get("id")

            # Handle body content
            body = msg.get("body", {})
            if body:
                content = body.get("content", "")
            else:
                content = str(msg)[:200]

            # Handle from field safely
            from_field = msg.get("from")
            if from_field and isinstance(from_field, dict):
                user = from_field.get("user", {})
                from_user = user.get("displayName", "Unknown") if user else "Unknown"
            else:
                from_user = "Unknown"

            created_time = msg.get("createdDateTime", "")

            print(f"{idx}. [{created_time}] {from_user}")
            print(f"   ID: {msg_id}")
            print(f"   내용: {content[:100]}")
            print()
    else:
        print(f"❌ 메시지 조회 실패: {result.get('message')}")
        print(f"오류: {result.get('error')}")


if __name__ == "__main__":
    asyncio.run(main())
