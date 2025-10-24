# Teams Chat MCP Server

Microsoft Teams 1:1 채팅 및 그룹 채팅 관리를 위한 MCP (Model Context Protocol) 서버입니다.

## 개요

Teams Chat MCP 서버는 Microsoft Teams의 1:1 채팅 및 그룹 채팅 메시지를 관리하기 위한 도구를 제공합니다. Microsoft Graph API를 사용하여 Teams 채팅과 통신합니다.

## 필요한 권한 (Azure AD)

Azure AD 앱 등록 시 다음 권한이 필요합니다:

### Microsoft Graph API 권한
- `Chat.Read` - 채팅 및 메시지 읽기
- `Chat.ReadWrite` - 채팅 메시지 읽기/쓰기
- `User.Read` - 사용자 프로필 읽기

> **참고**: 팀 채널 메시지는 지원하지 않습니다. 팀 채널 메시지 기능이 필요한 경우 `Team.ReadBasic.All`, `Channel.ReadBasic.All`, `ChannelMessage.Read.All`, `ChannelMessage.Send` 권한이 필요합니다.

## 제공 도구 (Tools)

### 1. teams_list_chats
사용자의 1:1 채팅 및 그룹 채팅 목록을 조회합니다.

**파라미터:**
- `user_id` (required): 사용자 ID

**예시:**
```json
{
  "user_id": "user@example.com"
}
```

**응답 예시:**
```
💬 총 5개 채팅 조회됨

• [1:1] John Doe
  ID: 19:abc123...

• [그룹] 프로젝트 팀
  ID: 19:def456...
```

### 2. teams_get_chat_messages
채팅의 메시지 목록을 조회합니다.

**파라미터:**
- `user_id` (required): 사용자 ID
- `chat_id` (required): 채팅 ID
- `limit` (optional): 조회할 메시지 수 (기본값: 50)

**예시:**
```json
{
  "user_id": "user@example.com",
  "chat_id": "19:abc123...",
  "limit": 50
}
```

**응답 예시:**
```
💬 총 10개 메시지 조회됨

• [2025-01-24T10:30:00Z] John Doe
  ID: 1234567890
  내용: 안녕하세요, 회의 시간 확인 부탁드립니다...

• [2025-01-24T10:31:00Z] You
  ID: 1234567891
  내용: 오후 2시에 진행합니다...
```

### 3. teams_send_chat_message
채팅에 메시지를 전송합니다.

**파라미터:**
- `user_id` (required): 사용자 ID
- `chat_id` (required): 채팅 ID
- `content` (required): 메시지 내용

**예시:**
```json
{
  "user_id": "user@example.com",
  "chat_id": "19:abc123...",
  "content": "안녕하세요, 확인했습니다!"
}
```

**응답 예시:**
```json
{
  "success": true,
  "message_id": "1234567892",
  "data": {
    "id": "1234567892",
    "createdDateTime": "2025-01-24T10:32:00Z",
    ...
  }
}
```

## 사용 방법

### Standalone 서버 실행
```bash
python3 -m modules.teams_mcp.mcp_server.http_server
```

서버는 기본적으로 `http://0.0.0.0:8004`에서 실행됩니다.

### Unified Server에서 사용
Unified MCP Server는 Teams 서버를 `/teams/` 경로에 마운트합니다:

```bash
python3 entrypoints/production/unified_http_server.py
```

Teams 서버 엔드포인트: `http://localhost:8000/teams/`

## API 엔드포인트

### MCP 프로토콜
- `POST /` - MCP JSON-RPC 요청 처리

### 헬스 체크
- `GET /health` - 서버 상태 확인
- `GET /info` - 서버 정보 조회

### OpenAPI 문서
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc 문서
- `GET /openapi.json` - OpenAPI 스키마

### MCP Discovery
- `GET /.well-known/mcp.json` - MCP 서버 메타데이터

## 모듈 구조

```
modules/teams_mcp/
├── __init__.py              # 모듈 초기화
├── schemas.py               # Pydantic 스키마
├── teams_handler.py         # Teams API 핸들러
├── handlers.py              # MCP 프로토콜 핸들러
├── mcp_server/
│   ├── __init__.py
│   └── http_server.py       # HTTP MCP 서버
└── README.md                # 이 문서
```

## 의존성

- `httpx` - HTTP 클라이언트
- `mcp` - Model Context Protocol SDK
- `pydantic` - 데이터 검증
- `starlette` - ASGI 프레임워크
- `fastapi` - OpenAPI 문서
- `uvicorn` - ASGI 서버

## 인증

Teams Chat MCP 서버는 DCR (Dynamic Client Registration) OAuth 2.0 인증을 지원합니다. 사용자는 Azure AD를 통해 인증하고, 서버는 Microsoft Graph API를 사용하여 Teams 채팅 데이터에 액세스합니다.

## Claude Custom Connector 설정

1. Azure AD 앱 등록
   - Azure Portal → App registrations → New registration
   - Redirect URI: `https://your-server.com/oauth/azure_callback`
   - API permissions → Add `Chat.Read`, `Chat.ReadWrite`, `User.Read`
   - Grant admin consent (테넌트 관리자)

2. Claude.ai Connector 설정
   - Settings → Connectors → Add custom connector
   - Server URL: `https://your-server.com/teams/`
   - OAuth 설정에서 client_id/client_secret 입력
   - 브라우저에서 Azure AD 로그인
   - Teams 채팅 도구 사용 가능

## 예제

### 채팅 목록 조회
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "teams_list_chats",
    "arguments": {
      "user_id": "user@example.com"
    }
  }
}
```

### 메시지 조회
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "teams_get_chat_messages",
    "arguments": {
      "user_id": "user@example.com",
      "chat_id": "19:abc123...",
      "limit": 20
    }
  }
}
```

### 메시지 전송
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "teams_send_chat_message",
    "arguments": {
      "user_id": "user@example.com",
      "chat_id": "19:abc123...",
      "content": "회의록 공유드립니다."
    }
  }
}
```

## 트러블슈팅

### 권한 오류
- Azure AD 앱에 `Chat.Read`, `Chat.ReadWrite` 권한이 부여되었는지 확인
- 관리자 동의가 필요한 권한은 테넌트 관리자의 승인 필요

### 메시지 전송 실패
- `Chat.ReadWrite` 권한 확인
- 사용자가 해당 채팅의 멤버인지 확인

### 토큰 만료
- 서버는 자동으로 토큰을 갱신합니다
- Refresh token이 만료된 경우 재인증 필요

### 채팅 목록이 비어있음
- 사용자에게 활성화된 채팅이 있는지 확인
- Teams 앱에서 메시지를 주고받은 채팅만 표시됨

## FAQ

**Q: 팀 채널 메시지도 지원하나요?**
A: 아니요, 현재 버전은 1:1 채팅과 그룹 채팅만 지원합니다. 팀 채널 메시지는 지원하지 않습니다.

**Q: 파일 공유도 가능한가요?**
A: 현재는 텍스트 메시지만 지원합니다. 파일 첨부는 향후 버전에서 추가될 예정입니다.

**Q: 어떤 채팅 유형을 지원하나요?**
A: 1:1 채팅(oneOnOne)과 그룹 채팅(group)을 모두 지원합니다.

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
