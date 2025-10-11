# MCP 서버 아키텍처 및 로깅 전략

## 📐 아키텍처 비교

### 1. Stdio 직접 연결 (현재)
```
Claude Desktop <--[stdio]--> mcp_server_stdio.py
                                    |
                                    ↓
                             logs/mcp_stdio.log (파일만)
```

**제약사항:**
- ❌ stdout 사용 불가 (MCP 프로토콜 전용)
- ❌ 콘솔 로그 출력 불가
- ❌ 실시간 디버깅 어려움
- ✅ 단순한 구조

### 2. HTTP 서버 모드
```
Client <--[HTTP]--> server.py (port 8002)
                         |
                         ↓
                  stdout + 파일 (자유로운 로깅)
```

**장점:**
- ✅ stdout/stderr 자유롭게 사용
- ✅ 콘솔에 컬러 로그 출력
- ✅ 실시간 디버깅 가능
- ✅ 여러 클라이언트 동시 접속
- ✅ 웹 UI 추가 가능

### 3. HTTP Wrapper를 통한 Stdio 브리지 (제안)

```
Claude Desktop <--[stdio]--> http_stdio_bridge.py <--[HTTP]--> server.py
                                    |                              |
                                    ↓                              ↓
                              브리지 로그                    서버 로그
                           (최소한의 로깅)              (자유로운 로깅)
```

## 🔧 HTTP Stdio Bridge 구현

### `http_stdio_bridge.py` (새로운 파일)
```python
#!/usr/bin/env python3
"""
HTTP-Stdio Bridge for MCP Server

Claude Desktop과 HTTP MCP 서버를 연결하는 브리지
stdout 제약 없이 HTTP 서버의 모든 기능 활용 가능
"""

import asyncio
import json
import sys
import aiohttp
from typing import Any, Dict
import logging
from pathlib import Path

# 로깅 설정 (파일로만)
log_file = Path(__file__).parent.parent.parent / "logs" / "mcp_bridge.log"
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file)]
)
logger = logging.getLogger(__name__)


class MCPHttpStdioBridge:
    """HTTP MCP 서버와 stdio를 연결하는 브리지"""

    def __init__(self, server_url: str = "http://localhost:8002"):
        self.server_url = server_url
        self.session = None

    async def start(self):
        """브리지 시작"""
        logger.info(f"Starting MCP HTTP-Stdio Bridge -> {self.server_url}")

        self.session = aiohttp.ClientSession()

        try:
            # HTTP 서버 상태 확인
            async with self.session.get(f"{self.server_url}/health") as resp:
                if resp.status == 200:
                    logger.info("✅ HTTP server is healthy")
                else:
                    logger.error(f"HTTP server returned {resp.status}")
                    sys.exit(1)

            # Stdio 입력 처리
            await self.handle_stdio()

        except aiohttp.ClientError as e:
            logger.error(f"Cannot connect to HTTP server: {e}")
            sys.stderr.write(f"Error: HTTP server not available at {self.server_url}\n")
            sys.exit(1)
        finally:
            if self.session:
                await self.session.close()

    async def handle_stdio(self):
        """stdio 입출력 처리"""
        logger.info("Starting stdio handler")

        # 비동기 stdin 읽기
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            try:
                # stdin에서 한 줄 읽기
                line = await reader.readline()
                if not line:
                    break

                # JSON 파싱
                try:
                    request = json.loads(line.decode())
                    logger.debug(f"Received: {request.get('method', 'unknown')}")
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    continue

                # HTTP 서버로 전달
                response = await self.forward_to_http(request)

                # stdout으로 응답 전송
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except Exception as e:
                logger.error(f"Error in stdio handler: {e}", exc_info=True)
                error_response = {
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()

    async def forward_to_http(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """요청을 HTTP 서버로 전달"""
        try:
            async with self.session.post(
                self.server_url,
                json=request,
                headers={"Content-Type": "application/json"}
            ) as resp:
                return await resp.json()
        except Exception as e:
            logger.error(f"HTTP forward failed: {e}")
            raise


async def main():
    """메인 진입점"""
    import os

    # 환경변수에서 서버 URL 읽기
    server_url = os.getenv("MCP_HTTP_SERVER_URL", "http://localhost:8002")

    bridge = MCPHttpStdioBridge(server_url)
    await bridge.start()


if __name__ == "__main__":
    asyncio.run(main())
```

## 🚀 사용 방법

### 1. HTTP 서버 실행 (별도 터미널)
```bash
# HTTP 서버는 자유롭게 로깅 가능
uv run python -m modules.mail_query_without_db.mcp_server.server
```

콘솔 출력:
```
🚀 HTTP Streaming Mail Attachment Server initialized on port 8002
✅ Database connection successful
📊 Active accounts found: 3
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8002
```

### 2. Claude Desktop 설정 (브리지 사용)
```json
{
  "mcpServers": {
    "mail-query": {
      "command": "uv",
      "args": ["run", "python", "-m", "modules.mail_query_without_db.http_stdio_bridge"],
      "env": {
        "MCP_HTTP_SERVER_URL": "http://localhost:8002"
      }
    }
  }
}
```

## 🎯 장점

### 1. **로깅 자유도**
- HTTP 서버: stdout, stderr, 파일, 원격 로깅 등 모두 가능
- 브리지: 최소한의 파일 로깅만
- 디버깅 시 HTTP 서버 콘솔에서 실시간 확인

### 2. **확장성**
- HTTP 서버를 원격에 배포 가능
- 여러 Claude Desktop이 하나의 서버 공유
- 로드 밸런싱, 캐싱 등 추가 가능

### 3. **모니터링**
```bash
# HTTP 서버 로그 (자세한 정보)
tail -f logs/mcp_server.log

# 브리지 로그 (연결 정보만)
tail -f logs/mcp_bridge.log

# HTTP 서버 콘솔 (실시간 디버깅)
# 서버 실행 터미널에서 직접 확인
```

### 4. **개발/운영 분리**
- 개발: HTTP 서버 직접 실행 (콘솔 로그 확인)
- 운영: 브리지 사용 (안정적인 연결)

## 📊 로그 출력 비교

### Stdio 직접 연결
```python
# ❌ 불가능
print("디버깅 메시지")
logger.info("서버 시작")  # 파일로만

# 디버깅하려면 파일 확인
tail -f logs/mcp_stdio.log
```

### HTTP + 브리지
```python
# ✅ HTTP 서버에서 모두 가능
print("디버깅 메시지")  # 콘솔 출력 OK
logger.info("서버 시작")  # 콘솔 + 파일
logger.debug(json.dumps(data, indent=2))  # 구조화된 출력

# 실시간으로 콘솔에서 확인 가능!
```

## 🔄 마이그레이션 전략

### 단계적 접근:
1. **현재**: `mcp_server_stdio.py` (직접 연결)
2. **개선**: `server.py` (HTTP) + `http_stdio_bridge.py` (브리지)
3. **최종**: 필요에 따라 선택적 사용

### 호환성 유지:
- 기존 stdio 서버는 그대로 유지
- HTTP 서버는 독립적으로 실행
- 브리지는 선택적 사용

## 📝 결론

HTTP 래핑을 통해:
1. **stdout 제약 해결** ✅
2. **자유로운 로깅** ✅
3. **실시간 디버깅** ✅
4. **확장 가능한 아키텍처** ✅

필요에 따라 직접 연결과 HTTP 브리지를 선택적으로 사용할 수 있습니다.