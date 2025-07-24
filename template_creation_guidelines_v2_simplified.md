# 쿼리 템플릿 작성 가이드라인 v2.0 (간소화 버전)

## 1. 핵심 원칙

1. **필수 파라미터는 명확히 구분** - 사용자가 반드시 제공해야 하는 값
2. **기본값은 합리적으로** - 대부분의 경우에 맞는 기본값 설정
3. **날짜는 유연하게** - days 또는 date_from/date_to 패턴 사용

## 2. 최소 템플릿 구조

```json
{
  "template_id": "organization_agenda_status_v2",
  "template_version": "2.0",
  "template_category": "agenda_status",
  "query_info": {
    "natural_questions": [
      "KR의 진행중인 의제 목록",
      "한국이 처리중인 안건들",
      "우리나라 ongoing 의제"
    ],
    "keywords": ["KR", "진행중", "ongoing", "한국"]
  },
  "target_scope": {
    "scope_type": "specific_organization",
    "target_organizations": ["KR"],
    "target_panels": "all"
  },
  "sql_template": {
    "query": "SELECT * FROM agendas WHERE organization_code = '{organization_code}' AND status = '{status}' AND created_at >= DATE('now', '-{days} days')"
  },
  "parameters": {
    "required_params": [
      {
        "name": "organization_code",
        "type": "string"
      }
    ],
    "optional_params": [
      {
        "name": "status",
        "type": "string"
      },
      {
        "name": "days",
        "type": "integer"
      }
    ],
    "default_params": {
      "organization_code": "KR",
      "status": "ongoing",
      "days": 30
    }
  },
  "embedding_config": {
    "model": "text-embedding-3-large",
    "dimension": 1536
  }
}
```

## 3. 파라미터 정의 가이드

### 3.1 필수 vs 선택 파라미터

**필수 파라미터 (required_params)**
- 쿼리 실행에 반드시 필요한 값
- 기본값이 있어도 사용자가 명시적으로 제공해야 함
- 예: 특정 조직 조회 시 organization_code

**선택 파라미터 (optional_params)**
- 없어도 쿼리 실행 가능
- default_params의 값으로 대체
- 예: 날짜 범위, 상태 필터

### 3.2 날짜 파라미터 패턴

#### 패턴 1: 최근 N일 (권장)
```json
{
  "optional_params": [
    {
      "name": "days",
      "type": "integer"
    }
  ],
  "default_params": {
    "days": 30
  }
}
```
SQL: `WHERE created_at >= DATE('now', '-{days} days')`

#### 패턴 2: 날짜 범위 지정
```json
{
  "optional_params": [
    {
      "name": "date_from",
      "type": "date"
    },
    {
      "name": "date_to", 
      "type": "date"
    }
  ],
  "default_params": {
    "date_from": null,
    "date_to": null
  }
}
```
SQL: `WHERE created_at BETWEEN '{date_from}' AND '{date_to}'`

#### 패턴 3: 하이브리드 (가장 유연함)
```json
{
  "optional_params": [
    {
      "name": "days",
      "type": "integer"
    },
    {
      "name": "date_from",
      "type": "date"
    },
    {
      "name": "date_to",
      "type": "date"
    }
  ],
  "default_params": {
    "days": 30,
    "date_from": null,
    "date_to": null
  }
}
```
SQL: 
```sql
WHERE created_at >= 
  CASE 
    WHEN '{date_from}' != 'null' THEN '{date_from}'
    ELSE DATE('now', '-{days} days')
  END
```

## 4. 카테고리별 템플릿 예시

### 4.1 조직별 의제 조회
```json
{
  "template_id": "org_agenda_list_v2",
  "template_category": "organization_response",
  "parameters": {
    "required_params": [
      {"name": "organization_code", "type": "string"}
    ],
    "optional_params": [
      {"name": "status", "type": "string"},
      {"name": "days", "type": "integer"}
    ],
    "default_params": {
      "status": "all",
      "days": 30
    }
  }
}
```

### 4.2 키워드 검색
```json
{
  "template_id": "keyword_search_v2",
  "template_category": "agenda_search",
  "parameters": {
    "required_params": [
      {"name": "keywords", "type": "string"}
    ],
    "optional_params": [
      {"name": "organization_code", "type": "string"},
      {"name": "days", "type": "integer"}
    ],
    "default_params": {
      "organization_code": "all",
      "days": 90
    }
  }
}
```

### 4.3 통계 조회
```json
{
  "template_id": "agenda_count_v2",
  "template_category": "agenda_statistics",
  "parameters": {
    "required_params": [],
    "optional_params": [
      {"name": "status", "type": "string"},
      {"name": "organization_code", "type": "string"}
    ],
    "default_params": {
      "status": "all",
      "organization_code": "all"
    }
  }
}
```

## 5. 파라미터 검증 동작

### 5.1 필수 파라미터 누락 시
```json
{
  "status": "error",
  "error": "필수 파라미터가 누락되었습니다: 'organization_code' - 조직 코드 (예: KR, US, JP)",
  "missing_params": ["organization_code"],
  "required_params": ["organization_code"]
}
```

### 5.2 성공 시
```json
{
  "status": "success",
  "template_id": "org_agenda_list_v2",
  "sql_query": "SELECT * FROM agendas WHERE organization_code = 'KR' AND status = 'ongoing'",
  "parameters": {
    "organization_code": "KR",
    "status": "ongoing",
    "days": 30
  }
}
```

## 6. 체크리스트

- [ ] 필수 파라미터는 최소화했는가?
- [ ] 기본값은 가장 일반적인 사용 케이스를 반영하는가?
- [ ] 날짜 처리는 days 파라미터를 우선 고려했는가?
- [ ] SQL 쿼리의 파라미터 플레이스홀더가 올바른가? (`{param_name}`)
- [ ] 자연어 질문은 3개 이상, 다양한 표현으로 작성했는가?
- [ ] 키워드는 검색에 도움이 되는 핵심 단어들인가?

## 7. 주의사항

1. **description 필드 제거** - 간소화를 위해 파라미터 설명은 제거
2. **validation 필드 제거** - 타입 체크만으로 충분
3. **날짜는 단순하게** - 특별한 경우가 아니면 days 파라미터 사용
4. **플레이스홀더 형식** - `{param_name}` 형식 사용 (`:param_name` 아님)