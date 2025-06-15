# Auth 모듈 - OAuth 2.0 인증 플로우 관리

Auth 모듈은 OAuth 2.0 인증 플로우를 조정하고 메모리 세션을 관리하는 경량화된 모듈입니다. 기존 infra 서비스들을 최대 활용하여 OAuth 플로우 관리에만 특화됩니다.

## 🚀 주요 기능

- **OAuth 플로우 조정**: 인증 URL 생성 → 콜백 처리 → 토큰 교환
- **메모리 세션 관리**: 임시 OAuth 세션 저장 (DB 저장 없음)
- **일괄 인증 처리**: 여러 계정의 순차적 인증 조정
- **infra 서비스 연동**: 기존 token_service, oauth_client, database 활용

## 📁 모듈 구조

```
modules/auth/
├── __init__.py                 # 모듈 초기화 및 export
├── auth_orchestrator.py        # OAuth 플로우 조정 (메인 API)
├── auth_web_server.py         # OAuth 콜백 처리 웹서버
├── auth_schema.py             # OAuth 관련 Pydantic 모델
├── _auth_helpers.py           # OAuth 전용 유틸리티
└── references/
    └── graphapi_delegated_auth.md  # Microsoft Graph API 인증 가이드
```

## 🔄 호출 스택 다이어그램

```
auth_orchestrator.py (OAuth 플로우 조정)
    ↓
auth_web_server.py          # OAuth 콜백 처리
_auth_helpers.py           # OAuth 전용 헬퍼
    ↓
infra.core.database        # accounts 테이블 직접 쿼리
infra.core.token_service   # 토큰 저장/갱신/상태확인
infra.core.oauth_client    # 토큰 교환
infra.core.config/logger   # 설정 및 로깅
```

## 📝 사용법

### 1. 단일 사용자 인증

```python
from modules.auth import get_auth_orchestrator, AuthStartRequest

auth_orchestrator = get_auth_orchestrator()

# 인증 시작
request = AuthStartRequest(user_id="user@example.com")
response = await auth_orchestrator.auth_orchestrator_start_authentication(request)

print(f"인증 URL: {response.auth_url}")
print(f"세션 ID: {response.session_id}")

# 사용자가 브라우저에서 인증 완료 후 상태 확인
status = await auth_orchestrator.auth_orchestrator_get_session_status(response.session_id)
print(f"인증 상태: {status.status}")
```

### 2. 일괄 인증

```python
from modules.auth import AuthBulkRequest

# 여러 사용자 일괄 인증
bulk_request = AuthBulkRequest(
    user_ids=["user1@example.com", "user2@example.com", "user3@example.com"],
    max_concurrent=3,
    timeout_minutes=15
)

bulk_response = await auth_orchestrator.auth_orchestrator_bulk_authentication(bulk_request)

for user_status in bulk_response.user_statuses:
    if user_status.status == AuthState.PENDING:
        print(f"{user_status.user_id}: {user_status.auth_url}")
    elif user_status.status == AuthState.COMPLETED:
        print(f"{user_status.user_id}: 이미 인증됨")
```

### 3. 세션 정리

```python
from modules.auth import AuthCleanupRequest

# 만료된 세션 정리
cleanup_request = AuthCleanupRequest(
    expire_threshold_minutes=60,
    force_cleanup=False
)

cleanup_response = await auth_orchestrator.auth_orchestrator_cleanup_sessions(cleanup_request)
print(f"정리된 세션: {cleanup_response.cleaned_sessions}개")
```

### 4. 전체 계정 상태 조회

```python
# 모든 계정의 인증 상태 조회
accounts = await auth_orchestrator.auth_orchestrator_get_all_accounts_status()

for account in accounts:
    print(f"{account['user_id']}: {account['status']} "
          f"(토큰만료: {account['token_expired']})")
```

## 🔧 주요 컴포넌트

### AuthOrchestrator
- OAuth 플로우의 메인 조정자
- 메모리 세션 관리
- infra 서비스들과의 연동

### AuthWebServer
- OAuth 콜백 처리 전용 웹서버
- 임시로 실행되며 인증 완료 후 종료 가능
- 성공/실패 페이지 제공

### AuthSession
- 메모리 기반 OAuth 세션
- CSRF 방지용 state 토큰 관리
- 세션 만료 시간 관리

## 🛡️ 보안 고려사항

- **CSRF 방지**: 각 세션마다 고유한 state 토큰 생성
- **세션 만료**: 기본 10분 후 자동 만료
- **민감 데이터 마스킹**: 로그에서 토큰 정보 마스킹
- **콜백 URL 검증**: 예상 리다이렉트 URI와 일치 확인

## 📊 데이터 흐름

1. **인증 시작**: 사용자 ID → 세션 생성 → 인증 URL 반환
2. **사용자 인증**: 브라우저에서 Azure AD 인증
3. **콜백 처리**: 웹서버가 인증 코드 수신 → 토큰 교환
4. **토큰 저장**: infra.token_service를 통해 DB 저장
5. **세션 완료**: 메모리 세션 상태 업데이트

## ⚙️ 의존성

- `infra.core.token_service`: 토큰 저장/갱신/상태확인
- `infra.core.oauth_client`: OAuth 클라이언트 (토큰 교환)
- `infra.core.database`: DB 연결 관리 및 직접 쿼리
- `infra.core.logger`: 전역 로깅 시스템
- `infra.core.config`: 환경 변수 관리

## 🚨 제한사항

- **메모리 세션**: 서버 재시작 시 세션 정보 소실
- **단일 서버**: 멀티 서버 환경에서는 세션 공유 불가
- **웹서버 포트**: 기본 8080 포트 사용 (설정 가능)
- **동시 인증**: 사용자당 하나의 진행 중인 세션만 허용

## 🔄 상태 관리

### AuthState 열거형
- `PENDING`: 사용자 인증 대기 중
- `CALLBACK_RECEIVED`: 콜백 수신됨, 토큰 교환 중
- `COMPLETED`: 인증 완료
- `FAILED`: 인증 실패
- `EXPIRED`: 세션 만료

## 📈 모니터링

모든 세션 활동은 로그로 기록됩니다:
- 세션 생성/만료
- 콜백 처리
- 토큰 교환 성공/실패
- 오류 발생

로그 예시:
```
INFO - 세션 활동 [auth_20241215...]: authentication_started
INFO - 세션 활동 [auth_20241215...]: callback_received
INFO - 세션 활동 [auth_20241215...]: authentication_completed
```

## 🧪 테스트

테스트는 `/test/scenario/`에 정의된 시나리오에 따라 수행됩니다:
- 단일 사용자 인증 플로우
- 일괄 인증 처리
- 오류 처리 및 복구
- 세션 만료 및 정리
