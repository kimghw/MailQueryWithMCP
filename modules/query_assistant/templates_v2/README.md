# Query Templates v2

IACSGRAPH 쿼리 시스템의 템플릿 및 문서 저장소입니다.

## 📁 디렉토리 구조

```
templates_v2/
├── README.md                           # 이 문서
├── UNIFIED_QUERY_SYSTEM_GUIDE.md      # 🔥 통합 시스템 가이드 (필독)
├── TEMPLATE_VERSION_HISTORY.md        # 버전별 변경 이력
├── QUERY_GUIDELINES.md                # 사용자 쿼리 작성 가이드
├── QUERY_GUIDELINES_TECHNICAL.md      # 개발자 기술 가이드
│
├── query_templates_v2.6.json          # v2.6 기본 템플릿
├── additional_templates_v2.7.json     # v2.7 통계/분석 템플릿
├── additional_templates_v2.8.json     # v2.8 상세 분석 템플릿
├── additional_templates_v2.9.json     # v2.9 라우팅 시스템 템플릿
├── additional_templates_v2.10.json    # v2.10 데이터 품질/조직 특화
│
├── v2.8_vectordb_routing.json         # v2.8 VectorDB 라우팅 템플릿
├── query_routing_metadata.json        # 쿼리 라우팅 메타데이터
├── v2.8_vectordb_metadata.json        # v2.8 VectorDB 메타데이터
│
└── version_summaries/                 # 버전별 상세 문서
    ├── V2.8_ROUTING_ANALYSIS.md
    ├── V2.9_TEMPLATE_SUMMARY.md
    ├── V2.10_ROUTING_SUMMARY.md
    ├── COMPLETE_ROUTING_SUMMARY.md
    ├── QUERY_ROUTING_UPDATE_v2.9.md
    ├── VECTORDB_INTEGRATION_SUMMARY.md
    └── VECTORDB_VS_QUERY_TEMPLATES.md
```

## 🚀 빠른 시작

### 1. 시스템 이해하기
**[UNIFIED_QUERY_SYSTEM_GUIDE.md](./UNIFIED_QUERY_SYSTEM_GUIDE.md)** 를 먼저 읽어보세요.
이 문서는 전체 시스템을 이해하는 데 필요한 모든 정보를 담고 있습니다.

### 2. 쿼리 작성하기
- 사용자라면: **[QUERY_GUIDELINES.md](./QUERY_GUIDELINES.md)**
- 개발자라면: **[QUERY_GUIDELINES_TECHNICAL.md](./QUERY_GUIDELINES_TECHNICAL.md)**

### 3. 템플릿 찾기
- 버전별 기능은 **[TEMPLATE_VERSION_HISTORY.md](./TEMPLATE_VERSION_HISTORY.md)** 참조
- 특정 기능의 템플릿은 해당 버전 JSON 파일에서 검색

## 📊 템플릿 통계

| 버전 | 주요 기능 | SQL | VectorDB | LLM | 총합 |
|------|-----------|-----|----------|-----|------|
| v2.6 | 기본 기능 | ~20 | 0 | 0 | ~20 |
| v2.7 | 통계/분석 | 46 | 0 | 0 | 46 |
| v2.8 | 상세 분석 | 33 | 9 | 0 | 42 |
| v2.9 | 라우팅 | 11 | 15 | 3 | 29 |
| v2.10 | 품질/조직 | 40 | 0 | 0 | 40 |
| **합계** | | **~150** | **24** | **3** | **~177** |

## 🔧 개발자 가이드

### 새 템플릿 추가하기
1. 적절한 버전 파일 선택 (새 버전이 필요하면 `v2.11.json` 생성)
2. 템플릿 구조 작성:
```json
{
  "template_id": "unique_identifier_v2",
  "template_version": "2.x",
  "template_category": "category_name",
  "query_info": {
    "natural_questions": ["질문1", "질문2", "질문3"],
    "keywords": ["키워드1", "키워드2"]
  },
  "routing_info": {  // 필요시
    "route_to": "sql|vectordb|llm_direct",
    "reason": "라우팅 이유"
  },
  "sql_template": {
    "query": "SQL 쿼리 또는 라우팅 안내",
    "system": "시스템 설명",
    "user": "사용자 설명"
  },
  "parameters": []
}
```

### 라우팅 타입
- **sql**: 일반 SQL 쿼리 실행
- **vectordb**: VectorDB MCP 호출
- **llm_direct**: LLM이 직접 응답

### 테스트
1. 템플릿 JSON 유효성 검증
2. 쿼리 매칭 테스트
3. 파라미터 추출 테스트
4. SQL 실행 테스트 (SQL 타입인 경우)

## 🔍 주요 기능별 템플릿 위치

### 의제 관리
- 기본 조회: v2.6
- 상태 관리: v2.6, v2.10
- 상세 분석: v2.8

### 응답 관리
- 기본 응답: v2.6
- 응답률 통계: v2.7, v2.10
- 의견 분석: v2.8

### 키워드 분석
- 기본 키워드: v2.7
- 시간별 키워드: v2.9
- 조직별 키워드: v2.10

### 회의/PT 정보
- 회의 정보: v2.8 (VectorDB)
- PT 정보: v2.9 (VectorDB)

### 기술 분석
- 기술 동향: v2.9 (LLM Direct)
- 기술 배경: v2.9 (LLM Direct)

## 📞 문의

질문이나 제안사항이 있으시면 이슈를 생성해주세요.