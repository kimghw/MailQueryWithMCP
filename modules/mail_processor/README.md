# Mail Processor 모듈

새 메일 자동 처리 및 키워드 추출 모듈

## 주요 기능
- 스케줄러를 통한 주기적 메일 조회
- OpenRouter API를 활용한 지능형 키워드 추출
- 발신자 필터링 (스팸/광고 차단)
- Kafka 이벤트 발행

## 데이터 파이프라인
```
스케줄러 → MailProcessorOrchestrator → 활성 계정 조회
                                  ↓
                          Graph API 메일 조회
                                  ↓
                    필터링 → 키워드 추출 (OpenRouter)
                                  ↓
                    mail_history 테이블 저장
                                  ↓
                    Kafka 이벤트 발행 (email-raw-data)
```

## 사용 방법

### 새 메일 처리
```python
from modules.mail_processor import MailProcessorOrchestrator

orchestrator = MailProcessorOrchestrator()
result = await orchestrator.process_new_mails()

print(f"처리 완료: {result.processed_count}개")
print(f"필터링: {result.skipped_count}개")
```

### 개별 메일 처리
```python
from modules.mail_processor import GraphMailItem

mail_item = GraphMailItem(
    id="mail_001",
    subject="프로젝트 진행 상황",
    from_address={"emailAddress": {"address": "sender@company.com"}},
    received_date_time=datetime.now(),
    body_preview="진행 상황을 보고합니다..."
)

result = await orchestrator.process_graph_mail_item(mail_item, "kimghw")
print(f"추출된 키워드: {result.keywords}")
```

## 이벤트 발행

### Kafka 토픽: email-raw-data
```json
{
    "event_type": "email.raw_data_received",
    "event_id": "uuid",
    "account_id": "kimghw",
    "occurred_at": "2025-06-16T10:30:00Z",
    "response_data": {
        "value": [{
            "id": "메일ID",
            "subject": "제목",
            "extracted_keywords": ["키워드1", "키워드2"]
        }]
    }
}
```

## 필터링 규칙
- 차단 도메인: noreply.com, marketing.com 등
- 차단 키워드: newsletter, 광고, 홍보 등
- 차단 패턴: noreply@, system@ 등

## 변경 방법
- 키워드 모델: OPENROUTER_MODEL 환경변수
- 최대 키워드: MAX_KEYWORDS_PER_MAIL 환경변수
- 필터 규칙: MailProcessorFilterService 클래스 수정