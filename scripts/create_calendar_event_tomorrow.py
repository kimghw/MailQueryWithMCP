#!/usr/bin/env python3
"""
내일 날짜로 캘린더 일정 생성
"""

import sys
import asyncio
from datetime import datetime, timedelta

sys.path.insert(0, '.')


async def create_tomorrow_event():
    """내일 날짜로 유아교육 진흥원 일정 생성"""
    from modules.mail_query_MCP.mcp_server.handlers import MCPHandlers

    # 내일 날짜 계산
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_str = tomorrow.strftime('%Y-%m-%d')

    print("=" * 60)
    print(f"📅 {tomorrow_str} (내일) 일정 생성")
    print("=" * 60)

    handlers = MCPHandlers()

    # 일정 생성
    create_args = {
        "user_id": "kimghw",
        "subject": "유아교육 진흥원 방문",
        "start": f"{tomorrow_str}T09:00:00",
        "end": f"{tomorrow_str}T17:00:00",
        "body": "유아교육 진흥원 방문 일정",
        "location": "유아교육 진흥원",
        "is_all_day": False
    }

    print(f"\n📝 일정 정보:")
    print(f"   날짜: {tomorrow_str} ({tomorrow.strftime('%A')})")
    print(f"   시간: 09:00 ~ 17:00")
    print(f"   위치: 유아교육 진흥원")

    try:
        result = await handlers.handle_calendar_call_tool(
            "calendar_create_event",
            create_args
        )

        print(f"\n✅ 일정 생성 완료!")
        print(result[0].text)

    except Exception as e:
        print(f"\n❌ 일정 생성 실패: {e}")


if __name__ == "__main__":
    asyncio.run(create_tomorrow_event())
