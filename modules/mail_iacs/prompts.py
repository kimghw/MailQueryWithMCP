"""
IACS MCP Prompts
데이터 처리 지침 및 사용 가이드
"""

from typing import Dict, Any
from mcp.types import Prompt, PromptArgument, PromptMessage, TextContent


def get_setup_panel_prompt() -> str:
    """패널 초기 설정 가이드"""
    return """
# 📋 IACS 패널 초기 설정 가이드

## 목적
의장(Chair)이 멤버들에게 아젠다를 발행하고, 멤버들이 응답하는 시스템 구축

## 설정 순서

### 1단계: 패널 정보 등록 (insert_info)

**필수 정보:**
- `chair_address`: 의장 이메일 주소 (예: chair@iacs.org)
- `panel_name`: 패널 이름 (예: sdtp, solas, marpol)
- `kr_panel_member`: 한국 패널 멤버 이메일 (메일 조회 인증에 사용)

**데이터 처리 규칙:**
- 같은 panel_name + chair_address 조합이 있으면 기존 데이터 삭제 후 재등록
- kr_panel_member 이메일은 Microsoft Graph API 인증이 완료된 계정이어야 함

**예시:**
```
insert_info(
    chair_address="chair.sdtp@iacs.org",
    panel_name="sdtp",
    kr_panel_member="kimghw@krs.co.kr"
)
```

### 2단계: 기본 패널 설정 (insert_default_value)

**목적:**
tool 호출 시 panel_name을 생략하면 자동으로 사용될 기본 패널 지정

**데이터 처리 규칙:**
- 시스템에 하나의 기본 패널만 존재 (기존 값 덮어씀)
- search_agenda, search_responses에서 panel_name 미지정 시 이 값 사용

**예시:**
```
insert_default_value(panel_name="sdtp")
```

### 3단계: 테스트

**아젠다 검색 테스트:**
```
search_agenda(
    panel_name="sdtp",
    content_field=["id", "subject", "from"]
)
```

## 데이터 흐름

```
의장 (chair@iacs.org)
    ↓ 아젠다 발송
멤버들 (전세계)
    ↓ 응답 회신
한국 멤버 (kr_panel_member)
    ↓ 이 계정으로 메일 조회
IACS 시스템
```

## 주의사항

⚠️ **인증 필수**: kr_panel_member 계정은 반드시 Microsoft OAuth 인증 완료 필요
⚠️ **권한 확인**: kr_panel_member가 해당 메일함 접근 권한 있어야 함
⚠️ **네트워크**: Microsoft Graph API 연결 가능한 환경이어야 함
"""


def get_agenda_search_data_guide(panel_name: str = "sdtp") -> str:
    """아젠다 검색 데이터 처리 가이드"""
    return f"""
# 📧 아젠다 메일 검색 데이터 처리 가이드

## 개요
의장이 멤버들에게 보낸 아젠다 메일을 검색합니다.

## 데이터 처리 방식

### 검색 메커니즘: $filter 방식
- **Microsoft Graph API의 $filter 쿼리 사용**
- `sender_address`로 의장 이메일 필터링
- 정확한 일치 검색 (부분 검색 아님)

### 데이터 흐름

```
1. panel_name으로 DB에서 chair_address 조회
   └─> iacs_panel_chair 테이블
       └─> panel_name="{panel_name}" → chair_address

2. kr_panel_member로 Microsoft Graph API 인증

3. $filter 쿼리 생성
   └─> from/emailAddress/address eq 'chair@iacs.org'
   └─> receivedDateTime ge 2024-07-14T00:00:00Z
   └─> receivedDateTime le 2025-10-14T00:00:00Z

4. 추가 필터링 (옵션)
   └─> agenda_code 있으면 subject contains 조건 추가

5. $select로 필요한 필드만 조회
   └─> 네트워크 트래픽 최소화
```

## 입력 파라미터 상세

### panel_name (옵션)
- 기본값: default_value 테이블의 값 사용
- 용도: chair_address 조회용
- 예시: "sdtp", "solas", "marpol"

### start_date / end_date (옵션)
- 기본값:
  - start_date: 현재 시간
  - end_date: 3개월 전
- 형식: ISO 8601 (예: "2025-10-14T00:00:00Z")
- **주의**: start_date가 더 최근, end_date가 더 과거

### agenda_code (옵션)
- 용도: 제목(subject)에서 키워드 필터링
- 예시: "SDTP-2024", "SOLAS-25-001"
- 처리: subject contains '{panel_name}agenda_code'

### content_field (옵션)
- 기본값: ["subject"]
- 조회할 필드 지정
- **성능 최적화**: 필요한 필드만 선택
- 예시:
  ```
  ["id", "subject", "from", "receivedDateTime"]
  ["id", "subject", "body", "attachments"]
  ```

## 출력 데이터 구조

```json
{{
  "success": true,
  "message": "5개의 아젠다를 찾았습니다",
  "total_count": 5,
  "panel_name": "sdtp",
  "chair_address": "chair.sdtp@iacs.org",
  "kr_panel_member": "kimghw@krs.co.kr",
  "mails": [
    {{
      "id": "AAMkAG...",
      "subject": "SDTP-2024-001 Agenda for Review",
      "from_address": {{
        "emailAddress": {{
          "name": "SDTP Chair",
          "address": "chair.sdtp@iacs.org"
        }}
      }},
      "received_date_time": "2025-10-01T09:30:00Z"
    }}
  ]
}}
```

## 데이터 처리 주의사항

⚠️ **날짜 역순**: start_date(최근) > end_date(과거)
⚠️ **필터 정확도**: $filter는 정확 일치, 부분 검색 필요 시 agenda_code 사용
⚠️ **성능**: content_field에 body, attachments 포함 시 응답 시간 증가
⚠️ **권한**: kr_panel_member가 해당 메일함 접근 권한 필요

## 사용 예시

**기본 검색:**
```
search_agenda(
    panel_name="{panel_name}",
    content_field=["id", "subject", "from", "receivedDateTime"]
)
```

**특정 아젠다 코드로 필터링:**
```
search_agenda(
    panel_name="{panel_name}",
    agenda_code="SDTP-2024",
    content_field=["id", "subject", "body"]
)
```

**날짜 범위 지정:**
```
search_agenda(
    panel_name="{panel_name}",
    start_date="2025-10-14T00:00:00Z",
    end_date="2025-09-01T00:00:00Z",
    content_field=["id", "subject"]
)
```
"""


def get_response_search_data_guide() -> str:
    """응답 메일 검색 데이터 처리 가이드"""
    return """
# 💬 응답 메일 검색 데이터 처리 가이드

## 개요
멤버들이 의장에게 보낸 응답 메일을 검색합니다.

## 데이터 처리 방식

### 검색 메커니즘: $search 방식
- **Microsoft Graph API의 $search 쿼리 사용**
- 제목(subject)에서 키워드 검색
- 전체 텍스트 검색 (부분 일치 가능)

### 데이터 흐름

```
1. default_value 테이블에서 기본 패널 조회
   └─> kr_panel_member 가져오기

2. agenda_code 앞 7자 추출
   └─> "SDTP-2024-001" → "SDTP-20"
   └─> 이유: 응답 메일 제목이 아젠다 코드로 시작하는 패턴

3. $search 쿼리 생성
   └─> search query: "subject:SDTP-20"

4. Microsoft Graph API 호출
   └─> kr_panel_member로 인증

5. 클라이언트 측 필터링
   └─> subject에 search_keyword 포함 확인
   └─> send_address 리스트로 발신자 필터링 (옵션)

6. 필터링된 결과 반환
```

## 입력 파라미터 상세

### agenda_code (필수)
- 검색할 아젠다 코드
- **최소 7자 이상**
- 앞 7자만 사용하여 검색
- 예시:
  - "SDTP-2024-001" → "SDTP-20" 검색
  - "SOLAS-25-003" → "SOLAS-2" 검색

### send_address (옵션)
- 특정 발신자로 필터링
- 리스트 형태로 복수 지정 가능
- 클라이언트 측 후처리
- 예시:
  ```
  ["member1@company.com", "member2@org.kr"]
  ```

### content_field (옵션)
- 기본값: ["subject"]
- 조회할 필드 지정
- 예시:
  ```
  ["id", "subject", "from", "receivedDateTime"]
  ["id", "subject", "body"]
  ```

## 데이터 처리 알고리즘

### 1단계: 서버 측 검색 ($search)
```
agenda_code = "SDTP-2024-001"
search_keyword = agenda_code[:7]  # "SDTP-20"
search_query = f"subject:{search_keyword}"

→ Microsoft Graph API $search 호출
```

### 2단계: 클라이언트 측 필터링

**제목 검증:**
```python
for mail in response.messages:
    subject = mail.subject or ""
    if search_keyword not in subject:
        continue  # 제외
```

**발신자 필터링 (send_address 있을 때):**
```python
if send_address:
    from_addr = mail.from_address.emailAddress.address
    if from_addr not in send_address:
        continue  # 제외
```

## 출력 데이터 구조

```json
{
  "success": true,
  "message": "3개의 응답을 찾았습니다",
  "total_count": 3,
  "agenda_code": "SDTP-2024-001",
  "mails": [
    {
      "id": "AAMkAG...",
      "subject": "Re: SDTP-2024-001 Comments from Korea",
      "from_address": {
        "emailAddress": {
          "name": "Kim GH",
          "address": "member@krs.co.kr"
        }
      },
      "received_date_time": "2025-10-02T14:20:00Z"
    }
  ]
}
```

## 검색 정확도 개선 팁

### agenda_code 길이별 정확도

| 길이 | 예시 | 정확도 | 비고 |
|------|------|--------|------|
| 7자 | SDTP-20 | 중간 | 같은 년도 아젠다 모두 매칭 |
| 10자 | SDTP-2024- | 높음 | 특정 년도 아젠다만 매칭 |
| 12자+ | SDTP-2024-001 | 매우 높음 | 특정 아젠다만 매칭 |

**권장:** 가능한 한 구체적인 코드 사용

### 발신자 필터링 활용

```
# 특정 국가/기관의 응답만 조회
send_address=[
    "kr.member@krs.co.kr",
    "jp.member@nk.jp",
    "cn.member@ccs.cn"
]
```

## 데이터 처리 주의사항

⚠️ **agenda_code 길이**: 최소 7자 이상 필요
⚠️ **검색 지연**: $search는 $filter보다 느릴 수 있음 (인덱싱 의존)
⚠️ **클라이언트 필터**: 최종 필터링은 클라이언트 측에서 수행
⚠️ **권한**: 기본 패널의 kr_panel_member 인증 필요

## 사용 예시

**기본 검색:**
```
search_responses(
    agenda_code="SDTP-2024-001",
    content_field=["id", "subject", "from"]
)
```

**특정 발신자만:**
```
search_responses(
    agenda_code="SDTP-2024-001",
    send_address=["member1@krs.co.kr", "member2@nk.jp"],
    content_field=["id", "subject", "body"]
)
```

**넓은 검색 (같은 년도 모든 응답):**
```
search_responses(
    agenda_code="SDTP-2024",  # 7자
    content_field=["id", "subject"]
)
```
"""


def get_data_management_guide() -> str:
    """데이터 관리 가이드"""
    return r"""
# 🗄️ IACS 데이터 관리 가이드

## 데이터베이스 구조

### 테이블 1: iacs_panel_chair

**목적:** 패널별 의장 및 한국 멤버 정보 저장

**스키마:**
```sql
CREATE TABLE iacs_panel_chair (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chair_address TEXT NOT NULL,
    panel_name TEXT NOT NULL,
    kr_panel_member TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(panel_name, chair_address)
);
```

**제약조건:**
- `panel_name` + `chair_address` 조합이 UNIQUE
- 같은 조합 입력 시 기존 레코드 삭제 후 신규 삽입

**데이터 예시:**
```
| id | chair_address      | panel_name | kr_panel_member    |
|----|-------------------|------------|-------------------|
| 1  | chair.sdtp@iacs   | sdtp       | kimghw@krs.co.kr  |
| 2  | chair.solas@iacs  | solas      | kimghw@krs.co.kr  |
| 3  | chair.marpol@iacs | marpol     | leejh@krs.co.kr   |
```

### 테이블 2: iacs_default_value

**목적:** 기본 패널 설정 (시스템 전역)

**스키마:**
```sql
CREATE TABLE iacs_default_value (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    panel_name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**제약조건:**
- `panel_name`이 UNIQUE → 하나의 레코드만 존재
- 신규 입력 시 기존 레코드 삭제 후 신규 삽입

**데이터 예시:**
```
| id | panel_name |
|----|-----------|
| 1  | sdtp      |
```

## 데이터 처리 규칙

### 1. 데이터 삽입 (insert_info)

**처리 로직:**
```
1. 입력: chair_address, panel_name, kr_panel_member
2. 중복 체크: SELECT WHERE panel_name=? AND chair_address=?
3. 중복 시: DELETE 기존 레코드
4. INSERT 신규 레코드
5. 커밋
```

**멱등성(Idempotency):**
- 같은 데이터 여러 번 입력해도 결과 동일
- 최신 데이터로 덮어씀

### 2. 기본값 설정 (insert_default_value)

**처리 로직:**
```
1. 입력: panel_name
2. DELETE 기존 레코드 (전체)
3. INSERT 신규 레코드
4. 커밋
```

**단일성:**
- 시스템에 하나의 기본 패널만 존재
- 변경 시 기존 값 자동 삭제

### 3. 패널 정보 조회 (search_agenda, search_responses)

**조회 로직:**
```sql
-- panel_name으로 조회
SELECT chair_address, kr_panel_member
FROM iacs_panel_chair
WHERE panel_name = ?;

-- 기본 패널 조회
SELECT panel_name
FROM iacs_default_value
LIMIT 1;
```

## 데이터 일관성 유지

### 외래키 없는 설계
- iacs_default_value.panel_name은 iacs_panel_chair.panel_name 참조
- **하지만 외래키 제약 없음** (유연성 위해)

### 데이터 정합성 체크

**주의할 시나리오:**
```
1. default_value에 "sdtp" 설정
2. iacs_panel_chair에서 "sdtp" 레코드 삭제
   → default_value는 남아있음 (고아 데이터)
3. search_agenda 호출 시 패널 정보 없음 오류
```

**권장 사항:**
- 패널 삭제 시 default_value도 함께 확인
- 또는 default_value를 다른 패널로 변경

## 데이터 백업 및 복구

### 백업
```bash
# SQLite 백업
sqlite3 mail_query.db ".backup backup_$(date +%Y%m%d).db"

# 테이블별 백업 (CSV)
sqlite3 -header -csv mail_query.db "SELECT * FROM iacs_panel_chair" > panel_chair.csv
```

### 복구
```bash
# 전체 복구
cp backup_20251014.db mail_query.db

# CSV에서 복구
sqlite3 mail_query.db <<EOF
.mode csv
.import panel_chair.csv iacs_panel_chair
EOF
```

## 데이터 마이그레이션

### 스키마 변경 시
```sql
-- 1. 새 테이블 생성
CREATE TABLE iacs_panel_chair_new (...);

-- 2. 데이터 복사
INSERT INTO iacs_panel_chair_new
SELECT * FROM iacs_panel_chair;

-- 3. 기존 테이블 삭제
DROP TABLE iacs_panel_chair;

-- 4. 테이블 이름 변경
ALTER TABLE iacs_panel_chair_new
RENAME TO iacs_panel_chair;
```

## 데이터 모니터링

### 주요 메트릭
- 등록된 패널 수
- 패널별 아젠다 검색 횟수
- 응답 메일 검색 횟수
- 인증 실패 횟수 (kr_panel_member)

### 로그 확인
```bash
# 데이터 처리 로그
tail -f logs/local/iacs.log | grep "insert_info\|search_agenda\|search_responses"
```
"""


async def get_prompt(name: str, arguments: Dict[str, Any]) -> PromptMessage:
    """
    Get specific prompt by name

    Available prompts:
    - setup_panel: 패널 초기 설정 가이드
    - agenda_search_data: 아젠다 검색 데이터 처리 가이드
    - response_search_data: 응답 검색 데이터 처리 가이드
    - data_management: 데이터 관리 가이드
    """

    if name == "setup_panel":
        prompt_content = get_setup_panel_prompt()

    elif name == "agenda_search_data":
        panel_name = arguments.get("panel_name", "sdtp")
        prompt_content = get_agenda_search_data_guide(panel_name)

    elif name == "response_search_data":
        prompt_content = get_response_search_data_guide()

    elif name == "data_management":
        prompt_content = get_data_management_guide()

    else:
        raise ValueError(f"Unknown prompt: {name}")

    return PromptMessage(
        role="assistant",
        content=TextContent(type="text", text=prompt_content)
    )
