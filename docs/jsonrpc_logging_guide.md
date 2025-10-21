# JSON-RPC 로깅 가이드

OneNote MCP 핸들러의 모든 호출을 데이터베이스에 자동으로 저장하는 방법입니다.

## 1. 데코레이터 적용 방법

### handlers.py에 임포트 추가

```python
# 기존 임포트
from infra.core.logger import get_logger
from .onenote_handler import OneNoteHandler

# 추가: JSON-RPC 로거
from infra.core.jsonrpc_logger import log_jsonrpc_call

logger = get_logger(__name__)
```

### handle_call_tool 메서드에 데코레이터 적용

```python
class OneNoteHandlers:
    """OneNote MCP Protocol Handlers"""

    def __init__(self):
        self.onenote_handler = OneNoteHandler()
        self.db_service = OneNoteDBService()
        self.db_service.initialize_tables()
        logger.info("✅ OneNoteHandlers initialized")

    # 기존 handle_list_tools는 그대로 유지
    async def handle_list_tools(self) -> List[Tool]:
        """List available MCP tools (OneNote only)"""
        # ... 코드 그대로 ...

    # 데코레이터 추가!
    @log_jsonrpc_call
    async def handle_call_tool(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle MCP tool calls (OneNote only)"""
        logger.info(f"🔨 [MCP Handler] call_tool({name}) with args: {arguments}")

        # ... 나머지 코드 그대로 ...
```

### call_tool_as_dict 메서드에도 적용 (선택)

```python
    @log_jsonrpc_call
    async def call_tool_as_dict(
        self, name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        HTTP API용 헬퍼: call_tool 결과를 dict로 반환
        """
        # ... 코드 그대로 ...
```

## 2. 로깅 데이터 구조

### 저장되는 데이터

```sql
CREATE TABLE jsonrpc_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,              -- ISO 8601 타임스탬프
    user_id TEXT,                         -- 사용자 ID
    tool_name TEXT NOT NULL,              -- 도구 이름
    action TEXT,                          -- action 파라미터 (있는 경우)
    request_data TEXT NOT NULL,           -- 요청 JSON
    response_data TEXT,                   -- 응답 JSON
    success BOOLEAN,                      -- 성공/실패
    error_message TEXT,                   -- 에러 메시지
    execution_time_ms INTEGER,            -- 실행 시간 (밀리초)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### 인덱스

- `timestamp`: 시간 기반 조회 최적화
- `user_id, tool_name`: 사용자별, 도구별 조회 최적화
- `action`: 액션별 조회 최적화

## 3. 로그 조회 및 분석

### Python 코드로 조회

```python
from infra.core.jsonrpc_logger import get_jsonrpc_logger

# 로거 인스턴스 가져오기
logger = get_jsonrpc_logger()

# 특정 사용자의 로그 조회
logs = logger.get_logs(user_id="kimghw", limit=50)

for log in logs:
    print(f"{log['timestamp']} - {log['tool_name']} ({log['action']})")
    print(f"  Request: {log['request_data']}")
    print(f"  Success: {log['success']}")
    print(f"  Time: {log['execution_time_ms']}ms")
    print()

# 통계 조회
stats = logger.get_stats(user_id="kimghw")

for tool_stat in stats['tools']:
    print(f"{tool_stat['tool_name']} ({tool_stat['action']})")
    print(f"  총 호출: {tool_stat['total_calls']}")
    print(f"  성공: {tool_stat['success_calls']}")
    print(f"  실패: {tool_stat['failed_calls']}")
    print(f"  평균 시간: {tool_stat['avg_execution_time_ms']}ms")
    print()
```

### SQL로 직접 조회

```sql
-- 최근 100개 로그
SELECT timestamp, tool_name, action, success, execution_time_ms
FROM jsonrpc_logs
ORDER BY timestamp DESC
LIMIT 100;

-- 도구별 호출 횟수
SELECT tool_name, action, COUNT(*) as count
FROM jsonrpc_logs
GROUP BY tool_name, action
ORDER BY count DESC;

-- 실패한 요청만 조회
SELECT timestamp, tool_name, action, error_message
FROM jsonrpc_logs
WHERE success = 0
ORDER BY timestamp DESC;

-- 평균 실행 시간 (도구별)
SELECT tool_name, action,
       AVG(execution_time_ms) as avg_time,
       MIN(execution_time_ms) as min_time,
       MAX(execution_time_ms) as max_time
FROM jsonrpc_logs
WHERE success = 1
GROUP BY tool_name, action
ORDER BY avg_time DESC;
```

## 4. HTTP API 엔드포인트 추가 (선택)

로그를 HTTP API로 조회하고 싶다면 unified_http_server.py에 추가:

```python
from infra.core.jsonrpc_logger import get_jsonrpc_logger

# 라우트 추가
async def logs_jsonrpc_handler(request):
    """JSON-RPC 로그 조회"""
    try:
        user_id = request.query_params.get("user_id")
        tool_name = request.query_params.get("tool_name")
        action = request.query_params.get("action")
        limit = int(request.query_params.get("limit", "100"))

        logger = get_jsonrpc_logger()
        logs = logger.get_logs(
            user_id=user_id,
            tool_name=tool_name,
            action=action,
            limit=limit
        )

        return JSONResponse(
            {"logs": logs, "total": len(logs)},
            headers={"Access-Control-Allow-Origin": "*"}
        )

    except Exception as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"}
        )

async def stats_jsonrpc_handler(request):
    """JSON-RPC 통계 조회"""
    try:
        user_id = request.query_params.get("user_id")

        logger = get_jsonrpc_logger()
        stats = logger.get_stats(user_id=user_id)

        return JSONResponse(
            stats,
            headers={"Access-Control-Allow-Origin": "*"}
        )

    except Exception as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"}
        )

# routes에 추가
routes = [
    # ... 기존 라우트들 ...
    Route("/api/jsonrpc/logs", endpoint=logs_jsonrpc_handler, methods=["GET"]),
    Route("/api/jsonrpc/stats", endpoint=stats_jsonrpc_handler, methods=["GET"]),
]
```

## 5. 사용 예시

### 요청 시

```python
# 사용자가 manage_sections_and_pages 호출
result = await handler.handle_call_tool(
    "manage_sections_and_pages",
    {"action": "list_sections", "user_id": "kimghw"}
)
```

### 자동으로 저장되는 데이터

```json
{
  "timestamp": "2025-10-21T10:30:00",
  "user_id": "kimghw",
  "tool_name": "manage_sections_and_pages",
  "action": "list_sections",
  "request_data": {
    "action": "list_sections",
    "user_id": "kimghw"
  },
  "response_data": [
    {
      "type": "text",
      "text": "📁 총 5개 섹션 조회됨..."
    }
  ],
  "success": true,
  "error_message": null,
  "execution_time_ms": 234
}
```

## 6. 장점

1. **자동 로깅**: 데코레이터만 추가하면 모든 호출 자동 기록
2. **성능 모니터링**: 실행 시간 자동 측정
3. **에러 추적**: 실패한 요청 자동 기록
4. **사용 통계**: 도구별, 액션별 사용 빈도 분석
5. **디버깅**: 요청/응답 전체 내역 저장으로 문제 추적 용이

## 7. 성능 고려사항

- 로그는 비동기로 저장되므로 핸들러 성능에 영향 최소화
- 필요시 로그 보관 기간 설정하여 오래된 로그 자동 삭제
- 대용량 응답은 요약만 저장하는 옵션 추가 가능

## 8. 보안 고려사항

- 민감한 정보 (토큰, 비밀번호 등)는 로그에서 제외
- 필요시 로그 암호화 적용
- 로그 조회는 권한 있는 사용자만 가능하도록 설정
