# Mail Query Module

Microsoft Graph API를 통해 사용자의 이메일을 조회하고 처리하는 모듈입니다.

## 주요 기능

1. **이메일 조회** - 다양한 필터 조건으로 이메일 검색
2. **메시지 검색** - 키워드 기반 이메일 검색
3. **메일박스 정보 조회** - 사용자 메일박스 설정 정보 확인
4. **JSON 저장** - 이메일 데이터를 JSON 파일로 저장

## 사용 방법

### 1. 모듈 임포트

```python
from modules.mail_query import (
    MailQueryOrchestrator,
    MailQueryRequest,
    MailQueryFilters,
    PaginationOptions
)
```

### 2. 오케스트레이터 초기화

```python
# 컨텍스트 매니저 사용 (권장)
async with MailQueryOrchestrator() as orchestrator:
    # 작업 수행
    pass

# 또는 수동 초기화
orchestrator = MailQueryOrchestrator()
# 작업 수행
await orchestrator.close()
```

## API 메서드

### 1. mail_query_user_emails - 이메일 조회

사용자의 이메일을 조회합니다.

**입력 형식:**
```python
request = MailQueryRequest(
    user_id="사용자ID",  # 필수
    filters=MailQueryFilters(  # 선택
        date_from=datetime(2025, 6, 1),  # 시작 날짜
        date_to=datetime(2025, 6, 30),   # 종료 날짜
        sender_address="sender@example.com",      # 발신자 이메일
        has_attachments=True,             # 첨부파일 여부
        is_read=False,                    # 읽음 여부
        importance="high",                # 중요도 (low/normal/high)
        subject_contains="회의"           # 제목 포함 텍스트
    ),
    pagination=PaginationOptions(  # 선택
        top=50,        # 페이지당 항목 수 (기본: 50)
        skip=0,        # 건너뛸 항목 수 (기본: 0)
        max_pages=10   # 최대 페이지 수 (기본: 10)
    ),
    select_fields=[  # 선택 - 반환할 필드 지정
        "id", "subject", "from", "receivedDateTime", 
        "bodyPreview", "hasAttachments", "importance"
    ],
    order_by="receivedDateTime desc"  # 선택 - 정렬 기준
)

response = await orchestrator.mail_query_user_emails(request)
```

**출력 형식:**
```python
MailQueryResponse(
    messages=[  # GraphMailItem 객체 리스트
        GraphMailItem(
            id="메시지ID",
            subject="메일 제목",
            sender={
                "emailAddress": {
                    "name": "발신자 이름",
                    "address": "sender@example.com"
                }
            },
            from_address={  # Python 예약어 'from' 대신 'from_address' 사용
                "emailAddress": {
                    "name": "발신자 이름",
                    "address": "sender@example.com"
                }
            },
            to_recipients=[
                {
                    "emailAddress": {
                        "name": "수신자 이름",
                        "address": "recipient@example.com"
                    }
                }
            ],
            received_date_time=datetime(2025, 6, 16, 10, 30),
            body_preview="메일 본문 미리보기...",
            body={
                "contentType": "text",
                "content": "전체 메일 본문"
            },
            is_read=False,
            has_attachments=True,
            importance="normal",
            web_link="https://outlook.office365.com/..."
        )
    ],
    total_fetched=100,  # 조회된 총 메일 수
    has_more=True,      # 추가 데이터 존재 여부
    next_link="@odata.nextLink URL",  # 다음 페이지 링크
    execution_time_ms=250,  # 실행 시간 (밀리초)
    query_info={  # 쿼리 메타 정보
        "odata_filter": "receivedDateTime ge 2025-06-01T00:00:00.000Z and isRead eq false",
        "select_fields": ["id", "subject", "from", "receivedDateTime", "bodyPreview"],
        "pages_fetched": 2,
        "pagination": {
            "top": 50,
            "skip": 0,
            "max_pages": 10
        },
        "performance_estimate": "FAST"  # FAST/MODERATE/SLOW
    }
)
```
## 필터 옵션 상세

### MailQueryFilters 필드

| 필드 | 타입 | 설명 | 예시 |
|------|------|------|------|
| date_from | datetime | 시작 날짜 (포함) | datetime(2025, 6, 1) |
| date_to | datetime | 종료 날짜 (포함) | datetime(2025, 6, 30) |
| sender_address | str | 발신자 이메일 | "sender@example.com" |
| has_attachments | bool | 첨부파일 포함 여부 | True/False |
| is_read | bool | 읽음 상태 | True/False |
| importance | str | 중요도 | "low", "normal", "high" |
| subject_contains | str | 제목 포함 텍스트 | "회의" |

### PaginationOptions 필드

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| top | int | 50 | 페이지당 항목 수 (1-1000) |
| skip | int | 0 | 건너뛸 항목 수 |
| max_pages | int | 10 | 최대 페이지 수 (1-50) |

## 에러 처리

모든 메서드는 다음 예외를 발생시킬 수 있습니다:

- `TokenNotFoundError`: 사용자 토큰이 없음
- `TokenExpiredError`: 토큰이 만료됨
- `APIConnectionError`: API 연결 실패
- `ValidationError`: 입력 데이터 검증 실패

**에러 처리 예시:**
```python
from infra.core.exceptions import TokenNotFoundError, APIConnectionError

try:
    response = await orchestrator.mail_query_user_emails(request)
except TokenNotFoundError:
    print("토큰이 없습니다. 인증이 필요합니다.")
except APIConnectionError as e:
    print(f"API 연결 실패: {e}")
```

## 사용 예시

### 기본 이메일 조회
```python
async def get_recent_emails():
    async with MailQueryOrchestrator() as orchestrator:
        request = MailQueryRequest(
            user_id="kimghw",
            pagination=PaginationOptions(top=10)
        )
        
        response = await orchestrator.mail_query_user_emails(request)
        
        for msg in response.messages:
            print(f"제목: {msg.subject}")
            print(f"발신자: {msg.from_address.get('emailAddress', {}).get('address')}")
            print(f"수신 시간: {msg.received_date_time}")
            print("---")
```

### 필터링된 조회
```python
async def get_unread_important_emails():
    async with MailQueryOrchestrator() as orchestrator:
        filters = MailQueryFilters(
            is_read=False,
            importance="high",
            date_from=datetime.now() - timedelta(days=7)
        )
        
        request = MailQueryRequest(
            user_id="kimghw",
            filters=filters
        )
        
        response = await orchestrator.mail_query_user_emails(request)
        print(f"읽지 않은 중요 메일: {response.total_fetched}개")
```
## 성능 고려사항

1. **페이징**: 대량의 메일 조회 시 적절한 `top` 값 설정
2. **필드 선택**: 필요한 필드만 `select_fields`로 지정하여 성능 향상
3. **필터 최적화**: 날짜 범위를 좁게 설정하여 조회 성능 개선
4. **배치 처리**: 대량 저장 시 `save_messages_to_json` 사용

## 주의사항

1. 토큰은 자동으로 검증되고 필요시 갱신됩니다
2. Graph API 제한: 분당 요청 수 제한이 있습니다
3. 메일박스 정보 조회는 추가 권한이 필요할 수 있습니다
4. JSON 저장 시 파일명에 마이크로초가 포함되어 중복을 방지합니다
