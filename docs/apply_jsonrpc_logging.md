# JSON-RPC 로깅 적용 방법

OneNote 핸들러에 로깅을 적용하는 방법입니다. **딱 2곳만 수정**하면 됩니다!

## 수정 1: Import 추가

**파일:** `modules/onenote_mcp/handlers.py`

**기존 코드 (라인 10):**
```python
from infra.core.logger import get_logger
```

**수정 후:**
```python
from infra.core.logger import get_logger
from infra.core.jsonrpc_logger import log_jsonrpc_call  # ← 이 줄 추가
```

## 수정 2: 데코레이터 추가

**파일:** `modules/onenote_mcp/handlers.py`

**handle_call_tool 메서드 찾기 (대략 라인 195):**

**기존 코드:**
```python
    async def handle_call_tool(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle MCP tool calls (OneNote only)"""
        logger.info(f"🔨 [MCP Handler] call_tool({name}) with args: {arguments}")

        try:
            # Handle OneNote-specific tools
            if name == "manage_sections_and_pages":
                ...
```

**수정 후:**
```python
    @log_jsonrpc_call  # ← 이 줄 추가!
    async def handle_call_tool(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle MCP tool calls (OneNote only)"""
        logger.info(f"🔨 [MCP Handler] call_tool({name}) with args: {arguments}")

        try:
            # Handle OneNote-specific tools
            if name == "manage_sections_and_pages":
                ...
```

## (선택) call_tool_as_dict에도 적용

HTTP API를 사용한다면 이것도 추가:

**파일:** `modules/onenote_mcp/handlers.py`

**call_tool_as_dict 메서드 찾기 (대략 라인 512):**

```python
    @log_jsonrpc_call  # ← 이 줄 추가!
    async def call_tool_as_dict(
        self, name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        HTTP API용 헬퍼: call_tool 결과를 dict로 반환
        """
        ...
```

---

## 끝! 이게 전부입니다.

이제 다음과 같이 동작합니다:

### 자동 로깅되는 항목

1. **모든 도구 호출**
   - `manage_sections_and_pages` (create_section, list_sections, list_pages)
   - `manage_page_content` (get, create, delete)
   - `edit_page`
   - `db_onenote_update`

2. **저장되는 데이터**
   ```json
   {
     "timestamp": "2025-10-21T10:30:00",
     "user_id": "kimghw",
     "tool_name": "manage_sections_and_pages",
     "action": "list_sections",
     "request_data": {"action": "list_sections", "user_id": "kimghw"},
     "response_data": [...],
     "success": true,
     "execution_time_ms": 234
   }
   ```

3. **에러도 자동 저장**
   ```json
   {
     "success": false,
     "error_message": "액세스 토큰이 없습니다",
     "execution_time_ms": 12
   }
   ```

### 로그 확인 방법

```python
from infra.core.jsonrpc_logger import get_jsonrpc_logger

logger = get_jsonrpc_logger()

# 최근 로그 조회
logs = logger.get_logs(user_id="kimghw", limit=10)
for log in logs:
    print(f"{log['tool_name']} - {log['action']} - {log['execution_time_ms']}ms")

# 통계 조회
stats = logger.get_stats(user_id="kimghw")
print(stats)
```

### SQL로 직접 조회

```sql
-- 최근 100개 로그
SELECT timestamp, tool_name, action, execution_time_ms
FROM jsonrpc_logs
ORDER BY timestamp DESC
LIMIT 100;

-- 가장 느린 호출 찾기
SELECT tool_name, action, MAX(execution_time_ms) as max_time
FROM jsonrpc_logs
WHERE success = 1
GROUP BY tool_name, action
ORDER BY max_time DESC;
```

---

## 요약

✅ **2줄만 추가하면 끝!**
1. `from infra.core.jsonrpc_logger import log_jsonrpc_call`
2. `@log_jsonrpc_call` 데코레이터

✅ **자동으로 처리됨:**
- 테이블 생성
- 로그 저장
- 실행 시간 측정
- 에러 추적

✅ **추가 작업 불필요**
- 각 도구별로 로깅 코드 작성 ❌
- DB 쿼리 작성 ❌
- 에러 핸들링 ❌
