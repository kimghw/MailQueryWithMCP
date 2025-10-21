# DCR (Dynamic Client Registration) 구현 문서

## 개요

Claude AI와 MCP 서버 간 OAuth 2.0 인증을 위한 DCR (Dynamic Client Registration) 구현을 완료했습니다.

RFC 7591 표준을 준수하며, Azure AD를 백엔드 인증 시스템으로 사용합니다.

## 구현 일자

2025-10-22

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

### 2. 데이터베이스 스키마 추가

#### dcr_clients 테이블
```sql
CREATE TABLE IF NOT EXISTS dcr_clients (
    client_id TEXT PRIMARY KEY,
    client_secret TEXT NOT NULL,
    client_name TEXT,
    redirect_uris TEXT,
    azure_tenant_id TEXT,
    azure_client_id TEXT,
    azure_client_secret TEXT,
    created_at TEXT NOT NULL
)
```

#### dcr_auth_codes 테이블
```sql
CREATE TABLE IF NOT EXISTS dcr_auth_codes (
    code TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    scope TEXT,
    code_challenge TEXT,
    code_challenge_method TEXT,
    azure_code TEXT,
    azure_access_token TEXT,
    azure_refresh_token TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    FOREIGN KEY (client_id) REFERENCES dcr_clients(client_id)
)
```

#### dcr_tokens 테이블
```sql
CREATE TABLE IF NOT EXISTS dcr_tokens (
    access_token TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    refresh_token TEXT,
    scope TEXT,
    azure_access_token TEXT NOT NULL,
    azure_refresh_token TEXT,
    azure_token_expiry TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (client_id) REFERENCES dcr_clients(client_id)
)
```

### 3. DCR 서비스 구현

#### 파일: `infra/core/dcr_service.py`

주요 메서드:
- `register_client()`: DCR 클라이언트 등록
- `get_client()`: 클라이언트 정보 조회
- `verify_client_credentials()`: 클라이언트 인증
- `create_authorization_code()`: Authorization code 생성
- `verify_authorization_code()`: Authorization code 검증
- `get_azure_tokens_by_auth_code()`: Azure 토큰 조회
- `store_token()`: DCR 토큰 저장
- `verify_bearer_token()`: Bearer token 검증

### 4. MCP 서버 인증 통합

#### 파일: `modules/mail_query_MCP/mcp_server/http_server.py`

변경 사항:
- Bearer token 검증 추가 (line 139-154)
- DCR 서비스를 통한 토큰 검증
- Azure AD 토큰을 사용한 Graph API 호출

```python
# Bearer 토큰 검증
if not auth_header.startswith("Bearer "):
    return JSONResponse(
        {"jsonrpc": "2.0", "error": {"code": -32001, "message": "Authentication required"}},
        status_code=401,
        headers={"WWW-Authenticate": 'Bearer realm="MCP Server"'}
    )

token = auth_header[7:]
dcr_service = DCRService()
token_info = dcr_service.verify_bearer_token(token)

if not token_info:
    return JSONResponse(
        {"jsonrpc": "2.0", "error": {"code": -32001, "message": "Invalid token"}},
        status_code=401
    )
```

### 5. 주요 버그 수정

#### 문제 1: Render.com URL 하드코딩
**증상**: Azure AD 토큰 교환 시 redirect_uri 불일치 에러
**원인**: `/oauth/token` 엔드포인트에서 `https://mailquery-mcp-server.onrender.com/oauth/azure_callback` 하드코딩
**해결**: `http://localhost:8000/oauth/azure_callback`로 변경 (line 551)

#### 문제 2: refresh_token 변수 미정의
**증상**: `/oauth/token` 핸들러에서 NameError 발생
**원인**: `refresh_token` 변수 생성 없이 사용
**해결**: `refresh_token = secrets.token_urlsafe(32)` 추가 (line 405)

#### 문제 3: Azure 토큰 조회 실패
**증상**: "Azure token not found for auth_code" 에러
**원인**: `get_azure_tokens_by_auth_code()` 쿼리에서 `used_at IS NULL` 조건
**배경**:
- `verify_authorization_code()`가 auth_code 검증 시 `used_at` 업데이트
- 그러나 Azure 토큰 조회는 `used_at IS NULL`인 레코드만 검색
**해결**: `used_at IS NULL` 조건 제거 (dcr_service.py line 439)

```sql
-- Before
WHERE code = ? AND used_at IS NULL AND azure_access_token IS NOT NULL

-- After
WHERE code = ? AND azure_access_token IS NOT NULL
```

## OAuth 인증 플로우

```
1. Claude AI → DCR Server
   POST /oauth/register
   ↓
   client_id, client_secret 발급

2. Claude AI → DCR Server
   GET /oauth/authorize?client_id=...&redirect_uri=...&code_challenge=...
   ↓
   DCR auth_code 생성 → Azure AD로 리다이렉트

3. User → Azure AD
   로그인 및 동의
   ↓
   Azure authorization code 발급

4. Azure AD → DCR Server
   GET /oauth/azure_callback?code=<azure_code>&state=<dcr_auth_code>
   ↓
   Azure 토큰 교환 → dcr_auth_codes 테이블에 저장
   ↓
   Claude AI로 리다이렉트 (DCR auth_code 전달)

5. Claude AI → DCR Server
   POST /oauth/token
   grant_type=authorization_code&code=<dcr_auth_code>&client_id=...&client_secret=...
   ↓
   DCR access_token 생성 및 Azure 토큰 매핑
   ↓
   access_token 응답

6. Claude AI → MCP Server
   POST /mail-query
   Authorization: Bearer <access_token>
   ↓
   토큰 검증 → Azure 토큰으로 Graph API 호출
   ↓
   MCP 응답
```

## 로컬 개발 환경 설정

### 1. Azure Portal 설정

**Redirect URIs 등록:**
- `http://localhost:8000/oauth/azure_callback`

### 2. 환경 변수 (.env)

```bash
# Azure AD 설정
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret

# DCR 설정 (선택)
DCR_BASE_URL=http://localhost:8000
```

### 3. 서버 실행

```bash
# 8000번 포트에서 실행
python entrypoints/production/unified_http_server.py --port 8000
```

### 4. Claude AI 연결

Claude Desktop 설정에서 MCP 서버 추가:
```json
{
  "mcpServers": {
    "mail-query": {
      "url": "http://localhost:8000/mail-query"
    }
  }
}
```

## 프로덕션 배포 (Render.com)

### 환경 변수 설정

Render.com 대시보드에서 다음 환경 변수 추가:

```bash
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
DCR_BASE_URL=https://mailquery-mcp-server.onrender.com
```

### Azure Portal Redirect URI

프로덕션 URL 등록:
- `https://mailquery-mcp-server.onrender.com/oauth/azure_callback`

## 테스트

### DCR 등록 테스트
```bash
curl -X POST http://localhost:8000/oauth/register \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Test Client",
    "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"]
  }'
```

### OAuth Discovery 테스트
```bash
curl http://localhost:8000/.well-known/oauth-authorization-server
```

### 전체 플로우 테스트
1. Claude Desktop에서 MCP 서버 연결
2. 이메일 조회 요청
3. OAuth 인증 플로우 진행
4. 정상 응답 확인

## 알려진 제한사항

1. **포트 고정**: 현재 localhost 테스트 시 8000번 포트 고정
2. **토큰 갱신**: Refresh token 플로우 미구현
3. **PKCE**: Code challenge 검증 구현 필요

## 향후 개선 사항

1. Refresh token 플로우 구현
2. PKCE code_verifier 검증
3. Token revocation 엔드포인트
4. Rate limiting
5. Client credentials 암호화 저장

## 참고 자료

- [RFC 7591 - OAuth 2.0 Dynamic Client Registration](https://datatracker.ietf.org/doc/html/rfc7591)
- [RFC 6749 - OAuth 2.0 Authorization Framework](https://datatracker.ietf.org/doc/html/rfc6749)
- [RFC 7636 - PKCE](https://datatracker.ietf.org/doc/html/rfc7636)
- [Azure AD OAuth 2.0](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow)
