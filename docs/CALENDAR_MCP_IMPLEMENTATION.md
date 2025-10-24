# Calendar MCP 모듈 구현 완료

## 개요

Microsoft Outlook Calendar API를 사용한 일정 관리 MCP 모듈을 구현하고, mail_query_MCP 모듈에서 상속하여 사용할 수 있도록 통합했습니다.

## 구현 내용

### 1. Calendar MCP 모듈 (`modules/calendar_mcp/`)

#### 파일 구조

```
modules/calendar_mcp/
├── __init__.py              # 모듈 초기화 및 export
├── calendar_handler.py      # Graph API 비즈니스 로직
├── handlers.py              # MCP 프로토콜 핸들러
├── schemas.py               # Pydantic 데이터 모델
├── README.md                # 모듈 문서
└── mcp_server/              # HTTP/stdio 서버 (선택적)
```

#### 주요 컴포넌트

##### CalendarHandler (`calendar_handler.py`)

Graph API를 사용한 Calendar 작업 처리:

- `list_events()` - 일정 목록 조회
  - 날짜 범위 필터링 (start_date, end_date)
  - 검색어 기반 조회 (search_query)
  - 기본값: 오늘부터 30일 후까지

- `create_event()` - 일정 생성
  - 일반 일정
  - 온라인 회의 (Teams 연동)
  - 종일 일정
  - 참석자 추가

- `update_event()` - 일정 수정
  - 제목, 시간, 위치 변경
  - 참석자 관리
  - 부분 업데이트 지원

- `delete_event()` - 일정 삭제

- `get_event()` - 특정 일정 상세 조회

##### CalendarHandlers (`handlers.py`)

MCP 프로토콜 인터페이스 구현:

- `handle_calendar_list_tools()` - Calendar 도구 목록 제공
- `handle_calendar_call_tool()` - Calendar 도구 실행
- `call_calendar_tool_as_dict()` - HTTP API용 헬퍼

##### Schemas (`schemas.py`)

Pydantic 기반 데이터 모델:

- `CalendarEvent` - 일정 데이터 모델
- `ListEventsRequest/Response` - 일정 목록 조회
- `CreateEventRequest/Response` - 일정 생성
- `UpdateEventRequest/Response` - 일정 수정
- `DeleteEventRequest/Response` - 일정 삭제

### 2. mail_query_MCP 통합

#### 다중 상속 구조

[modules/mail_query_MCP/mcp_server/handlers.py](modules/mail_query_MCP/mcp_server/handlers.py#L143):

```python
from modules.calendar_mcp import CalendarHandlers

class MCPHandlers(AttachmentFilterHandlers, CalendarHandlers):
    """MCP Protocol handlers for Mail Query (상속: AttachmentFilterHandlers, CalendarHandlers)"""

    def __init__(self):
        # 다중 상속 초기화
        AttachmentFilterHandlers.__init__(self)
        CalendarHandlers.__init__(self)

        self.tools = MailAttachmentTools()
        logger.info("✅ MCPHandlers initialized with AttachmentFilterHandlers and CalendarHandlers")
```

#### 도구 통합

[modules/mail_query_MCP/mcp_server/handlers.py](modules/mail_query_MCP/mcp_server/handlers.py#L323):

```python
async def handle_list_tools(self) -> List[Tool]:
    # Mail Query 도구
    mail_query_tools = [...]

    # AttachmentFilterHandlers 도구 추가
    attachment_tools = self.get_attachment_filter_tools()
    mail_query_tools.extend(attachment_tools)

    # CalendarHandlers 도구 추가
    calendar_tools = await self.handle_calendar_list_tools()
    mail_query_tools.extend(calendar_tools)

    return mail_query_tools
```

#### 도구 실행 통합

[modules/mail_query_MCP/mcp_server/handlers.py](modules/mail_query_MCP/mcp_server/handlers.py#L343):

```python
async def handle_call_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    try:
        # AttachmentFilterHandlers 툴 체크
        if self.is_attachment_filter_tool(name):
            return await self.handle_attachment_filter_tool(name, arguments)

        # CalendarHandlers 툴 체크
        if name.startswith("calendar_"):
            return await self.handle_calendar_call_tool(name, arguments)

        # Mail Query 툴 처리
        if name == "query_email":
            # ...
```

## MCP 도구 목록

mail_query_MCP는 이제 **총 9개의 도구**를 제공합니다:

### Calendar 도구 (5개)

1. **calendar_list_events** - 일정 목록 조회
   - 파라미터: user_id (필수), start_date, end_date, limit, search_query
   - 기본값: 오늘부터 30일 후까지

2. **calendar_create_event** - 일정 생성
   - 파라미터: user_id (필수), subject (필수), start (필수), end (필수), body, location, attendees, is_all_day, is_online_meeting
   - 온라인 회의 자동 생성 지원

3. **calendar_update_event** - 일정 수정
   - 파라미터: user_id (필수), event_id (필수), subject, start, end, body, location, attendees, is_online_meeting
   - 부분 업데이트 가능

4. **calendar_delete_event** - 일정 삭제
   - 파라미터: user_id (필수), event_id (필수)

5. **calendar_get_event** - 일정 상세 조회
   - 파라미터: user_id (필수), event_id (필수)

### Mail Query 도구 (3개)

6. **query_email** - 메일 조회
7. **query_email_help** - 메일 조회 도움말
8. **help** - 전체 도움말

### Attachment 도구 (1개)

9. **attachmentManager** - 첨부파일 관리

## 테스트

### 통합 테스트 결과

```bash
$ python3 scripts/test_calendar_integration.py
```

**결과:**

```
🎉 모든 테스트 통과!

✅ 성공 - Calendar 모듈
✅ 성공 - mail_query_MCP 통합
✅ 성공 - 도구 스키마 검증
```

### 테스트 케이스

1. **Calendar 모듈 테스트**
   - CalendarHandler 초기화
   - CalendarHandlers 초기화
   - 5개 Calendar 도구 발견

2. **mail_query_MCP 통합 테스트**
   - MCPHandlers 초기화
   - CalendarHandlers 상속 확인
   - 총 9개 도구 발견 (Calendar 5개 + Mail 3개 + Attachment 1개)

3. **도구 스키마 검증 테스트**
   - 모든 Calendar 도구의 스키마 검증 완료
   - 필수 파라미터 확인
   - 선택적 파라미터 확인

### 추가 테스트 파일

- [tests/handlers/test_calendar_handlers.py](tests/handlers/test_calendar_handlers.py) - pytest 기반 테스트
- [tests/handlers/jsonrpc_cases/calendar.json](tests/handlers/jsonrpc_cases/calendar.json) - JSON-RPC 테스트 케이스 (10개)

## 사용 예시

### 1. 일정 목록 조회

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "calendar_list_events",
    "arguments": {
      "user_id": "kimghw",
      "start_date": "2024-10-01",
      "end_date": "2024-10-31"
    }
  }
}
```

### 2. 일정 생성

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "calendar_create_event",
    "arguments": {
      "user_id": "kimghw",
      "subject": "팀 회의",
      "start": "2024-10-25T14:00:00",
      "end": "2024-10-25T15:00:00",
      "body": "월간 팀 미팅",
      "location": "회의실 A",
      "is_online_meeting": true
    }
  }
}
```

### 3. 일정 수정

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "calendar_update_event",
    "arguments": {
      "user_id": "kimghw",
      "event_id": "AAMkADY...",
      "subject": "팀 회의 (수정됨)",
      "start": "2024-10-25T15:00:00"
    }
  }
}
```

### 4. 일정 삭제

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "calendar_delete_event",
    "arguments": {
      "user_id": "kimghw",
      "event_id": "AAMkADY..."
    }
  }
}
```

## API 권한 요구사항

Microsoft Graph API의 다음 권한이 필요합니다:

- `Calendars.ReadWrite` - 일정 읽기 및 쓰기
- `Calendars.Read` - 일정 읽기 (조회만 필요한 경우)
- `OnlineMeetings.ReadWrite` - 온라인 회의 생성 (is_online_meeting=true 사용 시)

## 의존성

- `httpx` - HTTP 클라이언트
- `pydantic` - 데이터 검증
- `mcp` - MCP 프로토콜
- `infra.core.logger` - 로깅
- `infra.core.token_service` - 토큰 관리
- `infra.core.database` - 데이터베이스 관리

## 향후 개선 사항

1. **캐싱**: 최근 조회한 일정을 로컬 DB에 캐싱하여 성능 향상
2. **반복 일정**: 반복 일정 생성 및 관리 기능 추가
3. **알림 설정**: 일정 알림 관리 기능 추가
4. **다중 캘린더**: 여러 캘린더 지원 (기본 캘린더 외)
5. **첨부파일**: 일정에 파일 첨부 기능 추가

## 문서

- [modules/calendar_mcp/README.md](modules/calendar_mcp/README.md) - Calendar MCP 모듈 상세 문서
- [tests/handlers/jsonrpc_cases/calendar.json](tests/handlers/jsonrpc_cases/calendar.json) - JSON-RPC 테스트 케이스
- [scripts/test_calendar_integration.py](scripts/test_calendar_integration.py) - 통합 테스트 스크립트

## 요약

✅ **Calendar MCP 모듈 구현 완료**
- CalendarHandler (Graph API 연동)
- CalendarHandlers (MCP 프로토콜)
- Pydantic Schemas
- 5개 Calendar 도구

✅ **mail_query_MCP 통합 완료**
- 다중 상속을 통한 CalendarHandlers 통합
- 총 9개 도구 제공 (Calendar 5개 + Mail 3개 + Attachment 1개)
- 모든 테스트 통과

✅ **테스트 및 문서화 완료**
- 통합 테스트 스크립트
- JSON-RPC 테스트 케이스 10개
- README 및 사용 가이드
