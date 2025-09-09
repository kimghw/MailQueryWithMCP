# MCP Server claude.ai 연결 문제 해결 가이드

## 문제 증상

claude.ai에서 MCP 서버 연결 시 다음과 같은 문제가 발생했습니다:

1. **연결 상태 문제**: "연결됨" 대신 "구성"으로만 표시
2. **도구 가시성 문제**: 도구(tools)가 표시되지 않거나 검색되지 않음
3. **초기화 실패**: MCP 프로토콜 초기화 과정에서 오류 발생
4. **Tool execution failed 에러**: 서버는 정상 작동하지만 Claude Connector에서 에러 표시

## 근본 원인 분석

### 1. MCP 프로토콜 스펙 위반

#### Null 필드 처리 문제
```json
// 잘못된 예시 (스펙 위반)
{
  "capabilities": {
    "logging": null,  // ❌ null 값을 전송
    "resources": null
  }
}

// 올바른 예시
{
  "capabilities": {
    "logging": {},  // ✅ 빈 객체 사용
    "resources": {
      "listChanged": false
    }
  }
}
```

#### 프롬프트 역할(role) 문제
```python
# 잘못된 예시
PromptMessage(
    role="system",  # ❌ "system"은 허용되지 않음
    content=TextContent(type="text", text=prompt_content)
)

# 올바른 예시
PromptMessage(
    role="assistant",  # ✅ "user" 또는 "assistant"만 허용
    content=TextContent(type="text", text=prompt_content)
)
```

### 2. 복잡한 JSON Schema 문제

#### anyOf 구조 문제
```json
// Pydantic이 생성한 복잡한 스키마 (claude.ai가 파싱 실패)
{
  "extracted_organization": {
    "anyOf": [
      {"type": "string"},
      {"type": "null"}
    ],
    "default": null,
    "description": "Organization code"
  }
}

// 단순화된 스키마 (claude.ai가 정상 파싱)
{
  "extracted_organization": {
    "type": "string",
    "description": "Organization code (KR, NK, etc.)"
  }
}
```

### 3. 도구 응답 시 null 필드 포함

```python
# 문제가 되는 코드
tools_data = []
for tool in tools:
    tool_dict = tool.model_dump()
    tools_data.append(tool_dict)  # null 필드가 포함됨

# 수정된 코드
tools_data = []
for tool in tools:
    tool_dict = tool.model_dump()
    # null 필드 제거
    cleaned_tool = {}
    for key, value in tool_dict.items():
        if value is not None:
            cleaned_tool[key] = value
    tools_data.append(cleaned_tool)
```

## 해결 방법

### 1. 초기화 응답 수정

```python
@self.mcp_server.initialize()
async def handle_initialize(params: InitializeParams) -> InitializeResult:
    caps = self.mcp_server.get_capabilities()
    caps_dict = caps.model_dump()
    
    # null 필드를 빈 객체로 변경
    if caps_dict.get('logging') is None:
        caps_dict['logging'] = {}
    if caps_dict.get('resources') is None:
        caps_dict['resources'] = {"listChanged": False}
    
    return InitializeResult(
        protocolVersion=params.protocol_version,
        capabilities=ServerCapabilities(**caps_dict),
        serverInfo=ServerInfo(
            name="iacsgraph-query-assistant",
            title="IACSGRAPH Query Assistant",  # title 필수
            version="2.0.0"
        )
    )
```

#### HTTP Streaming Server에서의 수정 (2025-09-09 업데이트)

HTTP Streaming 방식의 MCP 서버에서는 tools와 prompts capabilities도 명시적으로 설정해야 합니다:

```python
# modules/mail_attachment/mcp_server/server.py
if method == "initialize":
    # Initialize session with standard Mcp-Session-Id
    session_id = secrets.token_urlsafe(24)
    caps = self.mcp_server.get_capabilities(
        notification_options=NotificationOptions(), experimental_capabilities={}
    )
    
    # Fix null fields to empty objects/lists for spec compliance
    caps_dict = caps.model_dump()
    if caps_dict.get("logging") is None:
        caps_dict["logging"] = {}
    if caps_dict.get("resources") is None:
        caps_dict["resources"] = {"listChanged": False}
    
    # Fix tools and prompts to show they are available
    if caps_dict.get("tools") is None:
        caps_dict["tools"] = {"listChanged": True}
    if caps_dict.get("prompts") is None:
        caps_dict["prompts"] = {"listChanged": True}
    
    # Remove completions field if it's null (not supported by this server)
    if caps_dict.get("completions") is None:
        caps_dict.pop("completions", None)
```

이 수정으로 초기화 응답이 다음과 같이 변경됩니다:

```json
{
  "capabilities": {
    "experimental": {},
    "logging": {},
    "prompts": {
      "listChanged": true  // null → {"listChanged": true}
    },
    "resources": {
      "listChanged": false
    },
    "tools": {
      "listChanged": true  // null → {"listChanged": true}
    }
  }
}
```

### 2. 도구 스키마 단순화

```python
# 복잡한 Pydantic 스키마 대신 단순한 JSON Schema 사용
Tool(
    name="query_with_llm_params",
    title="Query with LLM Parameters",
    description="Execute natural language query with LLM-extracted parameters",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language query"
            },
            "extracted_period": {
                "type": "object",
                "description": "Period with start and end dates",
                "properties": {
                    "start": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "end": {"type": "string", "description": "End date (YYYY-MM-DD)"}
                },
                "required": ["start", "end"]
            },
            "extracted_keywords": {
                "type": "array",
                "description": "Keywords from the query",
                "items": {"type": "string"}
            },
            "extracted_organization": {
                "type": "string",
                "description": "Organization code (KR, NK, etc.)"
            },
            "query_scope": {
                "type": "string",
                "description": "Query scope: all, one, or more",
                "enum": ["all", "one", "more"]
            },
            "intent": {
                "type": "string",
                "description": "Query intent: search, list, analyze, or count",
                "enum": ["search", "list", "analyze", "count"]
            }
        },
        "required": ["query"]
    }
)
```

### 3. 파라미터 전처리

```python
def _preprocess_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """claude.ai에서 전달받은 arguments 전처리"""
    import json
    
    # 문자열 "null"을 실제 None으로 변환
    null_fields = ['extracted_organization', 'category', 'query_scope', 'intent']
    for key in null_fields:
        if key in arguments and arguments[key] == 'null':
            arguments[key] = None
    
    # 문자열로 전달된 정수 변환
    if 'limit' in arguments and isinstance(arguments['limit'], str):
        try:
            arguments['limit'] = int(arguments['limit'])
        except ValueError:
            pass
    
    # JSON 문자열 파싱
    if 'extracted_period' in arguments and isinstance(arguments['extracted_period'], str):
        try:
            arguments['extracted_period'] = json.loads(arguments['extracted_period'])
        except:
            pass
    
    return arguments
```

## MCP 프로토콜 스펙 참조

MCP(Model Context Protocol) 프로토콜 스펙은 다음 위치에서 확인할 수 있습니다:

1. **공식 MCP 문서**: https://modelcontextprotocol.io/docs
2. **MCP TypeScript 구현**: https://github.com/modelcontextprotocol/typescript-sdk
3. **MCP Python SDK**: https://github.com/modelcontextprotocol/python-sdk
4. **프로토콜 스펙 상세**: https://spec.modelcontextprotocol.io/

### 주요 스펙 요구사항

1. **초기화 응답**:
   - `protocolVersion`: "2025-06-18" 형식
   - `capabilities`: null 필드 금지, 빈 객체 사용
   - `serverInfo.title`: 필수 필드

2. **도구 정의**:
   - `name`: 필수, 도구 식별자
   - `title`: 필수, UI 표시용 이름
   - `description`: 도구 설명
   - `inputSchema`: JSON Schema 형식
   - null 필드는 응답에서 제외

3. **프롬프트 역할**:
   - 허용된 값: "user" | "assistant"
   - "system"은 허용되지 않음

## 테스트 및 검증

### 1. 서버 로그 확인
```bash
tail -f mcp_server_latest.log | grep -E "(tools/list|Returning.*tools)"
```

### 2. 도구 가시성 확인
로그에서 다음과 같은 메시지 확인:
```
📤 Returning 3 tools: ['simple_query', 'query', 'query_with_llm_params']
```

### 3. claude.ai 연결 상태
- "구성" → "연결됨"으로 변경 확인
- 도구 목록에서 모든 도구 표시 확인
- 도구 검색 기능 작동 확인

## 추가 권장사항

1. **스키마 검증**: JSON Schema 검증 도구를 사용하여 도구 스키마 사전 검증
2. **단순한 스키마 유지**: 가능한 한 anyOf, oneOf 같은 복잡한 구조 피하기
3. **로깅 추가**: 디버깅을 위한 상세한 로깅 구현
4. **점진적 추가**: 도구를 하나씩 추가하며 테스트

## 관련 이슈

- GitHub Issue: [MCP 서버 claude.ai 연결 문제](https://github.com/anthropics/claude-code/issues)
- MCP 포럼: [anyOf 스키마 파싱 문제](https://forum.modelcontextprotocol.io)