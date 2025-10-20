# 핸들러 직접 테스트

핸들러를 JSON-RPC 형식으로 직접 테스트할 수 있는 도구입니다.

## 📁 파일 구조

```
tests/handlers/
├── README.md                          # 이 파일
├── run_jsonrpc_tests.py              # JSON 파일 기반 테스트 실행기 ⭐ 권장
├── test_with_jsonrpc.py              # 단일 툴 JSON-RPC 테스트
├── jsonrpc_cases/                     # JSON-RPC 테스트 케이스 모음
│   ├── enrollment.json               # Enrollment 테스트 케이스
│   ├── mail-query.json               # Mail Query 테스트 케이스
│   └── onenote.json                  # OneNote 테스트 케이스
├── test_enrollment_handlers.py       # Enrollment 자동 테스트
├── test_mail_query_handlers.py       # Mail Query 자동 테스트
├── test_onenote_handlers.py          # OneNote 자동 테스트
└── run_tests.sh                       # 자동 테스트 실행 스크립트
```

## 🚀 사용법

### 방법 1: JSON 파일 기반 테스트 (권장) ⭐

JSON 파일에 정의된 테스트 케이스를 실행합니다. **테스트 케이스를 추가/수정하기 가장 쉬운 방법입니다.**

```bash
# 특정 모듈 테스트
python tests/handlers/run_jsonrpc_tests.py enrollment
python tests/handlers/run_jsonrpc_tests.py mail-query
python tests/handlers/run_jsonrpc_tests.py onenote

# 모든 모듈 테스트
python tests/handlers/run_jsonrpc_tests.py all
```

#### 테스트 케이스 추가/수정 방법

1. **테스트 케이스 파일 열기:**
   - `tests/handlers/jsonrpc_cases/enrollment.json`
   - `tests/handlers/jsonrpc_cases/mail-query.json`
   - `tests/handlers/jsonrpc_cases/onenote.json`

2. **테스트 케이스 추가:**
   ```json
   {
     "name": "내가 추가한 테스트",
     "enabled": true,
     "tool": "query_email",
     "arguments": {
       "user_id": "kimghw",
       "days_back": 7,
       "subject_keywords": ["중요"]
     },
     "expect": {
       "contains": ["메일 조회 결과"]
     }
   }
   ```

3. **테스트 활성화/비활성화:**
   ```json
   {
     "enabled": true   // true: 실행, false: 건너뜀
   }
   ```

4. **테스트 실행:**
   ```bash
   python tests/handlers/run_jsonrpc_tests.py mail-query
   ```

#### 테스트 케이스 구조

```json
{
  "module": "enrollment",
  "description": "모듈 설명",
  "test_cases": [
    {
      "name": "테스트 이름",
      "enabled": true,
      "tool": "툴 이름",
      "arguments": {
        "param1": "value1",
        "param2": "value2"
      },
      "expect": {
        "contains": ["예상 결과1", "예상 결과2"]
      }
    }
  ]
}
```

- `name`: 테스트 케이스 이름
- `enabled`: 활성화 여부 (true/false)
- `tool`: 호출할 툴 이름
- `arguments`: 툴에 전달할 인자
- `expect.contains`: 결과에 포함되어야 할 문자열 (하나라도 포함되면 성공)

### 방법 2: 단일 툴 테스트

개별 툴을 빠르게 테스트할 때 사용합니다.

**기본 사용법:**
```bash
python tests/handlers/test_with_jsonrpc.py <module> <tool_name> <json_args>
```

**예시:**

#### Enrollment 모듈
```bash
# 환경변수로 계정 등록
python tests/handlers/test_with_jsonrpc.py enrollment register_account '{"use_env_vars":true}'

# 활성 계정 목록
python tests/handlers/test_with_jsonrpc.py enrollment list_active_accounts '{}'

# 계정 상태 조회
python tests/handlers/test_with_jsonrpc.py enrollment get_account_status '{"user_id":"kimghw"}'
```

#### Mail Query 모듈
```bash
# 도움말
python tests/handlers/test_with_jsonrpc.py mail-query help '{}'

# 메일 조회 (최근 3일)
python tests/handlers/test_with_jsonrpc.py mail-query query_email '{"user_id":"kimghw","days_back":3,"include_body":false}'

# 첨부파일 검색
python tests/handlers/test_with_jsonrpc.py mail-query attachmentManager '{"user_id":"kimghw","start_date":"2025-10-18","end_date":"2025-10-20","filename_keywords":["pdf"],"save_enabled":false}'
```

#### OneNote 모듈
```bash
# 노트북 목록
python tests/handlers/test_with_jsonrpc.py onenote list_notebooks '{"user_id":"kimghw"}'

# 섹션 정보 저장
python tests/handlers/test_with_jsonrpc.py onenote save_section_info '{"user_id":"kimghw","notebook_id":"1-xxx","section_id":"1-yyy","section_name":"My Section"}'
```

### 방법 3: 자동화된 테스트 스크립트

Python 코드로 작성된 자동 테스트를 실행합니다.

```bash
# Enrollment 핸들러 테스트
python tests/handlers/test_enrollment_handlers.py

# Mail Query 핸들러 테스트
python tests/handlers/test_mail_query_handlers.py

# OneNote 핸들러 테스트
python tests/handlers/test_onenote_handlers.py

# 또는 스크립트로 실행
bash tests/handlers/run_tests.sh enrollment
bash tests/handlers/run_tests.sh mail-query
bash tests/handlers/run_tests.sh onenote
bash tests/handlers/run_tests.sh  # 전체
```

## 📋 JSON-RPC 요청/응답 형식

### 요청 형식
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {
      "param1": "value1",
      "param2": "value2"
    }
  }
}
```

### 응답 형식

**성공:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "결과 메시지..."
      }
    ]
  }
}
```

**실패:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32603,
    "message": "Internal error",
    "data": {
      "type": "ExceptionType",
      "message": "에러 메시지..."
    }
  }
}
```

## 🔧 환경 설정

테스트 실행 전에 환경변수가 설정되어 있어야 합니다:

```bash
# .env 파일에 설정된 환경변수 사용
export PYTHONPATH=/home/kimghw/MailQueryWithMCP

# 또는 직접 실행 시 PYTHONPATH 지정
PYTHONPATH=/home/kimghw/MailQueryWithMCP python tests/handlers/run_jsonrpc_tests.py enrollment
```

## 💡 팁

### 1. 테스트 케이스 관리

**새 테스트 추가:**
```json
// jsonrpc_cases/mail-query.json에 추가
{
  "name": "긴급 메일 검색",
  "enabled": true,
  "tool": "query_email",
  "arguments": {
    "user_id": "kimghw",
    "days_back": 7,
    "subject_keywords": ["긴급", "urgent"]
  },
  "expect": {
    "contains": ["메일 조회 결과"]
  }
}
```

**테스트 비활성화:**
```json
{
  "name": "실행하고 싶지 않은 테스트",
  "enabled": false,  // 건너뜀
  ...
}
```

### 2. 여러 예상 결과

결과에 **하나라도 포함**되면 성공으로 처리됩니다:

```json
{
  "expect": {
    "contains": [
      "메일 조회 결과",
      "인증이 필요합니다",
      "계정이 없습니다"
    ]
  }
}
```

### 3. null 값 사용

```json
{
  "arguments": {
    "user_id": null,  // null 값 전달
    "days_back": 3
  }
}
```

## 🆚 테스트 방법 비교

| 항목 | JSON 파일 기반 | 단일 툴 테스트 | HTTP API 테스트 |
|------|--------------|--------------|----------------|
| 테스트 추가/수정 | ⭐ 매우 쉬움 (JSON 편집) | ⚠️ 명령줄 입력 | ⚠️ Bash 스크립트 편집 |
| 재사용성 | ✅ 높음 | ❌ 낮음 | ⚠️ 중간 |
| 여러 케이스 실행 | ✅ 자동 | ❌ 수동 | ✅ 자동 |
| 서버 필요 | ❌ 불필요 | ❌ 불필요 | ✅ 필요 |
| 속도 | 🚀 빠름 | 🚀 빠름 | 🐢 느림 |
| 활성화/비활성화 | ✅ 가능 | ❌ 불가 | ❌ 불가 |
| 적합한 상황 | 반복 테스트, 회귀 테스트 | 빠른 디버깅 | 통합 테스트 |

## 📚 참고

- 핸들러 코드: `modules/*/mcp_server/handlers.py`
- 테스트 케이스: `tests/handlers/jsonrpc_cases/*.json`
- HTTP API 테스트: `scripts/test_unified_mcp_tools.sh`
- 서버 실행: `entrypoints/production/run_unified_http.sh`

## 📝 예시: 전체 워크플로우

```bash
# 1. 테스트 케이스 파일 수정
vim tests/handlers/jsonrpc_cases/mail-query.json

# 2. 테스트 실행
python tests/handlers/run_jsonrpc_tests.py mail-query

# 3. 특정 케이스만 빠르게 테스트
python tests/handlers/test_with_jsonrpc.py mail-query query_email '{"user_id":"kimghw","days_back":1}'

# 4. 모든 모듈 테스트
python tests/handlers/run_jsonrpc_tests.py all
```
