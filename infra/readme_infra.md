# IACSGRAPH Infra Module

프로젝트의 모든 모듈이 공유하는 핵심 인프라스트럭처 서비스를 제공합니다.

## 🏗️ 주요 컴포넌트

### Core Services (`infra/core`)
- **Config**: `.env` 파일 기반의 환경 변수 관리. `get_config()`로 접근.
- **Database**: SQLite 연결 및 트랜잭션을 관리하고, 최초 실행 시 스키마를 자동 생성. `get_database_manager()`로 접근.
- **Logger**: 구조화된 전역 로깅 시스템. `get_logger()`로 접근.
- **Exceptions**: `DatabaseError`, `ValidationError` 등 표준 예외 클래스 정의.
- **KafkaClient**: Kafka 메시징 시스템 연동 클라이언트 (향후 사용 예정).
- **OAuthClient & TokenService**: OAuth 인증 및 토큰 관리 서비스 (향후 `auth` 모듈에서 사용 예정).

### Migrations (`infra/migrations`)
- **`initial_schema.sql`**: 애플리케이션의 전체 데이터베이스 스키마를 정의합니다. `database.py`에 의해 자동으로 실행됩니다.

## 📦 사용법

### 기본 Import 패턴
```python
from infra.core import get_config, get_database_manager, get_logger
from infra.core.exceptions import DatabaseError, ValidationError

# 설정 가져오기
config = get_config()

# 로거 가져오기
logger = get_logger(__name__)

# 데이터베이스 매니저 가져오기
db_manager = get_database_manager()
```

### 데이터베이스 트랜잭션 사용
`Account` 모듈과 같이 데이터의 원자적 연산이 필요할 때 사용합니다.
```python
db = get_database_manager()

try:
    with db.transaction() as conn:
        # 이 블록 안의 모든 DB 작업은 하나의 트랜잭션으로 묶입니다.
        cursor = conn.cursor()
        cursor.execute("INSERT INTO ...")
        cursor.execute("UPDATE ...")
except DatabaseError as e:
    logger.error(f"트랜잭션 실패: {e}")
```

## ⚙️ 필수 환경 설정 (`.env`)

애플리케이션이 정상적으로 동작하려면 프로젝트 루트에 `.env` 파일이 필요합니다.

```env
# 데이터베이스 경로
DATABASE_PATH=./data/iacsgraph.db

# 데이터 암호화를 위한 32바이트 URL-safe base64 키
# (예: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=your_32_byte_url_safe_base64_encryption_key

# 계정 설정 파일이 위치한 디렉터리
ENROLLMENT_DIRECTORY=enrollment

# 로깅 레벨 (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=DEBUG

# Kafka (향후 사용)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_EMAIL_EVENTS=email-raw-data-events

# OpenAI (향후 사용)
OPENAI_API_KEY=your_openai_key
```

## 🔄 호출 스택 및 의존성

- **단방향 의존성**: 모든 모듈(`account`, `auth` 등)은 `infra`에 의존하지만, `infra`는 다른 모듈에 의존하지 않습니다.
- **초기화 순서**:
  1. `get_config()`: 환경 변수 로드.
  2. `get_logger()`: 로깅 시스템 초기화.
  3. `get_database_manager()`: DB 연결 및 스키마 자동 생성.
  4. 각 모듈에서 필요한 인프라 서비스를 가져와 사용.

이 구조는 모듈 간의 결합도를 낮추고, 공통 기능의 유지보수성을 높입니다.
