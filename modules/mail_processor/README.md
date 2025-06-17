# Mail Processor 모듈

Microsoft Graph API를 통해 새로운 메일을 주기적으로 조회하고, 키워드를 추출하여 로컬 DB에 저장하며, Kafka 이벤트를 발행하는 모듈입니다.

## 🔄 데이터 파이프라인 구조

```
스케줄러 (5분마다)
        ↓
MailProcessorOrchestrator
        ↓
활성 계정 조회 (accounts 테이블)
        ↓
    ┌─────────────────────────┐
    │  계정별 병렬 처리 시작   │
    └─────────────────────────┘
              ↓
        Graph API 호출
              ↓
        메일 리스트 수신
              ↓
    ┌─────────────────────────┐
    │    개별 메일 처리        │
    ├─────────────────────────┤
    │ 1. 발신자 필터링        │
    │ 2. 중복 검사            │
    │ 3. 키워드 추출          │
    └─────────────────────────┘
              ↓
         ┌────┴────┐
         ↓         ↓
   DB 저장    Kafka 발행
         ↓         ↓
mail_history  email-raw-data
```

### 동작 방식
1. **계정 순회**: 활성 계정을 last_sync_time 순으로 처리
2. **증분 조회**: 마지막 동기화 이후의 메일만 조회
3. **필터링**: 스팸/광고 메일 자동 차단
4. **키워드 추출**: OpenRouter API 또는 Fallback 방식
5. **이벤트 발행**: 키워드 정보를 포함한 Kafka 이벤트

## 📋 모듈 설정 파일 관리

### 환경 변수 설정 (`.env`)
```env
# OpenRouter API 설정
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=openai/gpt-3.5-turbo
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# 메일 처리 설정
MAX_KEYWORDS_PER_MAIL=5
MIN_KEYWORD_LENGTH=2
MAX_MAILS_PER_ACCOUNT=200
MAIL_PROCESSING_BATCH_SIZE=50

# 필터링 설정
ENABLE_SENDER_FILTERING=true
BLOCKED_DOMAINS=noreply.com,no-reply.com,donotreply.com
BLOCKED_KEYWORDS=newsletter,promotion,marketing,광고,홍보

# Kafka 설정
KAFKA_TOPIC_EMAIL_EVENTS=email-raw-data
KAFKA_BATCH_SIZE=100
KAFKA_COMPRESSION_TYPE=gzip
```

## 🚀 모듈별 사용 방법 및 예시

### 1. 새 메일 처리 (전체 계정)
```python
from modules.mail_processor import MailProcessorOrchestrator
import asyncio

async def process_all_new_mails():
    orchestrator = MailProcessorOrchestrator()
    
    # 모든 활성 계정의 새 메일 처리
    result = await orchestrator.process_new_mails()
    
    print(f"=== 메일 처리 결과 ===")
    print(f"총 조회: {result.total_fetched}개")
    print(f"처리 성공: {result.processed_count}개")
    print(f"필터링: {result.skipped_count}개")
    print(f"처리 실패: {result.failed_count}개")
    print(f"실행 시간: {result.execution_time_ms}ms")
    
    if result.errors:
        print("\n오류 목록:")
        for error in result.errors[:5]:  # 상위 5개만
            print(f"- {error}")

asyncio.run(process_all_new_mails())
```

### 2. 개별 메일 처리 (GraphMailItem)
```python
from modules.mail_processor import GraphMailItem
from datetime import datetime

async def process_single_mail():
    orchestrator = MailProcessorOrchestrator()
    
    # GraphMailItem 객체 생성 (예: Mail Query에서 받은 메일)
    mail_item = GraphMailItem(
        id="AAMkADU2MGM5YzRjLTE4NmItNDE4NC...",
        subject="[EA004] 프로젝트 진행 상황 보고",
        from_address={
            "emailAddress": {
                "name": "김과장",
                "address": "manager@company.com"
            }
        },
        received_date_time=datetime.now(),
        body_preview="안녕하세요. 프로젝트 진행 상황을 보고드립니다...",
        body={
            "contentType": "text",
            "content": "프로젝트 EA004의 현재 진행률은 75%입니다..."
        },
        has_attachments=True,
        importance="high"
    )
    
    # 메일 처리
    result = await orchestrator.process_graph_mail_item(mail_item, "kimghw")
    
    print(f"처리 상태: {result.processing_status}")
    print(f"추출된 키워드: {result.keywords}")
    
    if result.error_message:
        print(f"오류: {result.error_message}")
```

### 3. 처리 통계 조회
```python
async def get_processing_statistics():
    orchestrator = MailProcessorOrchestrator()
    
    stats = await orchestrator.get_processing_stats()
    
    print("=== 메일 처리 통계 ===")
    print(f"총 처리 메일: {stats['mail_stats']['total_mails']}개")
    print(f"최근 1시간: {stats['mail_stats']['recent_hour']}개")
    print(f"최근 24시간: {stats['mail_stats']['recent_day']}개")
    
    print("\n=== 필터 통계 ===")
    print(f"차단 도메인: {stats['filter_stats']['blocked_domains_count']}개")
    print(f"차단 키워드: {stats['filter_stats']['blocked_keywords_count']}개")
    
    print("\n=== 서비스 상태 ===")
    for service, status in stats['services_status'].items():
        print(f"{service}: {status}")
```

### 4. 필터 규칙 관리
```python
# 필터 서비스 직접 사용
from modules.mail_processor.mail_filter_service import MailProcessorFilterService

filter_service = MailProcessorFilterService()

# 도메인 추가/제거
filter_service.add_blocked_domain("spam.com")
filter_service.remove_blocked_domain("newsletter.com")

# 키워드 추가/제거
filter_service.add_blocked_keyword("특가")
filter_service.remove_blocked_keyword("promotion")

# 현재 필터 상태 확인
stats = filter_service.get_filter_stats()
print(f"차단 도메인: {stats['blocked_domains']}")
print(f"차단 키워드: {stats['blocked_keywords']}")
```

## 📤 이벤트 발행 (Kafka)

### 이벤트 구조
```json
{
    "event_type": "email.raw_data_received",
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "account_id": "kimghw",
    "occurred_at": "2025-06-16T10:30:00Z",
    "api_endpoint": "/v1.0/me/messages",
    "response_status": 200,
    "request_params": {
        "$select": "id,subject,from,body,bodyPreview,receivedDateTime",
        "$top": 50
    },
    "response_data": {
        "value": [{
            "id": "AAMkADU2MGM5YzRjLTE4NmItNDE4NC...",
            "subject": "[EA004] 프로젝트 진행 상황 보고",
            "from": {
                "emailAddress": {
                    "address": "manager@company.com"
                }
            },
            "receivedDateTime": "2025-06-16T10:30:00Z",
            "extracted_keywords": ["EA004", "프로젝트", "진행상황", "보고서", "75%"]
        }]
    },
    "response_timestamp": "2025-06-16T10:30:05Z"
}
```

### Kafka Consumer 예시
```python
from kafka import KafkaConsumer
import json

# Kafka Consumer 설정
consumer = KafkaConsumer(
    'email-raw-data',
    bootstrap_servers=['localhost:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

# 이벤트 수신
for message in consumer:
    event = message.value
    
    if event['event_type'] == 'email.raw_data_received':
        for mail in event['response_data']['value']:
            print(f"\n새 메일: {mail['subject']}")
            print(f"키워드: {mail.get('extracted_keywords', [])}")
```

## 🧠 키워드 추출 메커니즘

### 1. OpenRouter API (Primary)
```python
# 프롬프트 예시
"""
다음 이메일 본문에서 가장 중요한 키워드 5개를 한국어로 추출해주세요.
키워드는 명사 위주로 추출하고, 콤마로 구분하여 나열해주세요.
- 문서번호나 프로젝트 코드는 반드시 포함
- 기관명, 회의 일정, 기술 내용 포함
- 중복 제거

이메일 본문: {email_content}
"""
```

### 2. Fallback 메커니즘
```python
# OpenRouter 실패 시 정규식 기반 추출
- 한국어 단어 (2글자 이상)
- 영문 단어 (3글자 이상)
- 식별자 패턴 (EA004, REQ-123 등)
- 빈도수 기반 상위 키워드 선택
```

## 📊 데이터 저장 구조

### mail_history 테이블
```sql
CREATE TABLE mail_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,           -- accounts.id 참조
    message_id TEXT NOT NULL UNIQUE,       -- Graph API 메일 ID
    received_time TIMESTAMP NOT NULL,      -- 메일 수신 시간
    subject TEXT,                          -- 메일 제목
    sender TEXT,                           -- 발신자 이메일
    keywords TEXT,                         -- JSON 배열 ["키워드1", "키워드2"]
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_mail_history_account_id ON mail_history(account_id);
CREATE INDEX idx_mail_history_received_time ON mail_history(received_time);
CREATE INDEX idx_mail_history_sender ON mail_history(sender);
```

## 🚦 필터링 규칙

### 기본 차단 도메인
- `noreply.com`, `no-reply.com`, `donotreply.com`
- `notifications.com`, `alerts.com`, `system.com`
- `newsletter.com`, `marketing.com`, `promo.com`

### 차단 키워드
- 영문: newsletter, promotion, marketing, advertisement
- 한글: 광고, 홍보, 마케팅, 뉴스레터, 구독취소

### 차단 발신자 패턴
- `noreply@`, `no-reply@`, `system@`
- `newsletter@`, `marketing@`, `promo@`

## ⚠️ 주의사항

### 1. API Rate Limiting
- Graph API: 분당 요청 수 제한
- OpenRouter: 분당 토큰 사용량 제한
- 자동 백오프 및 재시도 구현

### 2. 메모리 관리
- 계정당 최대 200개 메일 제한
- 50개씩 배치 처리
- 대용량 본문은 잘라서 처리

### 3. 에러 격리
- 한 계정의 실패가 다른 계정에 영향 없음
- 개별 메일 처리 실패 시 계속 진행
- Kafka 발행 실패는 전체 프로세스 중단하지 않음

## 🔗 다른 모듈과의 연계

### Account 모듈
- 활성 계정 목록 조회
- last_sync_time 업데이트

### Token Service
- Graph API 호출용 액세스 토큰
- 자동 토큰 갱신

### Kafka Client
- 이벤트 발행
- 배치 처리 및 압축

## 📈 성능 최적화

### 1. 증분 동기화
```python
# last_sync_time 이후의 메일만 조회
since_filter = f"receivedDateTime ge {last_sync_time}"
```

### 2. 병렬 처리
```python
# 계정별 독립 처리 (향후 asyncio.gather 활용 가능)
for account in active_accounts:
    await process_account_mails(account)
```

### 3. 캐싱 전략
- 중복 메일 ID 메모리 캐시 (향후)
- 필터 규칙 캐시
- OpenRouter 응답 캐시 (유사 본문)

## 🚨 모니터링

### 로그 레벨
```python
# 정보성 로그
logger.info(f"메일 처리 시작: account_count={len(accounts)}")

# 경고 로그
logger.warning(f"키워드 추출 실패, fallback 사용: {error}")

# 오류 로그
logger.error(f"Graph API 호출 실패: {error}", exc_info=True)
```

### 메트릭 수집
- 처리된 메일 수 (processed_count)
- 필터링된 메일 수 (skipped_count)
- 키워드 추출 성공률
- API 응답 시간
- 에러 발생률