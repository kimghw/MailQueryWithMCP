#!/usr/bin/env python3
"""
Calendar 일정 생성 테스트
"""

import sys
import asyncio
import json

sys.path.insert(0, '.')


async def test_create_event():
    """유아교육 진흥원 방문 일정 생성"""
    from modules.mail_query_MCP.mcp_server.handlers import MCPHandlers

    print("=" * 60)
    print("📅 Calendar 일정 생성 테스트")
    print("=" * 60)

    handlers = MCPHandlers()

    # 1. 일정 생성
    print("\n1️⃣ 일정 생성: 유아교육 진흥원 방문 (2024-10-25)")

    create_args = {
        "user_id": "kimghw",
        "subject": "유아교육 진흥원 방문",
        "start": "2024-10-25T09:00:00",
        "end": "2024-10-25T17:00:00",
        "body": "유아교육 진흥원 방문 일정",
        "location": "유아교육 진흥원",
        "is_all_day": False
    }

    print(f"\n요청 데이터:")
    print(json.dumps(create_args, indent=2, ensure_ascii=False))

    try:
        result = await handlers.handle_calendar_call_tool(
            "calendar_create_event",
            create_args
        )

        print(f"\n✅ 일정 생성 결과:")
        print(result[0].text)

        # 생성된 event_id 추출
        import re
        text = result[0].text
        event_id_match = re.search(r'"event_id":\s*"([^"]+)"', text)

        if event_id_match:
            event_id = event_id_match.group(1)
            print(f"\n📌 생성된 Event ID: {event_id}")
            return event_id
        else:
            print("\n⚠️ Event ID를 찾을 수 없습니다")
            return None

    except Exception as e:
        print(f"\n❌ 일정 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_list_events(event_id=None):
    """10월 일정 목록 조회"""
    from modules.mail_query_MCP.mcp_server.handlers import MCPHandlers

    print("\n" + "=" * 60)
    print("📅 10월 일정 목록 조회")
    print("=" * 60)

    handlers = MCPHandlers()

    list_args = {
        "user_id": "kimghw",
        "start_date": "2024-10-20",
        "end_date": "2024-10-31",
        "limit": 100
    }

    print(f"\n요청 데이터:")
    print(json.dumps(list_args, indent=2, ensure_ascii=False))

    try:
        result = await handlers.handle_calendar_call_tool(
            "calendar_list_events",
            list_args
        )

        print(f"\n✅ 일정 목록 조회 결과:")
        print(result[0].text)

        # 유아교육 진흥원 일정 찾기
        text = result[0].text
        if "유아교육 진흥원" in text:
            print("\n✅ '유아교육 진흥원' 일정을 찾았습니다!")
        else:
            print("\n⚠️ '유아교육 진흥원' 일정을 찾지 못했습니다")

        return True

    except Exception as e:
        print(f"\n❌ 일정 목록 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_event(event_id):
    """특정 일정 상세 조회"""
    if not event_id:
        print("\n⚠️ Event ID가 없어 상세 조회를 건너뜁니다")
        return

    from modules.mail_query_MCP.mcp_server.handlers import MCPHandlers

    print("\n" + "=" * 60)
    print("📅 일정 상세 조회")
    print("=" * 60)

    handlers = MCPHandlers()

    get_args = {
        "user_id": "kimghw",
        "event_id": event_id
    }

    print(f"\n요청 데이터:")
    print(json.dumps(get_args, indent=2, ensure_ascii=False))

    try:
        result = await handlers.handle_calendar_call_tool(
            "calendar_get_event",
            get_args
        )

        print(f"\n✅ 일정 상세 조회 결과:")
        print(result[0].text)

        return True

    except Exception as e:
        print(f"\n❌ 일정 상세 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """메인 테스트"""
    print("\n")
    print("█" * 60)
    print("Calendar API 테스트 - 유아교육 진흥원 방문 일정")
    print("█" * 60)

    # 1. 일정 생성
    event_id = await test_create_event()

    # 2. 일정 목록 조회
    await test_list_events(event_id)

    # 3. 일정 상세 조회
    if event_id:
        await test_get_event(event_id)

    print("\n" + "=" * 60)
    print("✅ 테스트 완료!")
    print("=" * 60)

    if event_id:
        print(f"\n💡 생성된 일정 정보:")
        print(f"   제목: 유아교육 진흥원 방문")
        print(f"   날짜: 2024-10-25 (금)")
        print(f"   시간: 09:00 ~ 17:00")
        print(f"   위치: 유아교육 진흥원")
        print(f"   Event ID: {event_id}")
        print(f"\n💡 일정 삭제가 필요하면 다음 명령을 사용하세요:")
        print(f'   calendar_delete_event(user_id="kimghw", event_id="{event_id}")')


if __name__ == "__main__":
    asyncio.run(main())
