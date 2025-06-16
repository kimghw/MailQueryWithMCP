# Mail Query 모듈

Microsoft Graph API를 통한 메일 데이터 조회 및 필터링을 담당하는 핵심 모듈입니다.

## 📋 개요

Mail Query 모듈은 **완전 독립적**으로 설계되어 다른 모듈(`account`, `auth`)에 의존하지 않으며, `infra` 서비스를 최대한 활용하여 중복을 제거하고 Graph API 호출과 OData 필터링에만 집중합니다.

### 핵심 기능
- ✅ Microsoft Graph API `/me/messages` 엔드포인트 호출
- ✅ OData 필터링 (날짜, 발신자, 제목, 읽음 상태 등)
- ✅ 페이징 처리 (`$top`, `$skip`, `@odata.nextLink`)
- ✅ 메시지 검색 (`$search` 지원)
- ✅ 조회 로그 기록 및 성능 분석
- ✅ 견고한 오류 처리 및 재시도 로직

## 🏗️ 아키텍처

### 모듈 구조
```
modules/mail_query/
├── __init__.py                    # 모듈 초기화 및 공개 API
├── mail_query_orchestrator.py     # 메인 오케스트레이터 (완전 독립적)
├── mail_query_schema.py           # Pydantic 데이터 모델
├── graph_api_client.py            # Microsoft Graph API 클라이언트
├── odata_filter_builder.py        # OData 필터 문자열 생성
├── _mail_query_helpers.py         # 유틸리티 함수
└── README.md                      # 모듈 사용법 가이드
```

### 의존성 관계 (단방향)
```
MailQueryOrchestrator (메인 API)
    ↓ (모듈 내부 구현)
GraphAPIClient + ODataFilterBuilder + Helpers
    ↓ (infra 서비스 직접 사용)
infra.core.token_service (토큰 관리)
infra.core.database (로그 저장)
infra.core.config (설정)
infra.core.logger (로깅)
```

## 🚀 사용법

### 기본 메일 조회

```python
from modules.mail_query import MailQueryRequest, MailQueryFilters, PaginationOptions
from modules.mail_query import get_mail_query_orchestrator

# 오케스트레이터 생성
orchestrator = get_mail_query_orchestrator()

# 기본 조회 요청
request = MailQueryRequest(
    user_id="user@example.com",
    pagination=PaginationOptions(top=50, skip=0, max_pages=5)
)

# 메일 조회 실행
response = await orchestrator.mail_query_user_emails(request)

print(f"조회된 메일 수: {response.total_fetched}")
print(f"실행 시간: {response.execution_time_ms}ms")
```

### 필터링된 메일 조회

```python
from datetime import datetime, timedelta

# 필터 조건 설정
filters = MailQueryFilters(
    date_from=datetime.now() - timedelta(days=7),  # 최근 7일
    sender_address="important@company.com",        # 특정 발신자
    is_read=False,                                 # 읽지 않은 메일
    has_attachments=True                           # 첨부파일 있는 메일
)

request = MailQueryRequest(
    user_id="user@example.com",
    filters=filters,
    select_fields=["id", "subject", "from", "receivedDateTime", "bodyPreview"]
)

response = await orchestrator.mail_query_user_emails(request)
```

### 메시지 검색

```python
# 전체 텍스트 검색
search_response = await orchestrator.mail_query_search_messages(
    user_id="user@example.com",
    search_term="프로젝트 보고서",
    select_fields=["id", "subject", "from", "bodyPreview"],
    top=100
)
```

### 특정 메시지 조회

```python
# 메시지 ID로 상세 조회
message = await orchestrator.mail_query_get_message_by_id(
    user_id="user@example.com",
    message_id="AAMkAGE...",
    select_fields=["id", "subject", "body", "attachments"]
)
```

### 메일박스 정보 조회

```python
# 사용자 메일박스 설정 정보
mailbox_info = await orchestrator.mail_query_get_mailbox_info("user@example.com")
print(f"표시 이름: {mailbox_info.display_name}")
print(f"시간대: {mailbox_info.time_zone}")
```

## 📊 데이터 모델

### 주요 스키마

#### MailQueryRequest
```python
class MailQueryRequest(BaseModel):
    user_id: str                                    # 사용자 ID (필수)
    filters: Optional[MailQueryFilters] = None      # 필터 조건
    pagination: Optional[PaginationOptions] = None  # 페이징 옵션
    select_fields: Optional[List[str]] = None       # 선택할 필드
```

#### MailQueryFilters
```python
class MailQueryFilters(BaseModel):
    date_from: Optional[datetime] = None        # 시작 날짜
    date_to: Optional[datetime] = None          # 종료 날짜
    sender_address: Optional[str] = None        # 발신자 이메일
    subject_contains: Optional[str] = None      # 제목 포함 텍스트
    is_read: Optional[bool] = None              # 읽음 상태
    has_attachments: Optional[bool] = None      # 첨부파일 여부
    importance: Optional[str] = None            # 중요도 (low/normal/high)
```

#### MailQueryResponse
```python
class MailQueryResponse(BaseModel):
    user_id: str                           # 사용자 ID
    total_fetched: int                     # 조회된 메일 수
    messages: List[GraphMailItem]          # 메일 목록
    has_more: bool                         # 추가 데이터 여부
    next_link: Optional[str] = None        # 다음 페이지 링크
    execution_time_ms: int                 # 실행 시간(밀리초)
    query_info: Dict[str, Any]             # 쿼리 정보
```

## 🔧 고급 기능

### 성능 최적화

```python
# 필요한 필드만 선택하여 페이로드 최소화
select_fields = ["id", "subject", "from", "receivedDateTime", "bodyPreview"]

# 페이지 크기 조정 (기본: 50, 최대: 1000)
pagination = PaginationOptions(top=100, max_pages=10)

# 성능 예상 확인
orchestrator = get_mail_query_orchestrator()
performance = orchestrator.filter_builder.estimate_query_performance(filters, 100)
print(f"예상 성능: {performance}")  # FAST/MODERATE/SLOW
```

### 오류 처리

```python
from infra.core.exceptions import AuthenticationError, APIConnectionError

try:
    response = await orchestrator.mail_query_user_emails(request)
except AuthenticationError as e:
    print(f"인증 오류: {e}")
    # 토큰 갱신 필요
except APIConnectionError as e:
    print(f"API 연결 오류: {e}")
    # 재시도 또는 대체 로직
except Exception as e:
    print(f"일반 오류: {e}")
```

### 로그 분석

모든 쿼리는 `query_logs` 테이블에 자동 기록됩니다:

```sql
SELECT 
    user_id,
    query_type,
    result_count,
    execution_time_ms,
    has_error,
    created_at
FROM query_logs 
WHERE user_id = 'user@example.com'
ORDER BY created_at DESC;
```

## 📈 성능 가이드라인

### 권장 사항
- **페이지 크기**: 50-100개 (기본: 50)
- **최대 페이지**: 10페이지 이하 권장
- **필터 조건**: 5개 이하로 제한
- **선택 필드**: 필요한 필드만 지정

### 성능 최적화 팁
1. **날짜 필터 우선 사용**: 인덱스가 있어 빠름
2. **텍스트 검색 최소화**: `subject_contains`는 느림
3. **적절한 페이지 크기**: 너무 크면 타임아웃 위험
4. **필드 선택 활용**: `bodyPreview` vs `body` 구분

## 🔗 연동 가이드

### infra 서비스 의존성
- `infra.core.token_service`: 자동 토큰 관리
- `infra.core.database`: 로그 저장
- `infra.core.config`: 설정 관리
- `infra.core.logger`: 구조화된 로깅

### 다른 모듈과의 연동
```python
# 향후 mail_processor 모듈에서 사용 예시
from modules.mail_query import query_user_emails, MailQueryRequest

async def process_recent_emails(user_id: str):
    request = MailQueryRequest(
        user_id=user_id,
        filters=MailQueryFilters(
            date_from=datetime.now() - timedelta(hours=1),
            is_read=False
        )
    )
    
    response = await query_user_emails(request)
    
    # 메일 처리 로직
    for message in response.messages:
        await process_message(message)
```

## 🚨 제한 사항

### Microsoft Graph API 제한
- **스로틀링**: 초당 2,000개 요청 제한
- **페이지 크기**: 최대 1,000개
- **검색 결과**: `$search`는 250개 제한
- **토큰 만료**: 59분마다 자동 갱신 필요

### 모듈 제한
- **필터 복잡성**: 5개 조건 이하 권장
- **페이징**: 최대 50페이지
- **파일 크기**: 모든 파일 350줄 이하 유지

## 🔍 문제 해결

### 일반적인 오류

1. **TokenExpiredError**
   - 원인: 액세스 토큰 만료
   - 해결: `infra.token_service`가 자동 처리

2. **InefficientFilter**
   - 원인: 복잡한 필터 조건
   - 해결: 필터 조건 단순화

3. **TooManyRequests (429)**
   - 원인: API 스로틀링
   - 해결: 자동 재시도 (Retry-After 준수)

### 디버깅 팁
```python
import logging
logging.getLogger('modules.mail_query').setLevel(logging.DEBUG)

# 상세 로그 확인
response = await orchestrator.mail_query_user_emails(request)
print(f"쿼리 정보: {response.query_info}")
```

## 📚 참고 자료

- [Microsoft Graph API 문서](https://learn.microsoft.com/en-us/graph/)
- [OData 쿼리 매개변수](https://learn.microsoft.com/en-us/graph/query-parameters)
- [Graph API 스로틀링 가이드](https://learn.microsoft.com/en-us/graph/throttling)
- [프로젝트 아키텍처 가이드](../../.clinerules/proejctArchitecture.md)

---

**버전**: 1.0.0  
**최종 업데이트**: 2025-06-16  
**담당자**: IACSGRAPH Team
