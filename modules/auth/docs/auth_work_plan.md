# Auth 모듈 구현 현황 및 작업 계획서 (As-Is)

## 📋 전체 개요

Auth 모듈은 **infra 서비스 최대 활용**을 통해 OAuth 2.0 인증 플로우 조정에만 집중하는 경량화된 모듈입니다. 이 문서는 현재 구현 상태를 반영한 명세서입니다.

### 🎯 핵심 목표
- **[x] OAuth 플로우 조정만**: 인증 URL 생성, 콜백 처리, 세션 관리
- **[x] infra 서비스 활용**: `token_service`, `database`, `oauth_client` 직접 사용
- **[x] Repository 레이어 제거**: `infra.core.database` 직접 사용
- **[x] 토큰 관리 제거**: `infra.core.token_service` 완전 활용

---

## ✅ 구현 완료된 기능

### Phase 1: 기본 OAuth 플로우
- **[x] 기본 스키마 구현 (`auth_schema.py`)**:
  - `AuthState` Enum, `AuthSession`, `AuthCallback`, `TokenData` 등 인증 플로우에 필요한 모든 Pydantic 모델이 정의되었습니다.
  - `AuthStartRequest/Response`, `AuthBulkRequest/Response` 등 API 계약 모델이 구현되었습니다.

- **[x] OAuth 헬퍼 구현 (`_auth_helpers.py`)**:
  - `auth_generate_session_id`, `auth_generate_state_token` 등 세션 및 상태 관리를 위한 유틸리티 함수가 구현되었습니다.
  - `auth_generate_callback_success_html`, `auth_generate_callback_error_html` 등 콜백 응답 페이지 생성을 위한 함수가 포함되었습니다.

- **[x] OAuth 콜백 웹서버 구현 (`auth_web_server.py`)**:
  - `AuthWebServerManager`를 통해 웹서버의 생명주기를 관리합니다.
  - `AuthOrchestrator`에 의해 내부적으로 제어되며, 콜백 수신 시 토큰 교환 및 저장을 처리합니다.

- **[x] 오케스트레이터 구현 (`auth_orchestrator.py`)**:
  - `get_auth_orchestrator`를 통해 싱글턴 인스턴스를 제공합니다.
  - `infra` 서비스(`database`, `token_service`, `oauth_client`)를 직접 사용하여 핵심 로직을 수행합니다.
  - 메모리 기반(`dict`)으로 임시 세션을 생성, 조회, 정리합니다.

- **[x] 토큰 교환 및 저장 구현**:
  - `auth_web_server`가 콜백을 받으면 `oauth_client`를 통해 토큰을 교환합니다.
  - 획득한 토큰은 `token_service`를 통해 데이터베이스에 저장됩니다.

### Phase 2: 토큰 및 계정 관리
- **[x] 토큰 상태 확인 연동**:
  - `auth_orchestrator_get_all_accounts_status`를 통해 모든 계정의 토큰 상태(만료 여부 포함)를 조회할 수 있습니다.
  - `infra.token_service`의 `check_authentication_status`를 활용하여 일괄 인증 시 개별 계정의 상태를 확인합니다.

- **[x] 일괄 인증 기능 구현**:
  - `auth_orchestrator_bulk_authentication`을 통해 여러 계정의 인증을 한 번에 시작할 수 있습니다.
  - 이미 유효한 토큰을 가진 계정은 건너뛰고, 인증이 필요한 계정에 대해서만 인증 URL을 생성합니다.

- **[x] 에러 처리 고도화**:
  - OAuth 콜백 에러, 토큰 교환 실패, 세션 만료 등 주요 실패 시나리오에 대한 처리 로직이 구현되었습니다.
  - 실패 시 세션 상태는 `FAILED` 또는 `EXPIRED`로 업데이트되고 관련 정보가 로깅됩니다.

### Phase 3: 보안 및 세션 관리
- **[x] State 검증 강화**:
  - CSRF 공격 방지를 위해 `state` 파라미터를 생성하고 콜백 시 검증하는 로직이 구현되었습니다.

- **[x] 세션 관리 최적화**:
  - 모든 세션은 타임아웃을 가지며, `is_expired()` 메서드를 통해 만료 여부를 확인할 수 있습니다.
  - `auth_orchestrator_cleanup_sessions`를 통해 만료된 세션을 수동으로 정리할 수 있습니다.

---

## 🚀 향후 개선 및 확장 계획

### Phase 4: 보안 강화 (선택)
- **[ ] PKCE(Proof Key for Code Exchange) 구현**:
  - 현재는 `state` 파라미터로 CSRF를 방지하고 있으나, 모바일 앱 등 public 클라이언트와의 연동을 고려할 경우 PKCE를 도입하여 보안을 한층 더 강화할 수 있습니다.

### Phase 5: 운영 기능 (선택)
- **[ ] 고급 모니터링 및 관리 기능**:
  - 인증 성공/실패율, 평균 인증 소요 시간 등 통계 지표를 수집하는 기능.
  - 관리자가 특정 세션을 강제로 만료시키거나 조회하는 등의 관리 기능.

---

## 🧪 테스트 현황

- **[x] 시나리오 기반 테스트**:
  - `/test/scenario/`에 정의된 시나리오에 따라 주요 기능(단일/일괄 인증, 상태 조회)에 대한 테스트가 수행됩니다.
  - 단위 테스트보다는 실제 사용 사례에 가까운 통합 테스트 중심으로 검증이 이루어집니다.
