# 통합 OAuth 아키텍처 - 단일 인증으로 모든 MCP 서비스 접근

## 📋 개요

기존에는 각 MCP 모듈(`/enrollment`, `/mail-query`, `/onenote` 등)마다 별도의 OAuth 인증이 필요했습니다. 이제 **루트 레벨에서 1번만 인증**하면 모든 MCP 서비스에 접근할 수 있도록 개선했습니다.

## 🏗️ 아키텍처 변경사항

### Before (개별 인증)
```
Claude.ai → /mail-query/oauth/authorize → Azure AD 로그인 (1)
Claude.ai → /onenote/oauth/authorize    → Azure AD 로그인 (2)
Claude.ai → /onedrive/oauth/authorize   → Azure AD 로그인 (3)
Claude.ai → /teams/oauth/authorize      → Azure AD 로그인 (4)
```
**문제점:**
- 사용자가 각 서비스마다 OAuth 플로우를 거쳐야 함
- DCR 클라이언트가 여러 개 생성됨
- 토큰 관리가 복잡함

### After (통합 인증)
```
Claude.ai → /.well-known/mcp.json       → 통합 MCP Discovery
Claude.ai → /oauth/authorize            → Azure AD 로그인 (1번만!)
Claude.ai → /oauth/token                → DCR 토큰 발급
Claude.ai → /mail-query/messages        → 동일 Bearer 토큰 사용
Claude.ai → /onenote/notebooks          → 동일 Bearer 토큰 사용
Claude.ai → /onedrive/files             → 동일 Bearer 토큰 사용
Claude.ai → /teams/chats                → 동일 Bearer 토큰 사용
```
**장점:**
- ✅ 1번만 인증하면 모든 서비스 이용 가능
- ✅ DCR 클라이언트 1개만 생성
- ✅ 토큰 관리 간소화
- ✅ 사용자 경험 개선

## 🔄 구현 세부사항

### 1. 통합 MCP Discovery
**엔드포인트:** `GET /.well-known/mcp.json`

**응답:**
```json
{
  "mcp_version": "1.0",
  "name": "Unified Microsoft 365 MCP Services",
  "oauth": {
    "authorization_endpoint": "https://your-domain/oauth/authorize",
    "token_endpoint": "https://your-domain/oauth/token",
    "registration_endpoint": "https://your-domain/oauth/register",
    "scopes_supported": [
      "Mail.Read", "Mail.ReadWrite",
      "Notes.Read", "Notes.ReadWrite",
      "Files.Read", "Files.ReadWrite",
      "Chat.Read", "Chat.ReadWrite",
      "User.Read"
    ],
    "grant_types_supported": ["authorization_code", "refresh_token"],
    "code_challenge_methods_supported": ["S256"]
  },
  "services": [
    {"name": "Mail Query", "path": "/mail-query"},
    {"name": "OneNote", "path": "/onenote"},
    {"name": "OneDrive", "path": "/onedrive"},
    {"name": "Teams", "path": "/teams"},
    {"name": "Enrollment", "path": "/enrollment"}
  ]
}
```

### 2. OAuth 플로우 (루트 레벨)

#### DCR 클라이언트 등록
```bash
curl -X POST https://your-domain/oauth/register \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Claude Unified MCP Client",
    "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"],
    "scope": "Mail.Read Notes.Read Files.Read Chat.Read User.Read"
  }'
```

**응답:**
```json
{
  "client_id": "dcr_xxxxxxxxxxxx",
  "client_secret": "yyyyyyyyyyyyyyyy",
  "client_id_issued_at": 1729843200
}
```

#### 인증 시작
```
GET /oauth/authorize?
  client_id=dcr_xxxxxxxxxxxx&
  redirect_uri=https://claude.ai/api/mcp/auth_callback&
  scope=Mail.Read%20Notes.Read%20Files.Read%20Chat.Read%20User.Read&
  code_challenge=XXXXXXX&
  code_challenge_method=S256&
  state=YYYYYYY
```

→ 사용자가 Azure AD 로그인
→ `/oauth/azure_callback?code=...&state=...`
→ Claude로 리다이렉트: `https://claude.ai/api/mcp/auth_callback?code={auth_code}&state={state}`

#### 토큰 교환
```bash
curl -X POST https://your-domain/oauth/token \
  -d "grant_type=authorization_code" \
  -d "code={auth_code}" \
  -d "client_id=dcr_xxxxxxxxxxxx" \
  -d "client_secret=yyyyyyyyyyyyyyyy" \
  -d "code_verifier={verifier}"
```

**응답:**
```json
{
  "access_token": "dcr_access_token_xxxxx",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "dcr_refresh_token_yyyyy",
  "scope": "Mail.Read Notes.Read Files.Read Chat.Read User.Read"
}
```

### 3. MCP 서비스 호출 (통합 Bearer 토큰)

모든 MCP 서비스에 동일한 Bearer 토큰을 사용:

```bash
# Mail Query
curl -X POST https://your-domain/mail-query/ \
  -H "Authorization: Bearer dcr_access_token_xxxxx" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"query_email"}}'

# OneNote
curl -X POST https://your-domain/onenote/ \
  -H "Authorization: Bearer dcr_access_token_xxxxx" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"list_notebooks"}}'

# OneDrive
curl -X POST https://your-domain/onedrive/ \
  -H "Authorization: Bearer dcr_access_token_xxxxx" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"list_files"}}'

# Teams
curl -X POST https://your-domain/teams/ \
  -H "Authorization: Bearer dcr_access_token_xxxxx" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"list_chats"}}'
```

### 4. 미들웨어 구조

**unified_http_server.py:**
```python
# 전역 OAuth 미들웨어 (환경변수로 제어)
if os.getenv("ENABLE_OAUTH_AUTH", "false").lower() == "true":
    app.add_middleware(OAuth2Middleware)
```

**OAuth2Middleware:**
```python
class OAuth2Middleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 1. Bearer 토큰 검증 (verify_bearer_token_middleware)
        # 2. DCR 토큰 → Azure 토큰 매핑
        # 3. request.state.azure_token 주입
        # 4. 다음 핸들러로 진행
```

**각 MCP 서버:**
```python
async def _handle_streaming_request(self, request: Request):
    # request.state.azure_token 사용
    # (ENABLE_OAUTH_AUTH=true 시 자동 주입됨)
```

## 🗄️ 데이터베이스 스키마

### dcr_clients (DCR 클라이언트)
```sql
CREATE TABLE dcr_clients (
    dcr_client_id TEXT PRIMARY KEY,       -- 1개만 생성
    dcr_client_secret TEXT NOT NULL,
    dcr_client_name TEXT,
    dcr_requested_scope TEXT,             -- 모든 scope 포함
    azure_application_id TEXT NOT NULL
);
```

### dcr_azure_tokens (Azure 사용자 토큰)
```sql
CREATE TABLE dcr_azure_tokens (
    object_id TEXT PRIMARY KEY,           -- Azure User Object ID
    application_id TEXT NOT NULL,
    access_token TEXT NOT NULL,           -- Azure Access Token
    refresh_token TEXT,
    expires_at DATETIME NOT NULL,
    scope TEXT,                            -- 모든 scope
    user_email TEXT,
    user_name TEXT
);
```

### dcr_tokens (DCR 토큰)
```sql
CREATE TABLE dcr_tokens (
    dcr_token_value TEXT PRIMARY KEY,     -- DCR Bearer 토큰
    dcr_client_id TEXT NOT NULL,          -- 동일한 client_id
    dcr_token_type TEXT NOT NULL,         -- 'Bearer', 'refresh'
    azure_object_id TEXT,                 -- Azure 사용자 매핑
    expires_at DATETIME NOT NULL
);
```

**핵심:**
- `dcr_clients`: 1개 행만 유지
- `dcr_tokens`: `azure_object_id`로 사용자별 토큰 관리
- 모든 MCP 서비스가 동일한 DCR 클라이언트 사용

## 📝 설정 방법

### 환경변수
```bash
# .env 파일
ENABLE_OAUTH_AUTH=true                     # OAuth 미들웨어 활성화

# Azure AD 설정
DCR_AZURE_CLIENT_ID=your-azure-app-id
DCR_AZURE_CLIENT_SECRET=your-azure-secret
DCR_AZURE_TENANT_ID=your-tenant-id
DCR_OAUTH_REDIRECT_URI=https://your-domain/oauth/azure_callback

# 접근 제어 (선택사항)
DCR_ALLOWED_USERS=user1@example.com,user2@example.com
```

### Azure Portal 설정
1. **Redirect URI 등록:**
   ```
   https://your-domain/oauth/azure_callback
   ```

2. **Scope 설정:**
   - Microsoft Graph
     - Mail.Read
     - Mail.ReadWrite
     - Notes.Read
     - Notes.ReadWrite
     - Files.Read
     - Files.ReadWrite
     - Chat.Read
     - Chat.ReadWrite
     - User.Read

3. **Client Secret 생성**

## 🚀 실행

```bash
# 통합 서버 시작
python entrypoints/production/unified_http_server.py --port 8000

# 또는 환경변수로 포트 지정
export MCP_PORT=8000
export ENABLE_OAUTH_AUTH=true
python entrypoints/production/unified_http_server.py
```

**로그 예시 (OAuth 활성화):**
```
================================================================================
🔐 OAuth 인증 미들웨어: 활성화됨 (ENABLE_OAUTH_AUTH=true)
   → 모든 MCP 요청에 Bearer 토큰 필요
   → 제외 경로: /oauth/, /health, /info, /.well-known/
================================================================================
```

## 🔍 테스트

### 1. MCP Discovery 확인
```bash
curl https://your-domain/.well-known/mcp.json
```

### 2. OAuth 플로우 테스트
```bash
# 1) DCR 클라이언트 등록
CLIENT_RESPONSE=$(curl -X POST https://your-domain/oauth/register \
  -H "Content-Type: application/json" \
  -d '{"client_name":"Test Client","redirect_uris":["http://localhost:3000/callback"]}')

CLIENT_ID=$(echo $CLIENT_RESPONSE | jq -r '.client_id')
CLIENT_SECRET=$(echo $CLIENT_RESPONSE | jq -r '.client_secret')

# 2) 인증 URL 생성 (브라우저에서 열기)
echo "https://your-domain/oauth/authorize?client_id=$CLIENT_ID&redirect_uri=http://localhost:3000/callback&scope=Mail.Read%20User.Read"

# 3) 콜백에서 받은 code로 토큰 교환
ACCESS_TOKEN=$(curl -X POST https://your-domain/oauth/token \
  -d "grant_type=authorization_code" \
  -d "code=$AUTH_CODE" \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" | jq -r '.access_token')

# 4) MCP 서비스 호출
curl -X POST https://your-domain/mail-query/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### 3. 토큰 검증
```bash
# 데이터베이스 확인
sqlite3 data/dcr_oauth.db "
SELECT
  d.dcr_client_id,
  d.dcr_token_type,
  a.user_email,
  a.scope
FROM dcr_tokens d
LEFT JOIN dcr_azure_tokens a ON d.azure_object_id = a.object_id
WHERE d.dcr_status = 'active'
  AND d.expires_at > datetime('now')
ORDER BY d.issued_at DESC;
"
```

## 🔒 보안

### 인증 제외 경로
다음 경로는 인증 없이 접근 가능:
- `/.well-known/*` - MCP/OAuth Discovery
- `/oauth/*` - OAuth 플로우
- `/health` - 헬스체크
- `/info` - 서버 정보
- `/enrollment/callback` - Enrollment OAuth 콜백 (레거시)

### 토큰 암호화
모든 민감 정보는 AES-256-GCM으로 암호화:
- `dcr_client_secret`
- `dcr_token_value`
- `azure_access_token`
- `azure_refresh_token`

### PKCE 지원
- Authorization Code Interception 공격 방지
- S256 method 지원
- code_challenge/code_verifier 검증

## 🎯 마이그레이션 가이드

### 기존 시스템에서 전환

1. **환경변수 추가:**
   ```bash
   ENABLE_OAUTH_AUTH=true
   ```

2. **기존 토큰 정리 (선택사항):**
   ```sql
   -- 기존 DCR 클라이언트가 여러 개인 경우
   DELETE FROM dcr_tokens WHERE dcr_status = 'active';
   DELETE FROM dcr_clients WHERE dcr_client_id != 'dcr_primary';
   ```

3. **서버 재시작:**
   ```bash
   systemctl restart unified-mcp-server
   ```

4. **Claude.ai에서 재인증:**
   - 기존 MCP 연결 삭제
   - `https://your-domain/.well-known/mcp.json`로 새로 등록
   - 1번만 OAuth 인증

## 📊 모니터링

### 활성 토큰 확인
```sql
SELECT
  COUNT(*) as active_tokens,
  COUNT(DISTINCT dcr_client_id) as unique_clients,
  COUNT(DISTINCT azure_object_id) as unique_users
FROM dcr_tokens
WHERE dcr_status = 'active'
  AND dcr_token_type = 'Bearer'
  AND expires_at > datetime('now');
```

### 사용자별 서비스 접근 로그
각 MCP 서버의 로그에서:
```
✅ Authenticated DCR client: dcr_xxxxx for /mail-query/messages
   → Azure user: user@example.com
   → Scope: Mail.Read User.Read
```

## 🆘 트러블슈팅

### 인증 실패
```json
{"error": {"code": -32001, "message": "Authentication required"}}
```
**원인:** Bearer 토큰이 없거나 만료됨
**해결:** `/oauth/token`으로 새 토큰 발급

### Scope 부족
```json
{"error": "insufficient_scope"}
```
**원인:** 요청한 서비스에 필요한 scope이 없음
**해결:** `/oauth/authorize`에서 필요한 scope 포함하여 재인증

### 중복 인증
**증상:** 각 MCP 서버에서 개별 인증 요구
**원인:** `ENABLE_OAUTH_AUTH=false` 또는 미설정
**해결:** `.env`에 `ENABLE_OAUTH_AUTH=true` 추가

## 📚 참고

- [DCR OAuth 플로우](./dcr-oauth-call-flow.md)
- [DCR 아키텍처 분석](./dcr-architecture-analysis.md)
- [RFC 7591: OAuth Dynamic Client Registration](https://tools.ietf.org/html/rfc7591)
- [RFC 7636: PKCE](https://tools.ietf.org/html/rfc7636)
