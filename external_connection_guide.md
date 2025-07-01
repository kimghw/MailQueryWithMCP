# IACSRAG 프로젝트 외부 접속 가이드

## 개요
IACSRAG 프로젝트에서 사용하는 MongoDB, Qdrant, Kafka 서버의 접속 정보와 데이터 타입 정보를 정리한 문서입니다.

## 1. 서버 접속 정보


### 1.3 Kafka
```yaml
접속 정보:
  브로커: localhost:9092
  Zookeeper: localhost:2181
  
Docker 컨테이너:
  Kafka 이미지: confluentinc/cp-kafka:7.4.0
  Kafka 컨테이너명: iacsrag-kafka
  Zookeeper 이미지: confluentinc/cp-zookeeper:7.4.0
  Zookeeper 컨테이너명: iacsrag-zookeeper

관리 UI:
  Kafka UI: http://localhost:8080
  컨테이너명: iacsrag-kafka-ui
```

### 1.4 Redis (선택사항)
```yaml
접속 정보:
  호스트: localhost
  포트: 6379
  연결 URL: redis://localhost:6379
  
Docker 컨테이너:
  이미지: redis:7.2-alpine
  컨테이너명: iacsrag-redis
```




## 4. Kafka 토픽 및 이벤트 구조

### 4.1 주요 토픽 목록
```yaml
문서 관련:
  - document-uploaded (파티션: 3)
  - document-processed (파티션: 3)

이메일 관련:
  - email.received (파티션: 3)

처리 작업 관련:
  - processing-job-events (파티션: 3)
  - text-extraction-events (파티션: 3)
  - chunking-events (파티션: 3)
  - embedding-events (파티션: 3)

검색 관련:
  - search-query-events (파티션: 3)
  - search-result-events (파티션: 3)

모니터링 관련:
  - system-metrics (파티션: 1)
  - system-alerts (파티션: 1)
  - health-check (파티션: 1)
```

### 4.2 표준 이벤트 구조
```json
{
  "event_type": "string",
  "source": "iacsrag",
  "correlation_id": "UUID string",
  "timestamp": "ISO 8601 timestamp",
  "version": "string",
  "data": {
    // 이벤트별 데이터
  }
}


### 4.5 Mail Raw Data 이벤트 구조
```json
{
  "event_type": "email_type",
  "event_id": "unique-event-id",
  "account_id": "user-account-id",
  "occurred_at": "2024-01-01T00:00:00Z",
  "api_endpoint": "/v1.0/me/messages",
  "response_status": 200,
  "request_params": {
    "$select": "id,subject,from,body,toRecipients,ccRecipients,bccRecipients,hasAttachments,receivedDateTime,importance,isRead,bodyPreview,categories,flag",
    "$top": 50,
    "$skip": 0
  },
  "response_data": {
    "value": [
      {
        "id": "graph-email-id",
        "subject": "[EA004] 이메일 제목",
        "from": {
          "emailAddress": {
            "name": "발신자 이름",
            "address": "sender@example.com"
          }
        },
        "body": {
          "contentType": "html",
          "content": "<html><body>이메일 본문 HTML</body></html>"
        },
        "toRecipients": [
          {
            "emailAddress": {
              "name": "수신자 이름",
              "address": "recipient@example.com"
            }
          }
        ],
        "ccRecipients": [],
        "bccRecipients": [],
        "hasAttachments": false,
        "receivedDateTime": "2024-01-01T00:00:00Z",
        "importance": "normal",
        "isRead": false,
        "bodyPreview": "이메일 미리보기 텍스트",
        "categories": [],
        "flag": {
          "flagStatus": "notFlagged"
        }
      }
    ],
    "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users('user-id')/messages",
    "@odata.nextLink": "https://graph.microsoft.com/v1.0/me/messages?$skip=50"
  },
  "response_timestamp": "2024-01-01T00:00:00Z"
}
```

## 5. 컨슈머 그룹 정보

### 5.1 주요 컨슈머 그룹

```

## 6. 연결 예시 코드

### 6.1 MongoDB 연결 (Python)
```python
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient

# 동기 연결
client = MongoClient("mongodb://admin:password@localhost:27017")
db = client.iacsrag_dev

# 비동기 연결
async_client = AsyncIOMotorClient("mongodb://admin:password@localhost:27017")
async_db = async_client.iacsrag_dev
```

### 6.3 Kafka 연결 (Python)
```python
from kafka import KafkaProducer, KafkaConsumer
import json

# Producer
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)

# Consumer
consumer = KafkaConsumer(
    'document-uploaded',
    bootstrap_servers=['localhost:9092'],
    group_id='my-consumer-group',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)
```

## 7. 환경 설정 파일

### 7.1 .env.development 주요 설정
```bash
# MongoDB
MONGODB_URL=mongodb://admin:password@localhost:27017
MONGODB_DATABASE=iacsrag_dev

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=documents

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_CONSUMER_GROUP_ID=iacsrag-dev

# Redis
REDIS_URL=redis://localhost:6379
```

### 7.2 Docker Compose 실행
```bash
# 모든 서비스 시작
docker-compose up -d

# 특정 서비스만 시작
docker-compose up -d mongodb qdrant kafka

# 서비스 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f kafka
```

## 8. 주의사항

### 8.1 보안
- 개발 환경용 설정이므로 프로덕션에서는 보안 설정 필요
- MongoDB, Kafka 등에 인증 및 암호화 적용 권장
- 네트워크 접근 제어 설정 필요

### 8.2 성능
- MongoDB 인덱스 최적화 필요
- Qdrant 컬렉션 설정 튜닝 권장
- Kafka 파티션 수 조정 고려

### 8.3 모니터링
- 각 서비스별 헬스체크 구현
- 메트릭 수집 및 알림 설정
- 로그 중앙화 관리 권장

이 문서는 IACSRAG 프로젝트의 외부 시스템 연동을 위한 기본 가이드입니다. 실제 운영 환경에서는 보안, 성능, 가용성을 고려한 추가 설정이 필요합니다.
