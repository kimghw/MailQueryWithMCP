# Query Assistant Template Database System

## Overview

새로운 템플릿 관리 시스템은 기존 JSONL 파일 기반에서 SQLite 데이터베이스 기반으로 전환되었습니다. 이를 통해 다음과 같은 이점을 제공합니다:

- **중앙화된 관리**: 모든 템플릿을 하나의 데이터베이스에서 관리
- **버전 관리**: 템플릿 변경 이력 추적
- **성능 최적화**: 인덱싱 상태 추적으로 불필요한 재인덱싱 방지
- **통계 수집**: 사용 빈도, 성공률 등 모니터링
- **확장성**: 웹 UI나 API 추가 용이

## 구조

```
modules/query_assistant/database/
├── __init__.py
├── template_db_schema.py    # SQLAlchemy 템플릿 모델
├── template_manager.py      # 템플릿 CRUD 및 동기화
├── migrate_jsonl.py        # JSONL 마이그레이션 도구
└── README.md              # 이 문서
```

## 사용 방법

### 1. 기존 JSONL 파일 마이그레이션

```bash
# 기본 마이그레이션
python -m modules.query_assistant.database.migrate_jsonl

# 특정 폴더에서 마이그레이션
python -m modules.query_assistant.database.migrate_jsonl --folder ./custom/templates

# 드라이런 (실제 마이그레이션 없이 테스트)
python -m modules.query_assistant.database.migrate_jsonl --dry-run
```

### 2. CLI를 통한 템플릿 관리

```bash
# 템플릿 목록 보기
python modules/query_assistant/cli_template_manager.py list

# 특정 카테고리 템플릿 보기
python modules/query_assistant/cli_template_manager.py list --category agenda_summary

# 템플릿 통계 보기
python modules/query_assistant/cli_template_manager.py stats

# VectorDB 동기화
python modules/query_assistant/cli_template_manager.py sync

# 템플릿 내보내기
python modules/query_assistant/cli_template_manager.py export --output backup.json
```

### 3. 코드에서 사용

#### 기본 사용법

```python
from modules.query_assistant.query_assistant_db import QueryAssistantWithDB

# Query Assistant 초기화
assistant = QueryAssistantWithDB(
    db_config={"type": "sqlite", "path": "agenda.db"},
    template_db_url="sqlite:///templates.db",
    openai_api_key="your-api-key"
)

# 쿼리 처리
result = assistant.process_query("최근 30일 아젠다 보여줘")
```

#### 템플릿 관리

```python
from modules.query_assistant.database.template_manager import TemplateManager

manager = TemplateManager()

# 새 템플릿 생성
template_data = {
    "template_id": "new_template",
    "natural_questions": "새로운 템플릿 질문",
    "sql_query": "SELECT * FROM table",
    "category": "test",
    "keywords": ["새로운", "템플릿"]
}
manager.create_template(template_data)

# 템플릿 업데이트
manager.update_template("new_template", {"natural_questions": "수정된 질문"})

# 템플릿 조회
template = manager.get_template("new_template")

# 통계 조회
stats = manager.get_statistics()
```

## 템플릿 형식

### 데이터베이스 스키마

```python
class QueryTemplateDB:
    id                    # 자동 증가 ID
    template_id          # 고유 템플릿 ID
    version              # 버전 (기본: "1.0.0")
    natural_questions    # 자연어 질문
    sql_query            # 기본 SQL 쿼리
    sql_query_with_parameters  # 파라미터화된 SQL
    keywords             # 키워드 리스트
    category             # 카테고리
    required_params      # 필수 파라미터
    optional_params      # 선택 파라미터
    default_params       # 기본값
    examples             # 사용 예시
    description          # 설명
    to_agent_prompt      # 에이전트 프롬프트
    vector_indexed       # VectorDB 인덱싱 여부
    embedding_model      # 임베딩 모델
    usage_count          # 사용 횟수
    is_active            # 활성화 상태
    created_at           # 생성 시각
    updated_at           # 수정 시각
    last_used_at         # 마지막 사용 시각
```

### JSON 템플릿 예시

```json
{
    "template_id": "recent_agendas_by_period",
    "natural_questions": "최근 {period} 아젠다 보여줘",
    "sql_query": "SELECT * FROM agenda_chair ORDER BY sent_time DESC LIMIT 20",
    "sql_query_with_parameters": "SELECT * FROM agenda_chair WHERE sent_time >= datetime('now', '-{days} days') ORDER BY sent_time DESC",
    "keywords": ["최근", "아젠다", "기간"],
    "category": "agenda_list",
    "required_params": ["period"],
    "optional_params": ["limit"],
    "default_params": {
        "days": 30,
        "limit": 20
    },
    "examples": [
        {
            "query": "최근 30일 아젠다",
            "params": {"period": "30일", "days": 30}
        }
    ]
}
```

## 마이그레이션 가이드

### 1단계: 백업

```bash
# 기존 JSONL 파일 백업
cp -r modules/query_assistant/templates/data ./backup_templates
```

### 2단계: 마이그레이션 실행

```bash
# 드라이런으로 확인
python -m modules.query_assistant.database.migrate_jsonl --dry-run

# 실제 마이그레이션
python -m modules.query_assistant.database.migrate_jsonl
```

### 3단계: 검증

```bash
# 통계 확인
python modules/query_assistant/cli_template_manager.py stats

# 템플릿 목록 확인
python modules/query_assistant/cli_template_manager.py list
```

### 4단계: 코드 업데이트

```python
# 기존 코드
from modules.query_assistant.query_assistant import QueryAssistant

# 새 코드
from modules.query_assistant.query_assistant_db import QueryAssistantWithDB
```

## 트러블슈팅

### VectorDB 동기화 실패

```bash
# 수동 동기화
python modules/query_assistant/cli_template_manager.py sync --batch-size 10
```

### 중복 템플릿 오류

```python
# 기존 템플릿 확인
templates = manager.list_templates()
existing_ids = [t.template_id for t in templates]
```

### 성능 최적화

- 배치 크기 조정: `--batch-size` 파라미터 사용
- 차원 축소 활성화: `use_dimension_reduction=True`
- 인덱스 최적화: 자주 검색되는 필드에 인덱스 추가

## 추가 기능

### 웹 API 엔드포인트

```python
# FastAPI 예시
@app.get("/api/templates")
async def list_templates(category: Optional[str] = None):
    templates = assistant.template_manager.list_templates(category=category)
    return [t.to_dict() for t in templates]

@app.post("/api/templates/sync")
async def sync_templates():
    result = await assistant.template_manager.full_sync()
    return result
```

### 모니터링

```python
# 사용 통계 수집
stats = assistant.get_template_stats()
print(f"Total templates: {stats['total_templates']}")
print(f"Most used: {stats['most_used'][0].template_id}")
```

## 참고사항

- SQLite 데이터베이스는 `templates.db` 파일로 생성됩니다
- VectorDB와의 동기화는 비동기로 실행됩니다
- 템플릿 수정 시 자동으로 `vector_indexed=False`로 설정되어 재인덱싱됩니다
- 소프트 삭제가 기본이며, 하드 삭제는 `--hard` 옵션 사용