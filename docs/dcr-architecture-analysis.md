# DCR 서버 구조 및 Claude.ai와의 데이터 교환 분석

## 📋 전체 아키텍처 개요

DCR(Dynamic Client Registration) 서버는 RFC 7591 표준 OAuth2 프록시로 구현되어 있습니다. **한 번의 Azure AD 인증으로 모든 MCP 서비스(mail-query, onenote, onedrive, teams)를 사용**할 수 있도록 설계되었습니다.

---

## 🔍 1. MCP Discovery 과정 (Claude.ai가 서버를 찾는 방법)

Claude.ai가 MCP 서버에 연결하기 전에 서버의 기능과 인증 방식을 자동으로 발견하는 과정입니다.

### Discovery Flow

```
Claude.ai
  ↓
1. GET /.well-known/oauth-authorization-server
  ↓ 응답
{
  "issuer": "https://your-server.com",
  "authorization_endpoint": "/oauth/authorize",
  "token_endpoint": "/oauth/token",
  "registration_endpoint": "/oauth/register",
  "grant_types_supported": ["authorization_code", "refresh_token"],
  "code_challenge_methods_supported": ["S256", "plain"]
}
  ↓
2. GET /.well-known/oauth-protected-resource
  ↓ 응답
{
  "resource": "https://your-server.com",
  "authorization_servers": ["https://your-server.com"],
  "bearer_methods_supported": ["header"],
  "scopes_supported": ["Mail.Read", "Mail.ReadWrite", "User.Read"]
}
  ↓
3. GET /mail-query/.well-known/mcp.json
  ↓ 응답
{
  "mcp_version": "1.0",
  "name": "Mail Query MCP Server",
  "description": "Email attachment management and query service",
  "oauth": {
    "authorization_endpoint": "https://your-server.com/oauth/authorize",
    "token_endpoint": "https://your-server.com/oauth/token",
    "registration_endpoint": "https://your-server.com/oauth/register",
    "scopes_supported": ["Mail.Read", "Mail.ReadWrite", "User.Read"],
    "grant_types_supported": ["authorization_code", "refresh_token"],
    "code_challenge_methods_supported": ["S256"]
  },
  "capabilities": {
    "tools": true,
    "resources": false,
    "prompts": false
  }
}
```

### Discovery 엔드포인트 구현

**OAuth Authorization Server Metadata (RFC 8414)**
- 경로: `/.well-known/oauth-authorization-server`
- 코드: `unified_http_server.py:266-287`
- 목적: OAuth 인증 서버의 엔드포인트와 지원 기능 공개

**OAuth Protected Resource Metadata (RFC 8707)**
- 경로: `/.well-known/oauth-protected-resource`
- 코드: `unified_http_server.py:289-306`
- 목적: 보호된 리소스의 인증 요구사항 명시

**MCP Service Discovery**
- 경로: `/{service}/.well-known/mcp.json`
  - `/mail-query/.well-known/mcp.json`
  - `/onenote/.well-known/mcp.json`
  - `/onedrive/.well-known/mcp.json`
  - `/teams/.well-known/mcp.json`
  - `/enrollment/.well-known/mcp.json`
- 코드: `unified_http_server.py:308-449`
- 목적: 각 MCP 서비스의 기능과 OAuth 설정 공개

### 주요 서비스별 Discovery 응답

#### Mail Query MCP Server
```json
{
  "mcp_version": "1.0",
  "name": "Mail Query MCP Server",
  "description": "Email attachment management and query service",
  "oauth": {
    "scopes_supported": ["Mail.Read", "Mail.ReadWrite", "User.Read"]
  },
  "capabilities": {
    "tools": true,
    "resources": false,
    "prompts": false
  }
}
```

#### OneNote MCP Server
```json
{
  "name": "OneNote MCP Server",
  "description": "OneNote notebooks, sections, and pages management service",
  "oauth": {
    "scopes_supported": ["Notes.ReadWrite", "Notes.Create", "User.Read"]
  }
}
```

#### OneDrive MCP Server
```json
{
  "name": "OneDrive MCP Server",
  "description": "OneDrive file management service with read/write capabilities",
  "oauth": {
    "scopes_supported": ["Files.Read", "Files.ReadWrite", "Files.ReadWrite.All", "User.Read"]
  }
}
```

#### Teams Chat MCP Server
```json
{
  "name": "Teams Chat MCP Server",
  "description": "Microsoft Teams 1:1 and group chat service",
  "oauth": {
    "scopes_supported": ["Chat.Read", "Chat.ReadWrite", "User.Read"]
  }
}
```

### Discovery의 중요성

1. **자동 설정**: Claude.ai가 수동 설정 없이 서버 기능을 자동으로 파악
2. **OAuth 엔드포인트 발견**: 인증 URL을 하드코딩하지 않고 동적으로 발견
3. **기능 협상**: 서버가 지원하는 기능(tools, resources, prompts)을 클라이언트가 확인
4. **Scope 결정**: 필요한 권한을 서버 메타데이터에서 확인
5. **PKCE 지원 확인**: 보안 강화를 위한 PKCE 사용 여부 결정

### 인증 제외 경로

Discovery 엔드포인트는 **Bearer 토큰 없이 접근 가능**합니다:

```python
# auth_middleware.py:26-28
if "/.well-known/" in path:
    return None  # Skip authentication for discovery endpoints
```

**이유:** 인증 전에 서버 정보를 먼저 알아야 인증 플로우를 시작할 수 있기 때문입니다.

---

## 🔐 2. OAuth2 인증 플로우 (Claude.ai ↔ DCR ↔ Azure AD)

### Phase 0: Discovery (선행 단계)

Claude.ai는 위의 Discovery 과정을 통해 다음 정보를 획득합니다:
- OAuth 엔드포인트: `/oauth/authorize`, `/oauth/token`, `/oauth/register`
- 지원 Grant Type: `authorization_code`, `refresh_token`
- PKCE 지원: `S256`, `plain`
- 필요한 Scope: `Mail.Read`, `Mail.ReadWrite`, `User.Read` 등

### Phase 1: 클라이언트 등록 (Dynamic Client Registration)

```
Claude.ai → POST /oauth/register
  ↓
DCRService.register_client()
  ↓ 생성
dcr_client_id, dcr_client_secret (DCR 자체 토큰)
  ↓ 저장
dcr_clients 테이블
```

**핵심 코드:** `modules/dcr_oauth/dcr_service.py:181-229`

**구현 세부사항:**
- DCR 클라이언트 ID: `dcr_{random_token}` 형식
- 클라이언트 시크릿: 32바이트 URL-safe 토큰
- 요청 정보: client_name, redirect_uris, grant_types, scope
- Azure Application ID와 매핑되어 저장

### Phase 2: 인증 시작

```
Claude.ai → GET /oauth/authorize?client_id={dcr_client_id}&redirect_uri={claude_callback}
  ↓
oauth_authorize_handler() (unified_http_server.py:489)
  ↓ 검증
dcr_client_id 유효성 확인
  ↓ 생성
authorization_code (내부 매핑용)
  ↓ 리다이렉트
Azure AD Authorization URL (state에 auth_code 포함)
```

**핵심 코드:** `entrypoints/production/unified_http_server.py:489-563`

**중요 메커니즘:**
- PKCE 지원 (code_challenge, code_challenge_method)
- Internal state: `{auth_code}:{original_state}` 형식으로 매핑 정보 보존
- Redirect URI 검증 (dcr_redirect_uris에 등록된 URI만 허용)
- Azure AD URL 생성:
  ```
  https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize?
    client_id={azure_application_id}&
    response_type=code&
    redirect_uri={azure_redirect_uri}&
    scope={scope}&
    state={internal_state}
  ```

### Phase 3: Azure AD 콜백 처리

```
Azure AD → GET /oauth/azure_callback?code={azure_code}&state={auth_code}
  ↓
oauth_azure_callback_handler() (unified_http_server.py:872)
  ↓ 토큰 교환
Azure AD Token Endpoint
  ↓ 사용자 정보 조회
Microsoft Graph API /me
  ↓ 저장
dcr_azure_tokens 테이블 (object_id 기준, 공유 가능)
  ↓ 업데이트
authorization_code에 azure_object_id 연결
  ↓ 리다이렉트
Claude.ai callback URL (auth_code 전달)
```

**핵심 코드:** `entrypoints/production/unified_http_server.py:872-1129`

**처리 단계:**
1. **State 파싱**: `{auth_code}:{original_state}` 분리
2. **Auth Code 검증**: dcr_tokens 테이블에서 조회 (유효성, 만료 시간 확인)
3. **Azure 토큰 교환**:
   - Endpoint: `https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token`
   - 파라미터: client_id, client_secret, code, redirect_uri, grant_type
4. **사용자 정보 조회**: Microsoft Graph API `/v1.0/me` 호출
   - object_id (Azure User Object ID)
   - userPrincipalName, displayName, mail
5. **접근 제어**: `DCR_ALLOWED_USERS` 환경변수로 허용된 사용자만 인증
6. **토큰 저장**: dcr_azure_tokens 테이블 (INSERT OR REPLACE)
7. **Auth Code 업데이트**: azure_object_id 연결
8. **Claude 리다이렉트**: `{claude_redirect_uri}?code={auth_code}&state={original_state}`

### Phase 4: 토큰 교환

```
Claude.ai → POST /oauth/token (grant_type=authorization_code)
  ↓
oauth_token_handler() (unified_http_server.py:575)
  ↓ 검증
auth_code → azure_object_id 조회
  ↓ 조회
dcr_azure_tokens (Azure 실제 토큰)
  ↓ 생성
새로운 dcr_access_token, dcr_refresh_token
  ↓ 저장
dcr_tokens 테이블 (azure_object_id 연결)
  ↓ 반환
{access_token, refresh_token, expires_in}
```

**핵심 코드:** `entrypoints/production/unified_http_server.py:575-869`

**Grant Type: authorization_code**
1. **클라이언트 인증**: client_id, client_secret 검증
2. **Auth Code 검증**: PKCE code_verifier 검증 포함
3. **Azure 토큰 조회**: azure_object_id로 dcr_azure_tokens 조회
4. **DCR 토큰 생성**:
   - access_token: 32바이트 URL-safe 토큰
   - refresh_token: 32바이트 URL-safe 토큰
   - expires_in: Azure 토큰과 동일
5. **중복 방지**: 기존 Bearer/refresh 토큰 DELETE 후 INSERT
6. **응답**:
   ```json
   {
     "access_token": "xxx",
     "token_type": "Bearer",
     "expires_in": 3600,
     "refresh_token": "xxx",
     "scope": "Mail.Read User.Read"
   }
   ```

**Grant Type: refresh_token**
1. **Refresh Token 검증**: dcr_tokens 테이블에서 암호화된 토큰 복호화 및 비교
2. **Azure 토큰 조회**: azure_object_id로 현재 유효한 Azure 토큰 조회
3. **새 토큰 생성**: 새로운 access_token, refresh_token 발급
4. **기존 토큰 삭제**: 중복 방지를 위해 DELETE 후 INSERT
5. **30일 유효기간**: refresh_token은 30일간 유효

---

## 🗄️ 3. 데이터베이스 스키마 (4계층 구조)

### dcr_azure_auth - Azure 앱 인증 정보

```sql
CREATE TABLE dcr_azure_auth (
    application_id TEXT PRIMARY KEY,  -- Azure Application (client) ID
    client_secret TEXT NOT NULL,      -- Azure Client Secret (암호화)
    tenant_id TEXT NOT NULL,          -- Azure Tenant ID
    redirect_uri TEXT,                -- Azure에 등록된 Redirect URI
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**용도:** Azure Portal에서 생성한 App Registration 정보 저장
- 환경변수에서 자동 로드 및 DB 저장 (DCRService.__init__)
- 모든 DCR 클라이언트가 공유하는 Azure 앱 설정

### dcr_azure_tokens - Azure 사용자 토큰 (공유 저장소)

```sql
CREATE TABLE dcr_azure_tokens (
    object_id TEXT PRIMARY KEY,       -- Azure User Object ID
    application_id TEXT NOT NULL,     -- 어느 Azure 앱으로 받았는지
    access_token TEXT NOT NULL,       -- Azure Access Token (암호화)
    refresh_token TEXT,               -- Azure Refresh Token (암호화)
    expires_at DATETIME NOT NULL,
    scope TEXT,
    user_email TEXT,
    user_name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES dcr_azure_auth(application_id)
);
```

**핵심 특징:**
- **토큰 공유**: 동일한 Azure 사용자(object_id)의 토큰을 여러 DCR 클라이언트가 공유
- **자동 갱신**: INSERT OR REPLACE로 토큰 갱신 시 기존 레코드 덮어쓰기
- **암호화 저장**: AES-256-GCM으로 access_token, refresh_token 암호화

### dcr_clients - Claude가 등록한 클라이언트

```sql
CREATE TABLE dcr_clients (
    dcr_client_id TEXT PRIMARY KEY,       -- dcr_xxx (DCR 서버가 생성)
    dcr_client_secret TEXT NOT NULL,      -- DCR 클라이언트 시크릿 (암호화)
    dcr_client_name TEXT,
    dcr_redirect_uris TEXT,               -- JSON array
    dcr_grant_types TEXT,                 -- JSON array
    dcr_requested_scope TEXT,
    azure_application_id TEXT NOT NULL,   -- 어느 Azure 앱을 사용하는지
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (azure_application_id) REFERENCES dcr_azure_auth(application_id)
);
```

**용도:** Claude.ai가 동적 등록한 클라이언트 정보 관리
- dcr_redirect_uris: `["https://claude.ai/api/mcp/auth_callback"]`
- dcr_grant_types: `["authorization_code", "refresh_token"]`

### dcr_tokens - DCR 발급 토큰

```sql
CREATE TABLE dcr_tokens (
    dcr_token_value TEXT PRIMARY KEY,     -- Bearer 토큰 (암호화)
    dcr_client_id TEXT NOT NULL,          -- 어느 DCR 클라이언트 토큰인지
    dcr_token_type TEXT NOT NULL,         -- 'Bearer', 'authorization_code', 'refresh'
    dcr_status TEXT DEFAULT 'active',     -- 'active', 'expired', 'revoked'
    azure_object_id TEXT,                 -- 어느 Azure 사용자 토큰인지 (JOIN 키)
    expires_at DATETIME NOT NULL,
    issued_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,                        -- JSON (PKCE, redirect_uri, state 등)
    FOREIGN KEY (dcr_client_id) REFERENCES dcr_clients(dcr_client_id) ON DELETE CASCADE,
    FOREIGN KEY (azure_object_id) REFERENCES dcr_azure_tokens(object_id) ON DELETE SET NULL
);
```

**토큰 타입:**
1. **authorization_code**: 일회용 인증 코드 (10분 유효)
   - metadata: redirect_uri, state, scope, code_challenge, code_challenge_method
2. **Bearer**: DCR access token (Azure 토큰과 동일한 만료 시간)
   - azure_object_id로 dcr_azure_tokens와 연결
3. **refresh**: DCR refresh token (30일 유효)
   - 토큰 갱신 시 사용

**인덱스:**
- `idx_dcr_tokens_expires`: 만료 시간 기준 검색
- `idx_dcr_tokens_client_status`: 클라이언트별 활성 토큰 조회
- `idx_dcr_tokens_object_id`: Azure 사용자별 토큰 조회
- `idx_dcr_tokens_type`: 토큰 타입별 조회

---

## 🔄 4. 프록시 패턴 핵심 메커니즘

### 토큰 매핑 구조

```
Claude.ai의 dcr_access_token
  ↓ (dcr_tokens 테이블: dcr_token_value)
azure_object_id
  ↓ (dcr_azure_tokens 테이블: object_id = PK)
Azure AD의 실제 access_token
  ↓
Microsoft Graph API 호출
```

**JOIN 쿼리 예시:**
```sql
SELECT d.dcr_client_id, d.expires_at, d.azure_object_id,
       a.access_token, a.scope, a.user_email
FROM dcr_tokens d
LEFT JOIN dcr_azure_tokens a ON d.azure_object_id = a.object_id
WHERE d.dcr_token_type = 'Bearer'
  AND d.dcr_status = 'active'
  AND d.expires_at > CURRENT_TIMESTAMP
```

### Bearer 토큰 검증 플로우

```
MCP 요청 → Authorization: Bearer {dcr_token}
  ↓
auth_middleware.py:14 (verify_bearer_token_middleware)
  ↓ 경로 검증
/.well-known/, /oauth/, /health, /info → 인증 제외
  ↓ 헤더 파싱
Authorization: Bearer {token}
  ↓
DCRService.verify_bearer_token() (dcr_service.py:439)
  ↓ 복호화 및 검증
dcr_tokens JOIN dcr_azure_tokens ON azure_object_id
  ↓ request.state에 주입
request.state.azure_token = azure_access_token
request.state.azure_object_id = object_id
request.state.dcr_client_id = dcr_client_id
request.state.token_scope = scope
  ↓
MCP 핸들러에서 request.state.azure_token 사용
```

**핵심 코드:**
- 미들웨어: `modules/dcr_oauth/auth_middleware.py:14-111`
- 토큰 검증: `modules/dcr_oauth/dcr_service.py:439-477`

**검증 로직:**
1. **암호화된 토큰 복호화**: AES-256-GCM
2. **constant-time 비교**: `secrets.compare_digest()` 사용 (타이밍 공격 방지)
3. **만료 시간 확인**: `expires_at > CURRENT_TIMESTAMP`
4. **Azure 토큰 존재 확인**: LEFT JOIN 결과 검증
5. **상태 주입**: request.state에 Azure 토큰 및 메타데이터 저장

---

## 🌐 5. Claude.ai와의 데이터 교환 (MCP 프로토콜)

### 엔드포인트 구조

```
https://your-server.com/
├── /oauth/register                          (DCR 클라이언트 등록)
├── /oauth/authorize                         (인증 시작 - Azure AD로 리다이렉트)
├── /oauth/token                             (토큰 교환 - DCR 토큰 발급)
├── /oauth/azure_callback                    (Azure AD 콜백 처리)
├── /.well-known/oauth-authorization-server  (OAuth 메타데이터)
├── /.well-known/oauth-protected-resource    (리소스 메타데이터)
└── MCP 서비스 (Bearer 토큰 인증 필요)
    ├── /mail-query/
    │   ├── /.well-known/mcp.json            (MCP discovery)
    │   └── /messages                        (MCP JSONRPC)
    ├── /onenote/
    │   ├── /.well-known/mcp.json
    │   └── /messages
    ├── /onedrive/
    │   ├── /.well-known/mcp.json
    │   └── /messages
    └── /teams/
        ├── /.well-known/mcp.json
        └── /messages
```

**서버 설정:** `entrypoints/production/unified_http_server.py:1132-1160`

### OAuth 메타데이터 응답

```json
{
  "issuer": "https://your-server.com",
  "authorization_endpoint": "https://your-server.com/oauth/authorize",
  "token_endpoint": "https://your-server.com/oauth/token",
  "registration_endpoint": "https://your-server.com/oauth/register",
  "grant_types_supported": ["authorization_code", "refresh_token"],
  "response_types_supported": ["code"],
  "code_challenge_methods_supported": ["plain", "S256"],
  "token_endpoint_auth_methods_supported": ["client_secret_post"]
}
```

### MCP Discovery 응답

```json
{
  "name": "mail-query-server",
  "version": "1.0.0",
  "protocol": "mcp",
  "transport": "http",
  "capabilities": {
    "tools": {},
    "resources": {}
  },
  "oauth": {
    "authorization_endpoint": "https://your-server.com/oauth/authorize",
    "token_endpoint": "https://your-server.com/oauth/token",
    "registration_endpoint": "https://your-server.com/oauth/register"
  }
}
```

### MCP 요청/응답 예시

**요청:**
```http
POST /mail-query/messages HTTP/1.1
Host: your-server.com
Authorization: Bearer eyJhbGc...  (DCR 토큰)
Content-Type: application/json
Mcp-Session-Id: session-xxx

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search_emails",
    "arguments": {
      "query": "from:boss@company.com",
      "max_results": 10
    }
  }
}
```

**미들웨어 처리:**
1. `verify_bearer_token_middleware()` 실행
2. DCR 토큰 → Azure 토큰 매핑
3. `request.state.azure_token` 주입
4. MCP 핸들러로 전달

**MCP 핸들러:**
```python
async def handle_tool_call(request, name, arguments):
    azure_token = request.state.azure_token

    # Microsoft Graph API 호출
    response = await graph_client.get(
        "https://graph.microsoft.com/v1.0/me/messages",
        headers={"Authorization": f"Bearer {azure_token}"},
        params={"$filter": "from/emailAddress/address eq 'boss@company.com'"}
    )

    return response.json()
```

**응답:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Found 3 emails from boss@company.com:\n1. Weekly Report - 2025-10-24\n2. ..."
      }
    ]
  }
}
```

---

## 🔒 6. 보안 메커니즘

### 암호화 (AES-256-GCM)

**구현:** `modules/enrollment/account/_account_helpers.py`

```python
class AccountCryptoHelpers:
    def account_encrypt_sensitive_data(self, plaintext: str) -> str:
        """AES-256-GCM 암호화"""
        key = self._get_encryption_key()  # 32바이트 키
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce), backend=default_backend())
        encrypted = cipher.encryptor().update(plaintext.encode()) + cipher.encryptor().finalize()
        return base64.b64encode(nonce + tag + encrypted).decode()

    def account_decrypt_sensitive_data(self, ciphertext: str) -> str:
        """AES-256-GCM 복호화"""
        data = base64.b64decode(ciphertext)
        nonce, tag, encrypted = data[:12], data[12:28], data[28:]
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag), backend=default_backend())
        return cipher.decryptor().update(encrypted) + cipher.decryptor().finalize().decode()
```

**암호화 대상:**
- `dcr_azure_auth.client_secret` (Azure 앱 시크릿)
- `dcr_azure_tokens.access_token` (Azure 액세스 토큰)
- `dcr_azure_tokens.refresh_token` (Azure 리프레시 토큰)
- `dcr_clients.dcr_client_secret` (DCR 클라이언트 시크릿)
- `dcr_tokens.dcr_token_value` (DCR 토큰)

### 사용자 접근 제어

**환경변수 설정:**
```bash
DCR_ALLOWED_USERS=user1@example.com,user2@example.com,user3@example.com
```

**검증 로직:** `unified_http_server.py:1036-1052`

```python
# Azure AD 콜백 처리 시 사용자 검증
user_email = user_info.get("mail") or user_info.get("userPrincipalName")

if not dcr_service.is_user_allowed(user_email):
    logger.warning(f"❌ User {user_email} is not in allowed users list")
    return Response("""
        <h1>❌ Access Denied</h1>
        <p>User <b>{user_email}</b> is not authorized.</p>
    """, status_code=403)
```

**DCRService 구현:**
```python
def is_user_allowed(self, user_email: str) -> bool:
    """사용자 허용 여부 확인"""
    if not self.allowed_users:
        return True  # 빈 리스트면 모든 사용자 허용

    user_email_lower = user_email.lower().strip()
    return user_email_lower in self.allowed_users
```

### PKCE 지원 (RFC 7636)

**PKCE Flow:**
```
1. Claude.ai가 code_verifier 생성 (43-128자 랜덤 문자열)
2. code_challenge 계산:
   - plain: code_challenge = code_verifier
   - S256: code_challenge = BASE64URL(SHA256(code_verifier))
3. /oauth/authorize?code_challenge={challenge}&code_challenge_method=S256
4. DCR이 metadata에 저장
5. /oauth/token?code_verifier={verifier}
6. DCR이 검증:
   - S256: BASE64URL(SHA256(verifier)) == challenge
   - plain: verifier == challenge
```

**구현:** `modules/dcr_oauth/dcr_service.py:538-547`

```python
def _verify_pkce(self, code_verifier: str, code_challenge: str, method: str = "plain") -> bool:
    """PKCE 검증"""
    if method == "plain":
        return secrets.compare_digest(code_verifier, code_challenge)
    elif method == "S256":
        digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        calculated_challenge = base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
        return secrets.compare_digest(calculated_challenge, code_challenge)
    else:
        return False
```

**authorization_code에 저장:**
```python
metadata = {
    "redirect_uri": redirect_uri,
    "state": state,
    "scope": scope,
    "code_challenge": code_challenge,
    "code_challenge_method": code_challenge_method
}
```

**token 교환 시 검증:**
```python
auth_data = dcr_service.verify_authorization_code(
    code=code,
    dcr_client_id=client_id,
    redirect_uri=redirect_uri,
    code_verifier=code_verifier  # PKCE 검증
)
```

### 토큰 만료 관리

**Authorization Code:**
- 유효기간: 10분
- 일회용 (사용 후 status='expired')

**Access Token:**
- 유효기간: Azure 토큰과 동일 (일반적으로 1시간)
- 자동 만료: `expires_at > CURRENT_TIMESTAMP` 체크

**Refresh Token:**
- 유효기간: 30일
- 갱신 후 기존 토큰 삭제 (중복 방지)

**만료된 토큰 정리:**
```sql
-- 자동 필터링 (쿼리 시)
WHERE expires_at > CURRENT_TIMESTAMP AND dcr_status = 'active'

-- 수동 정리 (배치 작업)
DELETE FROM dcr_tokens
WHERE expires_at < datetime('now', '-7 days');
```

---

## 📊 7. 요약 (한 번 인증으로 모든 서비스 접근)

### 데이터 플로우 다이어그램

```
┌─────────────┐                    ┌─────────────┐                    ┌─────────────┐
│             │  1. DCR 등록       │             │                    │             │
│  Claude.ai  ├───────────────────>│ DCR Server  │                    │  Azure AD   │
│             │  client_id/secret  │             │                    │             │
└─────┬───────┘                    └──────┬──────┘                    └──────┬──────┘
      │                                   │                                  │
      │  2. /oauth/authorize              │  3. Redirect to Azure            │
      ├───────────────────────────────────>│─────────────────────────────────>│
      │                                   │                                  │
      │                                   │  4. Azure callback               │
      │                                   │<─────────────────────────────────┤
      │                                   │                                  │
      │  5. auth_code                     │                                  │
      │<───────────────────────────────────┤                                  │
      │                                   │                                  │
      │  6. /oauth/token                  │                                  │
      ├───────────────────────────────────>│                                  │
      │  dcr_access_token, refresh_token  │                                  │
      │<───────────────────────────────────┤                                  │
      │                                   │                                  │
┌─────┴───────┐                    ┌──────┴──────┐
│             │  8. MCP 요청       │             │
│  Claude.ai  │  + Bearer token    │ DCR Server  │
│             ├───────────────────>│             │
└─────────────┘                    └──────┬──────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
              ┌─────▼──────┐       ┌─────▼──────┐       ┌─────▼──────┐
              │ Mail-Query │       │  OneNote   │       │  OneDrive  │
              │   Server   │       │   Server   │       │   Server   │
              └─────┬──────┘       └─────┬──────┘       └─────┬──────┘
                    │                     │                     │
                    └─────────────────────┼─────────────────────┘
                                          │
                                   ┌──────▼──────┐
                                   │     DCR     │
                                   │ Middleware  │
                                   └──────┬──────┘
                                          │
                                   ┌──────▼──────┐
                                   │ dcr_tokens  │
                                   │ ┌──────────┐│
                                   │ │ dcr_     ││
                                   │ │ token    ││
                                   │ └────┬─────┘│
                                   └──────┼──────┘
                                          │ azure_object_id
                                   ┌──────▼──────┐
                                   │ dcr_azure_  │
                                   │   tokens    │
                                   │ ┌──────────┐│
                                   │ │ azure_   ││
                                   │ │ token    ││
                                   │ └────┬─────┘│
                                   └──────┼──────┘
                                          │
                                   ┌──────▼──────┐
                                   │ Microsoft   │
                                   │ Graph API   │
                                   └─────────────┘
```

### 핵심 장점

1. **단일 인증 (SSO)**
   - 한 번의 Azure AD 로그인으로 모든 MCP 서비스 접근
   - Claude.ai는 하나의 DCR 토큰으로 여러 서비스 호출

2. **토큰 공유 및 재사용**
   - `azure_object_id` 기준으로 여러 DCR 클라이언트가 동일한 Azure 토큰 공유
   - 불필요한 Azure AD 인증 반복 제거
   - 토큰 갱신 시 모든 연결된 DCR 클라이언트에 자동 반영

3. **표준 준수**
   - RFC 7591: Dynamic Client Registration
   - RFC 6749: OAuth 2.0 Authorization Framework
   - RFC 7636: PKCE (Proof Key for Code Exchange)
   - MCP Protocol: Model Context Protocol HTTP Transport

4. **투명한 프록시**
   - Claude.ai는 DCR 토큰만 관리 (Azure 토큰은 서버에서 자동 매핑)
   - MCP 서버는 `request.state.azure_token`으로 투명하게 Azure API 호출
   - 토큰 암호화/복호화는 서버에서 자동 처리

5. **확장성**
   - 새로운 MCP 서비스 추가 시 DCR 인증 인프라 재사용
   - 여러 Azure 앱 지원 가능 (dcr_azure_auth 테이블)
   - 다중 테넌트 지원 가능

### 보안 특징

- **암호화**: 모든 민감 정보 AES-256-GCM 암호화
- **접근 제어**: 화이트리스트 기반 사용자 인증
- **PKCE**: Authorization code interception 공격 방지
- **토큰 격리**: DCR 토큰과 Azure 토큰 분리 관리
- **만료 관리**: 자동 토큰 만료 및 갱신

### 운영 고려사항

**환경변수 설정:**
```bash
# DCR Azure 앱 설정
DCR_AZURE_CLIENT_ID=your-azure-app-id
DCR_AZURE_CLIENT_SECRET=your-azure-secret
DCR_AZURE_TENANT_ID=your-tenant-id
DCR_OAUTH_REDIRECT_URI=https://your-server.com/oauth/azure_callback

# 사용자 접근 제어
DCR_ALLOWED_USERS=user1@example.com,user2@example.com

# OAuth 인증 활성화
ENABLE_OAUTH_AUTH=true

# 데이터베이스 경로
DCR_DATABASE_PATH=/path/to/claudedcr.db
```

**데이터베이스 백업:**
```bash
# 정기 백업
sqlite3 claudedcr.db ".backup claudedcr_backup_$(date +%Y%m%d).db"

# 토큰 정리 (7일 이상 만료된 토큰)
sqlite3 claudedcr.db "DELETE FROM dcr_tokens WHERE expires_at < datetime('now', '-7 days');"
```

**로깅 및 모니터링:**
- 인증 성공/실패: `✅ Authenticated DCR client: {dcr_client_id}`
- 토큰 발급: `✅ DCR access & refresh tokens stored`
- 사용자 접근 거부: `❌ Access denied for user: {email}`
- Azure 콜백 실패: `❌ Azure callback failed: {error}`

---

## 📚 8. 참고 문서

### 주요 파일

1. **DCR 서비스**
   - `modules/dcr_oauth/dcr_service.py` - 핵심 DCR 로직
   - `modules/dcr_oauth/auth_middleware.py` - Bearer 토큰 인증 미들웨어
   - `modules/dcr_oauth/migrations/dcr_schema_v3.sql` - 데이터베이스 스키마

2. **HTTP 서버**
   - `entrypoints/production/unified_http_server.py` - OAuth 엔드포인트 및 MCP 서비스 통합

3. **암호화**
   - `modules/enrollment/account/_account_helpers.py` - AES-256-GCM 암호화 헬퍼

### RFC 표준

- [RFC 7591 - OAuth 2.0 Dynamic Client Registration Protocol](https://tools.ietf.org/html/rfc7591)
- [RFC 6749 - OAuth 2.0 Authorization Framework](https://tools.ietf.org/html/rfc6749)
- [RFC 7636 - PKCE](https://tools.ietf.org/html/rfc7636)

### Microsoft 문서

- [Microsoft Graph API](https://docs.microsoft.com/en-us/graph/api/overview)
- [Azure AD OAuth 2.0](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow)
