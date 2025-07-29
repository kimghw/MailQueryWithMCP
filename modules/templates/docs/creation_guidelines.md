# IACSGRAPH Query Template Creation Guidelines

## 목차
1. [개요](#1-개요)
2. [템플릿 구조](#2-템플릿-구조)
3. [SQL 쿼리 작성 규칙](#3-sql-쿼리-작성-규칙)
4. [파라미터 처리](#4-파라미터-처리)
5. [데이터베이스 스키마 참조](#5-데이터베이스-스키마-참조)
6. [검증 방법](#6-검증-방법)
7. [일반적인 문제 해결](#7-일반적인-문제-해결)

## 1. 개요

IACSGRAPH 쿼리 템플릿은 자연어 질문을 SQL 쿼리로 변환하는 시스템입니다. 각 템플릿은 특정 비즈니스 요구사항에 대한 SQL 쿼리와 메타데이터를 포함합니다.

### 핵심 원칙
- **일관성**: 모든 템플릿은 동일한 구조와 명명 규칙을 따름
- **재사용성**: 파라미터를 통한 쿼리 재사용
- **검증 가능성**: 실제 데이터베이스에서 테스트 가능
- **확장성**: 새로운 요구사항에 쉽게 대응

## 2. 템플릿 구조

### 2.1 기본 구조
```json
{
  "template_id": "template_name",
  "template_version": "1.0.0",
  "template_category": "category_name",
  "query_info": {
    "natural_questions": [
      "자연어 질문 1",
      "자연어 질문 2",
      "자연어 질문 3"
    ],
    "keywords": ["키워드1", "키워드2"]
  },
  "target_scope": {
    "scope_type": "all",
    "target_organizations": [],
    "target_panels": "all"
  },
  "sql_template": {
    "query": "SELECT ... FROM ... WHERE ...",
    "system": "쿼리 목적 설명",
    "sql_prompt": "비즈니스 요구사항 설명"
  },
  "parameters": [],
  "related_db": "iacsgraph.db",
  "related_tables": ["table1", "table2"],
  "embedding_config": {
    "model": "text-embedding-3-large",
    "dimension": 3072
  },
  "routing_type": "sql",
  "to_agent": "에이전트에게 전달할 프롬프트"
}
```

### 2.2 필수 필드 설명

#### template_id
- 고유 식별자
- 명명 규칙: `{domain}_{action}_{target}`
- 예: `kr_pending_response_agendas`

#### template_category
사용 가능한 카테고리:
- `agenda_status`: 의제 상태 관련
- `response_tracking`: 응답 추적
- `keyword_analysis`: 키워드 분석
- `statistics`: 통계
- `mail_type`: 메일 유형별 조회
- `keyword_search`: 키워드 검색

#### natural_questions
- 사용자가 실제로 물어볼 만한 표현 사용
- 다양한 표현 방식 포함
- **중요**: 원본 쿼리 리스트 기반의 형식 준수
  - **original (1개)**: 사용자가 제공한 원본 쿼리 그대로 + "(original)" 표기
  - **similar (3-5개)**: 동일한 의미의 유사한 표현들
    - 단순한 질의: 3개의 similar
    - 복잡한 질의: 5개의 similar
    - "(similar1)", "(similar2)", "(similar3)" 등으로 표기
  - **ext (1개)**: 구체적이고 상세한 설명이 포함된 확장 질문 + "(ext)" 표기

## 3. SQL 쿼리 작성 규칙

### 3.1 대소문자 규칙
```sql
-- 올바른 예
WHERE mail_type = 'REQUEST'  -- 값은 대문자
WHERE mail_type = 'NOTIFICATION'
WHERE mail_type = 'RESPONSE'

-- 잘못된 예
WHERE mail_type = 'request'  -- 소문자 사용 X
```

### 3.2 컬럼명 정확성
```sql
-- 올바른 예
SELECT agenda_panel FROM agenda_chair  -- agenda_panel 사용

-- 잘못된 예  
SELECT panel FROM agenda_chair  -- panel 컬럼 없음
```

### 3.3 응답 필요 의제 조회 패턴
```sql
-- 기본 패턴: 마감일이 있고 아직 지나지 않은 의제
SELECT * FROM agenda_chair 
WHERE mail_type = 'REQUEST' 
  AND has_deadline = 1 
  AND deadline > datetime('now')
  
-- KR 미응답 의제 조회
SELECT c.* FROM agenda_chair c 
LEFT JOIN agenda_responses_content r 
  ON c.agenda_base_version = r.agenda_base_version
WHERE c.mail_type = 'REQUEST' 
  AND c.has_deadline = 1 
  AND c.deadline > datetime('now')
  AND r.KR IS NULL  -- KR 응답이 없는 경우
```

## 4. 파라미터 처리

### 4.1 파라미터 타입

#### period (기간)
```json
{
  "name": "period",
  "type": "period",
  "required": false,
  "default": {
    "type": "relative",
    "days": 30
  },
  "sql_builder": {
    "type": "period",
    "field": "sent_time",
    "placeholder": "{period_condition}"
  },
  "mcp_format": "extracted_period"
}
```

#### organization (조직)
```json
{
  "name": "organization",
  "type": "string",
  "required": true,
  "default": "KR",
  "sql_builder": {
    "type": "string",
    "placeholder": "{organization}"
  },
  "mcp_format": "extracted_organization"
}
```

#### keywords (키워드)
```json
{
  "name": "keywords",
  "type": "array",
  "required": true,
  "default": ["keyword1", "keyword2"],
  "sql_builder": {
    "type": "keywords",
    "fields": ["keywords", "subject"],
    "placeholder": "{keywords_condition}"
  },
  "mcp_format": "extracted_keywords"
}
```

### 4.2 플레이스홀더 사용

#### 기본 원칙
- **모든 필수 파라미터는 SQL 쿼리에서 플레이스홀더를 사용해야 함**
- 파라미터를 정의했다면 반드시 쿼리에서 해당 플레이스홀더를 사용
- 하드코딩된 값 대신 플레이스홀더를 통해 동적 치환 구현

#### 플레이스홀더 예시
```sql
-- 파라미터 플레이스홀더
WHERE {period_condition}
WHERE organization = '{organization}'
WHERE {keywords_condition}

-- 조직별 응답 확인 (동적)
WHERE r.{organization} IS NULL  -- 올바른 예: 플레이스홀더 사용
WHERE r.KR IS NULL              -- 잘못된 예: 하드코딩

-- CTE 이름도 일반화
WITH org_pending AS (...)       -- 올바른 예: 일반적인 이름
WITH kr_pending AS (...)        -- 피해야 할 예: 특정 조직명 사용

-- 특수 플레이스홀더 (query_executor.py에서 자동 처리)
{date_condition} → sent_time >= DATE('now', '-30 days')
{deadline_filter} → deadline IS NOT NULL AND deadline >= DATE('now')
```

### 4.3 MCP Format 매핑
- `period`, `date_range` → `"mcp_format": "extracted_period"`
- `organization` → `"mcp_format": "extracted_organization"`
- `keywords` → `"mcp_format": "extracted_keywords"`

## 5. 데이터베이스 스키마 참조

### 5.1 주요 테이블

#### agenda_chair
```sql
CREATE TABLE agenda_chair (
  agenda_base_version TEXT PRIMARY KEY,
  agenda_code TEXT NOT NULL,
  sender_type TEXT DEFAULT 'CHAIR',
  sender_organization TEXT NOT NULL,
  sent_time DATETIME NOT NULL,
  mail_type TEXT DEFAULT 'REQUEST',  -- REQUEST, NOTIFICATION, RESPONSE
  decision_status TEXT DEFAULT 'created',  -- created, ongoing, review, completed
  subject TEXT NOT NULL,
  body TEXT,
  keywords TEXT,
  deadline DATETIME,
  has_deadline BOOLEAN DEFAULT 0,
  agenda_panel TEXT NOT NULL,  -- 주의: panel이 아닌 agenda_panel
  -- 기타 컬럼들...
)
```

#### agenda_responses_content
```sql
CREATE TABLE agenda_responses_content (
  agenda_base_version TEXT PRIMARY KEY,
  ABS TEXT,
  BV TEXT,
  CCS TEXT,
  CRS TEXT,
  DNV TEXT,
  IRS TEXT,
  KR TEXT,
  NK TEXT,
  PRS TEXT,
  RINA TEXT,
  IL TEXT,
  TL TEXT,
  LR TEXT
  -- 주의: sent_time 컬럼 없음
)
```

### 5.2 조직 코드
- ABS: American Bureau of Shipping
- BV: Bureau Veritas
- CCS: China Classification Society
- CRS: Croatian Register of Shipping
- DNV: Det Norske Veritas
- IRS: Indian Register of Shipping
- KR: Korean Register
- NK: Nippon Kaiji Kyokai (ClassNK)
- PRS: Polish Register of Shipping
- RINA: Registro Italiano Navale
- IL: Intact Stability (특수)
- TL: Turkish Lloyd
- LR: Lloyd's Register

## 6. 검증 방법

### 6.1 개별 템플릿 검증
```bash
# 특정 템플릿 테스트
python -m modules.templates.validators.query_executor \
    modules/templates/data/query_templates_split/query_templates_part_001.json \
    data/iacsgraph.db \
    --template template_id
```

### 6.2 전체 파일 검증
```bash
# 파일 내 모든 템플릿 검증
python -m modules.templates.validators.query_executor \
    modules/templates/data/query_templates_split/query_templates_part_001.json \
    data/iacsgraph.db
```

### 6.3 결과 저장과 함께 검증
```bash
# 쿼리 결과를 CSV로 저장
python -m modules.templates.validators.query_executor \
    modules/templates/data/query_templates_split/query_templates_part_001.json \
    data/iacsgraph.db \
    --save-results \
    --output-dir validation_results
```

## 7. 일반적인 문제 해결

### 7.1 "no such column" 오류
**문제**: SQL Error: no such column: panel
**해결**: 
- `panel` → `agenda_panel` 변경
- 실제 테이블 스키마 확인: `sqlite3 data/iacsgraph.db ".schema table_name"`

### 7.2 대소문자 불일치
**문제**: 0건 결과 (데이터는 있는데)
**해결**:
- mail_type 값은 대문자 사용: 'REQUEST', 'NOTIFICATION', 'RESPONSE'
- 컬럼명은 소문자 사용

### 7.3 파라미터 치환 오류
**문제**: SQL Error: near "KR": syntax error
**원인**: LIKE '%'KR'%' 형태로 따옴표 중복
**해결**: 
- query_executor.py가 자동으로 따옴표 처리
- 템플릿에서는 플레이스홀더만 사용: `{organization}`

### 7.4 날짜 관련 문제
**문제**: 미래 마감일 의제가 없음
**해결**:
```sql
-- 테스트용 데이터 추가
INSERT INTO agenda_chair (..., deadline, ...) 
VALUES (..., datetime('now', '+30 days'), ...)
```

### 7.5 필수 파라미터와 플레이스홀더 불일치
**문제**: organization 파라미터는 정의되어 있지만 쿼리에서 사용 안 함
**예시**:
```json
"parameters": [
  {
    "name": "organization",
    "required": true,
    "placeholder": "{organization}"
  }
]
"query": "... WHERE r.KR IS NULL ..."  // 잘못된 예
```
**해결**:
```sql
-- 올바른 쿼리
"query": "... WHERE r.{organization} IS NULL ..."
```

### 7.6 템플릿 카테고리 분류
각 템플릿은 다음 중 하나의 카테고리에 속해야 함:
- `agenda_status`: 의제 상태 조회 (진행중, 완료, 미완료 등)
- `response_tracking`: 응답 추적 (KR 응답 필요, 미응답 등)
- `keyword_analysis`: 키워드 분석 및 추출
- `statistics`: 통계 및 집계 (COUNT, GROUP BY 등)
- `mail_type`: 메일 유형별 조회 (notification, request 등)
- `keyword_search`: 특정 키워드 검색 (IMO, UR 등)

## 부록: 템플릿 예시

### 간단한 통계 쿼리
```json
{
  "template_id": "pending_agendas_count",
  "template_version": "1.0.0",
  "template_category": "statistics",
  "query_info": {
    "natural_questions": [
      "처리 대기 중인 agenda의 수는?",
      "대기중인 의제가 몇 개야?",
      "미처리 안건 개수 알려줘"
    ],
    "keywords": ["대기중", "개수", "수량"]
  },
  "sql_template": {
    "query": "SELECT COUNT(*) as pending_count FROM agenda_chair WHERE mail_type = 'REQUEST' AND has_deadline = 1 AND deadline > datetime('now') AND {period_condition}",
    "system": "응답이 필요한 대기중인 의제의 수를 조회합니다.",
    "sql_prompt": "마감일이 지나지 않은 REQUEST 타입 의제의 개수를 카운트합니다."
  },
  "parameters": [
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
  "related_tables": ["agenda_chair"],
  "routing_type": "sql",
  "to_agent": "대기중인 의제 수를 알려주세요."
}
```

### 동적 조직 파라미터를 사용한 템플릿 예시
```json
{
  "template_id": "kr_pending_response_agendas",
  "template_version": "1.0.0",
  "template_category": "response_tracking",
  "query_info": {
    "natural_questions": [
      "진행되고 있는 의제들 중에서 KR이 아직 응답하지 않는 의제",
      "KR이 응답을 해야 하는 의제",
      "한국선급이 회신해야 할 대기중인 안건"
    ],
    "keywords": ["KR", "미응답", "응답필요"]
  },
  "sql_template": {
    "query": "SELECT c.agenda_code, c.agenda_base_version, c.subject, c.agenda_panel, c.sent_time, c.deadline FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.mail_type = 'REQUEST' AND c.has_deadline = 1 AND c.deadline > datetime('now') AND c.decision_status != 'completed' AND r.{organization} IS NULL AND {period_condition} ORDER BY c.deadline ASC",
    "system": "지정된 조직이 아직 응답하지 않은 진행중인 의제들을 조회합니다.",
    "sql_prompt": "지정된 조직이 응답해야 하는 의제를 찾으려면 agenda_chair에서 mail_type이 'request'이고 has_deadline이 1이며 deadline이 현재보다 미래인 의제 중, agenda_responses_content에 해당 조직의 응답이 없는 것을 찾아야 합니다."
  },
  "parameters": [
    {
      "name": "organization",
      "type": "string",
      "required": true,
      "default": "KR",
      "description": "조직 코드",
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
      "default": {"type": "relative", "days": 90},
      "sql_builder": {
        "type": "period",
        "field": "c.sent_time",
        "placeholder": "{period_condition}"
      },
      "mcp_format": "extracted_period"
    }
  ],
  "related_db": "iacsgraph.db",
  "related_tables": ["agenda_chair", "agenda_responses_content"],
  "routing_type": "sql",
  "to_agent": "의제 제목 리스트를 정리해 주세요."
}
```

## 8. 최근 수정사항 (2025년 1월)

### 8.1 필수 파라미터 플레이스홀더 처리 개선
**변경 사항**:
- 모든 필수 파라미터는 SQL 쿼리에서 플레이스홀더를 사용하도록 수정
- 하드코딩된 조직명(KR) 대신 `{organization}` 플레이스홀더 사용
- CTE 이름을 특정 조직명에서 일반적인 이름으로 변경 (kr_pending → org_pending)

**수정된 템플릿 목록**:
1. `kr_pending_response_agendas`
2. `kr_response_required_simple`
3. `kr_required_agendas_other_org_opinions`
4. `kr_required_agendas_keywords`
5. `kr_required_agendas_other_org_keywords`

**수정 예시**:
```sql
-- 변경 전
WHERE r.KR IS NULL
WITH kr_pending AS (...)

-- 변경 후
WHERE r.{organization} IS NULL
WITH org_pending AS (...)
```

### 8.2 query_executor.py 개선
**컬럼명 플레이스홀더 처리**:
```python
# 컬럼명으로 사용되는 플레이스홀더는 따옴표 없이 치환
elif f"r.{placeholder}" in sql_query or f"c.{placeholder}" in sql_query:
    final_query = final_query.replace(placeholder, default_value)
```

**하드코딩 제거**:
- special_replacements에서 `'{organization}': "'KR'"` 제거
- 동적 파라미터 치환을 통해 모든 조직에 대해 쿼리 실행 가능

### 8.3 대량 템플릿 생성 및 검증
**생성된 템플릿**:
- 총 165개 템플릿을 9개 파일에 분산 생성 (part_001 ~ part_009)
- 각 파일당 약 20개 템플릿 포함 (마지막 파일은 5개)
- 모든 템플릿 100% 검증 통과

**템플릿 카테고리 분포**:
- agenda_status: 의제 상태 조회
- response_tracking: 응답 추적 및 모니터링
- statistics: 통계 및 집계 분석
- keyword_analysis: 키워드 기반 분석
- keyword_search: 특정 키워드 검색
- mail_type: 메일 유형별 분류

### 8.4 to_agent 필드 개선 사항
**목적**: 단순 조회 결과를 분석이 필요한 형태로 에이전트에게 전달하기 위한 상세 지침 제공

**개선된 템플릿 수**: 32개 (전체 템플릿 중 분석이 필요한 모든 템플릿)

**주요 개선 사항**:
1. 단순 "정리해 주세요" → 구체적인 분석 지침으로 변경
2. 분석 관점과 주요 포인트 명시
3. 비교, 트렌드, 패턴 분석 요청 포함

**to_agent 필드 작성 가이드라인**:

#### 1. 통계 분석 템플릿
```json
// 변경 전
"to_agent": "통계를 정리해 주세요."

// 변경 후
"to_agent": "월별 의제 발송 및 응답 현황을 분석하여 추이를 설명해 주세요. 특히 응답률이 낮은 달이나 급격한 변화가 있는 시점을 주목해 주세요."
```

#### 2. 키워드 분석 템플릿
```json
// 변경 전
"to_agent": "키워드를 정리해 주세요."

// 변경 후
"to_agent": "키워드별 의제 분포를 분석하여 어떤 주제가 가장 많이 논의되고 있는지, 최근 트렌드는 무엇인지 설명해 주세요."
```

#### 3. 조직별 분석 템플릿
```json
// 변경 전
"to_agent": "조직별 현황을 정리해 주세요."

// 변경 후
"to_agent": "조직별 응답 현황을 분석하여 어떤 조직이 가장 적극적으로 참여하고 있는지, 응답이 저조한 조직은 어디인지 파악해 주세요."
```

#### 4. 패널 효율성 분석
```json
"to_agent": "패널별 효율성 지표를 분석하여 성과가 우수한 패널과 개선이 필요한 패널을 파악해 주세요. 완료율과 응답률의 관계를 분석해 주세요."
```

#### 5. 키워드 트렌드 분석
```json
"to_agent": "키워드 출현 빈도를 시간순으로 분석하여 트렌드 변화를 설명해 주세요. 새롭게 부상한 키워드나 사라진 키워드가 있는지 확인해 주세요."
```

### 8.5 개선된 템플릿 목록
다음 32개 템플릿의 to_agent 필드가 구체적인 분석 지침으로 업데이트됨:

**part_002.json**: 5개
- yearly_monthly_agenda_response_status
- kr_recent_responses_summary
- kr_organization_response_analysis
- kr_response_patterns
- panel_statistics

**part_003.json**: 4개
- agenda_statistics_by_panel
- keyword_count_panel
- keyword_trend_analysis
- meeting_related_agendas

**part_004.json**: 6개
- iacs_member_count
- iacs_member_composition
- iacs_panel_structure
- agenda_response_statistics
- organization_participation_ranking
- panel_activity_analysis

**part_005.json**: 5개
- panel_last_agenda_info
- agenda_history_analysis
- response_pattern_summary
- quarterly_statistics
- panel_response_performance

**part_006.json**: 1개
- request_mail_type_weekly

**part_007.json**: 5개
- weekly_agenda_volume_trend
- panel_collaboration_network
- response_speed_ranking
- keyword_evolution
- panel_workload_distribution

**part_008.json**: 4개
- panel_efficiency_metrics
- organization_alignment_analysis
- keyword_co_occurrence
- deadline_compliance_rate

**part_009.json**: 2개
- ai_ml_discussion_tracking
- agenda_complexity_index

### 8.6 검증 결과
- 모든 165개 템플릿 100% 통과
- 플레이스홀더 사용 검증 완료 (46개 템플릿에서 미사용 period 파라미터 확인)
- 다양한 조직에 대한 동적 쿼리 실행 확인
- to_agent 필드 개선으로 분석 품질 향상 기대

### 8.7 템플릿 생성 원칙 (2025년 7월 업데이트)

#### 원본 쿼리 준수 원칙
**중요**: 템플릿은 오직 사용자가 제공한 원본 쿼리 리스트에 기반하여 생성되어야 합니다.

1. **템플릿 생성 제한**
   - 사용자가 제공한 160+ 원본 쿼리에만 기반하여 템플릿 생성
   - 원본 쿼리에 없는 새로운 템플릿 임의 생성 금지
   - 예: "주말 활동 분석", "주말 업무 현황" 등은 원본에 없으므로 생성 불가

2. **natural_questions 형식**
   
   **단순한 질의 예시 (총 5개: original 1개 + similar 3개 + ext 1개)**
   ```json
   "natural_questions": [
     "향후 예정된 회의 알려줘 (original)",
     "앞으로 예정된 IACS 회의 일정을 보여주세요 (similar1)",
     "다가오는 회의 일정이 궁금합니다 (similar2)",
     "예정된 미팅 스케줄 확인해줘 (similar3)",
     "제목이나 본문에 'upcoming', 'scheduled', 'planned', '예정' 등의 미래 일정 관련 키워드가 포함된 의제를 찾아서 향후 회의 일정과 주요 안건을 정리해 주세요 (ext)"
   ]
   ```
   
   **복잡한 질의 예시 (총 7개: original 1개 + similar 5개 + ext 1개)**
   ```json
   "natural_questions": [
     "KR이 응답해야하는 의제에서 의제들의 주요 이슈 및 다른 기관의 의견 정리 (original)",
     "한국선급이 회신해야 할 안건의 핵심 내용과 타 기관 입장 요약해줘 (similar1)",
     "KR이 답변 필요한 의제들의 주요 쟁점과 다른 기관들의 견해를 보여주세요 (similar2)",
     "우리가 응답해야 하는 안건별로 주요 이슈와 타사 의견을 정리해주세요 (similar3)",
     "KR 응답 대기 중인 의제의 핵심 사항과 각 기관별 입장을 알려주세요 (similar4)",
     "한국선급이 피드백 줘야 하는 아젠다의 주요 논점과 타 선급 의견 분석해줘 (similar5)",
     "KR이 응답이 필요한 의제들에 대해 각 의제별 핵심 이슈, 다른 기관들(ABS, DNV, NK 등)의 상세 의견, 찬반 입장, 주요 우려사항 등을 체계적으로 분석하고 정리해 주세요 (ext)"
   ]
   ```

3. **형식 설명**
   - **(original)**: 사용자가 제공한 원본 쿼리 그대로 사용
   - **(similar1~5)**: 동일한 의미를 가진 다양한 유사 표현
   - **(ext)**: 더 구체적이고 상세한 설명이 포함된 확장 표현

4. **기간 관련 기본값**
   - "최근"이라는 단어가 포함된 쿼리는 90일을 기본값으로 설정
   - 예: "최근 진행된 회의" → default period 90 days

5. **검증 시 확인사항**
   - 모든 템플릿이 원본 쿼리 리스트와 매칭되는지 확인
   - natural_questions 형식이 (original), (ext), (ext2) 규칙을 따르는지 확인
   - 원본에 없는 템플릿이 포함되었는지 검토

이 가이드라인을 따라 일관성 있고 검증 가능한 쿼리 템플릿을 작성할 수 있습니다.