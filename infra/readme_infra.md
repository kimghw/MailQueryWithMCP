# IACSGRAPH Infra Module

프로젝트의 핵심 인프라스트럭처를 제공하는 공통 서비스 모듈입니다.

## 🏗️ 주요 컴포넌트

### Core Services
- **Config**: 환경 변수 기반 설정 관리
- **Database**: SQLite 연결 및 스키마 자동 초기화  
- **KafkaClient**: Producer/Consumer 관리
- **Logger**: 구조화된 로깅 시스템
- **OAuthClient**: Azure AD 인증 처리
- **TokenService**: 토큰 저장 및 자동 갱신
- **Exceptions**: 표준 예외 계층

## 📦 사용법

### 기본 Import 패턴
```python
from infra.core import (
    get_config, get_database, get_kafka_client, 
    get_logger, get_oauth_client, get_token_service
)
```

### 일반적인 사용 순서
```python
# 1. 설정 로드
config = get_config()

# 2. 로거 초기화  
logger = get_logger(__name__)

# 3. 데이터베이스 연결 (스키마 자동 생성됨)
db = get_database()

# 4. 필요시 Kafka/OAuth 클라이언트 사용
kafka = get_kafka_client()
oauth = get_oauth_client()
```

### 데이터베이스 사용
```python
db = get_database()
with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts")
    results = cursor.fetchall()
```

### Kafka 이벤트 발행
```python
kafka = get_kafka_client()
await kafka.produce("email-raw-data-events", event_data)
```

### 토큰 관리
```python
token_service = get_token_service()
access_token = await token_service.get_valid_access_token(account_id)
```

## ⚙️ 필수 환경 설정

`.env` 파일에 다음 설정이 필요합니다:

```env
# 데이터베이스
DATABASE_PATH=./data/iacsgraph.db

# Azure AD OAuth
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret  
AZURE_TENANT_ID=common
AZURE_SCOPES=User.Read,Mail.Read,offline_access

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_EMAIL_EVENTS=email-raw-data-events

# 기타
LOG_LEVEL=DEBUG
OPENAI_API_KEY=your_openai_key
```

## 🔄 호출 스택

```
Module Import
    ↓
get_config() - 환경 설정 로드
    ↓  
get_logger() - 로깅 시스템 초기화
    ↓
get_database() - DB 연결 및 스키마 생성
    ↓
[필요시] get_kafka_client() - 메시징 시스템
    ↓
[필요시] get_oauth_client() - 인증 시스템
    ↓
[필요시] get_token_service() - 토큰 관리
```

## 🚨 중요 사항

- **모든 서비스는 레이지 싱글톤**: 첫 호출 시에만 초기화됨
- **데이터베이스 스키마**: 첫 연결 시 자동으로 `initial_schema.sql` 실행
- **비동기 지원**: OAuth, Kafka, TokenService는 비동기 메서드 제공
- **예외 처리**: 모든 컴포넌트는 구조화된 예외 발생

## 📁 디렉터리 구조

```
infra/
├── core/               # 핵심 서비스들
│   ├── __init__.py    # 통합 진입점
│   ├── config.py      # 설정 관리
│   ├── database.py    # DB 연결 관리  
│   ├── kafka_client.py # Kafka 클라이언트
│   ├── logger.py      # 로깅 시스템
│   ├── oauth_client.py # OAuth 클라이언트
│   ├── token_service.py # 토큰 서비스
│   └── exceptions.py  # 예외 정의
├── migrations/        # DB 스키마 파일
└── references/        # 외부 API 가이드라인
```

## 🔧 모듈 의존성

infra는 다른 모듈에 의존하지 않으며, 모든 모듈이 infra를 참조하는 단방향 의존성을 유지합니다.
