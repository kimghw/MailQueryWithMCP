# MCP 서버 로깅 가이드

## 📍 Claude Desktop과 MCP 연결 시 로그 처리

### 1. **Stdio 모드 (Claude Desktop 연결)**

Claude Desktop은 MCP 서버와 **stdio**(표준 입출력)를 통해 통신합니다. 이 경우:

- **표준 출력(stdout)**: MCP 프로토콜 메시지만 전달 (로그 출력 금지)
- **표준 에러(stderr)**: 에러 메시지 출력 가능
- **파일 로깅**: 모든 로그를 파일에 저장

#### 현재 구현 (`entrypoints/local/run_stdio.py`):
```python
# 로그는 파일로만 출력 (stdout 방해 방지)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/local/stdio.log"),  # 파일로만 출력
    ],
)
```

### 2. **로그 파일 위치**

MCP 서버 로그는 다음 위치에 저장됩니다:

```
/home/kimghw/MailQueryWithMCP/
├── logs/
│   ├── mcp_stdio.log              # Stdio 서버 메인 로그
│   ├── infra_core_config.log      # 설정 관련 로그
│   ├── infra_core_database.log    # 데이터베이스 로그
│   ├── modules_mail_query_without_db_mcp_server_handlers.log  # MCP 핸들러 로그
│   ├── auth.log                   # 인증 전용 로그
│   └── app.log                     # 전체 애플리케이션 로그
```

### 3. **로그 확인 방법**

#### 실시간 로그 모니터링:
```bash
# Stdio 서버 로그 실시간 확인
tail -f logs/mcp_stdio.log

# MCP 핸들러 로그 확인
tail -f logs/modules_mail_query_without_db_mcp_server_handlers.log

# 모든 로그 동시 확인
tail -f logs/*.log
```

#### 에러만 필터링:
```bash
# ERROR 레벨 로그만 확인
grep "ERROR" logs/mcp_stdio.log

# 최근 에러 10개
grep "ERROR" logs/mcp_stdio.log | tail -10
```

### 4. **Claude Desktop 설정**

Claude Desktop의 MCP 설정 파일 (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "mail-query": {
      "command": "wsl",
      "args": [
        "-e",
        "/home/kimghw/IACSGRAPH/entrypoints/local/run_stdio.sh"
      ]
    }
  }
}
```

### 5. **로그 레벨 설정**

환경변수로 로그 레벨을 제어할 수 있습니다:

```bash
# .env 파일에서 설정
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### 6. **에러 처리 흐름**

```
Claude Desktop ← [stdio] → MCP Server
                              ↓
                        에러 발생 시
                              ↓
                    1. stderr로 에러 출력
                    2. 로그 파일에 상세 기록
                    3. Claude에 사용자 친화적 메시지 반환
```

### 7. **디버깅 팁**

#### MCP 서버가 시작되지 않을 때:
```bash
# 1. 직접 실행하여 에러 확인
./entrypoints/local/run_stdio.sh

# 2. 환경변수 검증
uv run python scripts/validate_env.py

# 3. 로그 파일 확인
cat logs/local/stdio.log
```

#### Claude Desktop에서 연결이 안 될 때:
```bash
# 1. Claude Desktop 로그 확인 (macOS)
tail -f ~/Library/Logs/Claude/claude.log

# 2. MCP 서버 프로세스 확인
ps aux | grep run_stdio

# 3. 포트 충돌 확인 (HTTP 서버의 경우)
lsof -i :8002
```

### 8. **통합 로깅 시스템 활용**

개선된 로깅 시스템의 기능:

#### 구조화된 로깅:
```python
from infra.core.logger import get_logger
from infra.core.error_messages import ErrorCode, MCPError

logger = get_logger(__name__)

try:
    # 작업 수행
    result = await tool.execute()
    logger.info("✅ Tool executed successfully", extra_data={"tool": tool_name})
except Exception as e:
    error = MCPError(
        ErrorCode.MCP_TOOL_EXECUTION_FAILED,
        tool_name=tool_name,
        original_exception=e
    )
    logger.error(error.to_dict())  # 구조화된 에러 로깅
```

#### JSON 형식 로깅 (분석용):
```python
from infra.core.logging_config import setup_logging, LogFormat

# JSON 형식으로 로깅 설정
setup_logging(
    level="INFO",
    format_type=LogFormat.JSON,
    log_dir=Path("logs")
)
```

출력 예시:
```json
{
  "timestamp": "2025-01-11T00:00:00.000Z",
  "level": "ERROR",
  "logger": "modules.mcp_server.handlers",
  "message": "Tool execution failed",
  "module": "handlers",
  "function": "handle_call_tool",
  "line": 285,
  "context": {
    "tool_name": "query_email",
    "error_code": 7004
  }
}
```

### 9. **로그 로테이션**

로그 파일이 커지는 것을 방지하기 위한 자동 로테이션:

```python
# logging_config.py 설정
max_bytes=10 * 1024 * 1024,  # 10MB
backup_count=5  # 5개 백업 파일 유지
```

로테이션된 파일:
```
logs/
├── mcp_stdio.log       # 현재 로그
├── mcp_stdio.log.1     # 이전 로그
├── mcp_stdio.log.2
├── mcp_stdio.log.3
├── mcp_stdio.log.4
└── mcp_stdio.log.5     # 가장 오래된 로그
```

### 10. **모니터링 스크립트**

간단한 로그 모니터링 스크립트:

```bash
#!/bin/bash
# scripts/monitor_mcp.sh

echo "🔍 MCP Server Log Monitor"
echo "========================="

# 최근 에러 확인
echo -e "\n📛 Recent Errors:"
grep "ERROR" logs/mcp_stdio.log | tail -5

# 활성 계정 상태
echo -e "\n👤 Account Status:"
grep "Active accounts" logs/mcp_stdio.log | tail -1

# 최근 도구 호출
echo -e "\n🔧 Recent Tool Calls:"
grep "call_tool" logs/modules_mail_query_without_db_mcp_server_handlers.log | tail -5

# 실시간 모니터링
echo -e "\n📊 Live Monitoring (Ctrl+C to stop):"
tail -f logs/mcp_stdio.log | grep -E "(ERROR|WARNING|✅|❌)"
```

### 11. **트러블슈팅**

#### 일반적인 문제와 해결 방법:

| 문제 | 로그 위치 | 해결 방법 |
|------|-----------|-----------|
| MCP 서버 시작 실패 | `logs/mcp_stdio.log` | 환경변수 확인: `uv run python scripts/validate_env.py` |
| 인증 오류 | `logs/auth.log` | 토큰 갱신 필요: 계정 재인증 |
| 도구 실행 실패 | `logs/modules_*_handlers.log` | 에러 코드 확인 후 해당 모듈 점검 |
| 데이터베이스 오류 | `logs/infra_core_database.log` | DB 파일 권한 및 경로 확인 |

### 12. **로그 분석 도구**

#### 로그 통계 확인:
```bash
# 로그 레벨별 카운트
echo "Log Level Statistics:"
for level in DEBUG INFO WARNING ERROR CRITICAL; do
  count=$(grep -c $level logs/mcp_stdio.log 2>/dev/null || echo 0)
  echo "$level: $count"
done

# 시간대별 에러 분포
echo -e "\nHourly Error Distribution:"
grep ERROR logs/mcp_stdio.log | awk '{print $2}' | cut -d: -f1 | sort | uniq -c
```

### 요약

Claude Desktop과 MCP 서버 연결 시:
1. **로그는 파일에만 저장** (stdio 통신 방해 방지)
2. **로그 위치**: `logs/` 디렉토리
3. **실시간 모니터링**: `tail -f logs/*.log`
4. **에러는 stderr와 로그 파일 모두에 기록**
5. **구조화된 로깅으로 디버깅 용이**

이제 로그를 체계적으로 관리하고 문제 발생 시 빠르게 원인을 파악할 수 있습니다.