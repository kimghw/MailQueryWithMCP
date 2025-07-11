# Query Assistant Module

벡터 데이터베이스 기반의 자연어 SQL 쿼리 변환 시스템입니다. Qdrant를 사용하여 의미적 유사성 검색과 키워드 매칭을 결합한 하이브리드 검색을 제공합니다.

## 주요 기능

- **자연어 쿼리 처리**: 한국어/영어 자연어를 SQL로 자동 변환
- **하이브리드 검색**: 벡터 유사도와 키워드 매칭을 결합한 정확한 템플릿 매칭
- **쿼리 확장**: 동의어, 관련어를 활용한 지능형 쿼리 이해
- **MCP 통합**: Claude Desktop에서 @iacsgraph로 직접 사용 가능

## 설치 방법

### 1. Qdrant 설치 및 실행

```bash
# Docker를 사용한 Qdrant 실행
docker run -p 6333:6333 \
  -v $(pwd)/qdrant_storage:/qdrant/storage:z \
  qdrant/qdrant
```

### 2. Python 의존성 설치

```bash
# 프로젝트 루트에서 실행
uv sync

# SQL Server 사용 시 추가 설치
pip install pyodbc

# PostgreSQL 사용 시 추가 설치
pip install psycopg2-binary
```

### 3. SQL Server ODBC 드라이버 설치 (SQL Server 사용 시)

#### Windows
- [Microsoft ODBC Driver 17 for SQL Server](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server) 다운로드 및 설치

#### Linux (Ubuntu/Debian)
```bash
# Microsoft 저장소 추가
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list

# ODBC 드라이버 설치
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql17
sudo apt-get install -y unixodbc-dev
```

## 사용 방법

### 1. 직접 사용

#### SQLite 사용
```python
from modules.query_assistant import QueryAssistant

# SQLite 데이터베이스 사용
qa = QueryAssistant(
    db_path="/path/to/iacsgraph.db",  # 기존 방식 (호환성)
    qdrant_url="localhost",
    qdrant_port=6333
)

# 또는 명시적 설정
qa = QueryAssistant(
    db_config={"type": "sqlite", "path": "/path/to/iacsgraph.db"},
    qdrant_url="localhost",
    qdrant_port=6333
)
```

#### SQL Server 사용
```python
# Windows 인증
qa = QueryAssistant(
    db_config={
        "type": "sqlserver",
        "server": "localhost\\SQLEXPRESS",
        "database": "IACSGraph",
        "trusted_connection": True,
        "driver": "{ODBC Driver 17 for SQL Server}"
    }
)

# SQL Server 인증
qa = QueryAssistant(
    db_config={
        "type": "sqlserver",
        "server": "localhost",
        "database": "IACSGraph",
        "username": "sa",
        "password": "YourPassword123!",
        "trusted_connection": False
    }
)

# Azure SQL Database
qa = QueryAssistant(
    db_config={
        "type": "sqlserver",
        "server": "your-server.database.windows.net",
        "database": "IACSGraph",
        "username": "your-username",
        "password": "your-password"
    }
)
```

#### PostgreSQL 사용
```python
qa = QueryAssistant(
    db_config={
        "type": "postgresql",
        "host": "localhost",
        "port": 5432,
        "database": "iacsgraph",
        "user": "postgres",
        "password": "password"
    }
)
```

#### 쿼리 실행
```python
# 자연어 쿼리 실행
result = qa.process_query("최근 7일 주요 아젠다는 무엇인가?")
print(f"실행된 SQL: {result.executed_sql}")
print(f"결과: {result.results}")

# 쿼리 분석 (실행하지 않음)
analysis = qa.analyze_query("KRSDTP 기관의 응답률은?")
print(f"추출된 키워드: {analysis['extracted_keywords']}")
print(f"매칭 템플릿: {analysis['matching_templates']}")
```

### 2. MCP Server 실행

#### SQLite 사용
```bash
# 환경 변수 설정
export IACSGRAPH_DB_PATH=/path/to/iacsgraph.db
export QDRANT_URL=localhost
export QDRANT_PORT=6333

# MCP Server 실행
python -m modules.query_assistant.mcp_server
```

#### SQL Server 사용
```bash
# JSON 형식으로 데이터베이스 설정
export IACSGRAPH_DB_CONFIG='{
  "type": "sqlserver",
  "server": "localhost\\SQLEXPRESS",
  "database": "IACSGraph",
  "trusted_connection": true,
  "driver": "{ODBC Driver 17 for SQL Server}"
}'

# MCP Server 실행
python -m modules.query_assistant.mcp_server
```

#### PostgreSQL 사용
```bash
export IACSGRAPH_DB_CONFIG='{
  "type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "database": "iacsgraph",
  "user": "postgres",
  "password": "password"
}'

python -m modules.query_assistant.mcp_server
```

### 3. Claude Desktop 설정

#### SQLite 사용
`claude_desktop_config.json`에 추가:

```json
{
  "mcpServers": {
    "iacsgraph": {
      "command": "python",
      "args": ["-m", "modules.query_assistant.mcp_server"],
      "env": {
        "IACSGRAPH_DB_PATH": "/path/to/iacsgraph.db"
      }
    }
  }
}
```

#### SQL Server 사용
```json
{
  "mcpServers": {
    "iacsgraph": {
      "command": "python",
      "args": ["-m", "modules.query_assistant.mcp_server"],
      "env": {
        "IACSGRAPH_DB_CONFIG": "{\"type\":\"sqlserver\",\"server\":\"localhost\\\\SQLEXPRESS\",\"database\":\"IACSGraph\",\"trusted_connection\":true}"
      }
    }
  }
}
```

## 지원되는 쿼리 유형

### 1. 아젠다 요약
- "최근 7일 주요 아젠다는 무엇인가?"
- "지난달 아젠다 목록을 보여주세요"

### 2. 기관별 통계
- "KRSDTP 기관의 응답률은 어떻게 되나요?"
- "기관별 응답률을 비교해주세요"

### 3. 상태별 조회
- "승인된 아젠다 목록을 보여주세요"
- "미결정 아젠다는 무엇인가요?"

### 4. 검색 기능
- "예산이 포함된 응답을 검색해주세요"
- "긴급 아젠다를 찾아주세요"

### 5. 분석 보고서
- "이번주 요약 보고서를 만들어주세요"
- "평균 응답 시간은 얼마나 되나요?"

## 쿼리 템플릿 추가

새로운 쿼리 패턴을 추가하려면 `templates/__init__.py`의 `QUERY_TEMPLATES`에 추가:

```python
{
    "id": "unique_template_id",
    "natural_query": "자연어 쿼리 패턴",
    "sql_template": """
        SELECT ... FROM ... WHERE ...
    """,
    "keywords": ["키워드1", "키워드2"],
    "required_params": ["param1"],
    "optional_params": ["param2"],
    "category": "category_name"
}
```

## 아키텍처

```
사용자 입력
    ↓
키워드 추출 (KeywordExpander)
    ↓
벡터 검색 (VectorStore + Qdrant)
    ↓
템플릿 매칭 & 파라미터 추출
    ↓
SQL 생성 및 실행
    ↓
결과 포맷팅
```

## 주요 컴포넌트

- **QueryAssistant**: 메인 쿼리 처리 엔진
- **VectorStore**: Qdrant 벡터 데이터베이스 관리
- **KeywordExpander**: 쿼리 확장 및 동의어 처리
- **Templates**: SQL 쿼리 템플릿 정의
- **MCPServer**: Claude Desktop 통합

## 성능 최적화

- 템플릿은 시작 시 한 번만 인덱싱
- 자주 사용되는 쿼리는 usage_count로 추적
- 하이브리드 스코어링으로 정확도 향상

## 문제 해결

### Qdrant 연결 오류
```bash
# Qdrant 상태 확인
curl http://localhost:6333/health
```

### 템플릿 매칭 실패
- 키워드가 충분히 구체적인지 확인
- `analyze_query()`로 쿼리 분석 결과 확인

### MCP Server 오류
- 로그 확인: `tail -f logs/query_assistant.log`
- 환경 변수 설정 확인