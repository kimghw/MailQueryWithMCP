# OAuth Scope 환경변수 처리 수정 요약

## 발견된 문제점

### 1. 환경변수 미설정
- **render.yaml**에 `DCR_OAUTH_SCOPE` 환경변수가 정의되지 않음
- `AUTO_REGISTER_DELEGATED_PERMISSIONS` 환경변수가 정의되어 있지만 실제로 사용되지 않음

### 2. 하드코딩된 Scope 값들
여러 파일에서 delegated_permissions이 하드코딩되어 있었음:
- `modules/dcr_oauth/dcr_service.py:638`
- `infra/handlers/auth_handlers.py:222, 255`
- `modules/mail_query_MCP/mcp_server/tools/account.py:84, 117, 204-211`
- `scripts/sync_dcr_accounts.py:76`

### 3. OAuth 2.0 표준 미준수
- OAuth 2.0 표준에 따르면 scope는 **공백으로 구분**되어야 함
- 일부 코드에서 쉼표로 구분하고 있었음

## 수정 사항

### 1. 코드 수정
모든 하드코딩된 scope를 환경변수에서 읽어오도록 수정:

```python
# 이전 (하드코딩)
delegated_permissions = "Mail.ReadWrite,Mail.Send,offline_access"

# 수정 후 (환경변수 사용)
dcr_oauth_scope = os.getenv("DCR_OAUTH_SCOPE", "offline_access User.Read Mail.ReadWrite")
# OAuth 2.0 표준: 공백 구분
delegated_permissions = ",".join(dcr_oauth_scope.split())  # DB 저장용 쉼표 구분으로 변환
```

### 2. 수정된 파일 목록
1. `modules/dcr_oauth/dcr_service.py` - DCR 서비스에서 환경변수 사용
2. `infra/handlers/auth_handlers.py` - 인증 핸들러에서 환경변수 사용
3. `modules/mail_query_MCP/mcp_server/tools/account.py` - MCP 계정 도구에서 환경변수 사용
4. `scripts/sync_dcr_accounts.py` - 계정 동기화 스크립트에서 환경변수 사용
5. `render.yaml` - DCR_OAUTH_SCOPE 환경변수 추가

### 3. render.yaml 환경변수 추가
```yaml
- key: DCR_OAUTH_SCOPE
  value: "offline_access User.Read Mail.Read Mail.ReadWrite Mail.Send Files.Read Files.ReadWrite Calendars.Read Calendars.ReadWrite Notes.Read Notes.ReadWrite"
```

## OAuth 2.0 표준 준수

### Scope 형식
- **OAuth 2.0 표준**: 공백으로 구분 (예: `"offline_access User.Read Mail.ReadWrite"`)
- **DB 저장 형식**: 쉼표로 구분 (예: `"offline_access,User.Read,Mail.ReadWrite"`)
- **JSON 배열 형식**: accounts 테이블용 (예: `["offline_access", "User.Read", "Mail.ReadWrite"]`)

### 환경변수 처리 흐름
1. 환경변수에서 공백 구분 문자열로 읽기 (OAuth 2.0 표준)
2. `.split()`으로 리스트로 변환
3. 필요에 따라 다른 형식으로 변환:
   - Azure API 호출: 공백 구분 그대로 사용
   - DB 저장: 쉼표 구분으로 변환
   - JSON 배열: `'["' + '", "'.join(scopes) + '"]'`

## 테스트 결과

`test_scope_reading.py` 실행 결과:
- ✅ 환경변수에서 scope 정상 읽기
- ✅ OAuth 2.0 표준 형식 (공백 구분) 유지
- ✅ DB 저장용 형식 변환 정상
- ✅ JSON 배열 형식 변환 정상

## 주의사항

1. **환경변수 설정 필수**: 배포 시 반드시 `DCR_OAUTH_SCOPE` 환경변수를 설정해야 함
2. **기본값 확인**: 환경변수가 없을 때 기본값은 `"offline_access User.Read Mail.ReadWrite"`
3. **권한 추가**: 필요한 추가 권한이 있으면 환경변수에 공백으로 구분해서 추가

## 권장 DCR_OAUTH_SCOPE 설정

```
offline_access User.Read Mail.Read Mail.ReadWrite Mail.Send Files.Read Files.ReadWrite Calendars.Read Calendars.ReadWrite Notes.Read Notes.ReadWrite
```

### 각 권한 설명
- `offline_access`: Refresh token 사용 (필수)
- `User.Read`: 사용자 프로필 읽기
- `Mail.Read`, `Mail.ReadWrite`, `Mail.Send`: 메일 관련 권한
- `Files.Read`, `Files.ReadWrite`: OneDrive 파일 권한
- `Calendars.Read`, `Calendars.ReadWrite`: 캘린더 권한
- `Notes.Read`, `Notes.ReadWrite`: OneNote 권한