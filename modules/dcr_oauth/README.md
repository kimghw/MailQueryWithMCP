# DCR OAuth Module

Dynamic Client Registration (DCR) OAuth 2.0 모듈

## 개요

이 모듈은 RFC 7591 (Dynamic Client Registration)과 RFC 6749 (OAuth 2.0)를 구현하여 Claude Custom Connector와의 통합을 지원합니다.

## 주요 기능

- **Dynamic Client Registration (RFC 7591)**
  - 런타임에 OAuth 클라이언트 동적 등록
  - Client ID/Secret 자동 발급
  - Redirect URI 화이트리스트 관리

- **OAuth 2.0 Authorization Server (RFC 6749)**
  - Authorization Code Flow
  - Bearer Token 인증 (RFC 6750)
  - Token 발급 및 검증

- **Azure AD 통합**
  - Azure AD를 Identity Provider로 사용
  - DCR 토큰과 Azure 토큰 매핑
  - Graph API 호출 지원

## 파일 구조

```
modules/dcr_oauth/
├── __init__.py          # 모듈 초기화 및 export
├── dcr_service.py       # DCR 서비스 구현
└── README.md           # 이 문서
```

## 사용법

### Import

```python
from modules.dcr_oauth import DCRService

dcr_service = DCRService()
```

### 클라이언트 등록

```python
# DCR 클라이언트 등록
response = await dcr_service.register_client({
    "client_name": "Claude Connector",
    "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"]
})

client_id = response["client_id"]        # dcr_xxx...
client_secret = response["client_secret"] # yyy...
```

### Authorization Code 생성

```python
# Authorization code 생성 (10분 유효)
auth_code = dcr_service.create_authorization_code(
    client_id=client_id,
    redirect_uri=redirect_uri,
    scope="Mail.Read User.Read",
    state=state
)
```

### Bearer 토큰 검증

```python
# Bearer 토큰 검증 및 Azure 토큰 조회
token_data = dcr_service.verify_bearer_token(bearer_token)
if token_data:
    azure_token = token_data["azure_access_token"]
    # Azure Graph API 호출에 azure_token 사용
```

## 데이터베이스 스키마

### dcr_clients
- DCR로 등록된 클라이언트 정보 저장
- Azure AD 앱 정보와 매핑

### dcr_tokens
- 발급된 액세스 토큰 저장
- DCR 토큰과 Azure 토큰 매핑

### dcr_auth_codes
- Authorization code 저장 (일회용, 10분 만료)
- Azure AD 콜백 후 토큰 저장

## 환경변수

```bash
# Azure AD 설정 (필수)
AZURE_CLIENT_ID=your_azure_client_id
AZURE_CLIENT_SECRET=your_azure_client_secret
AZURE_TENANT_ID=your_tenant_id_or_common
```

## 표준 준수

- ✅ RFC 7591 - OAuth 2.0 Dynamic Client Registration
- ✅ RFC 6749 - The OAuth 2.0 Authorization Framework
- ✅ RFC 6750 - OAuth 2.0 Bearer Token Usage
- ✅ RFC 8414 - OAuth 2.0 Authorization Server Metadata

## 관련 문서

- [/docs/CLAUDE_MCP_FLOW_DIAGRAM.md](../../docs/CLAUDE_MCP_FLOW_DIAGRAM.md) - OAuth 플로우 다이어그램
- [/docs/DCR_IMPLEMENTATION.md](../../docs/DCR_IMPLEMENTATION.md) - DCR 구현 상세