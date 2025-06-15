# Account 모듈

## 1. 개요

IACSGraph 프로젝트의 계정 관리를 담당하는 핵심 모듈입니다. `enrollment` 디렉터리의 YAML 파일을 기반으로 데이터베이스의 계정 정보를 동기화하고, 계정의 생명주기와 OAuth 인증 정보를 관리합니다.

## 2. 주요 기능

- **계정 동기화**: `enrollment/*.yaml` 파일을 스캔하여 데이터베이스와 계정 정보를 일치시킵니다.
  - 신규 파일 -> 계정 생성
  - 파일 변경 -> 계정 업데이트
  - 파일 삭제 -> 계정 비활성화 (구현 예정)
- **계정 관리**: 계정의 생성, 조회, 업데이트, 상태 변경(활성화/비활성화) 기능을 제공합니다.
- **보안**: Fernet을 사용하여 OAuth 클라이언트 시크릿, 토큰 등 민감한 정보를 안전하게 암호화하여 저장합니다.
- **감사 로그**: 모든 계정 변경 사항에 대한 감사 로그를 기록하여 추적성을 보장합니다.

## 3. 아키텍처

- **`account_orchestrator.py`**: 모듈의 비즈니스 로직을 총괄하는 오케스트레이터. API의 진입점 역할을 합니다.
- **`account_sync_service.py`**: 파일 시스템과 상호작용하며 동기화 작업을 수행하는 서비스.
- **`account_repository.py`**: 데이터베이스와의 모든 CRUD 작업을 담당하는 데이터 액세스 레이어.
- **`account_schema.py`**: Pydantic을 사용한 데이터 유효성 검증 및 모델 정의.
- **`_account_helpers.py`**: 암호화, 파일 처리 등 공통 유틸리티 함수 모음.

## 4. 사용법

### 4.1 오케스트레이터 가져오기
```python
from modules.account import get_account_orchestrator

orchestrator = get_account_orchestrator()
```

### 4.2 전체 계정 동기화
```python
# 모든 enrollment 파일을 스캔하여 DB와 동기화
sync_result = orchestrator.account_sync_all_enrollments()

print(f"총 {sync_result.total_files}개 파일 처리 완료.")
print(f"생성: {sync_result.created_accounts}, 업데이트: {sync_result.updated_accounts}")
```

### 4.3 계정 조회
```python
user_id = "kimghw"
account = orchestrator.account_get_by_user_id(user_id)

if account:
    print(f"계정명: {account.user_name}")
    print(f"상태: {account.status}")
```

### 4.4 계정 활성화
```python
user_id = "kimghw"
success = orchestrator.account_activate(user_id)

if success:
    print(f"{user_id} 계정이 활성화되었습니다.")
```

## 5. 데이터 모델 (`accounts` 테이블)

| 필드명                  | 타입      | 설명                               |
| ----------------------- | --------- | ---------------------------------- |
| `id`                    | `INTEGER` | PK, Auto-increment                 |
| `user_id`               | `TEXT`    | 사용자 ID (UNIQUE)                 |
| `user_name`             | `TEXT`    | 사용자 이름                        |
| `email`                 | `TEXT`    | 이메일 (UNIQUE)                    |
| `status`                | `TEXT`    | 계정 상태 (ACTIVE, INACTIVE 등)    |
| `is_active`             | `BOOLEAN` | 활성화 여부                        |
| `enrollment_file_path`  | `TEXT`    | 원본 enrollment 파일 경로          |
| `enrollment_file_hash`  | `TEXT`    | 파일 내용 해시 (변경 감지용)       |
| `oauth_client_id`       | `TEXT`    | OAuth 클라이언트 ID                |
| `oauth_client_secret`   | `TEXT`    | **암호화된** 클라이언트 시크릿     |
| `oauth_tenant_id`       | `TEXT`    | OAuth 테넌트 ID                    |
| `access_token`          | `TEXT`    | **암호화된** 액세스 토큰           |
| `refresh_token`         | `TEXT`    | **암호화된** 리프레시 토큰         |
| `token_expiry`          | `TIMESTAMP`| 토큰 만료 시간                     |
| `created_at`            | `TIMESTAMP`| 생성 시간                          |
| `updated_at`            | `TIMESTAMP`| 마지막 수정 시간                   |

## 6. 외부 의존성

- `infra.core`: 데이터베이스, 로거, 설정 등 공통 인프라
- `cryptography`: 데이터 암호화를 위한 Fernet
- `PyYAML`: `enrollment` 파일 파싱

이 문서는 Account 모듈의 현재 구현 상태를 반영합니다.
