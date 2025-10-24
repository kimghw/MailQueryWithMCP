#!/usr/bin/env python3
"""
Calendar 통합 테스트 스크립트
"""

import sys
import asyncio

sys.path.insert(0, '.')


async def test_calendar_module():
    """Calendar 모듈 테스트"""
    print("=" * 60)
    print("Calendar 모듈 테스트")
    print("=" * 60)

    try:
        from modules.calendar_mcp import CalendarHandler, CalendarHandlers

        # CalendarHandler 초기화
        print("\n1. CalendarHandler 초기화 테스트")
        handler = CalendarHandler()
        print("   ✅ CalendarHandler 초기화 성공")

        # CalendarHandlers 초기화
        print("\n2. CalendarHandlers 초기화 테스트")
        handlers = CalendarHandlers()
        print("   ✅ CalendarHandlers 초기화 성공")

        # 도구 목록 조회
        print("\n3. Calendar 도구 목록 조회")
        tools = await handlers.handle_calendar_list_tools()
        print(f"   ✅ {len(tools)}개의 Calendar 도구 발견:")
        for tool in tools:
            print(f"      • {tool.name}: {tool.description[:50]}...")

        print("\n✅ Calendar 모듈 테스트 완료")
        return True

    except Exception as e:
        print(f"\n❌ Calendar 모듈 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_mail_query_integration():
    """mail_query_MCP 통합 테스트"""
    print("\n" + "=" * 60)
    print("mail_query_MCP 통합 테스트")
    print("=" * 60)

    try:
        from modules.mail_query_MCP.mcp_server.handlers import MCPHandlers

        # MCPHandlers 초기화
        print("\n1. MCPHandlers 초기화 테스트")
        handlers = MCPHandlers()
        print("   ✅ MCPHandlers 초기화 성공")

        # CalendarHandlers 메서드 확인
        print("\n2. CalendarHandlers 상속 확인")
        assert hasattr(handlers, 'handle_calendar_list_tools'), "handle_calendar_list_tools 메서드 없음"
        print("   ✅ handle_calendar_list_tools 메서드 확인")

        assert hasattr(handlers, 'handle_calendar_call_tool'), "handle_calendar_call_tool 메서드 없음"
        print("   ✅ handle_calendar_call_tool 메서드 확인")

        assert hasattr(handlers, 'calendar_handler'), "calendar_handler 속성 없음"
        print("   ✅ calendar_handler 속성 확인")

        # 전체 도구 목록 조회
        print("\n3. 전체 도구 목록 조회")
        tools = await handlers.handle_list_tools()
        print(f"   ✅ 총 {len(tools)}개의 도구 발견")

        # Calendar 도구 확인
        calendar_tools = [t for t in tools if t.name.startswith('calendar_')]
        print(f"\n4. Calendar 도구 확인 ({len(calendar_tools)}개)")
        for tool in calendar_tools:
            print(f"   • {tool.name}")

        assert len(calendar_tools) == 5, f"Calendar 도구 5개 필요, {len(calendar_tools)}개 발견"
        print("   ✅ Calendar 도구 5개 모두 확인")

        # Mail Query 도구 확인
        mail_tools = [t for t in tools if t.name in ['query_email', 'query_email_help', 'help']]
        print(f"\n5. Mail Query 도구 확인 ({len(mail_tools)}개)")
        for tool in mail_tools:
            print(f"   • {tool.name}")

        assert len(mail_tools) == 3, f"Mail Query 도구 3개 필요, {len(mail_tools)}개 발견"
        print("   ✅ Mail Query 도구 3개 모두 확인")

        # Attachment 도구 확인
        attachment_tools = [t for t in tools if 'attachment' in t.name.lower()]
        print(f"\n6. Attachment 도구 확인 ({len(attachment_tools)}개)")
        for tool in attachment_tools:
            print(f"   • {tool.name}")

        print("\n✅ mail_query_MCP 통합 테스트 완료")
        return True

    except Exception as e:
        print(f"\n❌ mail_query_MCP 통합 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_schemas():
    """도구 스키마 검증 테스트"""
    print("\n" + "=" * 60)
    print("도구 스키마 검증 테스트")
    print("=" * 60)

    try:
        from modules.calendar_mcp import CalendarHandlers

        handlers = CalendarHandlers()
        tools = await handlers.handle_calendar_list_tools()

        # calendar_list_events 스키마 검증
        print("\n1. calendar_list_events 스키마 검증")
        list_tool = next(t for t in tools if t.name == "calendar_list_events")
        schema = list_tool.inputSchema

        assert "user_id" in schema["properties"], "user_id 속성 없음"
        assert "start_date" in schema["properties"], "start_date 속성 없음"
        assert "end_date" in schema["properties"], "end_date 속성 없음"
        assert "limit" in schema["properties"], "limit 속성 없음"
        assert "search_query" in schema["properties"], "search_query 속성 없음"
        assert "user_id" in schema["required"], "user_id가 required에 없음"
        print("   ✅ calendar_list_events 스키마 검증 완료")

        # calendar_create_event 스키마 검증
        print("\n2. calendar_create_event 스키마 검증")
        create_tool = next(t for t in tools if t.name == "calendar_create_event")
        schema = create_tool.inputSchema

        assert "user_id" in schema["properties"], "user_id 속성 없음"
        assert "subject" in schema["properties"], "subject 속성 없음"
        assert "start" in schema["properties"], "start 속성 없음"
        assert "end" in schema["properties"], "end 속성 없음"
        assert set(schema["required"]) == {"user_id", "subject", "start", "end"}, "required 필드 불일치"
        print("   ✅ calendar_create_event 스키마 검증 완료")

        # calendar_update_event 스키마 검증
        print("\n3. calendar_update_event 스키마 검증")
        update_tool = next(t for t in tools if t.name == "calendar_update_event")
        schema = update_tool.inputSchema

        assert "user_id" in schema["properties"], "user_id 속성 없음"
        assert "event_id" in schema["properties"], "event_id 속성 없음"
        assert set(schema["required"]) == {"user_id", "event_id"}, "required 필드 불일치"
        print("   ✅ calendar_update_event 스키마 검증 완료")

        # calendar_delete_event 스키마 검증
        print("\n4. calendar_delete_event 스키마 검증")
        delete_tool = next(t for t in tools if t.name == "calendar_delete_event")
        schema = delete_tool.inputSchema

        assert "user_id" in schema["properties"], "user_id 속성 없음"
        assert "event_id" in schema["properties"], "event_id 속성 없음"
        assert set(schema["required"]) == {"user_id", "event_id"}, "required 필드 불일치"
        print("   ✅ calendar_delete_event 스키마 검증 완료")

        # calendar_get_event 스키마 검증
        print("\n5. calendar_get_event 스키마 검증")
        get_tool = next(t for t in tools if t.name == "calendar_get_event")
        schema = get_tool.inputSchema

        assert "user_id" in schema["properties"], "user_id 속성 없음"
        assert "event_id" in schema["properties"], "event_id 속성 없음"
        assert set(schema["required"]) == {"user_id", "event_id"}, "required 필드 불일치"
        print("   ✅ calendar_get_event 스키마 검증 완료")

        print("\n✅ 도구 스키마 검증 테스트 완료")
        return True

    except Exception as e:
        print(f"\n❌ 도구 스키마 검증 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """메인 테스트 실행"""
    print("\n")
    print("█" * 60)
    print("Calendar MCP 모듈 통합 테스트")
    print("█" * 60)

    results = []

    # 1. Calendar 모듈 테스트
    result1 = await test_calendar_module()
    results.append(("Calendar 모듈", result1))

    # 2. mail_query_MCP 통합 테스트
    result2 = await test_mail_query_integration()
    results.append(("mail_query_MCP 통합", result2))

    # 3. 도구 스키마 검증 테스트
    result3 = await test_tool_schemas()
    results.append(("도구 스키마 검증", result3))

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ 성공" if passed else "❌ 실패"
        print(f"{status} - {name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 모든 테스트 통과!")
        print("=" * 60)
        return 0
    else:
        print("⚠️ 일부 테스트 실패")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
