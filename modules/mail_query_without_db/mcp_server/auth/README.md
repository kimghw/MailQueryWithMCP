# MCP Server Authentication

MCP 서버 접근 제어를 위한 인증 모듈입니다.

## 인증 방법

### 1. API Key 인증 (api_key_auth.py)

가장 간단한 인증 방식입니다.

**설정:**
```bash
API_KEYS=key1,key2,key3
```

**사용:**
```bash
# 헤더 방식
curl -H "X-API-Key: key1" https://your-server.com/

# 쿼리 파라미터 방식
curl https://your-server.com/?api_key=key1
```

---

### 2. JWT Bearer Token (jwt_auth.py)

JWT 토큰 기반 인증입니다. 토큰에 만료시간과 사용자 정보를 포함합니다.

**설정:**
```bash
JWT_SECRET=your-super-secret-key-minimum-32-characters
```

**토큰 생성:**
```bash
python -m modules.mail_query_without_db.mcp_server.auth.jwt_auth user123
```

**사용:**
```bash
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." https://your-server.com/
```

---

### 3. OAuth 2.0 (oauth2_auth.py)

외부 OAuth Provider를 사용한 인증입니다.

**지원 Provider:**
- Auth0
- Clerk
- Supabase
- Google Identity Platform
- 기타 OAuth 2.0 호환 서비스

**설정 (Auth0 예시):**
```bash
OAUTH_ISSUER=https://your-tenant.auth0.com/
OAUTH_AUDIENCE=https://mail-query-api
```

**필요 패키지:**
```bash
pip install python-jose[cryptography] requests
```

**사용:**
1. OAuth Provider에서 토큰 발급
2. API 호출 시 Bearer token으로 전달

```bash
curl -H "Authorization: Bearer <oauth-token>" https://your-server.com/
```

---

## 서버에 인증 적용

`server.py`에서 원하는 인증 방식을 선택:

```python
# API Key (현재 기본값)
from .auth import AuthMiddleware
self.auth = AuthMiddleware()

# JWT
from .auth import JWTAuth
self.auth = JWTAuth()

# OAuth 2.0
from .auth import OAuth2Auth
self.auth = OAuth2Auth()
```

---

## 인증 비활성화

개발 환경에서 인증을 비활성화하려면 환경변수를 설정하지 않으면 됩니다.

```bash
# 인증 비활성화 - 환경변수 없음
unset API_KEYS
unset JWT_SECRET
unset OAUTH_ISSUER
```
