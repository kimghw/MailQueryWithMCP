# 인프라 레이어 구현 명세서

## 1. 개요
프로젝트의 모든 모듈이 공유하는 핵심 기반 서비스를 제공합니다. 설정 관리, 데이터베이스 연결, 로깅, 예외 처리 등 공통 기능을 중앙에서 관리하여 모듈 간의 일관성을 유지하고 중복을 제거합니다.

## 2. 핵심 컴포넌트 (`infra/core`)

### 2.1 `config.py`
- **역할**: `.env` 파일의 환경 변수를 로드하고 애플리케이션 전체에 설정을 제공합니다.
- **구현**: `python-dotenv`를 사용하며, `functools.lru_cache`를 이용한 레이지 싱글톤 패턴으로 구현되어 어디서든 `get_config()`를 통해 동일한 설정 객체를 참조합니다.
- **주요 설정**:
    - `DATABASE_PATH`: SQLite 데이터베이스 파일 경로
    - `KAFKA_BOOTSTRAP_SERVERS`: Kafka 서버 주소
    - `ENCRYPTION_KEY`: Fernet 암호화 키 (32바이트 URL-safe base64)
    - `LOG_LEVEL`: 전역 로그 레벨 (DEBUG, INFO 등)
    - `ENROLLMENT_DIRECTORY`: 계정 설정 파일(`enrollment/*.yaml`)이 위치한 디렉터리

### 2.2 `database.py`
- **역할**: SQLite 데이터베이스 연결을 관리하고, 스키마를 자동으로 초기화합니다.
- **구현**:
    - `DatabaseManager` 클래스가 DB 연결 및 트랜잭션을 관리합니다.
    - `get_database_manager()`를 통해 싱글톤 인스턴스를 제공합니다.
    - 최초 연결 시 `infra/migrations/initial_schema.sql`을 실행하여 모든 테이블을 생성합니다.
    - `with db.transaction()` 컨텍스트 매니저를 통해 원자적 연산을 지원합니다.

### 2.3 `logger.py`
- **역할**: 구조화된 로그를 생성하고 관리합니다.
- **구현**: Python의 `logging` 모듈을 기반으로 하며, `config.py`의 `LOG_LEVEL`에 따라 로그 레벨을 동적으로 설정합니다. `get_logger(__name__)`으로 각 모듈에서 로거를 가져와 사용합니다.

### 2.4 `exceptions.py`
- **역할**: 프로젝트 전반에서 사용할 표준 예외 클래스를 정의합니다.
- **구현**: `IACSGraphError`를 최상위 예외로 두고, `DatabaseError`, `ValidationError`, `BusinessLogicError` 등 구체적인 예외 클래스를 파생하여 일관된 오류 처리를 지원합니다.

### 2.5 `kafka_client.py` (향후 사용 예정)
- **역할**: Kafka Producer 및 Consumer를 관리하는 클라이언트.
- **상태**: 현재 구현되어 있으나, Account 모듈에서는 직접 사용하지 않음. 향후 이벤트 기반 아키텍처에서 활용될 예정입니다.

### 2.6 `oauth_client.py` 및 `token_service.py` (향후 사용 예정)
- **역할**: OAuth 인증 및 토큰 관리를 담당.
- **상태**: 현재는 Account 모듈이 자체적으로 계정별 OAuth 정보를 관리하므로, 이 인프라 서비스들은 `auth` 모듈 구현 시 본격적으로 사용될 예정입니다.

## 3. 데이터베이스 스키마 관리 (`infra/migrations`)

- **`initial_schema.sql`**: 애플리케이션 실행 시 `database.py`에 의해 자동으로 실행되는 기본 스키마 파일입니다. `accounts`, `account_audit_logs` 등 모든 테이블 정의가 포함되어 있습니다.
- **`account_schema_update.sql`**: 개발 과정에서 사용된 스키마 변경 기록용 파일입니다. (현재는 `initial_schema.sql`에 통합됨)

## 4. Account 모듈과의 상호작용

`Account` 모듈은 다음과 같이 `infra` 레이어에 의존합니다:
- **`get_config()`**: `ENCRYPTION_KEY`, `ENROLLMENT_DIRECTORY` 등 주요 설정을 가져옵니다.
- **`get_database_manager()`**: 데이터베이스 연결 및 트랜잭션 관리를 위해 사용합니다.
- **`get_logger()`**: 모듈 내 활동을 로깅하기 위해 사용합니다.
- **`DatabaseError`, `ValidationError`**: 적절한 예외를 발생시키기 위해 사용합니다.

이 구조를 통해 `Account` 모듈은 인프라의 구체적인 구현 방식에 의존하지 않고, 비즈니스 로직에만 집중할 수 있습니다.
