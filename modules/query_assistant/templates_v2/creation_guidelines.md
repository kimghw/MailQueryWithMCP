# 쿼리 템플릿 작성 가이드라인 v2.3 (Updated Business Rules)

## 1. 핵심 원칙

1. **필수 파라미터는 명확히 구분** - 사용자가 반드시 제공해야 하는 값
2. **모든 파라미터는 플레이스홀더로** - 필수/선택 모두 `{param_name}` 형식 사용
3. **선택 파라미터는 반드시 기본값 제공** - default_params에 합리적인 기본값 설정
4. **자연어 질문 개수**:
   - 단순 쿼리: 3개
   - 복잡한 쿼리: 5개 이상

## 중요 비즈니스 규칙

### 응답 필요 의제 판단 기준
우리가 응답해야 하는 의제는 다음 조건을 모두 만족해야 함:
1. **agenda_chair 테이블의 메일**
2. **mail_type = 'request'** (요청 메일)
3. **has_deadline = 1 AND deadline > datetime('now')** (마감일이 있고 아직 지나지 않음)
4. **decision_status != 'completed'** (아직 완료되지 않음)

```sql
-- 응답 필요 의제 조회 예시
SELECT * FROM agenda_chair 
WHERE mail_type = 'request' 
  AND has_deadline = 1 
  AND deadline > datetime('now')
  AND decision_status != 'completed'
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
  AND a.decision_status != 'completed'
  AND r.id IS NULL  -- 응답이 없는 경우
  AND (a.response_org LIKE '%{organization_code}%' OR a.response_org = 'ALL')
```

### 주의사항
- agenda_all이 아닌 **agenda_chair** 테이블 사용
- mail_type = 'request' 조건 필수
- 마감일이 있고(has_deadline = 1) 아직 지나지 않은(deadline > datetime('now')) 의제만 해당
- decision_status != 'completed' 확인

## 테이블 구조 설명

### 주요 테이블
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

4. **agenda_responses_content**: 의제에 대한 응답 내용
   - sender_organization: 응답한 조직
   - agenda_code: 원본 의제 코드

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

### 2.1 표준 파라미터 목록
다음 파라미터들이 추출되면 반드시 플레이스홀더로 처리:
- `days` - 최근 N일 (integer)
- `organization` - 조직명 (array - 다중 조직 지원)
- `organization_code` - 조직 코드 (array - 다중 코드 지원)
- `agenda_base_version` - 의제 기본 버전 (string)
- `agenda_base` - 의제 기본 정보 (string)
- `keywords` - 검색 키워드 (array - 다중 키워드 지원)
- `status` - 상태 (string)

### 2.2 플레이스홀더 사용 원칙
```sql
-- 올바른 예시
WHERE organization_code = '{organization_code}' 
  AND status = '{status}' 
  AND sent_time >= DATE('now', '-{dates} days')
  AND keywords LIKE '%{keywords}%'

-- 잘못된 예시 (하드코딩)
WHERE organization_code = 'KR' 
  AND status = 'ongoing'
```

### 2.3 통합 파라미터 구조
파라미터는 하나의 배열로 통합 관리:
```json
"parameters": [
  {
    "name": "keywords",
    "type": "array",
    "required": false,
    "default": [],
    "sql_builder": {
      "type": "or_like",
      "fields": ["keywords", "subject", "body"],
      "placeholder": "{keywords_condition}"
    }
  },
  {
    "name": "days",
    "type": "integer",
    "required": false,
    "default": 30
  },
  {
    "name": "organization_code",
    "type": "array",
    "required": false,
    "default": [],
    "sql_builder": {
      "type": "in",
      "field": "organization_code",
      "placeholder": "{org_condition}"
    }
  }
]
```

### 2.4 다중 값 처리
배열 타입 파라미터는 자동으로 다중 값 처리:
- `keywords`: OR LIKE 조건으로 여러 키워드 검색
- `organization_code`: IN 절로 여러 조직 필터링
- `sql_builder`로 복잡한 SQL 조건 생성

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

## 4. 템플릿 구조 예시

### 4.1 단순 쿼리 템플릿
```json
{
  "template_id": "ongoing_agendas_v2",
  "template_version": "2.3",
  "template_category": "agenda_status",
  "query_info": {
    "natural_questions": [
      "진행중인 의제 목록",
      "ongoing 상태 아젠다",
      "현재 진행 중인 안건"
    ],
    "keywords": ["진행중", "ongoing", "진행"]
  },
  "target_scope": {
    "scope_type": "all",
    "target_organizations": [],
    "target_panels": "all"
  },
  "sql_template": {
    "query": "SELECT * FROM agenda_all WHERE decision_status = '{status}' AND sent_time >= DATE('now', '-{days} days') ORDER BY sent_time DESC",
    "system": "현재 진행중인 의제를 최근 날짜순으로 검색합니다. 활발히 논의되고 있는 의제들을 파악하기 위한 쿼리입니다.",
    "user": "진행중인 의제들의 목록을 보고 싶습니다. 의제 코드, 제목, 발송일자, 주요 내용을 포함해주세요."
  },
  "parameters": [
    {
      "name": "status",
      "type": "string",
      "required": false,
      "default": "ongoing"
    },
    {
      "name": "days",
      "type": "integer",
      "required": false,
      "default": 30
    }
  ],
  "embedding_config": {
    "model": "text-embedding-3-large",
    "dimension": 1536
  },
  "expected_response": {
    "description": "진행중인 의제 목록을 시간순으로 정렬하여 제공",
    "format": "list",
    "example": "최근 30일간 진행중인 의제:\n\n1. [IMO-MEPC-82-01] 탄소집약도 지표 개정 (2024-03-15)\n2. [IOPCF-APR24-02] 보상기금 한도 검토 (2024-03-10)\n\n총 5건의 진행중인 의제가 있습니다."
  }
}
```

### 4.2 복잡한 쿼리 템플릿
```json
{
  "template_id": "kr_agenda_with_responses_v2",
  "template_version": "2.3",
  "template_category": "agenda_analysis",
  "query_info": {
    "natural_questions": [
      "KR이 응답해야하는 의제의 주요 이슈 및 다른 기관 의견",
      "KR 답변 필요 안건의 쟁점과 타기관 입장",
      "우리나라 대응 의제의 핵심 사항과 각국 코멘트",
      "KR 회신 대상 아젠다의 이슈별 다른 나라 의견",
      "KR이 응답할 의제에 대한 타국 피드백 종합"
    ],
    "keywords": ["KR", "이슈", "의견", "타기관", "분석"]
  },
  "target_scope": {
    "scope_type": "specific_organization",
    "target_organizations": ["KR"],
    "target_panels": "all"
  },
  "sql_template": {
    "query": "SELECT a.*, r.sender_organization, r.body FROM agenda_chair a LEFT JOIN agenda_responses_content r ON a.agenda_code = r.agenda_code WHERE a.mail_type = 'request' AND a.has_deadline = 1 AND a.deadline > datetime('now') AND {org_response_condition} AND a.decision_status != '{status}'",
    "system": "KR이 응답해야 하는 의제와 다른 기관들의 응답을 함께 조회합니다. 의제별 주요 이슈와 각국의 입장을 종합적으로 파악하기 위한 쿼리입니다.",
    "user": "KR이 응답해야 하는 의제들에 대해 다른 나라들은 어떤 의견을 제시했는지 종합적으로 분석해서 보고 싶습니다. 주요 쟁점과 각국 입장차이를 명확히 정리해주세요."
  },
  "parameters": [
    {
      "name": "organization_code",
      "type": "array",
      "required": false,
      "default": ["KR"],
      "sql_builder": {
        "type": "custom",
        "template": "(a.response_org LIKE '%{value}%' OR a.response_org = 'ALL')",
        "placeholder": "{org_response_condition}"
      }
    },
    {
      "name": "status",
      "type": "string",
      "required": false,
      "default": "completed"
    }
  ],
  "embedding_config": {
    "model": "text-embedding-3-large",
    "dimension": 1536
  },
  "expected_response": {
    "description": "KR 응답 필요 의제의 주요 이슈와 타기관 의견을 종합 분석하여 제공",
    "format": "analysis",
    "example": "KR 응답 필요 의제 분석:\n\n[IMO-MEPC-82-04] GHG 감축 목표\n📌 주요 이슈:\n- 2050 넷제로 달성 방안\n- 중간 목표 설정\n\n🌍 타기관 의견:\n- EU: 2040년까지 70% 감축 제안\n- JP: 단계적 접근 선호\n- US: 시장 기반 조치 우선\n\n💡 권장 대응:\n- 기술적 실현가능성 강조\n- 개도국 지원 방안 포함"
  }
}
```

## 5. SQL 쿼리 작성 규칙

### 5.0 SQL 템플릿 구조
SQL 템플릿은 다음 세 가지 필드를 포함해야 합니다:

```json
"sql_template": {
  "query": "실제 SQL 쿼리문",
  "system": "이 쿼리가 무엇을 검색하는지에 대한 시스템 설명 (검색 의도)",
  "user": "사용자가 원하는 결과가 무엇인지에 대한 설명 (예상 결과)"
}
```

#### 예시:
```json
"sql_template": {
  "query": "SELECT * FROM agenda_chair WHERE mail_type = 'request' AND has_deadline = 1 AND deadline > datetime('now') ORDER BY deadline ASC",
  "system": "의장(Chair)이 발송한 요청 메일 중 마감일이 유효한 미완료 의제를 검색합니다. 우선순위가 높은 응답 필요 항목을 찾기 위한 쿼리입니다.",
  "user": "우리가 응답해야 하는 의제들을 마감일 순으로 정리해서 보고 싶습니다. 각 의제의 요청사항과 마감일까지 남은 기간을 명확히 파악할 수 있도록 해주세요."
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

#### 목록 형식 (list)
```json
"expected_response": {
  "description": "현재 진행중인 모든 패널의 의제 목록을 시간순으로 정렬하여 제공",
  "format": "list",
  "example": "최근 30일간 진행중인 의제 목록입니다:\n\n1. [IMO-MEPC-82] 선박 탄소집약도 지표(CII) 개정안 논의 (2024-03-15)\n   - 패널: MEPC\n   - 상태: ongoing\n   - 주요내용: CII 등급 기준 강화 제안\n\n총 15건의 진행중인 의제가 있습니다."
}
```

#### 우선순위 목록 (priority_list)
```json
"expected_response": {
  "description": "KR이 응답해야 하는 의제 목록을 마감일 순으로 정렬하여 제공",
  "format": "priority_list",
  "example": "KR 응답 필요 의제 (마감일순):\n\n🚨 긴급 (7일 이내):\n1. [IMO-MEPC-82-04] GHG 감축 목표 의견 요청\n   - 마감일: 2024-03-25 (D-3)\n   - 요청사항: 2050 넷제로 목표 달성 방안\n\n⚠️ 중요 (30일 이내):\n2. [IOPCF-APR24-01] 기금 분담금 조정안\n   - 마감일: 2024-04-10 (D-18)"
}
```

#### 분석 형식 (analysis)
```json
"expected_response": {
  "description": "KR 응답 필요 의제의 주요 이슈와 타기관 의견을 종합 분석하여 제공",
  "format": "analysis",
  "example": "KR 응답 필요 의제 분석 (3건):\n\n[IMO-MEPC-82-04] GHG 감축 목표\n📌 주요 이슈:\n- 2050 넷제로 달성 방안\n- 중간 목표(2030, 2040) 설정\n\n🌍 타기관 의견:\n- EU: 2040년까지 70% 감축 제안\n- JP: 기술개발 시간 고려, 단계적 접근"
}
```

#### 통계 형식 (statistics)
```json
"expected_response": {
  "description": "시스템에서 자동 분류되지 못한 메일 수를 제공",
  "format": "statistics",
  "example": "분류 보류 중인 메일: 7건\n\n주요 보류 사유:\n- 의제 코드 누락: 3건\n- 발신자 불명: 2건\n- 형식 오류: 2건"
}
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

## 8. 복잡도 판단 기준

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