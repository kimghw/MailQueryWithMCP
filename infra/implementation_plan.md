# Phase 2: 인프라 레이어 구현 계획

## 1. 목표
- 프로젝트의 핵심 기반이 되는 인프라스트럭처 레이어를 구축합니다.
- 설정 관리, 데이터베이스 연결, 메시징 큐, 예외 처리, 인증 등 공통 서비스를 구현하여 다른 모듈들이 안정적으로 사용할 수 있도록 합니다.

## 2. 작업 범위

### 2.1 Core 인프라 구현 (전역 서비스)
- **`infra/core/config.py`**:
  - **목표**: 환경 변수(.env)를 안전하게 로드하고 관리하는 설정 클래스 구현.
  - **구현 방식**: `python-dotenv`를 사용하고, `functools.lru_cache`를 이용한 레이지 싱글톤 패턴으로 구현하여 어디서든 동일한 설정 객체를 참조하도록 함.
  - **주요 설정값**: `DATABASE_URL`, `KAFKA_BOOTSTRAP_SERVERS`, `OPENAI_API_KEY`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`, `LOG_LEVEL`.
- **`infra/core/database.py`**:
  - **목표**: SQLite 데이터베이스 연결을 관리하는 매니저 클래스 구현.
  - **구현 방식**: 레이지 싱글톤 패턴으로 구현. `check_same_thread=False` 옵션을 사용하여 비동기 환경에서의 충돌을 방지. SQL 스크립트 실행 기능을 포함.
- **`infra/core/kafka_client.py`**:
  - **목표**: Kafka Producer 및 Consumer를 관리하는 클라이언트 클래스 구현.
  - **구현 방식**: 레이지 싱글톤 패턴으로 구현. Producer는 JSON 직렬화를, Consumer는 JSON 역직렬화를 기본으로 설정.
- **`infra/core/exceptions.py`**:
  - **목표**: 프로젝트 전반에서 사용할 표준 예외 클래스 정의.
  - **구현 방식**: `IACSGraphError`를 최상위 예외로 두고, `DatabaseError`, `KafkaError`, `APIConnectionError`, `AuthenticationError` 등 구체적인 예외 클래스를 파생하여 생성.
- **`infra/core/logger.py`**:
  - **목표**: 구조화된 로깅 시스템 구현.
  - **구현 방식**: `logging` 모듈을 사용. 설정 파일의 `LOG_LEVEL`에 따라 로그 레벨을 동적으로 설정.

### 2.2 OAuth 및 토큰 관리
- **`infra/core/oauth_client.py`**:
  - **목표**: Azure AD와의 OAuth 2.0 인증 플로우를 처리하는 비동기 클라이언트 구현.
  - **구현 방식**: `aiohttp`를 사용하여 비동기 HTTP 요청 처리. 인증 URL 생성, 인증 코드로 토큰 받기, 리프레시 토큰으로 토큰 갱신 기능 구현.
- **`infra/core/token_service.py`**:
  - **목표**: 데이터베이스와 연동하여 사용자별 토큰을 관리하고, 만료 시 자동으로 갱신하는 서비스 구현.
  - **구현 방식**: 토큰 저장, 유효한 액세스 토큰 조회 및 자동 갱신 기능 포함.

### 2.3 데이터베이스 초기화 (수정)
- **`infra/core/database.py` 내 통합**:
  - **목표**: `db_initializer.py`를 제거하고, `database.py`에서 데이터베이스 최초 연결 시 스키마를 자동으로 생성하도록 통합.
  - **구현 방식**: `get_connection()` 메서드 내에서 테이블 존재 여부를 확인하고, 테이블이 없으면 `initial_schema.sql` 스크립트를 실행하는 로직 추가.

### 2.4 기본 스키마 정의 (변경 없음)
- **목표**: 각 모듈에서 사용할 Pydantic V2 기반의 데이터 모델(스키마) 정의.
- **구현 방식**: 각 모듈(`account`, `auth`, `mail_query` 등) 디렉터리에 `schema.py` 파일을 생성하고, 각 도메인에 맞는 데이터 모델을 독립적으로 정의. (infra에서 정의하지 않음)

## 3. 완료 기준
- 위에 명시된 모든 `.py` 파일이 `infra/core` 디렉터리에 생성되고, 기본 코드가 작성됨.
- 각 모듈별 `schema.py` 파일이 생성되고, 기본 스키마가 정의됨.
- 별도의 테스트 코드는 작성하지 않으나, 코드 리뷰를 통해 논리적 오류가 없음을 확인.
- `pyproject.toml`에 필요한 의존성이 모두 추가됨.
