# Infra 모듈

## 1. 개요

IACSGraph 프로젝트의 모든 모듈이 공유하는 핵심 기반 서비스를 제공합니다. 설정 관리, 데이터베이스 연결, 로깅, 예외 처리 등 공통 기능을 중앙에서 관리하여 모듈 간의 일관성을 유지하고 중복을 제거합니다.

## 2. 핵심 컴포넌트 (`infra/core`)

- **`config.py`**: `.env` 파일의 환경 변수를 로드하고 애플리케이션 전체에 설정을 제공합니다. `get_config()`를 통해 싱글톤 인스턴스에 접근할 수 있습니다.
- **`database.py`**: SQLite 데이터베이스 연결 및 트랜잭션을 관리합니다. 최초 실행 시 `infra/migrations/initial_schema.sql`을 참조하여 스키마를 자동으로 생성합니다.
- **`logger.py`**: 구조화된 로그를 생성하고 관리합니다. `get_logger(__name__)`으로 각 모듈에서 로거를 가져와 사용합니다.
- **`exceptions.py`**: `IACSGraphError`를 기반으로 하는 표준 예외 클래스들을 정의하여 일관된 오류 처리를 지원합니다.
- **`kafka_client.py`**: Kafka 연동을 위한 클라이언트 (향후 이벤트 기반 아키텍처에서 사용 예정).
- **`oauth_client.py` / `token_service.py`**: OAuth 인증 및 토큰 관리를 위한 서비스 (향후 `auth` 모듈에서 사용 예정).

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
