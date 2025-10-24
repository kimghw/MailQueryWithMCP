"""
Calendar Handlers 테스트
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from modules.calendar_mcp import CalendarHandlers


@pytest.fixture
def calendar_handlers():
    """CalendarHandlers 인스턴스 생성"""
    return CalendarHandlers()


@pytest.mark.asyncio
async def test_calendar_handlers_init():
    """CalendarHandlers 초기화 테스트"""
    handlers = CalendarHandlers()
    assert handlers is not None
    assert hasattr(handlers, 'calendar_handler')
    assert hasattr(handlers, 'handle_calendar_list_tools')
    assert hasattr(handlers, 'handle_calendar_call_tool')


@pytest.mark.asyncio
async def test_list_calendar_tools(calendar_handlers):
    """Calendar 도구 목록 조회 테스트"""
    tools = await calendar_handlers.handle_calendar_list_tools()

    assert len(tools) == 5

    tool_names = [tool.name for tool in tools]
    assert "calendar_list_events" in tool_names
    assert "calendar_create_event" in tool_names
    assert "calendar_update_event" in tool_names
    assert "calendar_delete_event" in tool_names
    assert "calendar_get_event" in tool_names


@pytest.mark.asyncio
async def test_calendar_list_events_schema(calendar_handlers):
    """calendar_list_events 도구 스키마 검증"""
    tools = await calendar_handlers.handle_calendar_list_tools()

    list_events_tool = next(t for t in tools if t.name == "calendar_list_events")

    assert list_events_tool.description is not None
    assert "일정 목록" in list_events_tool.description

    schema = list_events_tool.inputSchema
    assert "user_id" in schema["properties"]
    assert "start_date" in schema["properties"]
    assert "end_date" in schema["properties"]
    assert "limit" in schema["properties"]
    assert "search_query" in schema["properties"]

    assert "user_id" in schema["required"]


@pytest.mark.asyncio
async def test_calendar_create_event_schema(calendar_handlers):
    """calendar_create_event 도구 스키마 검증"""
    tools = await calendar_handlers.handle_calendar_list_tools()

    create_event_tool = next(t for t in tools if t.name == "calendar_create_event")

    assert create_event_tool.description is not None
    assert "일정을 생성" in create_event_tool.description

    schema = create_event_tool.inputSchema
    assert "user_id" in schema["properties"]
    assert "subject" in schema["properties"]
    assert "start" in schema["properties"]
    assert "end" in schema["properties"]
    assert "body" in schema["properties"]
    assert "location" in schema["properties"]
    assert "attendees" in schema["properties"]
    assert "is_all_day" in schema["properties"]
    assert "is_online_meeting" in schema["properties"]

    assert set(schema["required"]) == {"user_id", "subject", "start", "end"}


@pytest.mark.asyncio
async def test_mail_query_mcp_integration():
    """mail_query_MCP와의 통합 테스트"""
    from modules.mail_query_MCP.mcp_server.handlers import MCPHandlers

    handlers = MCPHandlers()

    # CalendarHandlers가 상속되었는지 확인
    assert hasattr(handlers, 'handle_calendar_list_tools')
    assert hasattr(handlers, 'handle_calendar_call_tool')
    assert hasattr(handlers, 'calendar_handler')

    # 모든 도구 목록 조회
    tools = await handlers.handle_list_tools()

    # Calendar 도구 확인
    calendar_tool_names = [t.name for t in tools if t.name.startswith("calendar_")]
    assert len(calendar_tool_names) == 5

    # Mail Query 도구 확인
    mail_tool_names = [t.name for t in tools if t.name in ["query_email", "query_email_help", "help"]]
    assert len(mail_tool_names) == 3

    # Attachment 도구 확인
    attachment_tool_names = [t.name for t in tools if "attachment" in t.name.lower()]
    assert len(attachment_tool_names) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
