# MCP 서버 개발 가이드라인

> **Model Context Protocol (MCP) 공식 스펙 기반 서버 개발 가이드**
>
> 본 문서는 MCP 공식 스펙 (2025-06-18) 및 베스트 프랙티스를 기반으로 작성되었습니다.
> MailQueryWithMCP 프로젝트의 실제 구현을 참조하여 실용적인 예시를 제공합니다.

---

## 📋 목차

1. [MCP 프로토콜 개요](#1-mcp-프로토콜-개요)
2. [아키텍처 설계 원칙](#2-아키텍처-설계-원칙)
3. [레이어드 아키텍처](#3-레이어드-아키텍처)
4. [핵심 디자인 패턴](#4-핵심-디자인-패턴)
5. [MCP 서버 구현](#5-mcp-서버-구현)
6. [보안 및 권한 관리](#6-보안-및-권한-관리)
7. [에러 핸들링](#7-에러-핸들링)
8. [성능 최적화](#8-성능-최적화)
9. [테스트 전략](#9-테스트-전략)
10. [프로덕션 운영](#10-프로덕션-운영)
11. [프로젝트 구조](#11-프로젝트-구조)
12. [모범 사례](#12-모범-사례)

---

## 1. MCP 프로토콜 개요

### 1.1 MCP란?

Model Context Protocol (MCP)는 Anthropic이 2024년 11월에 발표한 오픈 표준으로, AI 시스템과 외부 데이터 소스 간의 통합을 표준화하는 프로토콜입니다.

### 1.2 핵심 개념

#### 액터 (Actors)
```
┌─────────────────────────────────────────────────────┐
│                    Host                              │
│  (AI Application - e.g., Claude Desktop)             │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│                   Client                             │
│  (MCP Client Instance - 1:1 with Server)             │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│                   Server                             │
│  (MCP Server - Data Provider)                        │
└─────────────────────────────────────────────────────┘
```

#### 기본 프리미티브 (Primitives)

| 프리미티브 | 설명 | 용도 |
|-----------|------|------|
| **Resources** | 구조화된 데이터/콘텐츠 | 모델에 추가 컨텍스트 제공 |
| **Tools** | 실행 가능한 함수 | 모델이 액션을 수행하거나 정보 검색 |
| **Prompts** | 사전 정의된 템플릿 | 언어 모델 상호작용 가이드 |

### 1.3 프로토콜 기반

- **JSON-RPC 2.0**: 모든 메시지는 JSON-RPC 2.0 스펙 준수
- **Stateful Session**: 상태를 유지하는 세션 프로토콜
- **Capability Negotiation**: 클라이언트와 서버 간 기능 협상

---

## 2. 아키텍처 설계 원칙

### 2.1 단일 책임 원칙 (Single Responsibility)

**MCP 공식 권장사항**: "Each MCP server should have one clear, well-defined purpose"

```python
# ✅ Good: 명확한 단일 목적
class EmailQueryServer:
    """이메일 조회 전용 서버"""
    pass

class AuthenticationServer:
    """인증 관리 전용 서버"""
    pass

# ❌ Bad: 여러 책임이 섞임
class SuperServer:
    """모든 기능을 한 서버에"""
    def handle_email(self): ...
    def handle_auth(self): ...
    def handle_files(self): ...
```

### 2.2 Defense in Depth (심층 방어)

MCP 보안 모델의 핵심 원칙:

```
┌──────────────────────────────────────┐
│  Layer 1: Network Isolation          │
│  - VPC, Firewall, Network Policies   │
└──────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────┐
│  Layer 2: Authentication             │
│  - OAuth 2.0, API Keys, JWT          │
└──────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────┐
│  Layer 3: Authorization              │
│  - RBAC, Fine-grained Permissions    │
└──────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────┐
│  Layer 4: Input Validation           │
│  - Schema Validation, Sanitization   │
└──────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────┐
│  Layer 5: Monitoring & Auditing      │
│  - Logging, Metrics, Alerting        │
└──────────────────────────────────────┘
```

### 2.3 Fail-Safe Design

시스템 장애 시 안전한 상태로 전환:

```python
class FailSafeHandler:
    """Fail-safe 설계 패턴"""

    def __init__(self):
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60
        )
        self.cache = CacheService()
        self.rate_limiter = RateLimiter(
            max_requests=100,
            window_seconds=60
        )

    async def handle_request(self, request):
        # 1. Rate Limiting
        if not self.rate_limiter.allow(request.client_id):
            return self._rate_limit_response()

        # 2. Circuit Breaker
        if self.circuit_breaker.is_open():
            # Fallback to cache
            cached = self.cache.get(request.key)
            if cached:
                return cached
            return self._service_unavailable()

        try:
            # 3. Normal processing
            result = await self._process(request)
            self.circuit_breaker.record_success()
            self.cache.set(request.key, result)
            return result

        except Exception as e:
            self.circuit_breaker.record_failure()
            # Graceful degradation
            return self._fallback_response(e)
```

---

## 3. 레이어드 아키텍처

### 3.1 MCP 표준 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                  Host Application                        │
│              (Claude, ChatGPT, etc.)                     │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    MCP Client                            │
│            (Protocol Implementation)                     │
└─────────────────────────────────────────────────────────┘
                            ↓
                    [JSON-RPC 2.0]
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    MCP Server                            │
│  ┌─────────────────────────────────────────────────┐   │
│  │          Transport Layer (HTTP/SSE/STDIO)        │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │          Protocol Layer (JSON-RPC Handler)       │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │      Application Layer (Business Logic)          │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │    Infrastructure Layer (DB, APIs, Files)        │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 3.2 계층별 책임

| 계층 | 책임 | 구현 예시 |
|------|------|-----------|
| **Transport** | 통신 프로토콜 처리 | HTTP (Starlette), SSE, STDIO |
| **Protocol** | MCP 스펙 구현 | JSON-RPC 핸들러, Tool/Resource 정의 |
| **Application** | 비즈니스 로직 | 도메인 서비스, 유스케이스 |
| **Infrastructure** | 외부 시스템 연동 | 데이터베이스, 외부 API, 파일시스템 |

---

## 4. 핵심 디자인 패턴

### 4.1 Repository Pattern (데이터 접근)

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

class Repository(ABC):
    """Repository 인터페이스"""

    @abstractmethod
    async def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def find_all(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def save(self, entity: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        pass

class SQLiteRepository(Repository):
    """SQLite 구현"""

    def __init__(self, db_manager, table_name: str):
        self.db = db_manager
        self.table = table_name

    async def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        query = f"SELECT * FROM {self.table} WHERE id = ?"
        row = await self.db.fetch_one(query, (id,))
        return dict(row) if row else None
```

### 4.2 Strategy Pattern (알고리즘 선택)

```python
from abc import ABC, abstractmethod

class AuthStrategy(ABC):
    """인증 전략 인터페이스"""

    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        pass

class OAuthStrategy(AuthStrategy):
    """OAuth 2.0 인증"""

    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        # OAuth 인증 로직
        return await self._validate_oauth_token(credentials["token"])

class APIKeyStrategy(AuthStrategy):
    """API Key 인증"""

    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        # API Key 검증 로직
        return await self._validate_api_key(credentials["api_key"])

class AuthContext:
    """인증 컨텍스트"""

    def __init__(self, strategy: AuthStrategy):
        self._strategy = strategy

    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        return await self._strategy.authenticate(credentials)
```

### 4.3 Circuit Breaker Pattern (장애 격리)

```python
import time
from enum import Enum
from typing import Callable

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """서킷 브레이커 패턴 구현"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    async def call(self, func: Callable, *args, **kwargs):
        """함수 호출을 서킷 브레이커로 보호"""

        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )

    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

---

## 5. MCP 서버 구현

### 5.1 입력값 우선순위 원칙

MCP 서버에서 파라미터를 처리할 때는 다음 우선순위를 따릅니다:

```
1순위: 사용자 입력값 (Tool arguments)
   ↓
2순위: 데이터베이스 저장값
   ↓
3순위: 환경 변수
   ↓
4순위: 하드코딩된 기본값
```

**구현 예시**:

```python
class ParameterResolver:
    """입력값 우선순위 처리"""

    def __init__(self):
        self.db = get_database_manager()
        self.config = get_config()

    async def resolve_user_id(
        self,
        user_input: Optional[str] = None,
        context: Dict[str, Any] = None
    ) -> str:
        """
        user_id 결정 (우선순위 적용)

        Args:
            user_input: 사용자가 직접 입력한 값
            context: 요청 컨텍스트 (세션 정보 등)

        Returns:
            결정된 user_id
        """
        # 1순위: 사용자 입력값
        if user_input:
            logger.info(f"Using user-provided user_id: {user_input}")
            return user_input

        # 2순위: 데이터베이스 저장값 (세션 기반)
        if context and context.get("session_id"):
            db_user_id = await self._get_user_from_session(context["session_id"])
            if db_user_id:
                logger.info(f"Using DB user_id from session: {db_user_id}")
                return db_user_id

        # 3순위: 환경 변수
        env_user_id = os.getenv("DEFAULT_USER_ID")
        if env_user_id:
            logger.info(f"Using env user_id: {env_user_id}")
            return env_user_id

        # 4순위: 하드코딩된 기본값
        default_user_id = "default_user"
        logger.warning(f"Using hardcoded default user_id: {default_user_id}")
        return default_user_id

    async def resolve_parameters(
        self,
        tool_name: str,
        user_arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Tool 파라미터 결정 (우선순위 적용)

        Args:
            tool_name: Tool 이름
            user_arguments: 사용자가 제공한 인자

        Returns:
            최종 파라미터 딕셔너리
        """
        resolved = {}

        # 파라미터별로 우선순위 적용
        param_specs = self._get_parameter_specs(tool_name)

        for param_name, spec in param_specs.items():
            # 1순위: 사용자 입력
            if param_name in user_arguments:
                resolved[param_name] = user_arguments[param_name]
                continue

            # 2순위: DB 저장값
            db_value = await self._get_db_default(tool_name, param_name)
            if db_value is not None:
                resolved[param_name] = db_value
                continue

            # 3순위: 환경 변수
            env_key = f"{tool_name.upper()}_{param_name.upper()}"
            env_value = os.getenv(env_key)
            if env_value is not None:
                resolved[param_name] = self._parse_env_value(env_value, spec["type"])
                continue

            # 4순위: 기본값
            if "default" in spec:
                resolved[param_name] = spec["default"]

        return resolved

    async def _get_user_from_session(self, session_id: str) -> Optional[str]:
        """세션에서 user_id 조회"""
        row = await self.db.fetch_one(
            "SELECT user_id FROM sessions WHERE session_id = ?",
            (session_id,)
        )
        return row["user_id"] if row else None

    async def _get_db_default(self, tool_name: str, param_name: str) -> Optional[Any]:
        """DB에서 기본값 조회"""
        row = await self.db.fetch_one(
            "SELECT value FROM parameter_defaults WHERE tool = ? AND param = ?",
            (tool_name, param_name)
        )
        return row["value"] if row else None

    def _parse_env_value(self, value: str, param_type: str) -> Any:
        """환경 변수 값을 타입에 맞게 변환"""
        if param_type == "integer":
            return int(value)
        elif param_type == "boolean":
            return value.lower() in ("true", "1", "yes")
        elif param_type == "array":
            return value.split(",")
        else:
            return value
```

**사용 예시**:

```python
class MCPHandlers:
    def __init__(self):
        self.resolver = ParameterResolver()

    async def handle_call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> List[TextContent]:
        """Tool 실행"""

        # 파라미터 우선순위 적용
        resolved_args = await self.resolver.resolve_parameters(name, arguments)

        # user_id 결정
        user_id = await self.resolver.resolve_user_id(
            user_input=arguments.get("user_id"),
            context=context
        )
        resolved_args["user_id"] = user_id

        logger.info(f"Resolved parameters: {resolved_args}")

        # Tool 실행
        if name == "query_data":
            result = await self.service.query_data(**resolved_args)
            return [TextContent(type="text", text=result)]
```

**환경 변수 설정 예시**:

```bash
# .env 파일
DEFAULT_USER_ID=admin
QUERY_DATA_MAX_RESULTS=100
QUERY_DATA_INCLUDE_ARCHIVED=false
```

### 5.2 기본 구조

```python
# mcp_server/handlers.py

from typing import List, Dict, Any
from mcp.types import Tool, Resource, Prompt, TextContent
from infra.core.logger import get_logger

logger = get_logger(__name__)

class MCPHandlers:
    """MCP 프로토콜 핸들러"""

    def __init__(self):
        self.service = ApplicationService()
        logger.info("✅ MCP Handlers initialized")

    # ========================================================================
    # MCP Protocol: Initialization
    # ========================================================================

    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize 핸들러 (MCP 스펙 필수)

        Returns:
            - protocolVersion: 프로토콜 버전
            - capabilities: 서버 기능
            - serverInfo: 서버 정보
        """
        return {
            "protocolVersion": "2025-06-18",
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"listChanged": False},
                "prompts": {"listChanged": False},
                "logging": {}
            },
            "serverInfo": {
                "name": "my-mcp-server",
                "version": "1.0.0",
                "description": "My MCP Server"
            }
        }

    # ========================================================================
    # MCP Protocol: Tools
    # ========================================================================

    async def handle_list_tools(self) -> List[Tool]:
        """
        사용 가능한 Tool 목록 반환

        MCP 스펙: Tool은 AI 모델이 실행할 수 있는 함수
        """
        return [
            Tool(
                name="query_data",
                description="Query data with filters",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "filters": {
                            "type": "object",
                            "description": "Optional filters"
                        }
                    },
                    "required": ["query"]
                }
            ),
        ]

    async def handle_call_tool(
        self,
        name: str,
        arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """
        Tool 실행

        MCP 스펙: 사용자 동의와 명시적 권한 필요
        """
        logger.info(f"🔧 Executing tool: {name}")

        # 권한 검증
        if not await self._check_permission(name, arguments):
            return [TextContent(
                type="text",
                text="❌ Permission denied. User consent required."
            )]

        # Tool 실행
        try:
            if name == "query_data":
                result = await self.service.query_data(**arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

            return [TextContent(type="text", text=result)]

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Error: {str(e)}"
            )]

    # ========================================================================
    # MCP Protocol: Resources
    # ========================================================================

    async def handle_list_resources(self) -> List[Resource]:
        """
        사용 가능한 Resource 목록 반환

        MCP 스펙: Resource는 컨텍스트와 데이터 제공
        """
        return [
            Resource(
                uri="file:///data/config.json",
                name="Configuration",
                description="Server configuration",
                mimeType="application/json"
            ),
        ]

    async def handle_read_resource(self, uri: str) -> str:
        """Resource 읽기"""
        # 권한 검증
        if not await self._check_resource_permission(uri):
            raise PermissionError(f"Access denied to resource: {uri}")

        # Resource 읽기 로직
        return await self.service.read_resource(uri)

    # ========================================================================
    # Private: Security
    # ========================================================================

    async def _check_permission(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> bool:
        """
        권한 검증 (MCP 보안 원칙)

        MCP 스펙 요구사항:
        - 명시적 사용자 동의
        - 세분화된 권한 관리
        - 감사 로깅
        """
        # 1. 사용자 동의 확인
        if not await self._has_user_consent(tool_name):
            logger.warning(f"No user consent for tool: {tool_name}")
            return False

        # 2. 권한 레벨 확인
        required_permission = self._get_required_permission(tool_name)
        if not await self._check_user_permission(required_permission):
            logger.warning(f"Insufficient permission for: {tool_name}")
            return False

        # 3. 감사 로그
        await self._audit_log(tool_name, arguments)

        return True
```

### 5.2 HTTP Transport 구현

```python
# mcp_server/http_server.py

import json
import secrets
from typing import Dict, Any

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from .handlers import MCPHandlers
from infra.core.logger import get_logger

logger = get_logger(__name__)

class MCPHTTPServer:
    """MCP HTTP Server (JSON-RPC 2.0)"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        self.host = host
        self.port = port
        self.handlers = MCPHandlers()
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.app = self._create_app()

    async def handle_jsonrpc(self, request: Request) -> Response:
        """
        JSON-RPC 2.0 요청 처리

        MCP 스펙: 모든 메시지는 JSON-RPC 2.0 준수
        """
        try:
            # 1. 요청 파싱
            body = await request.body()
            rpc_request = json.loads(body)

            # 2. JSON-RPC 필드 검증
            if rpc_request.get("jsonrpc") != "2.0":
                return self._error_response(
                    -32600,
                    "Invalid Request: jsonrpc must be 2.0",
                    rpc_request.get("id")
                )

            method = rpc_request.get("method")
            params = rpc_request.get("params", {})
            request_id = rpc_request.get("id")

            # 3. Notification 처리 (id가 없는 경우)
            if request_id is None:
                logger.info(f"Notification received: {method}")
                return Response(status_code=202)

            # 4. Method 라우팅
            result = await self._route_method(method, params)

            # 5. 응답 생성
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            })

        except Exception as e:
            logger.error(f"Request handling error: {e}")
            return self._error_response(
                -32603,
                f"Internal error: {str(e)}",
                request_id if 'request_id' in locals() else None
            )

    async def _route_method(self, method: str, params: Dict[str, Any]) -> Any:
        """메서드 라우팅"""

        # MCP 필수 메서드
        if method == "initialize":
            return await self.handlers.handle_initialize(params)

        elif method == "tools/list":
            tools = await self.handlers.handle_list_tools()
            return {"tools": [t.model_dump() for t in tools]}

        elif method == "tools/call":
            results = await self.handlers.handle_call_tool(
                params.get("name"),
                params.get("arguments", {})
            )
            return {"content": [r.model_dump() for r in results]}

        elif method == "resources/list":
            resources = await self.handlers.handle_list_resources()
            return {"resources": [r.model_dump() for r in resources]}

        elif method == "resources/read":
            content = await self.handlers.handle_read_resource(params.get("uri"))
            return {"content": content}

        else:
            raise ValueError(f"Method not found: {method}")

    def _error_response(self, code: int, message: str, id: Any) -> JSONResponse:
        """JSON-RPC 2.0 에러 응답"""
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            },
            "id": id
        })

    def _create_app(self) -> Starlette:
        """Starlette 앱 생성"""

        async def jsonrpc_endpoint(request):
            return await self.handle_jsonrpc(request)

        async def health_check(request):
            return JSONResponse({"status": "healthy"})

        routes = [
            Route("/", endpoint=jsonrpc_endpoint, methods=["POST"]),
            Route("/health", endpoint=health_check, methods=["GET"]),
        ]

        return Starlette(routes=routes)

    def run(self):
        """서버 실행"""
        logger.info(f"🚀 MCP Server starting on http://{self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port)
```

---

## 6. 보안 및 권한 관리

### 6.1 MCP 보안 원칙

MCP 공식 스펙의 보안 요구사항:

1. **Explicit User Consent** (명시적 사용자 동의)
2. **Data Privacy Protection** (데이터 프라이버시 보호)
3. **Safe Tool Execution** (안전한 도구 실행)
4. **Controlled LLM Sampling** (통제된 LLM 샘플링)

### 6.2 구현 예시

```python
class SecurityManager:
    """MCP 보안 관리자"""

    def __init__(self):
        self.consent_manager = ConsentManager()
        self.permission_manager = PermissionManager()
        self.audit_logger = AuditLogger()

    async def check_tool_permission(
        self,
        user_id: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> bool:
        """
        Tool 실행 권한 검증

        MCP 요구사항:
        1. 사용자 동의 확인
        2. 권한 레벨 검증
        3. 감사 로깅
        """
        # 1. 사용자 동의 확인
        if not await self.consent_manager.has_consent(user_id, tool_name):
            await self.audit_logger.log_denied(
                user_id,
                tool_name,
                "No user consent"
            )
            return False

        # 2. 권한 검증
        required_permissions = self._get_required_permissions(tool_name)
        user_permissions = await self.permission_manager.get_user_permissions(user_id)

        if not self._has_required_permissions(user_permissions, required_permissions):
            await self.audit_logger.log_denied(
                user_id,
                tool_name,
                "Insufficient permissions"
            )
            return False

        # 3. 데이터 접근 범위 확인
        if not await self._check_data_scope(user_id, arguments):
            await self.audit_logger.log_denied(
                user_id,
                tool_name,
                "Data access out of scope"
            )
            return False

        # 4. 성공 감사 로그
        await self.audit_logger.log_granted(user_id, tool_name, arguments)

        return True

    def _get_required_permissions(self, tool_name: str) -> List[str]:
        """Tool별 필요 권한 반환"""
        permission_map = {
            "read_email": ["email:read"],
            "send_email": ["email:read", "email:write"],
            "delete_email": ["email:read", "email:write", "email:delete"],
        }
        return permission_map.get(tool_name, [])

    async def _check_data_scope(
        self,
        user_id: str,
        arguments: Dict[str, Any]
    ) -> bool:
        """
        데이터 접근 범위 확인

        예: 사용자는 자신의 데이터만 접근 가능
        """
        requested_user = arguments.get("user_id")
        if requested_user and requested_user != user_id:
            # 다른 사용자 데이터 접근 시도
            return False
        return True

class ConsentManager:
    """사용자 동의 관리"""

    async def has_consent(self, user_id: str, tool_name: str) -> bool:
        """사용자 동의 확인"""
        # 데이터베이스에서 동의 정보 조회
        consent = await self.db.fetch_one(
            "SELECT * FROM user_consents WHERE user_id = ? AND tool_name = ?",
            (user_id, tool_name)
        )
        return consent is not None and consent["granted"]

    async def grant_consent(
        self,
        user_id: str,
        tool_name: str,
        scope: Dict[str, Any]
    ):
        """동의 부여"""
        await self.db.execute_query(
            """
            INSERT OR REPLACE INTO user_consents
            (user_id, tool_name, scope, granted_at)
            VALUES (?, ?, ?, datetime('now'))
            """,
            (user_id, tool_name, json.dumps(scope))
        )

    async def revoke_consent(self, user_id: str, tool_name: str):
        """동의 철회"""
        await self.db.execute_query(
            "DELETE FROM user_consents WHERE user_id = ? AND tool_name = ?",
            (user_id, tool_name)
        )
```

---

## 7. 에러 핸들링

### 7.1 JSON-RPC 2.0 에러 코드

MCP는 JSON-RPC 2.0 표준 에러 코드를 사용합니다:

| 코드 | 의미 | 사용 시점 |
|------|------|-----------|
| -32700 | Parse error | JSON 파싱 실패 |
| -32600 | Invalid Request | 잘못된 요청 구조 |
| -32601 | Method not found | 메서드가 존재하지 않음 |
| -32602 | Invalid params | 잘못된 파라미터 |
| -32603 | Internal error | 서버 내부 오류 |

### 7.2 구조화된 에러 처리

```python
from enum import Enum
from typing import Optional, Dict, Any

class ErrorCode(Enum):
    """애플리케이션 에러 코드"""
    # 인증/권한
    UNAUTHORIZED = 1001
    FORBIDDEN = 1002

    # 검증
    VALIDATION_ERROR = 2001
    INVALID_FORMAT = 2002

    # 리소스
    NOT_FOUND = 3001
    CONFLICT = 3002

    # 서버
    INTERNAL_ERROR = 5001
    SERVICE_UNAVAILABLE = 5002

class MCPError(Exception):
    """MCP 에러 클래스"""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_jsonrpc_error(self) -> Dict[str, Any]:
        """JSON-RPC 에러 형식으로 변환"""
        return {
            "code": -32603,  # Internal error
            "message": self.message,
            "data": {
                "error_code": self.code.value,
                "details": self.details
            }
        }

class ErrorHandler:
    """에러 핸들러"""

    def __init__(self):
        self.logger = get_logger(__name__)

    async def handle_error(self, error: Exception) -> Dict[str, Any]:
        """에러 처리 및 응답 생성"""

        if isinstance(error, MCPError):
            # 애플리케이션 에러
            self.logger.warning(f"Application error: {error.code} - {error.message}")
            return error.to_jsonrpc_error()

        elif isinstance(error, ValidationError):
            # 검증 에러
            self.logger.warning(f"Validation error: {str(error)}")
            return {
                "code": -32602,  # Invalid params
                "message": str(error)
            }

        elif isinstance(error, PermissionError):
            # 권한 에러
            self.logger.warning(f"Permission denied: {str(error)}")
            return {
                "code": -32603,
                "message": "Permission denied",
                "data": {"error": str(error)}
            }

        else:
            # 예상치 못한 에러
            self.logger.error(f"Unexpected error: {str(error)}", exc_info=True)
            return {
                "code": -32603,
                "message": "Internal server error",
                "data": {"error_id": self._generate_error_id()}
            }

    def _generate_error_id(self) -> str:
        """에러 추적용 ID 생성"""
        import uuid
        return str(uuid.uuid4())
```

---

## 8. 성능 최적화

### 8.1 MCP 성능 목표

공식 베스트 프랙티스 기준:

| 메트릭 | 목표 | 측정 방법 |
|--------|------|-----------|
| **Throughput** | >1000 req/s | 부하 테스트 |
| **Latency P95** | <100ms | 응답 시간 분포 |
| **Latency P99** | <500ms | 응답 시간 분포 |
| **Error Rate** | <0.1% | 에러 로그 분석 |
| **Availability** | >99.9% | 업타임 모니터링 |

### 8.2 최적화 전략

```python
class PerformanceOptimizer:
    """성능 최적화 구현"""

    def __init__(self):
        # 1. Connection Pooling
        self.connection_pool = ConnectionPool(
            min_size=10,
            max_size=100,
            timeout=30
        )

        # 2. Multi-level Caching
        self.cache = MultiLevelCache(
            l1_cache=InMemoryCache(max_size=1000),
            l2_cache=RedisCache(ttl=3600)
        )

        # 3. Rate Limiting
        self.rate_limiter = TokenBucketRateLimiter(
            rate=100,  # 100 req/s per client
            capacity=1000
        )

        # 4. Async Processing
        self.task_queue = AsyncTaskQueue(
            max_workers=50,
            queue_size=10000
        )

    async def process_request(self, request: Request) -> Response:
        """최적화된 요청 처리"""

        # 1. Rate limiting
        if not await self.rate_limiter.allow(request.client_id):
            return Response(status_code=429, content="Rate limit exceeded")

        # 2. Cache check
        cache_key = self._generate_cache_key(request)
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        # 3. Connection pooling
        async with self.connection_pool.acquire() as conn:
            # 4. Async processing
            result = await self.task_queue.submit(
                self._process_with_connection,
                conn,
                request
            )

        # 5. Cache update
        await self.cache.set(cache_key, result, ttl=300)

        return result

class ConnectionPool:
    """연결 풀 구현"""

    def __init__(self, min_size: int, max_size: int, timeout: int):
        self.min_size = min_size
        self.max_size = max_size
        self.timeout = timeout
        self._pool = asyncio.Queue(maxsize=max_size)
        self._size = 0
        self._lock = asyncio.Lock()

    async def acquire(self):
        """연결 획득"""
        try:
            # 풀에서 연결 가져오기
            conn = await asyncio.wait_for(
                self._pool.get(),
                timeout=self.timeout
            )
            return PooledConnection(conn, self)

        except asyncio.TimeoutError:
            # 새 연결 생성
            if self._size < self.max_size:
                async with self._lock:
                    if self._size < self.max_size:
                        conn = await self._create_connection()
                        self._size += 1
                        return PooledConnection(conn, self)

            raise TimeoutError("Connection pool exhausted")

    async def release(self, conn):
        """연결 반환"""
        try:
            self._pool.put_nowait(conn)
        except asyncio.QueueFull:
            await conn.close()
            self._size -= 1
```

---

## 9. 테스트 전략

### 9.1 테스트 피라미드

```
         /\
        /  \       E2E Tests (10%)
       /    \      - 전체 시나리오
      /______\     - 실제 외부 시스템 연동
     /        \
    /          \   Integration Tests (30%)
   /            \  - MCP 프로토콜 테스트
  /______________\ - 컴포넌트 간 통합
 /                \
/                  \ Unit Tests (60%)
/__________________\- 개별 함수/클래스
                    - Mock 사용
```

### 9.2 Unit Test 예시

```python
import pytest
from unittest.mock import Mock, AsyncMock
from mcp_server.handlers import MCPHandlers

@pytest.fixture
def handlers():
    """테스트용 핸들러"""
    handlers = MCPHandlers()
    handlers.service = Mock()
    return handlers

@pytest.mark.asyncio
async def test_handle_list_tools(handlers):
    """Tool 목록 테스트"""
    tools = await handlers.handle_list_tools()

    assert len(tools) > 0
    assert tools[0].name == "query_data"
    assert "query" in tools[0].inputSchema["properties"]

@pytest.mark.asyncio
async def test_handle_call_tool_with_permission(handlers):
    """권한이 있는 Tool 호출 테스트"""
    handlers._check_permission = AsyncMock(return_value=True)
    handlers.service.query_data = AsyncMock(return_value="test result")

    results = await handlers.handle_call_tool(
        "query_data",
        {"query": "test"}
    )

    assert len(results) == 1
    assert "test result" in results[0].text
    handlers.service.query_data.assert_called_once_with(query="test")

@pytest.mark.asyncio
async def test_handle_call_tool_without_permission(handlers):
    """권한이 없는 Tool 호출 테스트"""
    handlers._check_permission = AsyncMock(return_value=False)

    results = await handlers.handle_call_tool(
        "query_data",
        {"query": "test"}
    )

    assert "Permission denied" in results[0].text
    handlers.service.query_data.assert_not_called()
```

### 9.3 Integration Test 예시

```python
import pytest
from fastapi.testclient import TestClient
from mcp_server.http_server import MCPHTTPServer

@pytest.fixture
def client():
    """테스트 클라이언트"""
    server = MCPHTTPServer(port=9999)
    app = server.app
    return TestClient(app)

def test_jsonrpc_initialize(client):
    """Initialize 메서드 테스트"""
    response = client.post("/", json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    })

    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == 1
    assert data["result"]["protocolVersion"] == "2025-06-18"
    assert "capabilities" in data["result"]
    assert "serverInfo" in data["result"]

def test_jsonrpc_tools_list(client):
    """tools/list 메서드 테스트"""
    response = client.post("/", json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    })

    assert response.status_code == 200
    data = response.json()
    assert "tools" in data["result"]
    assert len(data["result"]["tools"]) > 0

def test_jsonrpc_error_handling(client):
    """에러 처리 테스트"""
    response = client.post("/", json={
        "jsonrpc": "2.0",
        "id": 3,
        "method": "unknown_method",
        "params": {}
    })

    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == -32601  # Method not found
```

### 9.4 Contract Test

```python
import pytest
from pydantic import ValidationError
from mcp.types import Tool

def test_tool_schema_validation():
    """Tool 스키마 검증 테스트"""
    # Valid tool
    tool = Tool(
        name="test_tool",
        description="Test tool",
        inputSchema={
            "type": "object",
            "properties": {
                "param": {"type": "string"}
            },
            "required": ["param"]
        }
    )
    assert tool.name == "test_tool"

    # Invalid tool (missing required field)
    with pytest.raises(ValidationError):
        Tool(
            name="test_tool"
            # description is required
        )
```

---

## 10. 프로덕션 운영

### 10.1 배포 체크리스트

- [ ] **환경 설정**
  - [ ] 환경 변수 설정 완료
  - [ ] 설정 파일 검증
  - [ ] 시크릿 관리 (Vault, KMS 등)

- [ ] **보안**
  - [ ] TLS/SSL 인증서 설정
  - [ ] 방화벽 규칙 구성
  - [ ] Rate limiting 설정
  - [ ] CORS 정책 구성

- [ ] **모니터링**
  - [ ] 헬스 체크 엔드포인트
  - [ ] 메트릭 수집 (Prometheus)
  - [ ] 로그 집계 (ELK Stack)
  - [ ] 알림 설정 (PagerDuty)

- [ ] **성능**
  - [ ] 부하 테스트 완료
  - [ ] 캐시 설정 검증
  - [ ] 연결 풀 크기 조정
  - [ ] 타임아웃 설정

- [ ] **복원력**
  - [ ] 백업 전략 수립
  - [ ] 재해 복구 계획
  - [ ] 롤백 절차 문서화
  - [ ] Chaos engineering 테스트

### 10.2 모니터링 구현

```python
from prometheus_client import Counter, Histogram, Gauge
import time

class MetricsCollector:
    """메트릭 수집기"""

    def __init__(self):
        # Counters
        self.request_count = Counter(
            'mcp_requests_total',
            'Total number of MCP requests',
            ['method', 'status']
        )

        self.error_count = Counter(
            'mcp_errors_total',
            'Total number of errors',
            ['error_type']
        )

        # Histograms
        self.request_duration = Histogram(
            'mcp_request_duration_seconds',
            'Request duration in seconds',
            ['method']
        )

        # Gauges
        self.active_sessions = Gauge(
            'mcp_active_sessions',
            'Number of active sessions'
        )

        self.connection_pool_size = Gauge(
            'mcp_connection_pool_size',
            'Current connection pool size'
        )

    def record_request(self, method: str, status: str, duration: float):
        """요청 메트릭 기록"""
        self.request_count.labels(method=method, status=status).inc()
        self.request_duration.labels(method=method).observe(duration)

    def record_error(self, error_type: str):
        """에러 메트릭 기록"""
        self.error_count.labels(error_type=error_type).inc()

    def update_sessions(self, count: int):
        """세션 수 업데이트"""
        self.active_sessions.set(count)

class RequestTracker:
    """요청 추적"""

    def __init__(self, metrics: MetricsCollector):
        self.metrics = metrics

    async def track(self, method: str, handler):
        """요청 실행 및 추적"""
        start_time = time.time()
        status = "success"

        try:
            result = await handler()
            return result

        except Exception as e:
            status = "error"
            self.metrics.record_error(type(e).__name__)
            raise

        finally:
            duration = time.time() - start_time
            self.metrics.record_request(method, status, duration)
```

### 10.3 로깅 전략

```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    """구조화된 로깅"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # JSON 포맷터
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)

    def log(self, level: str, message: str, **kwargs):
        """구조화된 로그 출력"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            **kwargs
        }

        if level == "debug":
            self.logger.debug(json.dumps(log_data))
        elif level == "info":
            self.logger.info(json.dumps(log_data))
        elif level == "warning":
            self.logger.warning(json.dumps(log_data))
        elif level == "error":
            self.logger.error(json.dumps(log_data))

    def log_request(self, method: str, params: dict, user_id: str = None):
        """요청 로깅"""
        self.log(
            "info",
            "MCP request received",
            method=method,
            user_id=user_id,
            params_size=len(json.dumps(params))
        )

    def log_response(self, method: str, duration: float, success: bool):
        """응답 로깅"""
        self.log(
            "info",
            "MCP response sent",
            method=method,
            duration_ms=duration * 1000,
            success=success
        )

    def log_error(self, method: str, error: Exception, context: dict = None):
        """에러 로깅"""
        self.log(
            "error",
            "MCP error occurred",
            method=method,
            error_type=type(error).__name__,
            error_message=str(error),
            context=context
        )

class JSONFormatter(logging.Formatter):
    """JSON 로그 포맷터"""

    def format(self, record):
        # 이미 JSON 형식인 경우 그대로 반환
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            try:
                json.loads(record.msg)
                return record.msg
            except:
                pass

        # 일반 로그를 JSON으로 변환
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }
        return json.dumps(log_obj)
```

---

## 11. 프로젝트 구조

### 11.1 권장 디렉토리 구조

```
project_root/
├── modules/                          # MCP 서버 모듈
│   ├── mcp_server/                   # MCP 프로토콜 계층
│   │   ├── __init__.py
│   │   ├── handlers.py               # MCP 핸들러
│   │   ├── http_server.py            # HTTP 전송
│   │   ├── stdio_server.py           # STDIO 전송 (선택)
│   │   └── security.py               # 보안 관리
│   │
│   ├── services/                     # 비즈니스 로직
│   │   ├── __init__.py
│   │   └── application_service.py
│   │
│   ├── repositories/                 # 데이터 접근
│   │   ├── __init__.py
│   │   └── data_repository.py
│   │
│   └── domain/                       # 도메인 모델
│       ├── __init__.py
│       └── entities.py
│
├── infra/                            # 인프라 계층
│   ├── core/                         # 핵심 인프라
│   │   ├── database.py
│   │   ├── logger.py
│   │   ├── config.py
│   │   └── exceptions.py
│   │
│   ├── monitoring/                   # 모니터링
│   │   ├── metrics.py
│   │   └── health.py
│   │
│   └── security/                     # 보안
│       ├── auth.py
│       └── encryption.py
│
├── tests/                            # 테스트
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── scripts/                          # 스크립트
│   ├── setup.sh
│   └── deploy.sh
│
├── config/                           # 설정 파일
│   ├── development.yaml
│   ├── staging.yaml
│   └── production.yaml
│
├── docs/                             # 문서
│   ├── architecture.md
│   ├── api.md
│   └── deployment.md
│
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 12. 모범 사례

### 12.1 DO's (권장사항)

✅ **단일 책임 원칙 준수**
- 각 MCP 서버는 하나의 명확한 목적을 가져야 함

✅ **명시적 사용자 동의**
- 모든 Tool 실행 전 사용자 동의 확인

✅ **구조화된 에러 처리**
- JSON-RPC 2.0 표준 에러 코드 사용
- 상세한 에러 정보 제공

✅ **포괄적인 로깅**
- 구조화된 로그 형식 사용
- 요청/응답 추적
- 감사 로깅

✅ **성능 최적화**
- 연결 풀링
- 캐싱 전략
- 비동기 처리

✅ **보안 우선**
- Defense in Depth 적용
- 최소 권한 원칙
- 데이터 암호화

✅ **입력값 우선순위 원칙**
- 사용자 입력값 (최우선)
- 데이터베이스 저장값
- 환경 변수
- 하드코딩된 기본값 (최후)

### 12.2 DON'Ts (피해야 할 것)

❌ **과도한 권한 부여**
- 필요 이상의 권한 요구 금지

❌ **동기 블로킹 작업**
- 긴 작업은 비동기로 처리

❌ **민감 정보 로깅**
- 패스워드, 토큰 등 민감 정보 로그 금지

❌ **에러 무시**
- 모든 에러는 적절히 처리하고 기록

❌ **하드코딩된 설정**
- 모든 설정은 외부 설정 파일이나 환경 변수로

### 12.3 구현 로드맵

| 단계 | 기간 | 주요 작업 |
|------|------|-----------|
| **Foundation** | Week 1-2 | Core protocol, Basic tools, Error handling |
| **Security** | Week 3 | Authentication, Authorization, Audit logging |
| **Performance** | Week 4 | Caching, Connection pooling, Optimization |
| **Testing** | Week 5 | Unit tests, Integration tests, Load testing |
| **Production** | Week 6 | Monitoring, Deployment, Documentation |

---

## 부록 A: 체크리스트

### MCP 서버 개발 체크리스트

- [ ] **프로토콜 구현**
  - [ ] JSON-RPC 2.0 메시지 처리
  - [ ] Initialize 핸들러
  - [ ] Tools/Resources/Prompts 구현
  - [ ] 에러 응답 형식

- [ ] **보안**
  - [ ] 사용자 동의 메커니즘
  - [ ] 권한 검증 시스템
  - [ ] 감사 로깅
  - [ ] 데이터 암호화

- [ ] **성능**
  - [ ] 연결 풀링
  - [ ] 캐싱 전략
  - [ ] 비동기 처리
  - [ ] Rate limiting

- [ ] **테스트**
  - [ ] Unit tests (>80% coverage)
  - [ ] Integration tests
  - [ ] Load tests
  - [ ] Security tests

- [ ] **운영**
  - [ ] 헬스 체크
  - [ ] 메트릭 수집
  - [ ] 구조화된 로깅
  - [ ] 알림 설정

- [ ] **문서화**
  - [ ] API 문서
  - [ ] 배포 가이드
  - [ ] 운영 매뉴얼
  - [ ] 트러블슈팅 가이드

---

## 부록 B: 참고 자료

### 공식 문서
- **MCP Specification**: https://modelcontextprotocol.io/specification
- **MCP Best Practices**: https://modelcontextprotocol.info/docs/best-practices/
- **JSON-RPC 2.0**: https://www.jsonrpc.org/specification

### 구현 SDK
- **Python SDK**: https://github.com/modelcontextprotocol/python-sdk
- **TypeScript SDK**: https://github.com/modelcontextprotocol/typescript-sdk

### 예제 구현
- **MCP Servers**: https://github.com/modelcontextprotocol/servers

---

**작성일**: 2025-10-18
**버전**: 3.0.0 (MCP 공식 스펙 기반)
**기반 스펙**: MCP Specification 2025-06-18