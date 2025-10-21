# Claude Connector 통합 가이드

DCR (Dynamic Client Registration)을 통한 Claude Connector와 MCP 서버 통합 방법

## 📋 목차

1. [개요](#개요)
2. [Render.com 배포](#rendercom-배포)
3. [Azure AD 앱 설정](#azure-ad-앱-설정)
4. [Claude Connector 연결](#claude-connector-연결)
5. [테스트](#테스트)
6. [문제 해결](#문제-해결)

---

## 개요

### 아키텍처

```
Claude Connector (claude.ai)
    ↓ DCR Registration
Your MCP Server (render.com)
    ↓ OAuth Proxy
Azure AD (login.microsoftonline.com)
    ↓ Access Token
Microsoft Graph API (Mail.Read)
```

### 플로우

1. **DCR Discovery**: Claude가 `/.well-known/oauth-authorization-server` 조회
2. **Client Registration**: Claude가 `/oauth/register`에 클라이언트 등록
3. **Authorization**: 사용자가 Azure AD 로그인
4. **Token Exchange**: Claude가 access_token 획득
5. **MCP Requests**: Bearer 토큰으로 메일 조회

---

## Render.com 배포

### 1. Render.com 계정 생성

https://render.com 에서 GitHub 계정으로 가입

### 2. 저장소 연결

```bash
# 현재 프로젝트를 GitHub에 푸시
git add .
git commit -m "feat: DCR 지원 추가로 Claude Connector 통합"
git push origin main
```

### 3. Render 대시보드에서 서비스 생성

1. **New** → **Blueprint** 선택
2. 저장소 선택: `MailQueryWithMCP`
3. `render.yaml` 자동 감지됨
4. **Apply** 클릭

### 4. 환경변수 설정

Render 대시보드에서 다음 환경변수 추가:

```bash
# 필수: DCR을 위한 Azure AD 앱 정보
AZURE_CLIENT_ID=<your-azure-app-id>
AZURE_CLIENT_SECRET=<your-azure-app-secret>
AZURE_TENANT_ID=<your-tenant-id>

# 필수: 암호화 키
ENCRYPTION_KEY=<32자 이상 랜덤 문자열>

# 선택: 자동 계정 등록 (첫 실행 시)
AUTO_REGISTER_USER_ID=your-email@example.com
AUTO_REGISTER_USER_NAME=Your Name
AUTO_REGISTER_EMAIL=your-email@example.com
AUTO_REGISTER_OAUTH_CLIENT_ID=<same-as-AZURE_CLIENT_ID>
AUTO_REGISTER_OAUTH_CLIENT_SECRET=<same-as-AZURE_CLIENT_SECRET>
AUTO_REGISTER_OAUTH_TENANT_ID=<same-as-AZURE_TENANT_ID>
AUTO_REGISTER_OAUTH_REDIRECT_URI=https://your-app.onrender.com/oauth/azure_callback
```

### 5. 배포 URL 확인

배포 완료 후 URL 확인:
```
https://mailquery-mcp-server.onrender.com
```

### 6. 헬스체크 확인

```bash
curl https://mailquery-mcp-server.onrender.com/health
```

예상 응답:
```json
{
  "status": "healthy",
  "server": "mail-attachment-server",
  "version": "1.0.0"
}
```

---

## Azure AD 앱 설정

### 1. Azure Portal에서 앱 등록

1. https://portal.azure.com → **Azure Active Directory**
2. **App registrations** → **New registration**
3. 이름: `MCP Mail Query Server - DCR`
4. **Supported account types**: Single tenant
5. **Redirect URI**:
   - Type: `Web`
   - URI: `https://your-app.onrender.com/oauth/azure_callback`
6. **Register** 클릭

### 2. Client Secret 생성

1. **Certificates & secrets** → **New client secret**
2. Description: `DCR Backend Secret`
3. Expires: `24 months`
4. **Add** → **Value 복사** (Render 환경변수에 사용)

### 3. API Permissions 추가

1. **API permissions** → **Add a permission**
2. **Microsoft Graph** → **Delegated permissions**
3. 다음 권한 추가:
   - `Mail.Read`
   - `Mail.ReadWrite`
   - `User.Read`
   - `offline_access`
4. **Grant admin consent** 클릭 (관리자 권한 필요)

### 4. 설정값 수집

다음 정보를 Render 환경변수에 입력:

- **Application (client) ID** → `AZURE_CLIENT_ID`
- **Client secret value** → `AZURE_CLIENT_SECRET`
- **Directory (tenant) ID** → `AZURE_TENANT_ID`

---

## Claude Connector 연결

### 1. OAuth 메타데이터 URL 준비

```
https://your-app.onrender.com/.well-known/oauth-authorization-server
```

### 2. Claude.ai에서 MCP 서버 추가

1. https://claude.ai 로그인
2. **Settings** → **Connectors** (또는 **Integrations**)
3. **Add MCP Server** 클릭
4. 다음 정보 입력:

```
Name: Mail Query Server
OAuth Metadata URL: https://your-app.onrender.com/.well-known/oauth-authorization-server
```

### 3. OAuth 인증 플로우

1. Claude가 자동으로 DCR 등록 수행
2. **Authorize** 버튼 클릭
3. Azure AD 로그인 페이지로 리다이렉트
4. Microsoft 계정으로 로그인
5. 권한 요청 수락
6. Claude로 자동 리다이렉트

### 4. 연결 확인

Claude 채팅에서:
```
Can you check my recent emails?
```

정상 작동 시 메일 목록이 표시됩니다.

---

## 테스트

### 1. OAuth 메타데이터 확인

```bash
curl https://your-app.onrender.com/.well-known/oauth-authorization-server | jq
```

예상 응답:
```json
{
  "issuer": "https://your-app.onrender.com",
  "authorization_endpoint": "https://your-app.onrender.com/oauth/authorize",
  "token_endpoint": "https://your-app.onrender.com/oauth/token",
  "registration_endpoint": "https://your-app.onrender.com/oauth/register",
  "response_types_supported": ["code"],
  "grant_types_supported": ["authorization_code", "refresh_token"],
  ...
}
```

### 2. DCR 등록 테스트

```bash
curl -X POST https://your-app.onrender.com/oauth/register \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Test Client",
    "redirect_uris": ["https://example.com/callback"]
  }' | jq
```

예상 응답:
```json
{
  "client_id": "dcr_...",
  "client_secret": "...",
  "client_id_issued_at": 1234567890,
  ...
}
```

### 3. 로컬 통합 테스트

```bash
# 프로젝트 루트에서
python tests/test_dcr_integration.py
```

모든 테스트 통과 확인:
```
✅ ALL TESTS PASSED
🎉 Ready for Claude Connector integration!
```

---

## 문제 해결

### 1. OAuth 메타데이터 404 오류

**증상:**
```
GET /.well-known/oauth-authorization-server
404 Not Found
```

**해결:**
1. Render 로그 확인: 서버가 정상 시작되었는지 확인
2. URL 확인: `/stream` 또는 `/steam` 경로가 아닌 루트 경로 사용
3. HTTP 서버 재시작

### 2. DCR 등록 실패

**증상:**
```json
{
  "error": "Azure AD configuration not available for DCR"
}
```

**해결:**
Render 환경변수 확인:
```bash
AZURE_CLIENT_ID=<설정되어 있어야 함>
AZURE_CLIENT_SECRET=<설정되어 있어야 함>
AZURE_TENANT_ID=<설정되어 있어야 함>
```

### 3. Azure AD 리다이렉트 오류

**증상:**
```
redirect_uri_mismatch
```

**해결:**
Azure Portal → App Registration → Authentication에서:
- Redirect URI가 정확히 `https://your-app.onrender.com/oauth/azure_callback`인지 확인
- Type이 `Web`인지 확인

### 4. 토큰 검증 실패

**증상:**
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32001,
    "message": "Invalid authentication token"
  }
}
```

**해결:**
1. 토큰 만료 확인 (기본 1시간)
2. Claude에서 재인증 수행
3. 서버 로그에서 토큰 검증 에러 확인

### 5. Database 오류

**증상:**
```
no such table: dcr_clients
```

**해결:**
```bash
# Render Shell에서 실행
sqlite3 ./data/graphapi.db < infra/migrations/dcr_schema.sql
```

또는 서버 재시작 시 자동 초기화됨.

---

## 참고 자료

### RFC 표준
- [RFC 7591: OAuth 2.0 Dynamic Client Registration](https://datatracker.ietf.org/doc/html/rfc7591)
- [RFC 8414: OAuth 2.0 Authorization Server Metadata](https://datatracker.ietf.org/doc/html/rfc8414)
- [RFC 6749: OAuth 2.0 Framework](https://datatracker.ietf.org/doc/html/rfc6749)

### Claude 문서
- [Claude Connector Documentation](https://docs.claude.com/en/docs/agents-and-tools/mcp-connector)
- [Building Custom Connectors](https://support.claude.com/en/articles/11503834-building-custom-connectors-via-remote-mcp-servers)

### 프로젝트 파일
- [DCR Service](../infra/core/dcr_service.py) - DCR 로직
- [DCR Schema](../infra/migrations/dcr_schema.sql) - DB 스키마
- [HTTP Server](../modules/mail_query_MCP/mcp_server/http_server.py) - OAuth 엔드포인트
- [Integration Tests](../tests/test_dcr_integration.py) - 통합 테스트

---

## 다음 단계

1. ✅ Render.com에 배포
2. ✅ Azure AD 앱 설정
3. ✅ Claude Connector 연결
4. 📧 메일 조회 테스트
5. 🔄 토큰 자동 갱신 확인
6. 📊 프로덕션 모니터링

문제가 발생하면 Render 로그를 확인하거나 GitHub Issues에 문의하세요.
