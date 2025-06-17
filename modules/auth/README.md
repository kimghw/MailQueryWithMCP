# Auth 모듈

OAuth 2.0 인증 플로우를 조정하고 메모리 기반의 임시 세션을 관리하는 경량화된 모듈입니다. `infra` 서비스들을 최대한 활용하여 OAuth 플로우 관리에만 집중합니다.

## 🔄 데이터 파이프라인 구조

```
인증 요청 (user_id)
        ↓
AuthOrchestrator (세션 생성)
        ↓
    ┌───────────────────┐
    │  메모리 세션 저장  │ ← state 토큰으로 CSRF 방지
    └───────────────────┘
        ↓
OAuth 인증 URL 생성 (계정별 설정 사용)
        ↓
사용자 브라우저 → Azure AD
        ↓
OAuth 콜백 (code + state)
        ↓
AuthWebServer (콜백 수신)
        ↓
토큰 교환 (계정별 client_secret 사용)
        ↓
TokenService → accounts 테이블 업데이트
```

### 동작 방식
1. **세션 생성**: 각 인증 요청마다 고유 세션 ID와 state 토큰 생성
2. **계정별 OAuth**: Account 모듈의 enrollment 설정 사용
3. **콜백 처리**: 로컬 웹서버(포트 5000)에서 OAuth 콜백 수신
4. **CSRF 검증**: state 토큰으로 요청 유효성 확인
5. **토큰 저장**: 획득한 토큰은 TokenService를 통해 암호화 저장

## 📋 모듈 설정 파일 관리

### 환경 변수 설정 (`.env`)
```env
# OAuth 콜백 서버 설정
OAUTH_CALLBACK_PORT=5000
OAUTH_CALLBACK_HOST=localhost

# 세션 설정
AUTH_SESSION_TIMEOUT_MINUTES=10
AUTH_MAX_CONCURRENT_SESSIONS=100

# 재시도 설정
AUTH_TOKEN_EXCHANGE_RETRIES=3
AUTH_TOKEN_EXCHANGE_TIMEOUT=30
```

### 계정별 OAuth 설정 (Account 모듈의 enrollment 파일 활용)
```yaml
# enrollment/user@company.com.yaml
oauth:
  redirect_uri: http://localhost:5000/auth/callback
  auth_type: "Authorization Code Flow"
  delegated_permissions:
    - Mail.ReadWrite
    - Mail.Send
    - offline_access
```

## 🚀 모듈별 사용 방법 및 예시

### 1. 단일 사용자 인증
```python
from modules.auth import get_auth_orchestrator, AuthStartRequest
import asyncio

async def authenticate_user():
    orchestrator = get_auth_orchestrator()
    
    # 인증 시작
    request = AuthStartRequest(user_id="kimghw")
    response = await orchestrator.auth_orchestrator_start_authentication(request)
    
    print(f"인증 URL: {response.auth_url}")
    print(f"세션 ID: {response.session_id}")
    print(f"만료 시간: {response.expires_at}")
    
    # 사용자를 브라우저로 리다이렉트
    # webbrowser.open(response.auth_url)
    
    # 상태 확인 (폴링)
    while True:
        status = await orchestrator.auth_orchestrator_get_session_status(
            response.session_id
        )
        print(f"상태: {status.status} - {status.message}")
        
        if status.is_completed:
            print("✅ 인증 완료!")
            break
        elif status.status in ["FAILED", "EXPIRED"]:
            print(f"❌ 인증 실패: {status.error_message}")
            break
            
        await asyncio.sleep(2)  # 2초마다 확인

# 실행
asyncio.run(authenticate_user())
```

### 2. 일괄 인증
```python
from modules.auth import AuthBulkRequest

async def bulk_authenticate():
    orchestrator = get_auth_orchestrator()
    
    # 여러 사용자 일괄 인증
    request = AuthBulkRequest(
        user_ids=["kimghw", "leehs", "parkjy"],
        max_concurrent=3,
        timeout_minutes=15
    )
    
    response = await orchestrator.auth_orchestrator_bulk_authentication(request)
    
    print(f"총 {response.total_users}명 처리")
    print(f"- 인증 대기: {response.pending_count}명")
    print(f"- 완료: {response.completed_count}명")
    print(f"- 실패: {response.failed_count}명")
    
    # 인증이 필요한 사용자들의 URL 출력
    for status in response.user_statuses:
        if status.auth_url:
            print(f"\n{status.user_id}: {status.auth_url}")
```

### 3. 모든 계정 상태 조회
```python
async def check_all_accounts():
    orchestrator = get_auth_orchestrator()
    
    accounts = await orchestrator.auth_orchestrator_get_all_accounts_status()
    
    for account in accounts:
        print(f"\n사용자: {account['user_id']}")
        print(f"- 토큰 만료: {account['token_expired']}")
        print(f"- 마지막 동기화: {account['last_sync_time']}")
        print(f"- 진행 중인 세션: {account['has_pending_session']}")
```

### 4. 세션 관리
```python
from modules.auth import AuthCleanupRequest

async def manage_sessions():
    orchestrator = get_auth_orchestrator()
    
    # 만료된 세션 정리
    cleanup_request = AuthCleanupRequest(
        expire_threshold_minutes=60,  # 60분 이상 된 세션
        force_cleanup=False
    )
    
    result = await orchestrator.auth_orchestrator_cleanup_sessions(cleanup_request)
    
    print(f"정리된 세션: {result.cleaned_sessions}개")
    print(f"활성 세션: {result.active_sessions}개")
```

## 🔐 보안 기능

### CSRF 보호
- 각 인증 요청마다 고유한 `state` 토큰 생성
- 콜백 시 state 검증으로 위조 요청 차단

### 세션 관리
```python
# 메모리 세션 구조
AuthSession {
    session_id: "auth_20250617143022_a1b2c3d4_e5f6g7h8"
    user_id: "kimghw"
    state: "랜덤한_32바이트_토큰"
    auth_url: "https://login.microsoftonline.com/..."
    status: "PENDING|CALLBACK_RECEIVED|COMPLETED|FAILED|EXPIRED"
    expires_at: "2025-06-17T14:40:22Z"  # 10분 후
}
```

## ⚠️ 주의사항

### 메모리 세션의 한계
1. **서버 재시작 시 소실**: 모든 진행 중인 세션이 사라집니다
2. **분산 환경 미지원**: 단일 서버에서만 동작
3. **세션 수 제한**: 메모리 사용량 고려 필요

### 포트 충돌
```bash
# 포트 5000이 사용 중인 경우
export OAUTH_CALLBACK_PORT=5001
```

### 인증 시간 제한
- 기본 세션 타임아웃: 10분
- 사용자가 10분 내에 인증을 완료해야 함

## 📊 인증 상태

| 상태 | 설명 | 다음 액션 |
|------|------|----------|
| `PENDING` | 사용자 인증 대기 중 | 브라우저에서 인증 진행 |
| `CALLBACK_RECEIVED` | 콜백 수신, 토큰 교환 중 | 자동 처리 |
| `COMPLETED` | 인증 완료 | 토큰 사용 가능 |
| `FAILED` | 인증 실패 | 오류 메시지 확인 |
| `EXPIRED` | 세션 만료 | 재인증 필요 |

## 🔗 다른 모듈과의 연계

### Account 모듈
- 계정별 OAuth 설정 (client_id, client_secret, scopes) 읽기
- 계정 상태 확인 (활성/비활성)

### Token Service
- 토큰 교환 후 자동 저장
- 토큰 유효성 검증

### Database
- accounts 테이블의 토큰 필드 업데이트
- 암호화된 상태로 저장

## 🚨 에러 처리

### 일반적인 오류와 해결 방법

1. **"계정별 OAuth 설정이 없습니다"**
   - Account 모듈에서 enrollment 파일 확인
   - 계정 동기화 실행

2. **"토큰 교환 실패: 401"**
   - Azure AD의 client_secret 확인
   - 리다이렉트 URI 일치 여부 확인

3. **"세션을 찾을 수 없습니다"**
   - 세션 만료 확인 (10분)
   - 서버 재시작 여부 확인

## 📈 성능 고려사항

- 동시 인증 세션: 기본 100개 제한
- 메모리 사용량: 세션당 약 1KB
- 콜백 처리 시간: 평균 200ms