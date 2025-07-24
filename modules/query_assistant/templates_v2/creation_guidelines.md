# 쿼리 템플릿 작성 가이드라인 v2.1 (Updated)

## 1. 핵심 원칙

1. **필수 파라미터는 명확히 구분** - 사용자가 반드시 제공해야 하는 값
2. **모든 파라미터는 플레이스홀더로** - 필수/선택 모두 `{param_name}` 형식 사용
3. **선택 파라미터는 반드시 기본값 제공** - default_params에 합리적인 기본값 설정
4. **자연어 질문 개수**:
   - 단순 쿼리: 3개
   - 복잡한 쿼리: 5개 이상

## 2. 파라미터 처리 규칙

### 2.1 표준 파라미터 목록
다음 파라미터들이 추출되면 반드시 플레이스홀더로 처리:
- `dates` - 최근 N일
- `organization` - 조직명
- `organization_code` - 조직 코드
- `agenda_base_version` - 의제 기본 버전
- `agenda_base` - 의제 기본 정보
- `keywords` - 검색 키워드
- `status` - 상태

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

### 2.3 기본값 설정
모든 선택 파라미터는 반드시 default_params에 기본값 필요:
```json
"default_params": {
  "dates": 30,
  "organization_code": "KR",
  "status": "all",
  "keywords": null,
  "agenda_base": null,
  "agenda_base_version": null
}
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
  "한국이 답변 필요한 안건의 타기관 코멘트",
  "KR 응답 대상 의제에 대한 각국 입장 요약",
  "우리나라가 회신해야 할 아젠다의 타국 의견",
  "한국 대응 필요 의제의 다른 나라 피드백 분석"
]
```

## 4. 템플릿 구조 예시

### 4.1 단순 쿼리 템플릿
```json
{
  "template_id": "ongoing_agendas_v2",
  "template_version": "2.0",
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
    "query": "SELECT * FROM agenda_all WHERE decision_status = '{status}' AND sent_time >= DATE('now', '-{dates} days') ORDER BY sent_time DESC"
  },
  "parameters": {
    "required_params": [],
    "optional_params": [
      {"name": "status", "type": "string"},
      {"name": "dates", "type": "integer"}
    ],
    "default_params": {
      "status": "ongoing",
      "dates": 30
    }
  },
  "embedding_config": {
    "model": "text-embedding-3-large",
    "dimension": 1536
  }
}
```

### 4.2 복잡한 쿼리 템플릿
```json
{
  "template_id": "kr_agenda_with_responses_v2",
  "template_version": "2.0",
  "template_category": "agenda_analysis",
  "query_info": {
    "natural_questions": [
      "KR이 응답해야하는 의제의 주요 이슈 및 다른 기관 의견",
      "한국 답변 필요 안건의 쟁점과 타기관 입장",
      "우리나라 대응 의제의 핵심 사항과 각국 코멘트",
      "KR 회신 대상 아젠다의 이슈별 다른 나라 의견",
      "한국이 응답할 의제에 대한 타국 피드백 종합"
    ],
    "keywords": ["KR", "이슈", "의견", "타기관", "분석"]
  },
  "target_scope": {
    "scope_type": "specific_organization",
    "target_organizations": ["KR"],
    "target_panels": "all"
  },
  "sql_template": {
    "query": "SELECT a.*, r.sender_organization, r.body FROM agenda_all a LEFT JOIN agenda_responses_content r ON a.agenda_code = r.agenda_code WHERE (a.response_org LIKE '%{organization_code}%' OR a.response_org = 'ALL') AND a.decision_status != '{status}' AND a.sent_time >= DATE('now', '-{dates} days')"
  },
  "parameters": {
    "required_params": [],
    "optional_params": [
      {"name": "organization_code", "type": "string"},
      {"name": "status", "type": "string"},
      {"name": "dates", "type": "integer"}
    ],
    "default_params": {
      "organization_code": "KR",
      "status": "completed",
      "dates": 30
    }
  },
  "embedding_config": {
    "model": "text-embedding-3-large",
    "dimension": 1536
  }
}
```

## 5. SQL 쿼리 작성 규칙

### 5.1 날짜 처리
```sql
-- dates 파라미터 사용
WHERE sent_time >= DATE('now', '-{dates} days')

-- date_from/date_to 사용
WHERE sent_time BETWEEN '{date_from}' AND '{date_to}'
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

## 6. 체크리스트

- [ ] 필수 파라미터는 최소화했는가?
- [ ] 모든 파라미터가 플레이스홀더로 되어 있는가?
- [ ] 선택 파라미터는 모두 기본값이 있는가?
- [ ] 단순 쿼리는 3개, 복잡한 쿼리는 5개 이상의 자연어 질문이 있는가?
- [ ] 표준 파라미터(dates, organization_code 등)를 올바르게 사용했는가?
- [ ] SQL에 하드코딩된 값이 없는가?

## 7. 복잡도 판단 기준

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