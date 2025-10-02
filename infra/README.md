# Infra - IACSGraph 프로젝트 인프라 계층

IACSGraph 프로젝트의 핵심 인프라스트럭처 모듈입니다. 데이터베이스, 로깅, OAuth 인증, Kafka 메시징, 토큰 관리 등 프로젝트 전반에서 사용되는 공통 서비스를 제공합니다.

## 📁 디렉토리 구조

```
infra/
├── core/                    # 핵심 인프라 컴포넌트
│   ├── __init__.py         # 모듈 엔트리포인트
│   ├── config.py           # 환경 설정 관리
│   ├── database.py         # SQLite 데이터베이스 관리
│   ├── logger.py           # 구조화된 로깅 시스템
│   ├── oauth_client.py     # Azure AD OAuth 2.0 클라이언트
│   ├── token_service.py    # 토큰 관리 서비스
│   ├── kafka_client.py     # Kafka Producer/Consumer
│   ├── auth_logger.py      # 인증 전용 로거
│   └── exceptions.py       # 표준 예외 클래스
├── migrations/             # 데이터베이스 마이그레이션 스크립트
└── references/             # 참고 자료 및 문서
```

## 🚀 핵심 컴포넌트

### 1. **Config** - 환경 설정 관리
`.env` 파일에서 환경 변수를 로드하고 프로젝트 전역에서 사용할 설정을 제공합니다.

```python
from infra.core import get_config

config = get_config()
print(config.database_path)       # SQLite DB 경로
print(config.kafka_bootstrap_servers)  # Kafka 서버 목록
print(config.azure_client_id)     # Azure AD 클라이언트 ID
```

**주요 기능:**
- 레이지 싱글톤 패턴: 어디서든 동일한 설정 객체 참조
- 필수 설정값 자동 검증 (`DATABASE_PATH`, `KAFKA_BOOTSTRAP_SERVERS`, `ENCRYPTION_KEY`)
- 데이터베이스 디렉토리 자동 생성
- Azure OAuth, OpenAI, Kafka 등 모든 서비스 설정 통합 관리

**설정 파일 (.env):**
```env
# 데이터베이스
DATABASE_PATH=./data/iacsgraph.db

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_EMAIL_EVENTS=email.received
KAFKA_CONSUMER_GROUP_ID=iacsgraph-dev

# Azure OAuth
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=common
AZURE_AUTHORITY=https://login.microsoftonline.com/common

# 보안
ENCRYPTION_KEY=your-encryption-key

# 로깅
LOG_LEVEL=INFO
KAFKA_LOG_LEVEL=WARNING
```

---

### 2. **DatabaseManager** - SQLite 데이터베이스 관리
SQLite 연결을 관리하고 CRUD 작업을 지원하는 데이터베이스 매니저입니다.

```python
from infra.core import get_database_manager

db = get_database_manager()

# 조회 (단일)
account = db.fetch_one(
    "SELECT * FROM accounts WHERE user_id = ?",
    ("kimghw",)
)

# 조회 (다중)
accounts = db.fetch_all("SELECT * FROM accounts WHERE is_active = 1")

# 삽입
account_id = db.insert(
    table="accounts",
    data={
        "user_id": "kimghw",
        "user_name": "Kim Ghw",
        "status": "ACTIVE"
    }
)

# 업데이트
db.update(
    table="accounts",
    data={"status": "INACTIVE"},
    where_clause="user_id = ?",
    where_params=("kimghw",)
)

# 삭제
db.delete(
    table="accounts",
    where_clause="id = ?",
    where_params=(account_id,)
)

# 트랜잭션
with db.transaction():
    db.insert("accounts", {...})
    db.update("accounts", {...})
```

**주요 기능:**
- 자동 연결 관리 (레이지 초기화)
- WAL 모드: 동시성 향상
- Row Factory: 딕셔너리 형태 결과 반환
- 외래키 제약조건 자동 활성화
- 스키마 자동 초기화
- 스레드 세이프

---

### 3. **Logger** - 구조화된 로깅 시스템
프로젝트 전반에서 사용할 표준화된 로거를 제공합니다.

```python
from infra.core import get_logger

logger = get_logger(__name__)

logger.debug("디버그 메시지")
logger.info("정보 메시지")
logger.warning("경고 메시지")
logger.error("에러 메시지", exc_info=True)
logger.critical("심각한 오류")
```

**로그 출력 형식:**
```
[2025-09-30 14:33:22] INFO     | modules.mail_query    | 메일 조회 시작
[2025-09-30 14:33:23] WARNING  | modules.auth          | 토큰이 곧 만료됩니다
[2025-09-30 14:33:24] ERROR    | infra.core.database   | DB 연결 실패
```

**주요 기능:**
- 타임스탬프 자동 추가
- 모듈명 자동 축약 (25자 제한)
- 레벨별 색상 구분 (콘솔 출력)
- 중복 로그 방지

---

### 4. **OAuthClient** - Azure AD OAuth 2.0 클라이언트
Azure AD와의 OAuth 인증 플로우를 처리하는 비동기 클라이언트입니다.

```python
from infra.core import get_oauth_client

oauth = get_oauth_client()

# 인증 URL 생성
auth_url = oauth.generate_auth_url(state="random-state-token")
print(auth_url)  # https://login.microsoftonline.com/...

# 토큰 교환 (authorization code → access token)
token_info = await oauth.exchange_code_for_token(
    code="authorization-code-from-callback"
)

# 토큰 갱신
new_token_info = await oauth.refresh_access_token(
    refresh_token="refresh-token"
)

# 토큰 검증
is_valid = await oauth.validate_token(access_token="token")
```

**주요 기능:**
- Authorization Code Flow 지원
- 토큰 자동 갱신
- 토큰 만료 시간 계산
- aiohttp 기반 비동기 처리
- HTTP 세션 재사용 (성능 향상)

---

### 5. **TokenService** - 토큰 관리 서비스
사용자별 토큰을 데이터베이스에 안전하게 저장하고 자동 갱신하는 서비스입니다.

```python
from infra.core import get_token_service

token_service = get_token_service()

# 토큰 저장
account_id = await token_service.store_tokens(
    user_id="kimghw",
    token_info={
        "access_token": "eyJ0eXAi...",
        "refresh_token": "0.AXoA...",
        "expiry_time": datetime.now() + timedelta(hours=1)
    },
    user_name="Kim Ghw"
)

# 토큰 조회 (자동 갱신)
token_info = await token_service.get_valid_token(user_id="kimghw")

# 토큰 강제 갱신
new_token = await token_service.refresh_token(user_id="kimghw")

# 토큰 상태 확인
is_valid = await token_service.is_token_valid(user_id="kimghw")
```

**주요 기능:**
- 토큰 만료 자동 감지
- refresh_token을 사용한 자동 갱신
- 계정 상태 관리 (ACTIVE/INACTIVE)
- 암호화된 토큰 저장
- OAuthClient와 자동 연동

---

### 6. **KafkaClient** - Kafka Producer/Consumer
Kafka 메시징을 통한 이벤트 기반 아키텍처를 지원합니다.

```python
from infra.core import get_kafka_client

kafka = get_kafka_client()

# 메시지 발행 (Producer)
await kafka.publish(
    topic="email.received",
    message={
        "event_type": "email_received",
        "user_id": "kimghw",
        "timestamp": datetime.now().isoformat()
    }
)

# 메시지 구독 (Consumer)
def handle_message(message):
    print(f"받은 메시지: {message}")

await kafka.subscribe(
    topic="email.received",
    callback=handle_message,
    group_id="iacsgraph-dev"
)

# Consumer 중지
kafka.stop_consumer(topic="email.received")
```

**주요 기능:**
- 비동기 메시지 발행/구독
- 자동 재연결
- JSON 직렬화/역직렬화
- 에러 핸들링 및 재시도
- Kafka 로그 레벨 자동 조정

---

### 7. **Exceptions** - 표준 예외 클래스
프로젝트 전반에서 사용할 구조화된 예외 계층을 제공합니다.

```python
from infra.core import (
    IACSGraphError,
    DatabaseError,
    ConnectionError,
    KafkaError,
    TokenError,
    TokenExpiredError,
    AuthenticationError,
    ValidationError
)

# 예외 발생
raise DatabaseError(
    message="사용자를 찾을 수 없습니다",
    operation="SELECT",
    table="accounts",
    details={"user_id": "kimghw"}
)

# 예외 처리
try:
    token = await token_service.get_valid_token("kimghw")
except TokenExpiredError as e:
    print(e.message)
    print(e.details)
```

**예외 계층:**
```
IACSGraphError (최상위)
├── DatabaseError
│   └── ConnectionError
├── KafkaError
│   ├── KafkaConnectionError
│   ├── KafkaProducerError
│   └── KafkaConsumerError
├── TokenError
│   ├── TokenExpiredError
│   └── TokenRefreshError
├── AuthenticationError
├── APIConnectionError
├── ValidationError
├── BusinessLogicError
└── ConfigurationError
```

---

## 🔗 모듈 간 연동

### 사용 예시 (mail_attachment 모듈)
```python
from infra.core import get_database_manager, get_logger
from infra.core.exceptions import DatabaseError

logger = get_logger(__name__)
db = get_database_manager()

class MailAttachmentTools:
    def __init__(self):
        self.db = db

    async def query_email(self, user_id: str):
        try:
            # DB에서 계정 조회
            account = self.db.fetch_one(
                "SELECT * FROM accounts WHERE user_id = ?",
                (user_id,)
            )

            if not account:
                raise DatabaseError(
                    f"계정을 찾을 수 없습니다: {user_id}",
                    table="accounts"
                )

            logger.info(f"메일 조회 시작: {user_id}")
            # ... 메일 조회 로직

        except DatabaseError as e:
            logger.error(f"DB 오류: {e}", exc_info=True)
            raise
```

---

## 📊 주요 의존성

infra 모듈은 다음 프로젝트에서 사용됩니다:

- `modules/mail_attachment` - 메일 첨부파일 서버
- `modules/mail_query` - 메일 조회
- `modules/mail_dashboard` - 메일 대시보드
- `modules/query_assistant` - 쿼리 어시스턴트
- `modules/auth` - OAuth 인증
- `modules/account` - 계정 관리
- `modules/mail_process` - 메일 처리

**import 예시:**
```python
from infra.core import (
    get_config,
    get_database_manager,
    get_logger,
    get_oauth_client,
    get_token_service,
    get_kafka_client
)
```

---

## 🛠️ 개발 가이드

### 1. 새 서비스 추가
1. `infra/core/` 에 서비스 파일 생성 (예: `new_service.py`)
2. 싱글톤 패턴 적용:
```python
from functools import lru_cache

class NewService:
    def __init__(self):
        self.config = get_config()

@lru_cache(maxsize=1)
def get_new_service() -> NewService:
    return NewService()
```
3. `infra/core/__init__.py`에 export 추가

### 2. 새 예외 추가
`infra/core/exceptions.py`에 예외 클래스 추가:
```python
class NewError(IACSGraphError):
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="NEW_ERROR",
            **kwargs
        )
```

### 3. 마이그레이션 작성
`infra/migrations/`에 마이그레이션 스크립트 추가:
```python
# apply_new_schema.py
from infra.core import get_database_manager

db = get_database_manager()

db.execute("""
    CREATE TABLE IF NOT EXISTS new_table (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
""")
```

---

## ⚠️ 주의사항

1. **순환 참조 방지**: infra는 다른 모듈에 의존하지 않아야 합니다
2. **환경 변수 필수**: `.env` 파일 없이는 실행 불가
3. **싱글톤 패턴**: 모든 서비스는 `@lru_cache`로 싱글톤 구현
4. **비동기 함수**: OAuth, Token, Kafka 관련 함수는 `async/await` 필수
5. **스레드 세이프**: DatabaseManager는 threading.Lock 사용

---

## 📝 환경 설정 체크리스트

실행 전 반드시 확인:
- [ ] `.env` 파일 존재
- [ ] `DATABASE_PATH` 설정
- [ ] `KAFKA_BOOTSTRAP_SERVERS` 설정
- [ ] `ENCRYPTION_KEY` 설정
- [ ] `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` 설정 (OAuth 사용 시)
- [ ] Kafka 서버 실행 중 (로컬 개발 시: `localhost:9092`)
- [ ] SQLite 데이터베이스 디렉토리 쓰기 권한

---

## 🔍 트러블슈팅

### 1. "필수 설정값이 누락되었습니다"
→ `.env` 파일에 `DATABASE_PATH`, `KAFKA_BOOTSTRAP_SERVERS`, `ENCRYPTION_KEY` 추가

### 2. "데이터베이스 연결 실패"
→ `DATABASE_PATH` 디렉토리 쓰기 권한 확인 또는 경로 수정

### 3. "Kafka 클러스터에 연결할 수 없습니다"
→ Kafka 서버 실행 상태 확인: `docker ps` 또는 `systemctl status kafka`

### 4. "OAuth 설정이 완료되지 않았습니다"
→ `.env`에 `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` 추가

### 5. 토큰 갱신 실패
→ `refresh_token`이 없거나 만료됨. 재인증 필요

---

## 📚 추가 자료

- [infra/references/](references/) - 참고 문서 및 예제
- [infra/migrations/](migrations/) - 데이터베이스 스키마 변경 이력
- Azure OAuth 2.0 문서: https://learn.microsoft.com/en-us/azure/active-directory/develop/
- Kafka Python Client: https://kafka-python.readthedocs.io/

---

**마지막 업데이트:** 2025-09-30
**담당자:** IACSGraph 개발팀