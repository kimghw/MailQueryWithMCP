# 쿼리 템플릿 작성 가이드라인 v3.1 (Database Schema Reference Update)

## 0. 데이터베이스 스키마 참조

템플릿 작성 시 `metadata.json`을 참조하세요:
- **table_schemas**: 각 테이블의 구조와 컬럼 정보
- **organization_codes**: 사용 가능한 조직 코드 목록
- **query_guidelines**: 쿼리 작성 시 주의사항

스키마 정보는 템플릿 파일의 메타데이터에서 확인 가능합니다.

## 1. 핵심 원칙

1. **필수 파라미터는 명확히 구분** - 사용자가 반드시 제공해야 하는 값이며, 제공하지 않을 시 default 값 사용
2. **모든 파라미터는 플레이스홀더로** - 필수/선택 모두 `{param_name}` 형식 사용
3. **선택 파라미터는 반드시 기본값 제공** - default에 합리적인 기본값 설정
5. **관련 데이터베이스 명시** - 'related_database' 필드에 참고하는 데이터베이스 목록 제공
6. **관련 테이블 명시** - `related_tables` 필드에 사용하는 테이블 목록 제공
7. **자연어 질문 개수**:
   - 단순 쿼리: 3개
   - 복잡한 쿼리: 5개 이상

## 중요 비즈니스 규칙

### 응답 필요 의제 판단 기준
우리가 응답해야 하는 의제는 다음 조건을 모두 만족해야 함:
1. **agenda_chair 테이블의 메일**
2. **mail_type = 'request'** (요청 메일)
3. **has_deadline = 1 AND deadline > datetime('now')** (마감일이 있고 아직 지나지 않음)

```sql
--기관의 응답여부 상관없이 현재 상태를 파악하기 위해 응답 필요 의제 조회 예시
SELECT * FROM agenda_chair 
WHERE mail_type = 'request' 
  AND has_deadline = 1 
  AND deadline > datetime('now')
  AND (response_org LIKE '%{organization_code}%' OR response_org = 'ALL')
ORDER BY deadline ASC

-- 미응답 요청 의제 조회 (KR이 아직 응답하지 않은 것)
SELECT a.* FROM agenda_chair a 
LEFT JOIN agenda_responses_content r 
  ON a.agenda_code = r.agenda_code 
  AND r.sender_organization = '{organization_code}'
WHERE a.mail_type = 'request' 
  AND a.has_deadline = 1 
  AND a.deadline > datetime('now')
  AND r.id IS NULL  -- 응답이 없는 경우
  AND (a.response_org LIKE '%{organization_code}%' OR a.response_org = 'ALL')
```

### 주의사항
- agenda_all이 아닌 **agenda_chair** 테이블 사용
- mail_type = 'request' 조건 필수
- 마감일이 있고(has_deadline = 1) 아직 지나지 않은(deadline > datetime('now')) 의제만 해당

### 조직 코드 사용
IACSGRAPH에서 사용하는 조직 코드 (Classification Society):
- **KR** - Korean Register (한국선급)
- **NK** - Nippon Kaiji Kyokai (일본선급)
- **CCS** - China Classification Society (중국선급)
- **ABS** - American Bureau of Shipping (미국선급)
- **DNV** - Det Norske Veritas (노르웨이선급)
- **BV** - Bureau Veritas (프랑스선급)
- **LR** - Lloyd's Register (영국선급)
- **RINA** - Registro Italiano Navale (이탈리아선급)
- **IRS** - Indian Register of Shipping (인도선급)
- **PRS** - Polish Register of Shipping (폴란드선급)
- **CRS** - Croatian Register of Shipping (크로아티아선급)
- **TL** - Türk Loydu (터키선급)

## 테이블 구조 설명

### 주요 테이블 (IACSGRAPH 실제 테이블)
1. **agenda_all**: 모든 의제 메일을 저장하는 메인 테이블
   - 일반적인 의제 관련 메일들이 저장됨
   - 의제 상태, 발송 정보, 내용 등 포함

2. **agenda_chair**: 의장(Chair)이 발송한 의제 메일
   - mail_type = 'request': 응답을 요청하는 메일
   - mail_type = 'notification': 단순 알림 메일
   - has_deadline: 마감일 존재 여부
   - deadline: 응답 마감일

3. **agenda_pending**: 분류가 보류 중인 메일
   - **주의**: 대기중인 안건이 아님
   - 시스템에서 자동 분류하지 못해 수동 처리가 필요한 메일
   - error_reason: 분류 실패 이유

4. **agenda_responses_content**: 의제에 대한 응답 내용 (비정규화된 구조)
   - agenda_base_version: 의제 기본 버전 (PK)
   - 각 조직별 컬럼: ABS, BV, CCS, CRS, DNV, IRS, KR, NK, PRS, RINA, IL, TL, LR
   - **주의**: 동적 컬럼 참조 불가 (arc.{organization} X)

5. **agenda_responses_receivedtime**: 응답 수신 시간
   - agenda_base_version: 의제 기본 버전 (PK)
   - 각 조직별 수신 시간 컬럼

### 대기중인 안건 vs 보류중인 메일
- **대기중인 안건 (응답 필요)**: 
  - agenda_chair 테이블에서 mail_type = 'request'이고 
  - has_deadline = 1이며 deadline > datetime('now')인 것
  - 우리(KR)가 아직 응답하지 않은 것
  
- **보류중인 메일 (agenda_pending)**:
  - 시스템이 자동으로 분류하지 못한 메일
  - 수동으로 처리해야 하는 메일
  - 의제 응답 여부와는 무관

## 2. 파라미터 처리 규칙

### 2.1 필수 파라미터 목록
다음 파라미터들이 추출되면 반드시 플레이스홀더로 처리:
- `period` - 기간 (date range)
- `organization` - 조직 코드 (string)
- `organization_code` - 조직 코드 (string) 
- `panel` - 패널코드 (string)
- `agenda_base` - 의제 기본 정보 (string)
- `agenda_base_version` - 의제 기본 버전 (string)
- `keywords` - 검색 키워드 (array)
필수 파라미턴느 반드시 default 값을 사용 :

### 2.2 플레이스홀더 사용 원칙
```sql
-- 올바른 예시
WHERE organization_code = '{organization_code}' 
  AND sent_time >= DATE('now', '-{dates} days')
  AND keywords LIKE '%{keywords}%'

-- 잘못된 예시 (하드코딩)
WHERE organization_code = 'KR' 
  AND status = 'ongoing'
```

### 2.2 MCP 통합 파라미터 구조
모든 파라미터는 MCP 서버와의 통합을 위해 `mcp_format` 필드를 포함해야 함:

```json
"parameters": [
  {
    "name": "organization",
    "type": "string",
    "required": true,
    "default": "KR",
    "description": "Organization code (e.g., KR, NK, CCS, ABS)",
    "sql_builder": {
      "type": "string",
      "placeholder": "{organization}"
    },
    "mcp_format": "extracted_organization"
  },
  {
    "name": "period",
    "type": "period",
    "required": false,
    "default": {"type": "relative", "days": 30},
    "sql_builder": {
      "type": "period",
      "field": "sent_time",
      "placeholder": "{period_condition}"
    },
    "mcp_format": "extracted_period"
  },
  {
    "name": "keywords",
    "type": "keywords",
    "required": false,
    "default": [],
    "sql_builder": {
      "type": "keywords",
      "field": "keywords",
      "operator": "LIKE",
      "placeholder": "{keywords_condition}"
    },
    "mcp_format": "extracted_keywords"
  }
]
```

### 2.3 MCP Format 매핑
파라미터 타입별 MCP format 매핑:
- `period`, `date_range` → `"mcp_format": "extracted_period"`
- `organization`, `organization_code` → `"mcp_format": "extracted_organization"`
- `keywords`, `keyword` → `"mcp_format": "extracted_keywords"`
- `agenda_base` → `"mcp_format": "agenda_base"`
- `agenda_base_version` → `"mcp_format": "agenda_base_version"`
- 기타 파라미터 → 직접 매핑 또는 없음

### 2.4 SQL Builder 타입
SQL 생성을 위한 빌더 타입:
- `period`: 날짜 범위 조건 생성
- `keywords`: 키워드 검색 조건 생성
- `string`: 단순 문자열 치환
- `number`: 숫자 값 치환
- `direct_replace`: 여러 플레이스홀더 직접 치환

### 2.5 동적 컬럼 참조 금지
`agenda_responses_content` 테이블의 조직별 컬럼은 동적 참조 불가:

```sql
-- ❌ 잘못된 예시
WHERE arc.{organization} IS NOT NULL

-- ✅ 올바른 예시 (CASE 문 사용)
WHERE CASE {organization}
    WHEN 'KR' THEN arc.KR
    WHEN 'ABS' THEN arc.ABS
    WHEN 'BV' THEN arc.BV
    -- ... 다른 조직들
END IS NOT NULL

-- ✅ 또는 SQL Generator가 처리하도록 특별한 플레이스홀더 사용
WHERE {organization_response_condition}
```

## 3. 자연어 질문 작성 규칙

### 3.1 단순 쿼리 (3개)
단일 조건이나 직관적인 조회:
```json
"natural_questions": [
  "최근 진행중인 의제 목록",
  "현재 ongoing 상태 아젠다",
  "진행 중인 안건들 보여줘"
]
```

### 3.2 복잡한 쿼리 (5개 이상)
- 여러 조건 조합
- JOIN이 필요한 경우
- 집계/분석이 포함된 경우
- 특수한 비즈니스 로직

```json
"natural_questions": [
  "KR이 응답해야하는 의제 중 다른 기관의 의견 정리",
  "KR이 답변 필요한 안건의 타기관 코멘트",
  "KR 응답 대상 의제에 대한 각국 입장 요약",
  "우리나라가 회신해야 할 아젠다의 타국 의견",
  "KR 대응 필요 의제의 다른 나라 피드백 분석"
]
```

## 3. 템플릿 구조

### 3.1 필수 필드
```json
{
  "template_id": "example_template",
  "template_version": "1.0.0",
  "template_category": "agenda_status",
  "query_info": {
    "natural_questions": [
      "질문 1",
      "질문 2",
      "질문 3"
    ],
    "keywords": ["키워드1", "키워드2"]
  },
  "target_scope": {
    "scope_type": "all",
    "target_organizations": [],
    "target_panels": "all"
  },
  "sql_template": {
    "query": "SELECT * FROM agenda_all WHERE ...",
    "system": "쿼리 목적 설명",
    "sql_prompt": "사용자 요구사항"
  },
  "parameters": [
    // MCP 통합 파라미터들
  ],
  "related_db": "iacsgraph.db",
  "related_tables": ["agenda_all"],
  "embedding_config": {
    "model": "text-embedding-3-large",
    "dimension": 1536
  },
  "routing_type": "sql",
  "to_agent": "의제와 키워드 정보를 정리해 주세요."
}
```

### 3.2 Related Tables 필드
템플릿에서 사용하는 모든 테이블을 명시:
```json
"related_tables": ["agenda_all", "agenda_responses_content", "agenda_responses_receivedtime"]
```

사용 가능한 테이블:
- `agenda_all`
- `agenda_chair`
- `agenda_pending`
- `agenda_responses_content`
- `agenda_responses_receivedtime`

## 4. 자연어 질문 작성 규칙

### 4.1 단순 쿼리 (3개)
단일 조건이나 직관적인 조회:
```json
"natural_questions": [
  "최근 진행중인 의제 목록",
  "현재 ongoing 상태 아젠다",
  "진행 중인 안건들 보여줘"
]
```

### 4.2 복잡한 쿼리 (5개 이상)
- 여러 조건 조합
- JOIN이 필요한 경우
- 집계/분석이 포함된 경우
- 특수한 비즈니스 로직

```json
"natural_questions": [
  "KR이 응답해야하는 의제 중 다른 기관의 의견 정리",
  "KR이 답변 필요한 안건의 타기관 코멘트",
  "KR 응답 대상 의제에 대한 각국 입장 요약",
  "우리나라가 회신해야 할 아젠다의 타국 의견",
  "KR 대응 필요 의제의 다른 나라 피드백 분석"
]
```

## 5. 예시 템플릿

### 5.1 단순 쿼리 템플릿 (MCP 통합)
```json
{
  "template_id": "org_recent_agendas_v2",
  "template_version": "1.0.0",
  "template_category": "agenda_status",
  "query_info": {
    "natural_questions": [
      "KR의 최근 의제 목록",
      "한국선급 관련 최신 안건",
      "KR이 참여한 최근 아젠다"
    ],
    "keywords": ["최근", "의제", "목록"]
  },
  "target_scope": {
    "scope_type": "specific_organization",
    "target_organizations": ["KR"],
    "target_panels": "all"
  },
  "sql_template": {
    "query": "SELECT * FROM agenda_all WHERE sender_organization = {organization} AND {period_condition} ORDER BY sent_time DESC",
    "system": "특정 조직의 최근 의제를 검색합니다.",
    "user": "조직의 최근 활동 내역을 파악하고 싶습니다."
  },
  "parameters": [
    {
      "name": "organization",
      "type": "string",
      "required": true,
      "default": "KR",
      "description": "Organization code (e.g., KR, NK, CCS, ABS)",
      "sql_builder": {
        "type": "string",
        "placeholder": "{organization}"
      },
      "mcp_format": "extracted_organization"
    },
    {
      "name": "period",
      "type": "period",
      "required": false,
      "default": {"type": "relative", "days": 30},
      "sql_builder": {
        "type": "period",
        "field": "sent_time",
        "placeholder": "{period_condition}"
      },
      "mcp_format": "extracted_period"
    }
  ],
  "related_db": "iacsgraph.db",
  "related_tables": ["agenda_all"],
  "embedding_config": {
    "model": "text-embedding-3-large",
    "dimension": 1536
  },
  "routing_type": "sql",
  "to_agent": "의제와 키워드 정보를 정리해 주세요."
}
```


## 5. SQL 쿼리 작성 규칙

### 5.0 SQL 템플릿 구조
SQL 템플릿은 다음 세 가지 필드를 포함해야 합니다:

```json
"sql_template": {
  "query": "실제 SQL 쿼리문, 필수 파라미터는 플레이스홀도로 처리",
  "system": "이 쿼리가 무엇을 검색하는지에 대한 시스템 설명 (검색 의도)",
  "sql_prompt": "natural_questions 에 대해 데이터베이스 스키마를 바탕으로 비즈니스 요구사항 분석 및 복잡한 퀄리 단계별 생성 절차   "
}
```

### 5.1 날짜 처리

#### 옵션 1: 상대적 날짜 (최근 N일)
```json
{
  "name": "days",
  "type": "integer",
  "required": false,
  "default": 30
}
```
```sql
WHERE sent_time >= DATE('now', '-{days} days')
```

#### 옵션 2: 날짜 범위 (시작/종료)
```json
{
  "name": "date_range",
  "type": "date_range",
  "required": false,
  "default": {
    "type": "relative",
    "days": 30
  },
  "sql_builder": {
    "type": "date_range",
    "field": "sent_time",
    "placeholder": "{date_condition}"
  }
}
```

사용자 입력 예시:
```json
// 상대적 날짜
{"date_range": {"type": "relative", "days": 60}}

// 절대적 날짜 범위
{"date_range": {"type": "range", "from": "2024-01-01", "to": "2024-12-31"}}

// 시작 날짜만
{"date_range": {"type": "range", "from": "2024-01-01"}}

// 종료 날짜만
{"date_range": {"type": "range", "to": "2024-12-31"}}
```

### 5.2 키워드 검색
```sql
-- 단일 필드
WHERE keywords LIKE '%{keywords}%'

-- 다중 필드
WHERE (keywords LIKE '%{keywords}%' 
    OR subject LIKE '%{keywords}%' 
    OR body LIKE '%{keywords}%')
```

### 5.3 조직 필터
```sql
-- organization_code 사용
WHERE organization_code = '{organization_code}'

-- 복수 조직 또는 ALL 포함
WHERE (response_org LIKE '%{organization_code}%' OR response_org = 'ALL')
```

## 6. 예상 응답 (Expected Response) 작성 규칙

각 템플릿에는 사용자가 기대하는 응답 형식을 정의하는 `expected_response` 필드를 포함해야 합니다.

### 6.1 Expected Response 구조
```json
"expected_response": {
  "description": "이 쿼리가 제공할 응답에 대한 간단한 설명",
  "format": "응답 형식 (list, analysis, statistics, priority_list 등)",
  "example": "실제 응답 예시 (구체적인 데이터 포함)"
}
```

### 6.2 응답 형식별 예시

```

## 7. 체크리스트

- [ ] 파라미터를 통합 배열 구조로 정의했는가?
- [ ] 각 파라미터에 type, required, default 속성이 있는가?
- [ ] 다중 값이 필요한 파라미터는 array 타입으로 정의했는가?
- [ ] 복잡한 SQL 조건은 sql_builder를 사용했는가?
- [ ] 단순 쿼리는 3개, 복잡한 쿼리는 5개 이상의 자연어 질문이 있는가?
- [ ] SQL에 하드코딩된 값이 없는가?
- [ ] SQL 템플릿에 system, user 필드를 포함했는가?
- [ ] expected_response를 작성했는가?

## 8. 주의사항

1. **동적 컬럼 참조 금지**: `arc.{organization}` 같은 패턴 사용 불가
2. **MCP 통합 필수**: 모든 파라미터에 `mcp_format` 필드 필수
3. **테이블 명시**: 사용하는 모든 테이블을 `related_tables`에 포함
4. **조직 코드 정확성**: KR, NK, CCS 등 실제 DB의 조직 코드만 사용
5. **기간 파라미터**: `period` 타입 사용 시 `mcp_format: "extracted_period"` 필수
6. **스키마 참조**: 템플릿 작성 전 metadata.database_schema 확인 필수

## 9. 복잡도 판단 기준

### 단순 (3개 질문)
- 단일 테이블 조회
- 1-2개 조건
- 기본적인 필터링/정렬

### 복잡 (5개 이상 질문)
- JOIN 포함
- 3개 이상 조건
- 집계/그룹화
- 서브쿼리
- 케이스별 처리 로직
- 다양한 표현이 가능한 비즈니스 요구사항