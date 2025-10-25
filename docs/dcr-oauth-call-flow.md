# DCR OAuth 모듈: Claude.ai ↔ DCR ↔ Azure AD 호출 구조

## 📋 개요

`modules/dcr_oauth` 모듈은 Claude.ai와 Azure AD 사이의 OAuth 프록시로 동작합니다. 이 문서는 세 주체 간의 상세한 호출 흐름과 구현 방식을 설명합니다.

---

## 🏗️ 모듈 구조

```
modules/dcr_oauth/
├── __init__.py                     # 모듈 진입점
├── dcr_service.py                  # DCR 핵심 로직 (RFC 7591)
├── auth_middleware.py              # Bearer 토큰 인증 미들웨어
└── migrations/
    ├── dcr_schema_v3.sql          # 데이터베이스 스키마
    └── dcr_migration_v2_to_v3.sql # 마이그레이션 스크립트
```

### 주요 컴포넌트

#### 1. DCRService (`dcr_service.py`)

**역할:** Dynamic Client Registration 서버의 핵심 비즈니스 로직

**주요 메서드:**
```python
class DCRService:
    def __init__(self)

    # 클라이언트 관리
    async def register_client(request_data: Dict) -> Dict
    def get_client(dcr_client_id: str) -> Optional[Dict]
    def verify_client_credentials(dcr_client_id: str, dcr_client_secret: str) -> bool

    # Authorization Code 플로우
    def create_authorization_code(...) -> str
    def verify_authorization_code(...) -> Optional[Dict]

    # 토큰 관리
    def store_tokens(...)
    def verify_bearer_token(token: str) -> Optional[Dict]
    def get_azure_tokens_by_object_id(azure_object_id: str) -> Optional[Dict]

    # 유틸리티
    def update_auth_code_with_object_id(auth_code: str, azure_object_id: str)
    def is_user_allowed(user_email: str) -> bool
    def _verify_pkce(code_verifier: str, code_challenge: str, method: str) -> bool
```

#### 2. verify_bearer_token_middleware (`auth_middleware.py`)

**역할:** 모든 MCP 요청의 Bearer 토큰 검증

**처리 흐름:**
```python
async def verify_bearer_token_middleware(request, call_next=None):
    # 1. 경로 검증 (/.well-known/, /oauth/ 등은 제외)
    # 2. Authorization 헤더 파싱
    # 3. DCRService.verify_bearer_token() 호출
    # 4. request.state에 Azure 토큰 주입
    # 5. 다음 핸들러로 전달
```

---

## 🔄 전체 호출 플로우 (상세)

### Phase 1: 클라이언트 등록 (DCR)

```
┌─────────────┐                    ┌─────────────────────┐                    ┌──────────────┐
│             │  POST /oauth/       │                     │                    │              │
│  Claude.ai  │  register           │  unified_http_      │                    │ dcr_service  │
│             ├────────────────────>│  server.py          ├───────────────────>│ .py          │
│             │  {client_name,      │                     │ register_client()  │              │
│             │   redirect_uris}    │ dcr_register_       │                    │              │
└─────────────┘                    │ handler()           │                    └──────┬───────┘
                                   └─────────────────────┘                           │
                                                                                      │
                                                                          ┌───────────▼──────────┐
                                                                          │ dcr_clients 테이블   │
                                                                          │ INSERT:              │
                                                                          │ - dcr_client_id      │
                                                                          │ - dcr_client_secret  │
                                                                          │ - azure_app_id       │
                                                                          └──────────────────────┘
```

**구현 위치:**
- HTTP 핸들러: `unified_http_server.py:459-486` (`dcr_register_handler`)
- 비즈니스 로직: `dcr_service.py:181-229` (`register_client`)

**처리 과정:**
1. Claude.ai가 클라이언트 메타데이터 전송
2. DCRService가 `dcr_{random_token}` 형식의 클라이언트 ID 생성
3. 32바이트 URL-safe 시크릿 생성
4. dcr_clients 테이블에 암호화하여 저장
5. 클라이언트 ID/Secret 반환

**응답 예시:**
```json
{
  "client_id": "dcr_xxxxxxxxxxxx",
  "client_secret": "yyyyyyyyyyyyyyyy",
  "client_id_issued_at": 1729843200,
  "client_secret_expires_at": 0,
  "grant_types": ["authorization_code", "refresh_token"],
  "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"]
}
```

---

### Phase 2: 인증 시작 (Claude → DCR → Azure AD)

```
┌─────────────┐                    ┌─────────────────────┐                    ┌──────────────┐
│             │  GET /oauth/        │                     │                    │              │
│  Claude.ai  │  authorize?         │  unified_http_      │                    │ dcr_service  │
│             │  client_id=dcr_xxx  │  server.py          ├───────────────────>│ .py          │
│             │  &redirect_uri=     │                     │ get_client()       │              │
│             │  &code_challenge    │ oauth_authorize_    │                    │              │
└──────┬──────┘                    │ handler()           │                    └──────────────┘
       │                            └──────────┬──────────┘
       │                                       │
       │                                       │ create_authorization_code()
       │                                       │ (PKCE 지원)
       │                                       ▼
       │                            ┌─────────────────────┐
       │                            │ dcr_tokens 테이블   │
       │                            │ INSERT:             │
       │                            │ - auth_code         │
       │                            │ - metadata:         │
       │                            │   {code_challenge,  │
       │                            │    redirect_uri}    │
       │                            └─────────────────────┘
       │                                       │
       │                                       │ Azure AD URL 생성
       │                                       ▼
       │                            https://login.microsoftonline.com/
       │                            {tenant}/oauth2/v2.0/authorize?
       │                            client_id={azure_app_id}
       │                            &state={auth_code}:{state}
       │                            &redirect_uri={azure_redirect_uri}
       │                                       │
       │  302 Redirect                         │
       │<───────────────────────────────────────┘
       │
       │  사용자 브라우저가 Azure AD로 리다이렉트
       │
       ▼
┌──────────────────┐
│                  │
│   Azure AD       │
│   로그인 페이지   │
│                  │
└──────────────────┘
```

**구현 위치:**
- HTTP 핸들러: `unified_http_server.py:489-563` (`oauth_authorize_handler`)
- DCR 클라이언트 조회: `dcr_service.py:231-257` (`get_client`)
- Auth Code 생성: `dcr_service.py:266-300` (`create_authorization_code`)

**처리 과정:**

1. **파라미터 파싱:**
   ```python
   client_id = params.get("client_id")          # dcr_xxx
   redirect_uri = params.get("redirect_uri")    # https://claude.ai/...
   scope = params.get("scope")                  # Mail.Read User.Read
   state = params.get("state")                  # Claude가 생성한 state
   code_challenge = params.get("code_challenge")           # PKCE
   code_challenge_method = params.get("code_challenge_method")  # S256
   ```

2. **DCR 클라이언트 검증:**
   - `get_client(dcr_client_id)` 호출
   - redirect_uri가 등록된 URI 목록에 있는지 확인

3. **Authorization Code 생성:**
   ```python
   auth_code = secrets.token_urlsafe(32)  # 32바이트 랜덤 코드

   # metadata에 PKCE 정보 저장
   metadata = {
       "redirect_uri": redirect_uri,
       "state": state,
       "scope": scope,
       "code_challenge": code_challenge,
       "code_challenge_method": code_challenge_method
   }

   # dcr_tokens 테이블에 저장 (10분 유효)
   INSERT INTO dcr_tokens (
       dcr_token_value, dcr_client_id, dcr_token_type,
       expires_at, metadata
   ) VALUES (auth_code, client_id, 'authorization_code',
             NOW() + 10 minutes, json(metadata))
   ```

4. **Azure AD URL 생성:**
   ```python
   # Internal state: DCR auth_code + 원래 state를 콜론으로 결합
   internal_state = f"{auth_code}:{state}" if state else auth_code

   azure_auth_url = (
       f"https://login.microsoftonline.com/{azure_tenant_id}/oauth2/v2.0/authorize?"
       f"client_id={azure_application_id}&"
       f"response_type=code&"
       f"redirect_uri={urllib.parse.quote(azure_redirect_uri)}&"
       f"response_mode=query&"
       f"scope={urllib.parse.quote(scope)}&"
       f"state={urllib.parse.quote(internal_state)}"
   )
   ```

5. **리다이렉트:**
   - 사용자 브라우저를 Azure AD 로그인 페이지로 리다이렉트
   - state 파라미터에 `{auth_code}:{original_state}` 포함

---

### Phase 3: Azure AD 콜백 처리 (Azure → DCR)

```
┌──────────────────┐                    ┌─────────────────────┐
│                  │  사용자 로그인       │                     │
│   Azure AD       │  완료 후            │  unified_http_      │
│                  │  GET /oauth/        │  server.py          │
│                  │  azure_callback?    │                     │
│                  │  code={azure_code}  │ oauth_azure_        │
│                  │  &state={auth_code} │ callback_handler()  │
└─────────┬────────┘                    └──────────┬──────────┘
          │                                        │
          │                                        │ 1. state 파싱
          │                                        │    auth_code, original_state 분리
          │                                        │
          │                                        │ 2. auth_code 검증
          │                                        ▼
          │                             ┌─────────────────────┐
          │                             │ dcr_tokens 테이블   │
          │                             │ SELECT WHERE        │
          │                             │ dcr_token_value =   │
          │                             │ auth_code           │
          │                             └──────────┬──────────┘
          │                                        │
          │                                        │ 3. Azure AD 토큰 교환
          │                                        ▼
          └────────────────────────────> POST https://login.microsoftonline.com/
                                         {tenant}/oauth2/v2.0/token

                                         Body:
                                         - client_id: {azure_app_id}
                                         - client_secret: {azure_secret}
                                         - code: {azure_code}
                                         - grant_type: authorization_code
                                         - redirect_uri: {azure_redirect_uri}

                                         ▼

                                         Response:
                                         {
                                           "access_token": "eyJ0eXAi...",
                                           "refresh_token": "0.AXcA...",
                                           "expires_in": 3600,
                                           "token_type": "Bearer"
                                         }

                                         │
                                         │ 4. 사용자 정보 조회
                                         ▼

                                         GET https://graph.microsoft.com/v1.0/me
                                         Authorization: Bearer {azure_access_token}

                                         Response:
                                         {
                                           "id": "azure-object-id-xxxx",
                                           "userPrincipalName": "user@example.com",
                                           "displayName": "User Name",
                                           "mail": "user@example.com"
                                         }

                                         │
                                         │ 5. 사용자 접근 제어
                                         │    is_user_allowed(email)
                                         │
                                         │ 6. Azure 토큰 저장
                                         ▼

                              ┌─────────────────────────────┐
                              │ dcr_azure_tokens 테이블     │
                              │ INSERT OR REPLACE:          │
                              │ - object_id (PK)            │
                              │ - access_token (암호화)      │
                              │ - refresh_token (암호화)     │
                              │ - expires_at                │
                              │ - user_email, user_name     │
                              └──────────────┬──────────────┘
                                             │
                                             │ 7. auth_code 업데이트
                                             ▼
                              ┌─────────────────────────────┐
                              │ dcr_tokens 테이블           │
                              │ UPDATE:                     │
                              │ SET azure_object_id =       │
                              │ WHERE dcr_token_value =     │
                              │ auth_code                   │
                              └──────────────┬──────────────┘
                                             │
                                             │ 8. Claude로 리다이렉트
                                             ▼
┌─────────────┐                    302 Redirect to:
│             │<───────────────────  {claude_redirect_uri}?
│  Claude.ai  │                      code={auth_code}
│             │                      &state={original_state}
└─────────────┘
```

**구현 위치:**
- HTTP 핸들러: `unified_http_server.py:872-1129` (`oauth_azure_callback_handler`)
- 토큰 저장: 직접 SQL 실행 (dcr_service._execute_query)

**처리 과정:**

1. **State 파싱:**
   ```python
   state = params.get("state")  # "{auth_code}:{original_state}"

   if ":" in state:
       auth_code, original_state = state.split(":", 1)
   else:
       auth_code = state
       original_state = None
   ```

2. **Auth Code 검증:**
   ```python
   query = """
   SELECT dcr_client_id, metadata
   FROM dcr_tokens
   WHERE dcr_token_type = 'authorization_code'
     AND dcr_token_value = ?
     AND dcr_status = 'active'
     AND expires_at > datetime('now')
   """
   result = dcr_service._fetch_one(query, (auth_code,))
   ```

3. **Azure AD 토큰 교환 (httpx 사용):**
   ```python
   import httpx

   async with httpx.AsyncClient() as http_client:
       token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

       token_data = {
           "client_id": azure_application_id,
           "client_secret": azure_client_secret,
           "code": azure_code,  # Azure가 발급한 code
           "redirect_uri": azure_redirect_uri,
           "grant_type": "authorization_code",
           "scope": scope or "https://graph.microsoft.com/.default"
       }

       response = await http_client.post(token_url, data=token_data)
       azure_token_data = response.json()
       # {access_token, refresh_token, expires_in, ...}
   ```

4. **사용자 정보 조회 (Microsoft Graph API):**
   ```python
   user_info_response = await http_client.get(
       "https://graph.microsoft.com/v1.0/me",
       headers={"Authorization": f"Bearer {azure_token_data['access_token']}"}
   )

   user_info = user_info_response.json()
   azure_object_id = user_info.get("id")         # Azure User Object ID
   user_email = user_info.get("mail") or user_info.get("userPrincipalName")
   user_name = user_info.get("displayName")
   ```

5. **사용자 접근 제어:**
   ```python
   if not dcr_service.is_user_allowed(user_email):
       return Response("Access Denied", status_code=403)
   ```

6. **Azure 토큰 저장 (암호화):**
   ```python
   from modules.enrollment.account import AccountCryptoHelpers
   crypto = AccountCryptoHelpers()

   azure_insert_query = """
   INSERT OR REPLACE INTO dcr_azure_tokens (
       object_id, application_id, access_token, refresh_token,
       expires_at, scope, user_email, user_name, updated_at
   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
   """

   dcr_service._execute_query(
       azure_insert_query,
       (
           azure_object_id,
           azure_application_id,
           crypto.account_encrypt_sensitive_data(azure_token_data["access_token"]),
           crypto.account_encrypt_sensitive_data(azure_token_data["refresh_token"]),
           azure_expiry,
           scope,
           user_email,
           user_name
       )
   )
   ```

7. **Auth Code에 Object ID 연결:**
   ```python
   update_auth_code_query = """
   UPDATE dcr_tokens
   SET azure_object_id = ?
   WHERE dcr_token_value = ? AND dcr_token_type = 'authorization_code'
   """
   dcr_service._execute_query(update_auth_code_query, (azure_object_id, auth_code))
   ```

8. **Claude로 리다이렉트:**
   ```python
   redirect_params = {"code": auth_code}
   if original_state:
       redirect_params["state"] = original_state

   redirect_url = f"{claude_redirect_uri}?{urllib.parse.urlencode(redirect_params)}"
   return RedirectResponse(url=redirect_url)
   ```

---

### Phase 4: 토큰 교환 (Claude → DCR)

```
┌─────────────┐                    ┌─────────────────────┐                    ┌──────────────┐
│             │  POST /oauth/       │                     │                    │              │
│  Claude.ai  │  token              │  unified_http_      │                    │ dcr_service  │
│             ├────────────────────>│  server.py          ├───────────────────>│ .py          │
│             │  grant_type=        │                     │                    │              │
│             │  authorization_code │ oauth_token_        │ verify_client_     │              │
│             │  &code={auth_code}  │ handler()           │ credentials()      │              │
│             │  &client_id=dcr_xxx │                     │                    │              │
│             │  &client_secret=... │                     │                    │              │
│             │  &code_verifier=... │                     │                    │              │
└──────┬──────┘  (PKCE)             └──────────┬──────────┘                    └──────┬───────┘
       │                                       │                                      │
       │                                       │                                      │
       │                                       │ verify_authorization_code()          │
       │                                       │ (PKCE 검증 포함)                      │
       │                                       ▼                                      │
       │                            ┌─────────────────────┐                          │
       │                            │ dcr_tokens 테이블   │                          │
       │                            │ SELECT:             │                          │
       │                            │ - metadata          │                          │
       │                            │ - azure_object_id   │                          │
       │                            │                     │                          │
       │                            │ PKCE 검증:          │                          │
       │                            │ SHA256(verifier)    │                          │
       │                            │ == code_challenge   │                          │
       │                            │                     │                          │
       │                            │ UPDATE:             │                          │
       │                            │ dcr_status='expired'│                          │
       │                            └──────────┬──────────┘                          │
       │                                       │                                      │
       │                                       │ get_azure_tokens_by_object_id()      │
       │                                       ├─────────────────────────────────────>│
       │                                       │                                      │
       │                                       │                                      ▼
       │                                       │                       ┌─────────────────────┐
       │                                       │                       │ dcr_azure_tokens    │
       │                                       │                       │ SELECT WHERE        │
       │                                       │                       │ object_id = ?       │
       │                                       │<──────────────────────┤                     │
       │                                       │ {azure_access_token,  │ 복호화:             │
       │                                       │  scope, expires_in}   │ - access_token      │
       │                                       │                       │ - refresh_token     │
       │                                       │                       └─────────────────────┘
       │                                       │
       │                                       │ DCR 토큰 생성
       │                                       │ (새로운 access & refresh token)
       │                                       ▼
       │                            ┌─────────────────────────────┐
       │                            │ dcr_tokens 테이블           │
       │                            │ DELETE 기존 Bearer/refresh  │
       │                            │ (중복 방지)                  │
       │                            │                             │
       │                            │ INSERT Bearer:              │
       │                            │ - dcr_token_value (암호화)   │
       │                            │ - azure_object_id (링크)     │
       │                            │ - expires_at                │
       │                            │                             │
       │                            │ INSERT refresh:             │
       │                            │ - dcr_token_value (암호화)   │
       │                            │ - expires_at (30일)          │
       │                            └─────────────────────────────┘
       │                                       │
       │  Response:                            │
       │  {access_token,                       │
       │   refresh_token,                      │
       │   expires_in}                         │
       │<──────────────────────────────────────┘
       │
       │  이제 Claude.ai는 DCR access_token으로
       │  모든 MCP 서비스 호출 가능
       │
       ▼
```

**구현 위치:**
- HTTP 핸들러: `unified_http_server.py:575-869` (`oauth_token_handler`)
- Auth Code 검증: `dcr_service.py:302-360` (`verify_authorization_code`)
- Azure 토큰 조회: `dcr_service.py:479-511` (`get_azure_tokens_by_object_id`)

**처리 과정:**

1. **클라이언트 인증:**
   ```python
   client_id = form_data.get("client_id")
   client_secret = form_data.get("client_secret")

   if not dcr_service.verify_client_credentials(client_id, client_secret):
       return JSONResponse({"error": "invalid_client"}, status_code=401)
   ```

2. **Authorization Code 검증 (PKCE 포함):**
   ```python
   code = form_data.get("code")  # DCR auth_code
   code_verifier = form_data.get("code_verifier")  # PKCE

   auth_data = dcr_service.verify_authorization_code(
       code=code,
       dcr_client_id=client_id,
       redirect_uri=redirect_uri,
       code_verifier=code_verifier
   )

   # verify_authorization_code 내부:
   # 1. dcr_tokens 테이블에서 auth_code 조회
   # 2. 만료 시간 확인
   # 3. PKCE 검증 (S256 or plain)
   # 4. status를 'expired'로 변경 (일회용)
   # 5. {scope, state, azure_object_id} 반환
   ```

3. **PKCE 검증 로직:**
   ```python
   # dcr_service.py:538-547
   def _verify_pkce(self, code_verifier: str, code_challenge: str, method: str) -> bool:
       if method == "plain":
           return secrets.compare_digest(code_verifier, code_challenge)
       elif method == "S256":
           digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
           calculated_challenge = base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
           return secrets.compare_digest(calculated_challenge, code_challenge)
       else:
           return False
   ```

4. **Azure 토큰 조회:**
   ```python
   azure_object_id = auth_data.get("azure_object_id")

   azure_tokens = dcr_service.get_azure_tokens_by_object_id(azure_object_id)
   # {access_token, refresh_token, scope, expires_in, user_email}

   # get_azure_tokens_by_object_id 내부:
   # 1. dcr_azure_tokens 테이블 조회
   # 2. 암호화된 토큰 복호화
   # 3. 만료 시간 계산 (expires_at - now)
   ```

5. **DCR 토큰 생성 및 저장:**
   ```python
   access_token = secrets.token_urlsafe(32)
   refresh_token = secrets.token_urlsafe(32)

   # 기존 토큰 삭제 (중복 방지)
   dcr_service._execute_query("""
       DELETE FROM dcr_tokens
       WHERE dcr_client_id = ? AND azure_object_id = ?
         AND dcr_token_type IN ('Bearer', 'refresh')
         AND dcr_status = 'active'
   """, (client_id, azure_object_id))

   # Bearer 토큰 저장
   dcr_service._execute_query("""
       INSERT INTO dcr_tokens (
           dcr_token_value, dcr_client_id, dcr_token_type,
           azure_object_id, expires_at, dcr_status
       ) VALUES (?, ?, 'Bearer', ?, ?, 'active')
   """, (
       crypto.account_encrypt_sensitive_data(access_token),
       client_id,
       azure_object_id,
       azure_token_expiry
   ))

   # Refresh 토큰 저장 (30일)
   dcr_service._execute_query("""
       INSERT INTO dcr_tokens (
           dcr_token_value, dcr_client_id, dcr_token_type,
           azure_object_id, expires_at, dcr_status
       ) VALUES (?, ?, 'refresh', ?, ?, 'active')
   """, (
       crypto.account_encrypt_sensitive_data(refresh_token),
       client_id,
       azure_object_id,
       refresh_expiry
   ))
   ```

6. **응답 반환:**
   ```json
   {
       "access_token": "dcr_access_token_xxxxx",
       "token_type": "Bearer",
       "expires_in": 3600,
       "refresh_token": "dcr_refresh_token_yyyyy",
       "scope": "Mail.Read User.Read"
   }
   ```

---

### Phase 5: MCP 요청 인증 (Claude → DCR → MCP → Graph API)

```
┌─────────────┐                    ┌─────────────────────┐                    ┌──────────────┐
│             │  POST /mail-query/  │                     │                    │              │
│  Claude.ai  │  messages           │  auth_middleware    │                    │ dcr_service  │
│             │  Authorization:     │  .py                ├───────────────────>│ .py          │
│             │  Bearer {dcr_token} │                     │                    │              │
│             ├────────────────────>│ verify_bearer_      │ verify_bearer_     │              │
│             │                     │ token_middleware()  │ token()            │              │
└─────────────┘                    └──────────┬──────────┘                    └──────┬───────┘
                                              │                                      │
                                              │                                      │
                                              │                                      ▼
                                              │                       ┌─────────────────────────┐
                                              │                       │ dcr_tokens 테이블       │
                                              │                       │ SELECT d.*, a.*         │
                                              │                       │ FROM dcr_tokens d       │
                                              │                       │ LEFT JOIN               │
                                              │                       │   dcr_azure_tokens a    │
                                              │                       │ ON d.azure_object_id    │
                                              │                       │    = a.object_id        │
                                              │                       │ WHERE                   │
                                              │                       │   d.dcr_token_type      │
                                              │                       │   = 'Bearer'            │
                                              │                       │   AND d.dcr_status      │
                                              │                       │   = 'active'            │
                                              │                       │   AND d.expires_at >    │
                                              │                       │   NOW()                 │
                                              │                       │                         │
                                              │                       │ 복호화:                  │
                                              │                       │ - dcr_token_value       │
                                              │                       │ - azure_access_token    │
                                              │<──────────────────────┤                         │
                                              │ {azure_access_token,  │ secrets.compare_digest()│
                                              │  azure_object_id,     │ (constant-time 비교)     │
                                              │  user_email, scope}   └─────────────────────────┘
                                              │
                                              │ request.state 주입:
                                              │ - azure_token = azure_access_token
                                              │ - azure_object_id = object_id
                                              │ - token_scope = scope
                                              │ - dcr_client_id = client_id
                                              │
                                              ▼
                                   ┌─────────────────────┐
                                   │  MCP Handler        │
                                   │  (mail_query,       │
                                   │   onenote, etc)     │
                                   │                     │
                                   │  azure_token =      │
                                   │  request.state.     │
                                   │  azure_token        │
                                   └──────────┬──────────┘
                                              │
                                              │ Graph API 호출
                                              ▼
                                   ┌─────────────────────────────┐
                                   │  Microsoft Graph API        │
                                   │                             │
                                   │  GET /v1.0/me/messages      │
                                   │  Authorization: Bearer      │
                                   │  {azure_access_token}       │
                                   │                             │
                                   │  Response:                  │
                                   │  {value: [...emails...]}    │
                                   └──────────┬──────────────────┘
                                              │
                                              │ MCP Response
                                              ▼
┌─────────────┐                    ┌─────────────────────┐
│             │  JSONRPC Response   │                     │
│  Claude.ai  │<────────────────────┤  MCP Handler        │
│             │  {result: {...}}    │                     │
└─────────────┘                    └─────────────────────┘
```

**구현 위치:**
- 미들웨어: `auth_middleware.py:14-111` (`verify_bearer_token_middleware`)
- 토큰 검증: `dcr_service.py:439-477` (`verify_bearer_token`)

**처리 과정:**

1. **경로 검증 (미들웨어):**
   ```python
   # auth_middleware.py:26-40

   # 인증 제외 경로
   if "/.well-known/" in path:
       return None

   excluded_path_prefixes = [
       "/oauth/",
       "/health",
       "/info",
       "/enrollment/callback",
       "/auth/callback"
   ]

   if any(path.startswith(excluded) for excluded in excluded_path_prefixes):
       return None

   if request.method == "OPTIONS":
       return None
   ```

2. **Authorization 헤더 파싱:**
   ```python
   auth_header = request.headers.get("Authorization", "")

   if not auth_header.startswith("Bearer "):
       return JSONResponse(
           {"error": {"code": -32001, "message": "Authentication required"}},
           status_code=401
       )

   token = auth_header[7:]  # "Bearer " 제거
   ```

3. **Bearer 토큰 검증 (DCRService):**
   ```python
   # dcr_service.py:439-477

   def verify_bearer_token(self, token: str) -> Optional[Dict[str, Any]]:
       query = """
       SELECT d.dcr_client_id, d.dcr_token_value, d.expires_at, d.azure_object_id,
              a.access_token, a.expires_at, a.scope, a.user_email
       FROM dcr_tokens d
       LEFT JOIN dcr_azure_tokens a ON d.azure_object_id = a.object_id
       WHERE d.dcr_token_type = 'Bearer'
         AND d.dcr_status = 'active'
         AND d.expires_at > CURRENT_TIMESTAMP
       """

       results = self._fetch_all(query)

       for row in results:
           dcr_client_id, encrypted_token, dcr_expires_at, azure_object_id, \
           encrypted_azure_token, azure_expires_at, scope, user_email = row

           try:
               # 복호화 및 constant-time 비교 (타이밍 공격 방지)
               decrypted_token = self.crypto.account_decrypt_sensitive_data(encrypted_token)
               if secrets.compare_digest(decrypted_token, token):
                   azure_access_token = self.crypto.account_decrypt_sensitive_data(
                       encrypted_azure_token
                   )
                   return {
                       "dcr_client_id": dcr_client_id,
                       "azure_object_id": azure_object_id,
                       "azure_access_token": azure_access_token,
                       "azure_expires_at": azure_expires_at,
                       "scope": scope,
                       "user_email": user_email
                   }
           except Exception as e:
               logger.error(f"Token decryption error: {e}")
               continue

       return None
   ```

4. **request.state 주입:**
   ```python
   # auth_middleware.py:78-84

   if token_data:
       request.state.azure_token = token_data["azure_access_token"]
       request.state.token_scope = token_data.get("scope", "")
       request.state.dcr_client_id = token_data.get("dcr_client_id", "")
       request.state.azure_object_id = token_data.get("azure_object_id", "")

       return None  # 인증 성공, 다음 핸들러로 진행
   else:
       return JSONResponse({"error": "Invalid token"}, status_code=401)
   ```

5. **MCP 핸들러에서 Azure 토큰 사용:**
   ```python
   # 예: mail_query MCP 핸들러

   async def handle_search_emails(request, arguments):
       azure_token = request.state.azure_token

       # Microsoft Graph API 호출
       async with httpx.AsyncClient() as client:
           response = await client.get(
               "https://graph.microsoft.com/v1.0/me/messages",
               headers={"Authorization": f"Bearer {azure_token}"},
               params={"$filter": arguments.get("query")}
           )

           emails = response.json()
           return emails
   ```

---

## 🔄 Refresh Token Flow

```
┌─────────────┐                    ┌─────────────────────┐
│             │  POST /oauth/token  │                     │
│  Claude.ai  │  grant_type=        │  unified_http_      │
│             │  refresh_token      │  server.py          │
│             │  &refresh_token=... │                     │
│             ├────────────────────>│ oauth_token_        │
│             │  &client_id=dcr_xxx │ handler()           │
│             │  &client_secret=... │                     │
└──────┬──────┘                    └──────────┬──────────┘
       │                                       │
       │                                       │ 1. refresh_token 검증
       │                                       ▼
       │                            ┌─────────────────────┐
       │                            │ dcr_tokens 테이블   │
       │                            │ SELECT WHERE        │
       │                            │ dcr_token_type =    │
       │                            │ 'refresh'           │
       │                            │                     │
       │                            │ 복호화 및 비교       │
       │                            │ secrets.compare_    │
       │                            │ digest()            │
       │                            └──────────┬──────────┘
       │                                       │
       │                                       │ 2. Azure 토큰 조회
       │                                       ▼
       │                            ┌─────────────────────┐
       │                            │ dcr_azure_tokens    │
       │                            │ SELECT WHERE        │
       │                            │ object_id = ?       │
       │                            └──────────┬──────────┘
       │                                       │
       │                                       │ 3. 새 DCR 토큰 생성
       │                                       │    (access + refresh)
       │                                       │
       │                                       │ 4. 기존 토큰 삭제
       │                                       │    (중복 방지)
       │                                       ▼
       │                            ┌─────────────────────┐
       │                            │ dcr_tokens 테이블   │
       │                            │ DELETE old tokens   │
       │                            │ INSERT new Bearer   │
       │                            │ INSERT new refresh  │
       │                            └─────────────────────┘
       │                                       │
       │  Response:                            │
       │  {access_token: new,                  │
       │   refresh_token: new,                 │
       │   expires_in: 3600}                   │
       │<──────────────────────────────────────┘
       │
```

**구현 위치:** `unified_http_server.py:603-726`

**핵심 특징:**
- Azure AD 재인증 **불필요** (Azure 토큰은 그대로 재사용)
- DCR 토큰만 새로 발급
- 기존 토큰 DELETE 후 INSERT (중복 방지)
- Refresh token 유효기간: 30일

---

## 📊 데이터 흐름 요약

### 토큰 매핑 체인

```
Claude DCR Token (request)
  ↓ (verify_bearer_token)
DCR Tokens Table (dcr_token_value)
  ↓ (azure_object_id FK)
Azure Tokens Table (object_id PK)
  ↓ (access_token 복호화)
Azure Access Token
  ↓ (Graph API 호출)
Microsoft 365 Resources
```

### 데이터베이스 관계

```sql
-- 1:N 관계
dcr_azure_auth (1) ──< dcr_clients (N)
  application_id         azure_application_id

-- 1:N 관계
dcr_clients (1) ──< dcr_tokens (N)
  dcr_client_id      dcr_client_id

-- 1:N 관계
dcr_azure_tokens (1) ──< dcr_tokens (N)
  object_id (PK)         azure_object_id (FK)
```

**핵심:** `azure_object_id`가 DCR 토큰과 Azure 토큰을 연결하는 JOIN 키

---

## 🔒 보안 메커니즘

### 1. 암호화 (AES-256-GCM)

**암호화 대상:**
- `dcr_clients.dcr_client_secret`
- `dcr_tokens.dcr_token_value` (모든 타입)
- `dcr_azure_tokens.access_token`
- `dcr_azure_tokens.refresh_token`

**구현:**
```python
from modules.enrollment.account import AccountCryptoHelpers

crypto = AccountCryptoHelpers()
encrypted = crypto.account_encrypt_sensitive_data(plaintext)
decrypted = crypto.account_decrypt_sensitive_data(encrypted)
```

### 2. Constant-Time 비교 (타이밍 공격 방지)

```python
import secrets

# ❌ 취약한 비교 (타이밍 공격 가능)
if decrypted_token == user_token:
    return True

# ✅ 안전한 비교 (constant-time)
if secrets.compare_digest(decrypted_token, user_token):
    return True
```

### 3. PKCE (Authorization Code Interception 방지)

**S256 검증:**
```python
def _verify_pkce(self, code_verifier: str, code_challenge: str, method: str) -> bool:
    if method == "S256":
        digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        calculated_challenge = base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
        return secrets.compare_digest(calculated_challenge, code_challenge)
```

### 4. 토큰 만료 관리

- **Authorization Code:** 10분 (일회용)
- **Access Token:** Azure 토큰과 동일 (일반적으로 1시간)
- **Refresh Token:** 30일

### 5. 사용자 접근 제어

```python
# 환경변수 설정
DCR_ALLOWED_USERS=user1@example.com,user2@example.com

# 검증
def is_user_allowed(self, user_email: str) -> bool:
    if not self.allowed_users:
        return True  # 빈 리스트면 모두 허용

    return user_email.lower().strip() in self.allowed_users
```

---

## 🎯 핵심 설계 원칙

### 1. 프록시 패턴 (Proxy Pattern)

DCR 서버는 투명한 프록시로 동작:
- Claude.ai는 Azure AD를 직접 알 필요 없음
- DCR 토큰만 관리하면 됨
- Azure 토큰은 서버에서 자동 매핑

### 2. 토큰 공유 (Token Sharing)

`azure_object_id` 기준으로 여러 DCR 클라이언트가 동일한 Azure 토큰 공유:
- 불필요한 Azure AD 재인증 방지
- 사용자 경험 개선
- 토큰 관리 간소화

### 3. 데이터 분리 (Separation of Concerns)

- **dcr_azure_auth:** Azure 앱 설정 (관리자가 설정)
- **dcr_azure_tokens:** Azure 사용자 토큰 (Azure AD가 발급)
- **dcr_clients:** DCR 클라이언트 (Claude가 등록)
- **dcr_tokens:** DCR 토큰 (DCR 서버가 발급)

### 4. 보안 우선 (Security First)

- 모든 민감 정보 암호화
- Constant-time 비교
- PKCE 지원
- 사용자 접근 제어
- 토큰 만료 관리

---

## 📚 참고 코드 위치

### DCR 모듈
- `modules/dcr_oauth/dcr_service.py` - 핵심 비즈니스 로직
- `modules/dcr_oauth/auth_middleware.py` - Bearer 토큰 미들웨어

### HTTP 엔드포인트
- `entrypoints/production/unified_http_server.py:459-486` - DCR 등록
- `entrypoints/production/unified_http_server.py:489-563` - OAuth 인증 시작
- `entrypoints/production/unified_http_server.py:872-1129` - Azure 콜백
- `entrypoints/production/unified_http_server.py:575-869` - 토큰 교환

### 스키마
- `modules/dcr_oauth/migrations/dcr_schema_v3.sql` - 데이터베이스 스키마

### 암호화
- `modules/enrollment/account/_account_helpers.py` - AES-256-GCM 암호화

---

## 🔍 디버깅 팁

### 로그 확인

**인증 성공:**
```
✅ DCR client registered: dcr_xxxxx
✅ Got Azure token, expires_in: 3600
✅ Azure token saved for object_id: xxxx, user: user@example.com
✅ Authenticated DCR client: dcr_xxxxx for /mail-query/messages
```

**인증 실패:**
```
❌ Azure token exchange failed: ...
❌ Invalid Bearer token for path: /mail-query/messages
❌ Access denied for user: user@example.com
```

### SQL 쿼리

**현재 활성 DCR 토큰 조회:**
```sql
SELECT d.dcr_client_id, d.dcr_token_type, d.expires_at,
       a.user_email, a.scope
FROM dcr_tokens d
LEFT JOIN dcr_azure_tokens a ON d.azure_object_id = a.object_id
WHERE d.dcr_status = 'active'
  AND d.expires_at > datetime('now')
ORDER BY d.issued_at DESC;
```

**Azure 토큰 상태 확인:**
```sql
SELECT object_id, user_email, expires_at,
       CASE WHEN expires_at > datetime('now') THEN '유효' ELSE '만료' END as status
FROM dcr_azure_tokens
ORDER BY updated_at DESC;
```

**클라이언트별 토큰 수:**
```sql
SELECT dcr_client_id, dcr_token_type, COUNT(*) as count
FROM dcr_tokens
WHERE dcr_status = 'active'
GROUP BY dcr_client_id, dcr_token_type;
```
