# OneNote MCP Server

Microsoft Graph API를 통한 OneNote 읽기/쓰기/생성 기능을 제공하는 MCP 서버입니다.

## 주요 기능

- **인증 통합**: 기존 `account`, `auth` 모듈을 상속하여 Microsoft OAuth 인증 지원
- **OneNote 조회**: 노트북, 섹션, 페이지 목록 조회
- **페이지 읽기**: OneNote 페이지 내용 HTML 형식으로 조회
- **페이지 생성**: 새 OneNote 페이지 생성
- **페이지 업데이트**: 기존 페이지에 내용 추가 (append)
- **다중 프로토콜**: stdio (Claude Desktop), HTTP (REST API) 지원

## 아키텍처

```
modules/onenote_mcp/
├── __init__.py              # 모듈 진입점 및 export
├── schemas.py               # Request/Response Pydantic 모델
├── onenote_handler.py       # OneNote Graph API 핸들러
├── handlers.py              # MCP 프로토콜 핸들러 (AuthHandlers 상속)
├── entrypoints/
│   ├── stdio_server.py      # MCP stdio 서버 (Claude Desktop)
│   └── http_server.py       # MCP HTTP 서버 (REST API)
└── tests/
    └── test_handlers.py     # 핸들러 테스트
```

## 도구 목록

### 인증 도구 (상속)
- `register_account`: 계정 등록
- `get_account_status`: 계정 상태 조회
- `start_authentication`: OAuth 인증 시작
- `list_active_accounts`: 활성 계정 목록

### OneNote 도구
- `list_notebooks`: 노트북 목록 조회
- `list_sections`: 섹션 목록 조회
- `list_pages`: 페이지 목록 조회
- `get_page_content`: 페이지 내용 조회
- `create_page`: 새 페이지 생성
- `update_page`: 페이지 업데이트 (append)

## 실행 방법

### 1. stdio 서버 (Claude Desktop)

```bash
PYTHONPATH=/home/kimghw/MailQueryWithMCP python modules/onenote_mcp/entrypoints/stdio_server.py
```

### 2. HTTP 서버

```bash
# 기본 포트: 8003
PYTHONPATH=/home/kimghw/MailQueryWithMCP python modules/onenote_mcp/entrypoints/http_server.py

# 커스텀 포트
ONENOTE_SERVER_PORT=8080 PYTHONPATH=/home/kimghw/MailQueryWithMCP python modules/onenote_mcp/entrypoints/http_server.py
```

## 테스트

### HTTP 서버 테스트

```bash
# HTTP 서버 시작 (터미널 1)
PYTHONPATH=/home/kimghw/MailQueryWithMCP python modules/onenote_mcp/entrypoints/http_server.py

# 테스트 실행 (터미널 2)
./scripts/test_onenote_http.sh
```

### stdio 서버 테스트 (gRPC)

```bash
./scripts/test_onenote_stdio.sh
```

## API 예시

### 1. 노트북 목록 조회

```bash
curl -X POST http://localhost:8003/api/list_notebooks \
  -H "Content-Type: application/json" \
  -d '{"user_id": "kimghw"}'
```

### 2. 페이지 내용 조회

```bash
curl -X POST http://localhost:8003/api/get_page_content \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "kimghw",
    "page_id": "0-abc123def456"
  }'
```

### 3. 새 페이지 생성

```bash
curl -X POST http://localhost:8003/api/create_page \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "kimghw",
    "section_id": "0-xyz789",
    "title": "테스트 페이지",
    "content": "<p>이것은 테스트 내용입니다.</p>"
  }'
```

### 4. 페이지 업데이트

```bash
curl -X POST http://localhost:8003/api/update_page \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "kimghw",
    "page_id": "0-abc123def456",
    "content": "<p>추가 내용</p>"
  }'
```

## 인증 설정

### 1. Azure App 등록

1. Azure Portal → App registrations → New registration
2. Redirect URI: `http://localhost:5000/auth/callback`
3. API permissions → Microsoft Graph → Delegated:
   - `Notes.Read`
   - `Notes.ReadWrite`
   - `Notes.Create`
   - `offline_access`

### 2. 계정 등록

```bash
curl -X POST http://localhost:8003/api/tool/register_account \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "kimghw",
    "email": "kimghw@krs.co.kr",
    "oauth_client_id": "YOUR_CLIENT_ID",
    "oauth_client_secret": "YOUR_CLIENT_SECRET",
    "oauth_tenant_id": "YOUR_TENANT_ID"
  }'
```

### 3. OAuth 인증 시작

```bash
curl -X POST http://localhost:8003/api/tool/start_authentication \
  -H "Content-Type: application/json" \
  -d '{"user_id": "kimghw"}'
```

반환된 URL을 브라우저에서 열고 Microsoft 로그인을 완료합니다.

## 환경 변수

- `ONENOTE_SERVER_PORT`: HTTP 서버 포트 (기본값: 8003)
- `MCP_STDIO_MODE`: stdio 모드 활성화 (1)
- `NO_COLOR`: 색상 비활성화 (1)
- `PYTHONUNBUFFERED`: 버퍼링 비활성화 (1)

## 의존성

- `mcp`: MCP 프로토콜 SDK
- `fastapi`: HTTP 서버
- `httpx`: HTTP 클라이언트 (Graph API 호출)
- `pydantic`: 데이터 검증
- `infra.handlers.AuthHandlers`: 인증 핸들러 상속

## 참고

- [Microsoft Graph OneNote API](https://learn.microsoft.com/en-us/graph/api/resources/onenote-api-overview)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
