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
- 최소 3개의 자연어 질문 포함
- 사용자가 실제로 물어볼 만한 표현 사용
- 다양한 표현 방식 포함

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
```sql
-- 파라미터 플레이스홀더
WHERE {period_condition}
WHERE organization = '{organization}'
WHERE {keywords_condition}

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

### 7.5 템플릿 카테고리 분류
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

이 가이드라인을 따라 일관성 있고 검증 가능한 쿼리 템플릿을 작성할 수 있습니다.