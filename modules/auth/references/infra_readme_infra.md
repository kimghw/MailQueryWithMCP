# Infra 모듈

## 1. 개요

IACSGraph 프로젝트의 모든 모듈이 공유하는 핵심 기반 서비스를 제공합니다. 설정 관리, 데이터베이스 연결, 로깅, 예외 처리 등 공통 기능을 중앙에서 관리하여 모듈 간의 일관성을 유지하고 중복을 제거합니다.

## 2. 핵심 컴포넌트 (`infra/core`)

### 2.1 **`config.py`** - 환경설정 관리
- `.env` 파일의 환경 변수를 로드하고 애플리케이션 전체에 설정을 제공
- `get_config()` 싱글톤 함수로 접근
- 주요 설정: `database_path`, `encryption_key`, `enrollment_directory`, `log_level`

### 2.2 **`database.py`** - SQLite 데이터베이스 관리 (레이지 싱글톤)
- **연결 관리**: SQLite 연결을 레이지 싱글톤으로 관리, 멀티스레드 지원
- **스키마 초기화**: 최초 실행 시 `infra/migrations/initial_schema.sql` 자동 실행
- **주요 메서드**:
  - `fetch_one(query, params)` - 단일 행 조회
  - `fetch_all(query, params)` - 다중 행 조회
  - `insert(table, data)` - 데이터 삽입, 생성된 ID 반환
  - `update(table, data, where_clause, where_params)` - 데이터 업데이트
  - `delete(table, where_clause, where_params)` - 데이터 삭제
  - `execute_query(query, params, fetch_result)` - 범용 쿼리 실행
  - `execute_many(query, params_list)` - 배치 쿼리 실행
- **트랜잭션**: `with db.transaction()` 컨텍스트 매니저 지원
- **접근**: `from infra.core.database import get_database_manager`

### 2.3 **`token_service.py`** - 토큰 관리 서비스 (레이지 싱글톤)
- **토큰 저장/조회**: accounts 테이블과 연동하여 토큰 관리
- **자동 갱신**: 만료된 토큰 자동 감지 및 refresh_token으로 갱신
- **주요 메서드**:
  - `store_tokens(user_id, token_info, user_name)` - 토큰 정보 저장
  - `get_valid_access_token(user_id)` - 유효한 액세스 토큰 반환 (자동 갱신 포함)
  - `validate_and_refresh_token(user_id)` - 토큰 검증 및 갱신
  - `check_authentication_status(user_id)` - 인증 상태 확인 및 재인증 필요 여부 판단
  - `get_all_active_accounts()` - 모든 활성 계정 조회
  - `update_account_status(user_id, status)` - 계정 상태 업데이트
  - `revoke_tokens(user_id)` - 토큰 무효화
- **접근**: `from infra.core.token_service import get_token_service`

### 2.4 **`oauth_client.py`** - OAuth 클라이언트
- **토큰 교환**: Authorization code를 access_token으로 교환
- **토큰 갱신**: refresh_token으로 새로운 access_token 획득
- **토큰 검증**: Microsoft Graph API를 통한 토큰 유효성 확인
- **주요 메서드**:
  - `exchange_code_for_tokens(code, redirect_uri, code_verifier)` - 인증 코드 교환
  - `refresh_access_token(refresh_token)` - 토큰 갱신
  - `validate_token(access_token)` - 토큰 유효성 검증
- **접근**: `from infra.core.oauth_client import get_oauth_client`

### 2.5 **`logger.py`** - 구조화된 로깅
- 구조화된 로그를 생성하고 관리
- `get_logger(__name__)`으로 각 모듈에서 로거를 가져와 사용
- 로그 레벨: DEBUG, INFO, WARNING, ERROR

### 2.6 **`exceptions.py`** - 표준 예외 클래스
- `IACSGraphError`를 기반으로 하는 표준 예외 클래스들 정의
- 일관된 오류 처리 지원
- 주요 예외: `DatabaseError`, `TokenError`, `AuthenticationError`, `ValidationError`

### 2.7 **`kafka_client.py`** - Kafka 클라이언트
- Kafka 연동을 위한 클라이언트 (이벤트 기반 아키텍처용)
- Producer/Consumer 기능 제공

## 3. 사용법

### 3.1 기본 사용 패턴

```python
# 필요한 인프라 서비스들을 import
from infra.core import get_config, get_database_manager, get_logger
from infra.core.exceptions import DatabaseError, ValidationError

# 설정 객체 가져오기
config = get_config()
encryption_key = config.encryption_key

# 로거 가져오기
logger = get_logger(__name__)
logger.info("인프라 서비스 초기화 완료")

# 데이터베이스 매니저를 통한 트랜잭션 처리
db_manager = get_database_manager()
try:
    with db_manager.transaction() as conn:
        # 이 블록 내의 모든 DB 작업은 원자적으로 처리됩니다.
        conn.execute("INSERT INTO accounts (user_id, ...) VALUES (?, ...)", ("test_user", ...))
except DatabaseError as e:
    logger.error(f"데이터베이스 트랜잭션 실패: {e}", exc_info=True)

```

## 4. 필수 환경 설정 (`.env` 파일)

프로젝트 루트에 아래와 같은 `.env` 파일을 생성해야 합니다.

```env
# 데이터베이스 파일 경로
DATABASE_PATH=./data/iacsgraph.db

# 데이터 암호화를 위한 32바이트 URL-safe base64 키
# (생성 예: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=your_secret_encryption_key_here

# 계정 설정 파일(enrollment/*.yaml)이 위치한 디렉터리
ENROLLMENT_DIRECTORY=./enrollment

# 전역 로그 레벨 (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

## 5. 아키텍처 원칙

- **단방향 의존성**: 모든 상위 모듈(`account`, `auth` 등)은 `infra` 모듈에 의존할 수 있지만, `infra` 모듈은 다른 상위 모듈을 절대 참조하지 않습니다.
- **싱글톤 패턴**: `get_config()`, `get_database_manager()` 등 팩토리 함수를 통해 모든 서비스가 싱글톤으로 관리되어 애플리케이션 전체에서 동일한 인스턴스를 공유합니다.

이러한 구조는 모듈 간의 결합도를 낮추고, 공통 기능의 재사용성과 유지보수성을 극대화합니다.
