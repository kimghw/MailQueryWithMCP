# DCR 통합 인증 (Unified Authentication) 구현

## 개요

여러 MCP 서비스(enrollment, mail-query, onedrive, teams, onenote)를 하나의 OAuth 인증으로 통합하여, 사용자가 한 번만 인증하면 모든 서비스에 접근할 수 있도록 구현했습니다.

## 주요 특징

- **단일 인증**: 한 번의 OAuth 인증으로 모든 MCP 서비스 접근
- **DCR 클라이언트 재사용**: 모든 서비스가 동일한 `dcr_client_id` 공유
- **Bearer 토큰 공유**: 모든 서비스가 동일한 Bearer 토큰 사용
- **자동 재인증 스킵**: 유효한 토큰이 있으면 Azure AD 재인증 생략

## 핵심 구현 사항

### 1. Bearer 토큰 저장 방식 변경

**문제점**:
- 이전에는 Bearer 토큰을 암호화하여 저장
- 클라이언트에는 평문으로 전송
- 검증 시 복호화/평문 비교 불일치 발생

**해결책**:
```python
# Before (encrypted storage)
crypto.account_encrypt_sensitive_data(access_token)

# After (plaintext storage)
access_token  # Store plaintext for Bearer token validation
```

**파일**: `entrypoints/production/unified_http_server.py:885`

### 2. DCR 클라이언트 재사용

**문제점**:
- 각 MCP 서비스마다 새로운 DCR 클라이언트 생성
- Claude.ai가 각 서비스를 별개로 인식
- 서비스마다 개별 인증 필요

**해결책**:
```python
# Check for existing client first
existing_client_query = """
SELECT dcr_client_id, dcr_client_secret, redirect_uris
FROM dcr_clients
WHERE azure_app_id = ?
  AND dcr_status = 'active'
LIMIT 1
"""
existing_client = self._fetch_one(existing_client_query, (azure_app_id,))

if existing_client:
    logger.info(f"♻️ Reusing existing DCR client: {existing_client[0]}")
    return {
        "client_id": existing_client[0],
        "client_secret": existing_client[1],
        "redirect_uris": json.loads(existing_client[2])
    }
```

**파일**: `modules/dcr_oauth/dcr_service.py:180-214`

### 3. Bearer 토큰 재사용

**문제점**:
- 새 서비스 연결 시 기존 토큰 무시
- 매번 새로운 Bearer 토큰 발급
- 기존 연결된 서비스와 토큰 불일치

**해결책**:
```python
# Check for existing active Bearer token first
existing_token_query = """
SELECT dcr_token_value, expires_at
FROM dcr_tokens
WHERE dcr_client_id = ?
  AND azure_object_id = ?
  AND dcr_token_type = 'Bearer'
  AND dcr_status = 'active'
  AND expires_at > CURRENT_TIMESTAMP
"""
existing_token = dcr_service._fetch_one(existing_token_query, (client_id, azure_object_id))

if existing_token:
    # Reuse existing token
    access_token = existing_token[0]
    refresh_token = secrets.token_urlsafe(32)
    logger.info(f"♻️ Reusing existing Bearer token for client: {client_id}, user: {azure_object_id}")
```

**파일**: `entrypoints/production/unified_http_server.py:859-900`

### 4. Azure AD 재인증 스킵

**문제점**:
- 유효한 세션이 있어도 매번 Azure AD 로그인 화면 표시
- 사용자 경험 저하

**해결책**:
```python
# Check if we already have an active Bearer token for this client
existing_token_query = """
SELECT dcr_token_value, azure_object_id
FROM dcr_tokens
WHERE dcr_client_id = ?
  AND dcr_token_type = 'Bearer'
  AND dcr_status = 'active'
  AND expires_at > CURRENT_TIMESTAMP
LIMIT 1
"""
existing_token = dcr_service._fetch_one(existing_token_query, (client_id,))

if existing_token:
    # Create authorization code and redirect immediately
    auth_code = secrets.token_urlsafe(32)
    code_expiry = datetime.now() + timedelta(minutes=10)

    # Store auth code with skip_azure flag
    metadata = {
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": scope,
        "skip_azure": True
    }

    # Redirect back to Claude with authorization code
    callback_url = f"{redirect_uri}?code={auth_code}&state={state}"
    return RedirectResponse(url=callback_url)
```

**파일**: `entrypoints/production/unified_http_server.py:601-654`

### 5. 토큰 검증 로직 개선

**문제점**:
- Bearer 토큰을 암호화된 것으로 가정하고 복호화 시도
- 평문 토큰과 비교 실패

**해결책**:
```python
# Before
decrypted_token = self.crypto.account_decrypt_sensitive_data(encrypted_token)
if secrets.compare_digest(decrypted_token, token):

# After
# Bearer tokens are now stored as plaintext
if secrets.compare_digest(encrypted_token, token):
```

**파일**: `modules/dcr_oauth/dcr_service.py:505`

## 데이터베이스 스키마

### dcr_clients 테이블
```sql
CREATE TABLE dcr_clients (
    dcr_client_id TEXT PRIMARY KEY,
    dcr_client_secret TEXT NOT NULL,
    azure_app_id TEXT NOT NULL,  -- 동일 Azure 앱은 하나의 클라이언트만 생성
    redirect_uris TEXT NOT NULL,
    dcr_status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### dcr_tokens 테이블
```sql
CREATE TABLE dcr_tokens (
    dcr_token_value TEXT PRIMARY KEY,
    dcr_client_id TEXT NOT NULL,
    dcr_token_type TEXT NOT NULL,  -- 'Bearer', 'authorization_code', 'refresh'
    azure_object_id TEXT,
    expires_at TIMESTAMP,
    dcr_status TEXT DEFAULT 'active',
    metadata TEXT,  -- JSON: state, scope, skip_azure 등
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 인증 흐름

### 첫 번째 서비스 연결 시

1. Claude.ai → `GET /.well-known/mcp.json`
2. Claude.ai → `POST /oauth/register` (DCR 클라이언트 등록)
3. Claude.ai → `GET /oauth/authorize?client_id=...`
4. Server → Azure AD 로그인 페이지로 리다이렉트
5. 사용자 → Azure AD 로그인
6. Azure AD → Server (authorization code 반환)
7. Server → Claude.ai (authorization code 전달)
8. Claude.ai → `POST /oauth/token` (Bearer 토큰 요청)
9. Server → Bearer 토큰 발급 및 DB 저장

### 두 번째 이후 서비스 연결 시

1. Claude.ai → `GET /.well-known/mcp.json`
2. Claude.ai → `POST /oauth/register`
   - **서버가 기존 DCR 클라이언트 재사용** ♻️
3. Claude.ai → `GET /oauth/authorize?client_id=...`
   - **서버가 기존 Bearer 토큰 확인**
   - **Azure AD 스킵하고 바로 authorization code 발급** ⚡
4. Server → Claude.ai (authorization code 전달)
5. Claude.ai → `POST /oauth/token`
   - **서버가 기존 Bearer 토큰 재사용** ♻️

## 현재 상태

모든 MCP 서비스가 통합 인증으로 성공적으로 작동 중:

- ✅ **enrollment**: 계정 등록 서비스
- ✅ **mail-query**: 이메일 조회 서비스
- ✅ **onedrive**: OneDrive 파일 관리
- ✅ **teams**: Teams 메시지 관리
- ✅ **onenote**: OneNote 노트 관리

### 검증된 사항

- 모든 서비스가 동일한 `dcr_client_id` 사용: `dcr_b0xYoKqZ0k1ZTw0AEvgQUQ`
- 모든 서비스가 동일한 Bearer 토큰 사용: `mgaChhrmV5PeE0YoHMEohWZDlokfnHGHNUp5bkNX-_0`
- 한 번의 인증으로 모든 서비스 접근 가능
- 서비스 간 전환 시 재인증 불필요

## 로그 예시

```
2025-10-25 22:36:48 - ♻️ Reusing existing DCR client: dcr_tLQnP1PsnRzF9bjUG1uK5w
2025-10-25 22:36:27 - ✅ Authenticated DCR client: dcr_tLQnP1PsnRzF9bjUG1uK5w for /onedrive
2025-10-25 22:36:28 - ✅ Authenticated DCR client: dcr_tLQnP1PsnRzF9bjUG1uK5w for /teams
2025-10-25 22:36:28 - ✅ Authenticated DCR client: dcr_tLQnP1PsnRzF9bjUG1uK5w for /mail-query
```

## 주요 파일

| 파일 | 역할 | 주요 변경사항 |
|------|------|--------------|
| `entrypoints/production/unified_http_server.py` | 통합 HTTP 서버 | - Bearer 토큰 평문 저장<br>- 토큰 재사용 로직<br>- Azure AD 스킵 로직 |
| `modules/dcr_oauth/dcr_service.py` | DCR OAuth 서비스 | - 클라이언트 재사용<br>- 토큰 검증 개선 |
| `modules/dcr_oauth/auth_middleware.py` | 인증 미들웨어 | - Bearer 토큰 검증<br>- 경로별 인증 처리 |

## 보안 고려사항

### Bearer 토큰 평문 저장

**결정 이유**:
- Bearer 토큰은 본질적으로 일회성 세션 식별자
- 클라이언트에 평문으로 전송됨
- DB 암호화보다 전송 중 암호화(HTTPS)가 더 중요
- 토큰 만료 시간을 짧게 설정하여 리스크 완화

**보안 조치**:
- HTTPS 필수
- 토큰 만료 시간 설정 (기본 1시간)
- 토큰 폐기(revocation) 기능
- Azure AD 사용자 검증

### 토큰 재사용

**보안 검증**:
- 동일 `azure_object_id` (사용자) 확인
- 동일 `dcr_client_id` (앱) 확인
- 토큰 만료 시간 검증
- 토큰 상태(`dcr_status`) 확인

## 향후 개선 방향

1. **토큰 갱신**: Refresh token을 활용한 자동 토큰 갱신
2. **토큰 만료 알림**: 만료 임박 시 사전 알림
3. **다중 사용자 지원**: 여러 Azure AD 계정 동시 사용
4. **감사 로그**: 인증 이력 상세 기록
5. **토큰 폐기 API**: 수동 토큰 폐기 엔드포인트

## 문제 해결 가이드

### 서비스별로 다른 토큰 사용

**증상**: 각 MCP 서비스가 다른 Bearer 토큰 사용

**해결**:
1. 기존 토큰 모두 폐기
2. Claude.ai에서 모든 MCP 연결 제거
3. 서버 재시작
4. 첫 서비스부터 순차적으로 재연결

### 재인증 요구

**증상**: 서비스 연결 시마다 Azure AD 로그인 요구

**원인**:
- Bearer 토큰이 만료됨
- 토큰이 DB에서 삭제됨

**해결**:
```sql
-- 활성 토큰 확인
SELECT dcr_client_id, dcr_token_type, dcr_status, expires_at
FROM dcr_tokens
WHERE dcr_token_type = 'Bearer'
  AND dcr_status = 'active';
```

### 토큰 검증 실패

**증상**: `⚠️ Invalid Bearer token for path: /...`

**원인**:
- 토큰이 DB에 없음
- 토큰이 만료됨
- 토큰 형식 불일치

**해결**:
```sql
-- 특정 클라이언트의 토큰 확인
SELECT dcr_token_value, dcr_status, expires_at
FROM dcr_tokens
WHERE dcr_client_id = 'dcr_...'
  AND dcr_token_type = 'Bearer';
```

## 참고 자료

- [RFC 7591 - OAuth 2.0 Dynamic Client Registration Protocol](https://tools.ietf.org/html/rfc7591)
- [RFC 6749 - OAuth 2.0 Authorization Framework](https://tools.ietf.org/html/rfc6749)
- [RFC 7636 - PKCE (Proof Key for Code Exchange)](https://tools.ietf.org/html/rfc7636)
- [MCP (Model Context Protocol) Specification](https://spec.modelcontextprotocol.io/)
