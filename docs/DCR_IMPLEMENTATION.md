# DCR (Dynamic Client Registration) 구현 문서

## 개요

Claude AI Custom Connector와 MCP 서버 간 OAuth 2.0 인증을 위한 DCR (Dynamic Client Registration) 구현 문서입니다.

**주요 특징**:
- RFC 7591 (Dynamic Client Registration) 표준 준수
- RFC 6749 (OAuth 2.0 Authorization Framework) 준수
- Azure AD를 백엔드 인증 제공자로 사용
- SQLite 기반 클라이언트 및 토큰 관리
- Fernet 암호화를 통한 민감 데이터 보호

**구현 위치**:
- 서비스: [infra/core/dcr_service.py](../infra/core/dcr_service.py)
- 엔드포인트: [entrypoints/production/unified_http_server.py](../entrypoints/production/unified_http_server.py)
- 데이터베이스: `data/database.db` (SQLite)

## 최종 업데이트

2025-10-22 (로컬 테스트 환경 완성)

## 주요 변경 사항

### 1. DCR 엔드포인트 추가

#### OAuth Discovery Endpoint
- **경로**: `/.well-known/oauth-authorization-server`
- **기능**: OAuth 2.0 서버 메타데이터 제공
- **응답**:
  - `authorization_endpoint`: `/oauth/authorize`
  - `token_endpoint`: `/oauth/token`
  - `registration_endpoint`: `/oauth/register`

#### DCR 등록 엔드포인트
- **경로**: `POST /oauth/register`
- **기능**: 동적 클라이언트 등록 (RFC 7591)
- **요청**: `client_name`, `redirect_uris` 등
- **응답**: `client_id`, `client_secret`, 토큰 엔드포인트 정보

#### OAuth 인증 엔드포인트
- **경로**: `GET /oauth/authorize`
- **기능**: Azure AD 인증 시작
- **플로우**:
  1. DCR 클라이언트 검증
  2. Authorization code 생성 및 DB 저장
  3. Azure AD로 리다이렉트 (PKCE 지원)

#### Azure AD 콜백 엔드포인트
- **경로**: `GET /oauth/azure_callback`
- **기능**: Azure AD로부터 authorization code 수신 및 토큰 교환
- **처리**:
  1. Azure AD에서 authorization code 수신
  2. Azure AD 토큰 엔드포인트에서 access_token 교환
  3. DCR auth_code와 Azure 토큰 매핑하여 DB 저장
  4. Claude AI로 리다이렉트 (DCR auth_code 전달)

#### 토큰 교환 엔드포인트
- **경로**: `POST /oauth/token`
- **기능**: DCR authorization code를 access token으로 교환
- **처리**:
  1. DCR 클라이언트 인증 (client_id, client_secret)
  2. Authorization code 검증
  3. Azure 토큰 조회
  4. DCR access_token 생성 및 Azure 토큰과 매핑
  5. Bearer token 응답

### 2. 데이터베이스 스키마

DCR 서비스는 3개의 테이블을 사용하여 클라이언트 정보, 인증 코드, 토큰을 관리합니다.

#### dcr_clients 테이블
**용도**: DCR로 등록된 클라이언트 정보 저장

```sql
CREATE TABLE IF NOT EXISTS dcr_clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL UNIQUE,           -- DCR이 발급한 클라이언트 ID (예: dcr_xxx)
    client_secret TEXT NOT NULL,              -- 클라이언트 시크릿 (암호화 저장)
    client_id_issued_at INTEGER NOT NULL,     -- 발급 시각 (Unix timestamp)
    client_secret_expires_at INTEGER DEFAULT 0,
    redirect_uris TEXT,                       -- 허용된 리다이렉트 URI 목록 (JSON 배열)
    grant_types TEXT,                         -- 지원하는 grant type (JSON 배열)
    response_types TEXT,                      -- 지원하는 response type (JSON 배열)
    client_name TEXT,                         -- 클라이언트 이름
    client_uri TEXT,
    scope TEXT,                               -- 요청 가능한 스코프
    azure_client_id TEXT NOT NULL,            -- 매핑된 Azure AD 클라이언트 ID
    azure_client_secret TEXT NOT NULL,        -- Azure AD 클라이언트 시크릿 (암호화 저장)
    azure_tenant_id TEXT NOT NULL,            -- Azure AD 테넌트 ID
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**주요 인덱스**:
- `idx_dcr_clients_client_id`: client_id 조회
- `idx_dcr_clients_azure_client_id`: Azure 클라이언트 매핑
- `idx_dcr_clients_is_active`: 활성 클라이언트 필터링

#### dcr_auth_codes 테이블
**용도**: Authorization code와 Azure 토큰 매핑

```sql
CREATE TABLE IF NOT EXISTS dcr_auth_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,                -- DCR이 발급한 authorization code
    client_id TEXT NOT NULL,                  -- 클라이언트 ID (외래키)
    redirect_uri TEXT NOT NULL,               -- 클라이언트의 콜백 URL
    scope TEXT,                               -- 요청된 스코프
    state TEXT,                               -- Claude가 전달한 원본 state 값
    azure_code TEXT,                          -- Azure AD authorization code (사용 안 함)
    azure_access_token TEXT,                  -- Azure AD 액세스 토큰 (콜백 시 저장)
    azure_refresh_token TEXT,                 -- Azure AD 리프레시 토큰 (콜백 시 저장)
    expires_at DATETIME NOT NULL,             -- Authorization code 만료 시간 (10분)
    used_at DATETIME,                         -- 토큰 교환에 사용된 시간 (일회용)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES dcr_clients(client_id)
);
```

**주요 인덱스**:
- `idx_dcr_auth_codes_code`: code 조회
- `idx_dcr_auth_codes_expires_at`: 만료된 코드 정리

**중요**: `azure_access_token`과 `azure_refresh_token`은 `/oauth/azure_callback` 엔드포인트에서 저장됩니다.

#### dcr_tokens 테이블
**용도**: DCR 토큰과 Azure 토큰 매핑

```sql
CREATE TABLE IF NOT EXISTS dcr_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL,                  -- 클라이언트 ID (외래키)
    access_token TEXT NOT NULL,               -- DCR이 발급한 액세스 토큰 (암호화 저장)
    refresh_token TEXT,                       -- DCR이 발급한 리프레시 토큰 (암호화 저장)
    token_type TEXT DEFAULT 'Bearer',
    expires_at DATETIME NOT NULL,             -- 토큰 만료 시간
    scope TEXT,                               -- 토큰이 허용하는 스코프
    azure_access_token TEXT,                  -- 매핑된 Azure AD 액세스 토큰 (암호화 저장)
    azure_refresh_token TEXT,                 -- 매핑된 Azure AD 리프레시 토큰 (암호화 저장)
    azure_token_expiry DATETIME,              -- Azure 토큰 만료 시간
    revoked_at DATETIME,                      -- 토큰 무효화 시간
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES dcr_clients(client_id)
);
```

**주요 인덱스**:
- `idx_dcr_tokens_client_id`: 클라이언트별 토큰 조회
- `idx_dcr_tokens_access_token`: 토큰 검증
- `idx_dcr_tokens_expires_at`: 만료된 토큰 정리

**암호화 필드**:
- `access_token`, `refresh_token`, `azure_access_token`, `azure_refresh_token`
- `AccountCryptoHelpers` 클래스 사용 (Fernet 기반)

### 3. DCR 서비스 구현

#### 파일: [infra/core/dcr_service.py](../infra/core/dcr_service.py)

**클래스**: `DCRService`

**초기화**:
- Azure AD 설정을 환경변수(`AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`)에서 로드
- 환경변수가 없으면 `accounts` 테이블의 첫 번째 활성 계정에서 로드
- `AccountCryptoHelpers`를 사용하여 민감 데이터 암호화/복호화

**주요 메서드**:

| 메서드 | 설명 | 사용 위치 |
|--------|------|-----------|
| `_ensure_dcr_schema()` | DCR 테이블 스키마 초기화 | 첫 클라이언트 등록 시 |
| `register_client(request_data)` | DCR 클라이언트 등록 (RFC 7591) | `POST /oauth/register` |
| `get_client(client_id)` | 클라이언트 정보 조회 | `GET /oauth/authorize` |
| `verify_client_credentials(client_id, client_secret)` | 클라이언트 인증 | `POST /oauth/token` |
| `create_authorization_code(client_id, redirect_uri, scope, state)` | Authorization code 생성 (10분 유효) | `GET /oauth/authorize` |
| `verify_authorization_code(code, client_id, redirect_uri)` | Authorization code 검증 및 일회용 처리 | `POST /oauth/token` |
| `get_azure_tokens_by_auth_code(auth_code)` | DCR auth_code로 Azure 토큰 조회 | `POST /oauth/token` |
| `store_token(...)` | DCR 토큰과 Azure 토큰 매핑 저장 | `POST /oauth/token` |
| `verify_bearer_token(token)` | Bearer 토큰 검증 및 Azure 토큰 반환 | MCP 요청 처리 |
| `delete_client(client_id, registration_access_token)` | 클라이언트 삭제 (Soft delete) | - |

**보안 기능**:
- `secrets.token_urlsafe()`를 사용한 안전한 토큰 생성
- `secrets.compare_digest()`를 사용한 타이밍 공격 방지
- Fernet 암호화를 통한 민감 데이터 보호
- Authorization code 일회용 처리 (`used_at` 컬럼)

### 4. OAuth 엔드포인트 구현

#### 파일: [entrypoints/production/unified_http_server.py](../entrypoints/production/unified_http_server.py)

모든 OAuth 엔드포인트는 `UnifiedMCPServer` 클래스의 `_create_unified_app()` 메서드에서 정의됩니다.

**엔드포인트 목록**:

| 엔드포인트 | 메서드 | 핸들러 함수 | 설명 |
|------------|--------|-------------|------|
| `/.well-known/oauth-authorization-server` | GET | `oauth_metadata_handler` | OAuth 메타데이터 (RFC 8414) |
| `/oauth/register` | POST | `dcr_register_handler` | 클라이언트 등록 (RFC 7591) |
| `/oauth/authorize` | GET | `oauth_authorize_handler` | 인증 시작 (Azure AD로 리다이렉트) |
| `/oauth/azure_callback` | GET | `oauth_azure_callback_handler` | Azure AD 콜백 처리 |
| `/oauth/token` | POST | `oauth_token_handler` | 토큰 교환 |

**주요 로직**:

##### 1. `/oauth/authorize` (인증 시작)
```python
# 1. 클라이언트 검증
client = dcr_service.get_client(client_id)

# 2. Redirect URI 검증
if redirect_uri not in client["redirect_uris"]:
    return error

# 3. Authorization code 생성
auth_code = dcr_service.create_authorization_code(client_id, redirect_uri, scope, state)

# 4. Azure AD URL 생성 (localhost:8000 하드코딩)
azure_redirect_uri = "http://localhost:8000/oauth/azure_callback"
internal_state = f"{auth_code}:{state}"  # DCR auth_code를 state에 포함

# 5. Azure AD로 리다이렉트
return RedirectResponse(azure_auth_url)
```

##### 2. `/oauth/azure_callback` (Azure 콜백)
```python
# 1. State에서 DCR auth_code 추출
if ":" in state:
    auth_code, original_state = state.split(":", 1)

# 2. Azure AD 토큰 교환
oauth_client = OAuthClient(azure_client_id, azure_client_secret, azure_tenant_id)
token_response = oauth_client.exchange_code_for_token(azure_code, azure_redirect_uri)

# 3. Azure 토큰을 auth_code에 저장
UPDATE dcr_auth_codes SET azure_access_token = ?, azure_refresh_token = ? WHERE code = ?

# 4. 성공 페이지 표시 (또는 Claude로 리다이렉트)
return success_html
```

##### 3. `/oauth/token` (토큰 교환)
```python
# 1. 클라이언트 인증
if not dcr_service.verify_client_credentials(client_id, client_secret):
    return error

# 2. Authorization code 검증 (일회용)
auth_data = dcr_service.verify_authorization_code(code, client_id, redirect_uri)

# 3. Azure 토큰 조회
azure_tokens = dcr_service.get_azure_tokens_by_auth_code(code)

# 4. DCR 토큰 생성 및 매핑
access_token = secrets.token_urlsafe(32)
dcr_service.store_token(client_id, access_token, refresh_token, expires_in, scope,
                        azure_access_token, azure_refresh_token, azure_token_expiry)

# 5. 토큰 응답
return {"access_token": access_token, "token_type": "Bearer", ...}
```

### 5. 주요 버그 수정 및 개선 사항

#### 버그 1: Azure redirect_uri 하드코딩
**파일**: `unified_http_server.py:316`
**증상**: Production 배포 시 redirect_uri 불일치
**원인**: `azure_redirect_uri = "http://localhost:8000/oauth/azure_callback"` 하드코딩
**현재 상태**: 로컬 테스트용으로 고정됨
**향후 개선**: 환경변수 `DEPLOY_URL` 기반으로 동적 생성 필요

#### 버그 2: Authorization code 재사용 방지
**파일**: `dcr_service.py:434`
**증상**: "Azure token not found for auth_code" 에러
**원인**: `get_azure_tokens_by_auth_code()`에서 `used_at IS NULL` 조건
**해결**: `used_at` 조건 제거하여 이미 사용된 코드도 조회 가능하게 변경

```python
# Before (dcr_service.py:439)
WHERE code = ? AND used_at IS NULL AND azure_access_token IS NOT NULL

# After
WHERE code = ? AND azure_access_token IS NOT NULL
```

**배경**:
1. `/oauth/token`에서 `verify_authorization_code()` 호출 → `used_at` 업데이트
2. 이후 `get_azure_tokens_by_auth_code()` 호출 → `used_at IS NULL` 조건으로 인해 조회 실패
3. 해결: `used_at` 체크는 `verify_authorization_code()`에서만 수행

#### 개선 3: 토큰 암호화
**파일**: `dcr_service.py` 전체
**개선 내용**: 모든 민감 데이터를 `AccountCryptoHelpers`로 암호화 저장
- `dcr_clients.client_secret`
- `dcr_clients.azure_client_secret`
- `dcr_tokens.access_token`
- `dcr_tokens.refresh_token`
- `dcr_tokens.azure_access_token`
- `dcr_tokens.azure_refresh_token`

#### 개선 4: 스키마 자동 초기화
**파일**: `dcr_service.py:56-138`
**개선 내용**: `_ensure_dcr_schema()` 메서드가 첫 클라이언트 등록 시 자동으로 테이블 생성

## OAuth 인증 플로우

### 전체 플로우 다이어그램

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  Claude AI  │         │ DCR Server  │         │  Azure AD   │
└──────┬──────┘         └──────┬──────┘         └──────┬──────┘
       │                       │                       │
       │ 1. POST /oauth/register                       │
       │─────────────────────>│                       │
       │                       │                       │
       │<─────────────────────│                       │
       │   {client_id, secret} │                       │
       │                       │                       │
       │ 2. GET /oauth/authorize                       │
       │─────────────────────>│                       │
       │                       │                       │
       │                       │ 3. Redirect to Azure AD
       │                       │       (state=auth_code)
       │                       │──────────────────────>│
       │                       │                       │
       │                       │                  User Login
       │                       │                       │
       │                       │ 4. GET /azure_callback│
       │                       │<──────────────────────│
       │                       │   (code, state)       │
       │                       │                       │
       │                       │ 5. Exchange code      │
       │                       │──────────────────────>│
       │                       │                       │
       │                       │<──────────────────────│
       │                       │   {access_token}      │
       │                       │                       │
       │                       │ Save Azure tokens     │
       │                       │ to dcr_auth_codes     │
       │                       │                       │
       │ 6. Show success page  │                       │
       │  (or redirect to Claude)                      │
       │                       │                       │
       │ 7. POST /oauth/token  │                       │
       │─────────────────────>│                       │
       │   (code=auth_code)    │                       │
       │                       │                       │
       │                       │ Lookup Azure tokens   │
       │                       │ by auth_code          │
       │                       │                       │
       │<─────────────────────│                       │
       │   {access_token: DCR} │                       │
       │                       │                       │
       │ 8. MCP Request        │                       │
       │─────────────────────>│                       │
       │   Bearer: DCR token   │                       │
       │                       │                       │
       │                       │ Verify DCR token      │
       │                       │ → Get Azure token     │
       │                       │                       │
       │                       │ 9. Graph API Call     │
       │                       │──────────────────────>│
       │                       │                       │
       │                       │<──────────────────────│
       │                       │   API Response        │
       │                       │                       │
       │<─────────────────────│                       │
       │   MCP Response        │                       │
       │                       │                       │
```

### 단계별 상세 설명

#### 1단계: DCR 클라이언트 등록
```http
POST /oauth/register
Content-Type: application/json

{
  "client_name": "Claude Connector",
  "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"]
}
```

**응답**:
```json
{
  "client_id": "dcr_xxx",
  "client_secret": "yyy",
  "client_id_issued_at": 1234567890,
  "token_endpoint_auth_method": "client_secret_post",
  "grant_types": ["authorization_code", "refresh_token"],
  "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"]
}
```

#### 2-4단계: 사용자 인증
```http
GET /oauth/authorize?client_id=dcr_xxx&redirect_uri=...&scope=Mail.Read
→ Redirect to Azure AD
→ User logs in
→ Azure redirects to /oauth/azure_callback?code=azure_code&state=auth_code
```

#### 5-6단계: Azure 토큰 교환 및 저장
```python
# DCR 서버가 Azure AD와 토큰 교환
POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
→ {access_token, refresh_token}

# dcr_auth_codes 테이블에 저장
UPDATE dcr_auth_codes
SET azure_access_token = ?, azure_refresh_token = ?
WHERE code = auth_code
```

#### 7단계: DCR 토큰 발급
```http
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
code=auth_code&
client_id=dcr_xxx&
client_secret=yyy&
redirect_uri=https://claude.ai/api/mcp/auth_callback
```

**응답**:
```json
{
  "access_token": "dcr_token_zzz",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "dcr_refresh_aaa",
  "scope": "Mail.Read"
}
```

#### 8-9단계: MCP API 호출
```http
POST /mail-query/
Authorization: Bearer dcr_token_zzz
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {...}
}
```

**DCR 서버 처리**:
1. `verify_bearer_token(dcr_token_zzz)` 호출
2. `dcr_tokens` 테이블에서 `azure_access_token` 조회
3. Azure Graph API 호출
4. MCP 응답 반환

## 로컬 개발 환경 설정

### 1. Azure Portal 설정

**중요**: Azure AD 앱 등록에 다음 Redirect URI를 추가해야 합니다.

1. Azure Portal → App registrations → 해당 앱 선택
2. Authentication → Platform configurations → Web
3. Redirect URIs에 추가:
   ```
   http://localhost:8000/oauth/azure_callback
   ```
4. Save 클릭

**참고**: 현재 `unified_http_server.py:316`에서 `localhost:8000`이 하드코딩되어 있습니다.

### 2. 환경 변수 설정

`.env` 파일에 Azure AD 설정 추가:

```bash
# Azure AD 설정 (필수)
AZURE_CLIENT_ID=88f1daa2-a6cc-4c7b-b575-b76bf0a6435b
AZURE_CLIENT_SECRET=your_azure_client_secret
AZURE_TENANT_ID=your_tenant_id

# 데이터베이스 경로 (선택, 기본값: data/database.db)
DATABASE_PATH=data/database.db

# 암호화 키 (선택, 자동 생성됨)
ENCRYPTION_KEY=your_fernet_key
```

**또는** `accounts` 테이블에 계정이 등록되어 있으면 환경변수 없이도 동작합니다:
```sql
SELECT oauth_client_id, oauth_tenant_id FROM accounts WHERE is_active = 1 LIMIT 1;
```

### 3. 서버 실행

```bash
# 기본 포트 (8000)
python entrypoints/production/unified_http_server.py

# 또는 포트 지정
python entrypoints/production/unified_http_server.py --port 8000
```

**서버 시작 로그**:
```
✅ Loaded environment variables from /path/to/.env
🚀 Initializing Unified MCP Server
📧 Initializing Mail Query MCP Server...
🔐 Initializing Enrollment MCP Server...
📝 Initializing OneNote MCP Server...
✅ Unified MCP Server initialized
Starting server on http://0.0.0.0:8000
```

### 4. 로컬 테스트

#### 4.1. DCR 등록
```bash
curl -X POST http://localhost:8000/oauth/register \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Local Test Client",
    "redirect_uris": ["http://localhost:8000/"]
  }'
```

**응답 예시**:
```json
{
  "client_id": "dcr_AbCdEf1234567890",
  "client_secret": "XyZ...",
  "client_id_issued_at": 1698765432,
  "client_secret_expires_at": 0,
  "grant_types": ["authorization_code", "refresh_token"],
  "redirect_uris": ["http://localhost:8000/"]
}
```

#### 4.2. 브라우저에서 인증 시작
```
http://localhost:8000/oauth/authorize?client_id=dcr_AbCdEf1234567890&redirect_uri=http://localhost:8000/&response_type=code&scope=Mail.Read
```

**플로우**:
1. Azure AD 로그인 페이지로 리다이렉트
2. 로그인 및 권한 동의
3. `http://localhost:8000/oauth/azure_callback`으로 리다이렉트
4. 성공 페이지 표시 (URL에 `code` 파라미터 포함)

#### 4.3. 토큰 교환
```bash
# 브라우저에서 받은 code 값 사용
CODE="<브라우저 URL의 code 파라미터>"
CLIENT_ID="dcr_AbCdEf1234567890"
CLIENT_SECRET="XyZ..."

curl -X POST http://localhost:8000/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=${CODE}&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}&redirect_uri=http://localhost:8000/"
```

#### 4.4. MCP API 테스트
```bash
ACCESS_TOKEN="<받은 access_token>"

curl http://localhost:8000/mail-query/ \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

## Production 배포 (Render.com)

### 1. 환경 변수 설정

Render.com Dashboard → Environment 탭에서 추가:

```bash
AZURE_CLIENT_ID=88f1daa2-a6cc-4c7b-b575-b76bf0a6435b
AZURE_CLIENT_SECRET=<your_secret>
AZURE_TENANT_ID=<your_tenant_id>
```

### 2. Azure Portal Redirect URI

**중요**: Production 배포를 위해 다음 URI를 추가해야 합니다.

```
https://mailquery-mcp-server.onrender.com/oauth/azure_callback
```

**문제**: 현재 코드는 `localhost:8000`을 하드코딩하고 있어 Production에서 동작하지 않습니다.

**해결 방법** (향후 구현 필요):
```python
# unified_http_server.py:316
# Before
azure_redirect_uri = "http://localhost:8000/oauth/azure_callback"

# After
base_url = os.getenv("DEPLOY_URL", "http://localhost:8000")
azure_redirect_uri = f"{base_url}/oauth/azure_callback"
```

### 3. Claude Custom Connector 설정

1. Claude.ai → Settings → Connectors → Add custom connector
2. Server URL: `https://mailquery-mcp-server.onrender.com`
3. 자동으로 DCR 등록 및 OAuth 플로우 시작

## 테스트 및 디버깅

### OAuth 메타데이터 확인
```bash
curl http://localhost:8000/.well-known/oauth-authorization-server | jq
```

**응답**:
```json
{
  "issuer": "http://localhost:8000",
  "authorization_endpoint": "http://localhost:8000/oauth/authorize",
  "token_endpoint": "http://localhost:8000/oauth/token",
  "registration_endpoint": "http://localhost:8000/oauth/register",
  "response_types_supported": ["code"],
  "grant_types_supported": ["authorization_code", "refresh_token"],
  "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
  "scopes_supported": ["Mail.Read", "Mail.ReadWrite", "User.Read"]
}
```

### 데이터베이스 확인

```bash
# DCR 클라이언트 목록
sqlite3 data/database.db "SELECT client_id, client_name, created_at FROM dcr_clients;"

# Authorization code 상태
sqlite3 data/database.db "SELECT code, used_at, expires_at, azure_access_token IS NOT NULL as has_azure_token FROM dcr_auth_codes ORDER BY created_at DESC LIMIT 5;"

# 토큰 목록
sqlite3 data/database.db "SELECT client_id, expires_at, revoked_at FROM dcr_tokens ORDER BY created_at DESC LIMIT 5;"
```

### 서버 로그 확인

로컬 테스트 시 콘솔 출력에서 다음 로그 확인:

```
✅ DCR client registered: dcr_xxx
🔍 Verifying authorization code: xxx...
✅ Authorization code verified
🔍 Looking for Azure tokens with auth_code: xxx...
✅ Azure token found
```

## 알려진 제한사항 및 향후 개선 사항

### 현재 제한사항

1. **Azure redirect_uri 하드코딩**
   - **파일**: `unified_http_server.py:316`
   - **문제**: `http://localhost:8000/oauth/azure_callback` 고정
   - **영향**: Production 환경에서 동작하지 않음
   - **해결 필요**: 환경변수 `DEPLOY_URL` 기반 동적 생성

2. **PKCE 미지원**
   - **파일**: `dcr_service.py`
   - **문제**: `code_challenge` 및 `code_verifier` 검증 미구현
   - **영향**: 공개 클라이언트(모바일 앱 등)에서 보안 취약
   - **참고**: 웹 애플리케이션에서는 client_secret으로 충분

3. **Refresh token 플로우 미구현**
   - **파일**: `unified_http_server.py`
   - **문제**: `grant_type=refresh_token` 엔드포인트 없음
   - **영향**: 토큰 만료 시 재인증 필요
   - **해결 필요**: Azure refresh_token을 사용한 토큰 갱신 구현

4. **Token revocation 미구현**
   - **파일**: 없음
   - **문제**: `POST /oauth/revoke` 엔드포인트 없음
   - **영향**: 사용자가 명시적으로 토큰을 무효화할 수 없음
   - **대안**: `dcr_tokens.revoked_at` 컬럼은 존재하나 API 없음

5. **Rate limiting 없음**
   - **문제**: API 엔드포인트에 요청 제한 없음
   - **영향**: DoS 공격에 취약
   - **해결 필요**: `slowapi` 또는 `fastapi-limiter` 통합

### 향후 개선 사항

#### 우선순위 1: Production 배포 지원

```python
# unified_http_server.py에 추가
import os

def get_base_url(request):
    """동적으로 base URL 결정"""
    # 환경변수 우선
    deploy_url = os.getenv("DEPLOY_URL")
    if deploy_url:
        return deploy_url

    # 요청 헤더에서 추출
    scheme = request.url.scheme
    host = request.url.netloc
    return f"{scheme}://{host}"

# /oauth/authorize 핸들러에서 사용
base_url = get_base_url(request)
azure_redirect_uri = f"{base_url}/oauth/azure_callback"
```

#### 우선순위 2: Refresh token 플로우

```python
# /oauth/token 핸들러에 추가
if grant_type == "refresh_token":
    refresh_token = form_data.get("refresh_token")

    # DCR refresh_token 검증
    token_info = dcr_service.get_token_by_refresh_token(refresh_token)

    # Azure refresh_token으로 새 토큰 발급
    oauth_client = OAuthClient(...)
    new_tokens = oauth_client.refresh_access_token(azure_refresh_token)

    # DCR 토큰 갱신
    new_access_token = secrets.token_urlsafe(32)
    dcr_service.update_token(...)

    return {"access_token": new_access_token, ...}
```

#### 우선순위 3: PKCE 지원

```python
# dcr_service.py에 추가
def verify_code_challenge(self, code: str, code_verifier: str) -> bool:
    """PKCE code_verifier 검증"""
    query = """
    SELECT code_challenge, code_challenge_method
    FROM dcr_auth_codes
    WHERE code = ?
    """
    result = self.db.fetch_one(query, (code,))

    if not result:
        return False

    code_challenge, method = result

    if method == "S256":
        import hashlib
        import base64
        computed = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip("=")
        return secrets.compare_digest(computed, code_challenge)

    return False
```

#### 우선순위 4: Token revocation

```python
# unified_http_server.py에 추가
async def oauth_revoke_handler(request):
    """RFC 7009: Token Revocation"""
    form_data = await request.form()
    token = form_data.get("token")

    dcr_service = DCRService()
    dcr_service.revoke_token(token)

    return Response(status_code=200)
```

#### 우선순위 5: MCP 서버 인증 통합

현재 MCP 서버(`http_server.py`)에서는 DCR 토큰 검증이 구현되지 않았습니다.

```python
# modules/mail_query_MCP/mcp_server/http_server.py에 추가
from infra.core.dcr_service import DCRService

async def handle_mcp_request(request):
    # Bearer 토큰 추출
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    token = auth_header[7:]

    # DCR 토큰 검증
    dcr_service = DCRService()
    token_info = dcr_service.verify_bearer_token(token)

    if not token_info:
        return JSONResponse({"error": "Invalid token"}, status_code=401)

    # Azure 토큰으로 Graph API 호출
    azure_token = token_info["azure_access_token"]
    # ... MCP 요청 처리
```

## 참고 자료

### RFC 표준
- [RFC 7591 - OAuth 2.0 Dynamic Client Registration Protocol](https://datatracker.ietf.org/doc/html/rfc7591)
- [RFC 6749 - OAuth 2.0 Authorization Framework](https://datatracker.ietf.org/doc/html/rfc6749)
- [RFC 7636 - PKCE (Proof Key for Code Exchange)](https://datatracker.ietf.org/doc/html/rfc7636)
- [RFC 8414 - OAuth 2.0 Authorization Server Metadata](https://datatracker.ietf.org/doc/html/rfc8414)
- [RFC 7009 - OAuth 2.0 Token Revocation](https://datatracker.ietf.org/doc/html/rfc7009)

### Azure AD 문서
- [Microsoft Identity Platform - OAuth 2.0 authorization code flow](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow)
- [Microsoft Graph API](https://learn.microsoft.com/en-us/graph/overview)

### 관련 프로젝트 파일
- [dcr_service.py](../infra/core/dcr_service.py) - DCR 서비스 구현
- [unified_http_server.py](../entrypoints/production/unified_http_server.py) - OAuth 엔드포인트
- [oauth_client.py](../infra/core/oauth_client.py) - Azure AD 토큰 교환
- [CLAUDE_MCP_FLOW_DIAGRAM.md](CLAUDE_MCP_FLOW_DIAGRAM.md) - 플로우 다이어그램

## 버전 히스토리

- **2025-10-22**: 로컬 테스트 환경 완성
  - Azure AD 콜백 처리 구현
  - 토큰 매핑 및 저장 완료
  - 데이터베이스 스키마 최종화
  - 암호화 기능 추가

- **2025-10-21**: DCR 엔드포인트 구현
  - OAuth 메타데이터 엔드포인트
  - 클라이언트 등록 엔드포인트
  - Authorization 엔드포인트

- **2025-10-20**: 프로젝트 시작
  - 기본 아키텍처 설계
  - Azure AD 통합 계획
