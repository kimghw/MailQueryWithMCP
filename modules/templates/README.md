# Template Management Module

템플릿 관리를 위한 독립적인 모듈입니다.

## 구조

```
modules/templates/
├── data/
│   └── unified/
│       └── query_templates_unified.json    # 통합 템플릿 파일
├── uploaders/
│   ├── sql_uploader.py                     # SQL DB 업로더
│   ├── qdrant_uploader.py                  # Vector DB 업로더
│   └── uploader.py                         # 통합 업로더
├── validators/
│   ├── template_validator.py               # 템플릿 구조 검증
│   └── parameter_validator.py              # 파라미터 검증
└── tools/
    └── cli.py                              # CLI 도구
```

## 사용법

### 1. 템플릿 검증
```bash
# 기본 템플릿 파일 검증
python -m modules.templates.tools.cli validate

# 특정 파일 검증
python -m modules.templates.tools.cli validate --file path/to/templates.json
```

### 2. 템플릿 업로드
```bash
# SQL과 Qdrant 모두 업로드
python -m modules.templates.tools.cli upload

# SQL만 업로드
python -m modules.templates.tools.cli upload --target sql

# Qdrant만 업로드 (컬렉션 재생성)
python -m modules.templates.tools.cli upload --target qdrant --recreate
```

### 3. 동기화 상태 확인
```bash
python -m modules.templates.tools.cli sync
```

### 4. 템플릿 검색
```bash
python -m modules.templates.tools.cli search "한국선급 응답"
```

## 템플릿 추가 워크플로우

1. **템플릿 작성**
   - `data/unified/query_templates_unified.json` 파일 편집
   - 새 템플릿 추가

2. **검증**
   ```bash
   python -m modules.templates.tools.cli validate
   ```

3. **업로드**
   ```bash
   python -m modules.templates.tools.cli upload
   ```

4. **확인**
   ```bash
   python -m modules.templates.tools.cli sync
   python -m modules.templates.tools.cli search "새 템플릿 관련 검색어"
   ```

## 템플릿 구조

```json
{
  "template_id": "example_template_v2",
  "template_version": "1.0.0",
  "template_category": "agenda_status",
  "query_info": {
    "natural_questions": [
      "예시 질문 1",
      "예시 질문 2",
      "예시 질문 3"
    ],
    "keywords": ["키워드1", "키워드2"]
  },
  "target_scope": {
    "scope_type": "all",
    "target_organizations": [],
    "target_panels": "all"
  },
  "sql_template": {
    "query": "SELECT * FROM agenda_all WHERE {condition}",
    "system": "쿼리 목적 설명",
    "user": "사용자 요구사항"
  },
  "parameters": [
    {
      "name": "condition",
      "type": "string",
      "required": false,
      "default": "1=1"
    }
  ]
}
```

## 주의사항

- template_id는 `_v2`로 끝나야 함
- natural_questions는 최소 3개 이상
- SQL의 플레이스홀더 `{param}`은 parameters에 정의되어야 함
- 카테고리는 정의된 목록 중에서 선택