# Auth 모듈 구현 작업 계획서 (간소화)

## 📋 전체 개요

Auth 모듈을 **infra 서비스 최대 활용**으로 간소화하여 구현합니다. OAuth 2.0 인증 플로우 조정에만 집중하고, 나머지는 기존 infra 레이어를 활용합니다.

### 🎯 핵심 목표
- **OAuth 플로우 조정만**: 인증 URL 생성, 콜백 처리, 세션 관리
- **infra 서비스 활용**: `token_service`, `database`, `oauth_client` 직접 사용
- **Repository 레이어 제거**: infra.core.database 직접 사용
- **토큰 관리 제거**: infra.core.token_service 완전 활용

### 💡 간소화 내용
- ❌ `auth_repository.py` → `infra.core.database` 직접 사용
- ❌ 토큰 저장/갱신 로직 → `infra.core.token_service` 사용
- ❌ DB 연결 관리 → `infra.core.database` 사용
- ✅ OAuth 플로우 조정 로직만 구현
- ✅ 메모리 기반 임시 세션 관리
- ✅ 일괄 인증 기능

---

## 🎯 Phase 1: OAuth 플로우 구현 (8-12시간)

### Step 1.1: 기본 스키마 구현
**소요시간**: 1시간  
**우선순위**: 최고

#### 1.1.1 auth_schema.py 구현 (OAuth 모델만)
- [ ] **AuthStatus** Enum 정의 (PENDING, AUTHENTICATED, FAILED)
- [ ] **AuthFlowConfig** 인증 플로우 설정 모델
- [ ] **AuthStartResponse** 인증 시작 응답 모델
- [ ] **AuthCompleteResponse** 인증 완료 응답 모델
- [ ] **AuthCallbackData** OAuth 콜백 데이터 모델
- [ ] **PKCEData** PKCE 관련 데이터 모델

**검증 기준**:
```python
from modules.auth.auth_schema import AuthStatus, AuthFlowConfig
config = AuthFlowConfig(user_id="test")
assert config.user_id == "test"
```

### Step 1.2: OAuth 헬퍼 구현
**소요시간**: 2시간  
**우선순위**: 최고

#### 1.2.1 _auth_helpers.py 구현 (OAuth 전용만)
- [ ] **AuthStateGenerator** 클래스
  - [ ] `auth_generate_session_id()` - UUID 기반 세션 ID 생성
  - [ ] `auth_generate_state()` - CSRF 방지용 state 값 생성
  - [ ] `auth_generate_pkce_data()` - PKCE code_verifier/challenge 생성
- [ ] **AuthURLBuilder** 클래스
  - [ ] `auth_build_authorization_url()` - 인증 URL 구성
- [ ] **AuthValidationHelpers** 클래스
  - [ ] `auth_validate_state()` - State 값 검증
  - [ ] `auth_validate_callback_data()` - 콜백 데이터 검증

**검증 기준**:
```python
generator = AuthStateGenerator()
session_id = generator.auth_generate_session_id()
assert len(session_id) > 0
```

### Step 1.3: OAuth 콜백 웹서버 구현
**소요시간**: 3-4시간  
**우선순위**: 최고

#### 1.3.1 auth_web_server.py 구현
- [ ] **AuthWebServer** 클래스 기본 구조
- [ ] **서버 관리**:
  - [ ] `auth_start_server(port=None)` - 동적 포트 할당으로 서버 시작
  - [ ] `auth_stop_server()` - 서버 중지
  - [ ] `auth_is_server_running()` - 서버 상태 확인
- [ ] **콜백 처리**:
  - [ ] `auth_wait_for_callback(timeout)` - 콜백 대기 (블로킹)
  - [ ] `_handle_callback_request()` - HTTP 콜백 요청 처리
  - [ ] `_parse_callback_data()` - 콜백 데이터 파싱
- [ ] **응답 페이지**:
  - [ ] `_create_response_page()` - 성공/실패 응답 페이지 생성

**검증 기준**:
```python
server = AuthWebServer()
redirect_uri = server.auth_start_server()
assert redirect_uri.startswith("http://localhost:")
server.auth_stop_server()
```

### Step 1.4: 오케스트레이터 구현 (infra 연동)
**소요시간**: 2-3시간  
**우선순위**: 최고

#### 1.4.1 auth_orchestrator.py 구현 (infra 서비스 활용)
- [ ] **AuthOrchestrator** 클래스 기본 구조
- [ ] `__init__()` - infra 서비스 직접 연동:
  - [ ] `self.db = get_database_manager()` - DB 직접 사용
  - [ ] `self.token_service = get_token_service()` - 토큰 서비스 사용
  - [ ] `self.oauth_client = get_oauth_client()` - OAuth 클라이언트 사용
- [ ] **메모리 세션 관리**:
  - [ ] `_sessions` 딕셔너리 - 메모리 기반 세션 저장소
  - [ ] `_create_memory_session()` - 임시 세션 생성
  - [ ] `_cleanup_session()` - 세션 정리
- [ ] **기본 인증 플로우**:
  - [ ] `auth_start_authentication(user_id)` - 인증 시작
  - [ ] `auth_complete_authentication(session_id, timeout)` - 인증 완료 대기
  - [ ] `_build_authorization_url()` - 인증 URL 생성

**검증 기준**:
```python
orchestrator = AuthOrchestrator()
response = orchestrator.auth_start_authentication("kimghw")
assert response.auth_url.startswith("https://login.microsoftonline.com")
```

### Step 1.5: 토큰 교환 및 저장 구현
**소요시간**: 2-3시간  
**우선순위**: 최고

#### 1.5.1 토큰 교환 기능 구현 (infra 서비스 활용)
- [ ] `_process_oauth_callback()` - OAuth 콜백 처리 로직
- [ ] **infra.oauth_client 활용**:
  - [ ] `oauth_client.exchange_code_for_tokens()` 사용
- [ ] **infra.token_service 활용**:
  - [ ] `token_service.store_tokens()` 사용
- [ ] **에러 처리**:
  - [ ] `_handle_authentication_error()` - 인증 오류 처리

**검증 기준**:
```python
# 토큰 교환 로직 단위 테스트 (Mock 사용)
# infra 서비스들과의 연동 확인
```

---

## 🔧 Phase 2: 토큰 관리 구현 (필수)

### Step 2.1: 토큰 상태 확인 연동
**소요시간**: 2-3시간  
**우선순위**: 높음

#### 2.1.1 infra.token_service 연동
- [ ] `auth_check_accounts_token_status()` - 모든 계정 토큰 상태 확인
- [ ] infra.token_service의 `get_valid_access_token()` 활용
- [ ] 토큰 만료 및 갱신 상태 확인
- [ ] 계정별 인증 필요 여부 판단

**검증 기준**:
```python
# 토큰 상태 확인 기능 검증
status = orchestrator.auth_check_accounts_token_status()
assert isinstance(status, dict)
```

### Step 2.2: 일괄 인증 기능 구현
**소요시간**: 4-5시간  
**우선순위**: 높음

#### 2.2.1 일괄 인증 로직 구현
- [ ] `auth_authenticate_all_accounts()` - 모든 계정 일괄 인증
- [ ] 유효한 토큰이 있는 계정 건너뛰기 (`skip_valid_tokens` 옵션)
- [ ] 순차적 인증 처리 (동시 실행 방지)
- [ ] 진행 상황 로깅 및 결과 집계
- [ ] 개별 계정 인증 실패 시 계속 진행

**검증 기준**:
```python
# 일괄 인증 기능 검증
results = orchestrator.auth_authenticate_all_accounts(auto_open_browser=False)
assert isinstance(results, dict)
```

### Step 2.3: 에러 처리 고도화
**소요시간**: 2-3시간  
**우선순위**: 중간

#### 2.3.1 포괄적인 오류 처리
- [ ] OAuth 에러 코드별 처리 로직
- [ ] 네트워크 에러 복구 전략
- [ ] 토큰 만료 시 자동 재인증 유도
- [ ] 계정 상태 자동 업데이트
- [ ] 에러 로그 상세화

**검증 기준**:
```python
# 에러 처리 시나리오 테스트
# 잘못된 계정 정보로 인증 시도 시 적절한 에러 처리 확인
```

---

## 🔒 Phase 3: 보안 강화 (권장)

### Step 3.1: PKCE 구현
**소요시간**: 3-4시간  
**우선순위**: 중간

#### 3.1.1 PKCE 보안 강화
- [ ] code_verifier 생성 (43-128자 랜덤 문자열)
- [ ] code_challenge 생성 (SHA256 해시, base64url 인코딩)
- [ ] 인증 URL에 code_challenge 포함
- [ ] 토큰 교환 시 code_verifier 검증
- [ ] PKCE 플로우 테스트

**검증 기준**:
```python
# PKCE 데이터 생성 및 검증
pkce_data = generator.auth_generate_pkce_data()
assert len(pkce_data.code_verifier) >= 43
assert len(pkce_data.code_challenge) > 0
```

### Step 3.2: State 검증 강화
**소요시간**: 2시간  
**우선순위**: 중간

#### 3.2.1 CSRF 방지 강화
- [ ] 암호학적으로 안전한 state 생성
- [ ] 콜백 시 state 검증 로직 강화
- [ ] state 만료 시간 관리
- [ ] 재사용 방지 로직

### Step 3.3: 세션 관리 최적화
**소요시간**: 2-3시간  
**우선순위**: 낮음

#### 3.3.1 메모리 세션 최적화
- [ ] 세션 자동 만료 처리
- [ ] 메모리 사용량 최적화
- [ ] 동시 세션 제한
- [ ] 가비지 컬렉션 최적화

---

## 📊 Phase 4: 운영 기능 (선택)

### Step 4.1: 모니터링 기능
**소요시간**: 3-4시간  
**우선순위**: 낮음

#### 4.1.1 인증 상태 모니터링
- [ ] 계정별 인증 상태 대시보드
- [ ] 토큰 만료 예정 알림
- [ ] 인증 실패 통계
- [ ] 시스템 상태 모니터링

### Step 4.2: 분석 기능
**소요시간**: 2-3시간  
**우선순위**: 낮음

#### 4.2.1 인증 통계 및 로깅
- [ ] 인증 성공/실패 통계
- [ ] 성능 지표 수집
- [ ] 사용 패턴 분석
- [ ] 보고서 생성

---

## 🧪 테스트 계획

### 단위 테스트
- [ ] **auth_schema.py**: 모든 Pydantic 모델 검증
- [ ] **_auth_helpers.py**: 각 헬퍼 클래스 기능 테스트
- [ ] **auth_repository.py**: DB 조작 기능 테스트
- [ ] **auth_web_server.py**: 웹서버 시작/중지 테스트

### 통합 테스트
- [ ] **기본 인증 플로우**: 전체 OAuth 플로우 테스트
- [ ] **토큰 갱신**: infra.token_service 연동 테스트
- [ ] **일괄 인증**: 여러 계정 동시 처리 테스트
- [ ] **에러 시나리오**: 다양한 실패 상황 테스트

### 수동 테스트
- [ ] **실제 OAuth 인증**: Microsoft Graph API 실제 인증
- [ ] **브라우저 플로우**: 실제 브라우저를 통한 인증 테스트
- [ ] **토큰 갱신**: 실제 토큰 만료 및 갱신 테스트

---

## 📝 완료 체크리스트

### Phase 1 완료 기준
- [ ] 기본 인증 플로우가 정상 동작 (인증 URL 생성 → 콜백 처리 → 토큰 저장)
- [ ] 단일 계정 인증이 성공적으로 완료
- [ ] accounts 테이블에 토큰이 정상 저장
- [ ] 에러 상황에서 적절한 예외 처리

### Phase 2 완료 기준
- [ ] 토큰 상태 확인 기능 정상 동작
- [ ] 일괄 인증 기능으로 여러 계정 처리 가능
- [ ] infra.token_service와 정상 연동
- [ ] 포괄적인 에러 처리 완료

### 전체 완료 기준
- [ ] 모든 기능이 정상 동작
- [ ] 테스트 케이스 90% 이상 통과
- [ ] 성능 요구사항 만족
- [ ] 보안 요구사항 만족
- [ ] 문서화 완료

---

## ⚠️ 주의사항 및 리스크

### 기술적 리스크
1. **OAuth 플로우 복잡성**: Microsoft Graph API의 OAuth 구현 세부사항
2. **토큰 갱신 타이밍**: infra.token_service와의 동기화 이슈
3. **포트 충돌**: 동시 인증 시 웹서버 포트 충돌 방지
4. **메모리 누수**: 세션 정리되지 않을 경우 메모리 사용량 증가

### 의존성 리스크
1. **infra.token_service**: 기존 구현에 의존하는 부분
2. **accounts 테이블**: account 모듈과의 데이터 충돌 가능성
3. **외부 라이브러리**: requests, webbrowser 등 외부 의존성

### 완화 전략
1. **단계적 구현**: Phase별로 단계적 구현 및 검증
2. **충분한 테스트**: 각 단계별 완료 후 충분한 테스트
3. **에러 처리**: 모든 예외 상황에 대한 처리 로직 구현
4. **문서화**: 각 기능별 상세 문서화

---

이 작업 계획서를 통해 auth 모듈을 단계별로 구현하며, 각 단계의 완료 후 검증을 거쳐 안정적인 OAuth 인증 시스템을 구축할 수 있습니다.
