# Account 모듈

IACSGraph 프로젝트의 계정 관리를 담당하는 핵심 모듈입니다. `enrollment` 디렉토리의 YAML 파일을 기반으로 데이터베이스의 계정 정보를 동기화하고, 계정의 생명주기와 OAuth 인증 정보를 관리합니다.

## 🔄 데이터 파이프라인 구조

```
enrollment/*.yaml 파일
        ↓
AccountSyncService (파일 스캔 및 파싱)
        ↓
AccountOrchestrator (비즈니스 로직 조정)
        ↓
AccountRepository (데이터 영속화)
        ↓
    ┌─────────────────┬────────────────────┐
    ↓                 ↓                    ↓
accounts 테이블    account_audit_logs    토큰 암호화 저장
```

### 동작 방식
1. **파일 감지**: `enrollment` 디렉토리의 YAML 파일 변경 감지
2. **해시 비교**: 파일 내용의 SHA256 해시로 변경 여부 확인
3. **동기화 처리**: 
   - 신규 파일 → 계정 생성
   - 변경된 파일 → 계정 업데이트
   - 삭제된 파일 → (현재 미구현, 수동 비활성화 필요)
4. **암호화 저장**: OAuth 클라이언트 시크릿과 토큰은 Fernet 암호화
5. **감사 로그**: 모든 변경사항을 `account_audit_logs` 테이블에 기록

## 📋 모듈 설정 파일 관리

### Enrollment 파일 형식 (`enrollment/user@company.com.yaml`)
```yaml
# 계정 기본 정보
account:
  email: user@company.com
  name: 사용자명

# Microsoft Graph API 설정
microsoft_graph:
  client_id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  client_secret: YOUR_CLIENT_SECRET_HERE
  tenant_id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# OAuth 설정
oauth:
  redirect_uri: http://localhost:5000/auth/callback
  auth_type: "Authorization Code Flow"
  delegated_permissions:
    - Mail.ReadWrite
    - Mail.Send
    - offline_access
    - User.Read
```

### 환경 변수 설정 (`.env`)
```env
# 암호화 키 (필수)
ENCRYPTION_KEY=YOUR_FERNET_ENCRYPTION_KEY_HERE

# Enrollment 디렉토리 경로
ENROLLMENT_DIRECTORY=./enrollment

# 계정 동기화 설정
ACCOUNT_SYNC_INTERVAL=300  # 5분 (초 단위)
ACCOUNT_AUTO_ACTIVATE=true
```

## 🚀 모듈별 사용 방법 및 예시

### 1. 기본 사용법
```python
from modules.account import get_account_orchestrator

# 오케스트레이터 인스턴스 가져오기
orchestrator = get_account_orchestrator()
```

### 2. 전체 계정 동기화
```python
# enrollment 디렉토리의 모든 파일 동기화
result = orchestrator.account_sync_all_enrollments()

print(f"처리 결과:")
print(f"- 총 파일: {result.total_files}개")
print(f"- 생성: {result.created_accounts}개")
print(f"- 업데이트: {result.updated_accounts}개")
print(f"- 오류: {len(result.errors)}개")
```

### 3. 개별 계정 관리
```python
# 계정 조회
account = orchestrator.account_get_by_user_id("kimghw")
if account:
    print(f"계정: {account.user_name} ({account.email})")
    print(f"상태: {account.status}")
    print(f"토큰 유효: {account.has_valid_token}")

# 계정 활성화/비활성화
orchestrator.account_activate("kimghw")    # 활성화
orchestrator.account_deactivate("kimghw")  # 비활성화
```

### 4. 토큰 정보 업데이트
```python
from modules.account import TokenInfo
from datetime import datetime, timedelta

# Auth 모듈에서 받은 토큰 정보 저장
token_info = TokenInfo(
    access_token="새로운_액세스_토큰",
    refresh_token="새로운_리프레시_토큰",
    token_expiry=datetime.utcnow() + timedelta(hours=1)
)

success = orchestrator.account_update_token_info("kimghw", token_info)
```

### 5. Enrollment 파일 검증
```python
# 파일 업로드 전 유효성 검사
validation_result = orchestrator.account_validate_enrollment_file(
    "enrollment/newuser@company.com.yaml"
)

if validation_result['valid']:
    print("✅ 파일이 유효합니다")
else:
    print("❌ 오류:", validation_result['errors'])
```

## 📊 데이터베이스 스키마

### accounts 테이블
| 필드명 | 설명 | 특징 |
|--------|------|------|
| `id` | 기본 키 | AUTO_INCREMENT |
| `user_id` | 사용자 ID | UNIQUE, enrollment 파일명 기반 |
| `email` | 이메일 주소 | UNIQUE |
| `oauth_client_secret` | 클라이언트 시크릿 | **암호화됨** |
| `access_token` | 액세스 토큰 | **암호화됨** |
| `refresh_token` | 리프레시 토큰 | **암호화됨** |
| `status` | 계정 상태 | ACTIVE/INACTIVE/LOCKED/REAUTH_REQUIRED |
| `enrollment_file_hash` | 파일 해시 | 변경 감지용 |

### account_audit_logs 테이블
모든 계정 변경사항이 자동으로 기록됩니다:
- 계정 생성/수정/삭제
- 상태 변경
- 토큰 업데이트
- 민감 정보는 자동 마스킹

## 🔐 보안 고려사항

1. **암호화**: 모든 OAuth 시크릿과 토큰은 Fernet 암호화
2. **감사 로그**: 민감 정보는 `***REDACTED***`로 마스킹
3. **권한 분리**: enrollment 파일은 관리자만 접근 가능하도록 설정
4. **해시 검증**: 파일 무결성을 SHA256 해시로 확인

## ⚠️ 주의사항

1. **Enrollment 파일명**: 반드시 `user_id.yaml` 형식 준수
2. **YAML 형식**: 들여쓰기와 구조를 정확히 유지
3. **클라이언트 시크릿**: Azure Portal에서 복사 시 공백 제거
4. **파일 삭제**: 계정은 자동 삭제되지 않음 (수동 비활성화 필요)

## 🔗 다른 모듈과의 연계

- **Auth 모듈**: 계정별 OAuth 설정을 읽어 인증 수행
- **Mail Processor**: 활성 계정 목록 조회
- **Token Service**: 토큰 저장 시 계정 정보 업데이트