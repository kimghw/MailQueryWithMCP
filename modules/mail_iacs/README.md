# IACS 메일 관리 모듈

의장(Chair)이 멤버들에게 아젠다를 발행하고, 멤버들이 그 아젠다에 대한 응답을 회신하는 시스템입니다.

## 목차

- [개요](#개요)
- [아키텍처](#아키텍처)
- [설치 및 실행](#설치-및-실행)
- [MCP Tools](#mcp-tools)
- [사용 예시](#사용-예시)
- [DB 스키마](#db-스키마)

## 개요

### 주요 기능

1. **패널 관리**: 의장 및 한국 멤버 정보 저장
2. **아젠다 검색**: 의장이 보낸 아젠다 메일 검색 ($filter 방식)
3. **응답 검색**: 멤버들이 보낸 응답 메일 검색 ($search 방식)
4. **기본값 설정**: 기본 패널 이름 설정

### 시스템 흐름

```
1. 의장 정보 등록 (insert_info)
   └─> chair_address, panel_name, kr_panel_member

2. 기본 패널 설정 (insert_default_value)
   └─> panel_name

3. 아젠다 검색 (search_agenda)
   └─> 의장 → 멤버 방향 메일
   └─> $filter (sender_address)

4. 응답 검색 (search_responses)
   └─> 멤버 → 의장 방향 메일
   └─> $search (agenda_code)
```

## 아키텍처

### 디렉토리 구조

```
modules/mail_iacs/
├── __init__.py              # 모듈 Export
├── schemas.py               # Pydantic 데이터 모델
├── db_service.py            # DB 서비스 레이어
├── tools.py                 # MCP Tools 구현
├── schema.sql               # DB 스키마
├── entrypoints/
│   ├── stdio_server.py      # stdio MCP 서버
│   └── http_server.py       # HTTP API 서버
├── tests/
│   └── test_tools.py        # 테스트 스크립트
└── README.md                # 문서
```

### 레이어 구조

```
┌─────────────────────────────────┐
│   MCP Server (stdio/http)       │
├─────────────────────────────────┤
│   IACSTools (비즈니스 로직)     │
├─────────────────────────────────┤
│   IACSDBService (데이터 접근)   │
├─────────────────────────────────┤
│   MailQueryOrchestrator          │
│   (mail_query 모듈 활용)        │
└─────────────────────────────────┘
```

## 설치 및 실행

### 1. stdio 서버 (Claude Desktop)

```bash
# 직접 실행
python modules/mail_iacs/entrypoints/stdio_server.py

# Claude Desktop 설정 (claude_desktop_config.json)
{
  "mcpServers": {
    "iacs-mail": {
      "command": "python",
      "args": [
        "/absolute/path/to/modules/mail_iacs/entrypoints/stdio_server.py"
      ]
    }
  }
}
```

### 2. HTTP 서버 (RESTful API)

```bash
# 서버 실행 (기본 포트: 8002)
python modules/mail_iacs/entrypoints/http_server.py

# 포트 변경
IACS_SERVER_PORT=9000 python modules/mail_iacs/entrypoints/http_server.py

# 헬스 체크
curl http://localhost:8002/health
```

## MCP Tools

### 1. insert_info

패널 의장 및 멤버 정보 삽입

**입력:**
```json
{
  "chair_address": "chair@example.com",
  "panel_name": "sdtp",
  "kr_panel_member": "member@example.com"
}
```

**출력:**
```json
{
  "success": true,
  "message": "패널 정보가 성공적으로 저장되었습니다: sdtp",
  "panel_name": "sdtp",
  "chair_address": "chair@example.com",
  "kr_panel_member": "member@example.com"
}
```

### 2. search_agenda

의장이 보낸 아젠다 메일 검색

**특징:**
- `$filter` 방식 사용 (sender_address로 필터링)
- 날짜 범위 지정 가능 (기본: 현재 ~ 3개월 전)
- agenda_code로 추가 필터링 가능

**입력:**
```json
{
  "panel_name": "sdtp",
  "content_field": ["id", "subject", "body", "attachments"],
  "agenda_code": "SDTP-2024",
  "start_date": "2025-01-14T00:00:00Z",
  "end_date": "2024-10-14T00:00:00Z"
}
```

**출력:**
```json
{
  "success": true,
  "message": "5개의 아젠다를 찾았습니다",
  "total_count": 5,
  "panel_name": "sdtp",
  "chair_address": "chair@example.com",
  "kr_panel_member": "member@example.com",
  "mails": [...]
}
```

### 3. search_responses

멤버들이 보낸 응답 메일 검색

**특징:**
- `$search` 방식 사용 (subject 키워드 검색)
- agenda_code 앞 7자로 매칭
- send_address로 발신자 필터링 (옵션)

**입력:**
```json
{
  "agenda_code": "SDTP-2024-001",
  "content_field": ["id", "subject", "body"],
  "send_address": ["member1@example.com", "member2@example.com"]
}
```

**출력:**
```json
{
  "success": true,
  "message": "3개의 응답을 찾았습니다",
  "total_count": 3,
  "agenda_code": "SDTP-2024-001",
  "mails": [...]
}
```

### 4. insert_default_value

기본 패널 이름 설정

**입력:**
```json
{
  "panel_name": "sdtp"
}
```

**출력:**
```json
{
  "success": true,
  "message": "기본 패널이 설정되었습니다: sdtp",
  "panel_name": "sdtp"
}
```

## 사용 예시

### Python 코드

```python
import asyncio
from modules.mail_iacs import (
    IACSTools,
    InsertInfoRequest,
    SearchAgendaRequest,
    SearchResponsesRequest,
)

async def main():
    tools = IACSTools()

    # 1. 패널 정보 등록
    request = InsertInfoRequest(
        chair_address="chair@iacs.org",
        panel_name="sdtp",
        kr_panel_member="kr.member@company.com"
    )
    response = await tools.insert_info(request)
    print(f"등록 완료: {response.success}")

    # 2. 아젠다 검색
    request = SearchAgendaRequest(
        panel_name="sdtp",
        agenda_code="SDTP-2024",
        content_field=["id", "subject", "from", "receivedDateTime"]
    )
    response = await tools.search_agenda(request)
    print(f"아젠다 {response.total_count}개 발견")

    # 3. 응답 검색
    request = SearchResponsesRequest(
        agenda_code="SDTP-2024-001",
        content_field=["id", "subject", "from"]
    )
    response = await tools.search_responses(request)
    print(f"응답 {response.total_count}개 발견")

asyncio.run(main())
```

### HTTP API

```bash
# 1. 패널 정보 등록
curl -X POST http://localhost:8002/api/insert_info \
  -H "Content-Type: application/json" \
  -d '{
    "chair_address": "chair@example.com",
    "panel_name": "sdtp",
    "kr_panel_member": "member@example.com"
  }'

# 2. 아젠다 검색
curl -X POST http://localhost:8002/api/search_agenda \
  -H "Content-Type: application/json" \
  -d '{
    "panel_name": "sdtp",
    "content_field": ["id", "subject"]
  }'

# 3. 응답 검색
curl -X POST http://localhost:8002/api/search_responses \
  -H "Content-Type: application/json" \
  -d '{
    "agenda_code": "SDTP-2024-001",
    "content_field": ["id", "subject"]
  }'
```

## DB 스키마

### iacs_panel_chair 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER | Primary Key |
| chair_address | TEXT | 의장 이메일 주소 |
| panel_name | TEXT | 패널 이름 |
| kr_panel_member | TEXT | 한국 패널 멤버 이메일 |
| created_at | TIMESTAMP | 생성 시간 |
| updated_at | TIMESTAMP | 수정 시간 |

**제약조건:**
- UNIQUE(panel_name, chair_address)

### iacs_default_value 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER | Primary Key |
| panel_name | TEXT | 기본 패널 이름 (UNIQUE) |
| created_at | TIMESTAMP | 생성 시간 |
| updated_at | TIMESTAMP | 수정 시간 |

## 의존성

- **infra.core**: 데이터베이스, 로거, 설정 관리
- **modules.mail_query**: 메일 조회 ($filter, $search)
- **mcp**: MCP 프로토콜
- **fastapi**: HTTP API 서버
- **pydantic**: 데이터 검증

## 테스트

```bash
# 단위 테스트
python modules/mail_iacs/tests/test_tools.py

# HTTP 서버 테스트
pytest modules/mail_iacs/tests/
```

## 문제 해결

### 1. 스키마 초기화 실패

```bash
# 수동 스키마 적용
sqlite3 mail_query.db < modules/mail_iacs/schema.sql
```

### 2. 메일 조회 실패

- **인증 확인**: kr_panel_member 이메일이 올바른지 확인
- **토큰 확인**: Microsoft Graph API 토큰이 유효한지 확인
- **패널 정보**: panel_name이 DB에 등록되어 있는지 확인

### 3. 응답 검색 결과 없음

- **agenda_code**: 7자 이상이어야 함
- **제목 형식**: 응답 메일 제목이 agenda_code로 시작해야 함
- **기본 패널**: default_value 테이블에 패널이 설정되어 있어야 함

## 라이선스

MIT License
