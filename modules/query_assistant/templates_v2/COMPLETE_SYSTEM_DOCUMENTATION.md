# IACSGRAPH 쿼리 시스템 완전 통합 문서

## 목차
1. [시스템 개요](#1-시스템-개요)
2. [쿼리 작성 가이드](#2-쿼리-작성-가이드)
3. [기술 구현 가이드](#3-기술-구현-가이드)
4. [템플릿 시스템](#4-템플릿-시스템)
5. [쿼리 라우팅 시스템](#5-쿼리-라우팅-시스템)
6. [VectorDB 통합](#6-vectordb-통합)
7. [KR 템플릿 분석 및 업데이트](#7-kr-템플릿-분석-및-업데이트)
8. [버전 관리 및 히스토리](#8-버전-관리-및-히스토리)

---

## 1. 시스템 개요

### 1.1 시스템 아키텍처

IACSGRAPH 쿼리 시스템은 자연어 쿼리를 분석하여 적절한 처리 방식으로 라우팅하는 통합 시스템입니다.

```
사용자 쿼리 
    ↓
LLM 파라미터 추출 (Claude)
    ↓
MCP 서버 (query_with_llm_params)
    ↓
쿼리 라우터 (자동 라우팅)
    ↓
┌─────────────┬──────────────┬─────────────┐
│ SQL Template│  VectorDB    │ LLM Direct  │
│             │              │             │
│ 구조화 데이터│ 문서 검색    │ 직접 응답   │
└─────────────┴──────────────┴─────────────┘
```

### 1.2 주요 구성 요소

#### MCP Server (Enhanced)
- LLM 파라미터 지원
- 쿼리 스코프 처리 (all/one/more)
- 향상된 날짜 처리 (30일 기본값)
- 조직 파라미터화 지원

#### QueryAssistant
- 템플릿 매칭 (Qdrant 벡터 DB)
- 하이브리드 스코어링 (70% 벡터, 30% 키워드)
- 3% 허용 범위 내 유사 템플릿 제시

#### Query Router
- SQL/VectorDB/LLM 자동 라우팅
- routing_info 메타데이터 기반 처리
- 패턴 기반 폴백 메커니즘

### 1.3 처리 방식별 특징

#### SQL Templates
- 구조화된 데이터베이스 쿼리
- 의제 정보, 응답 현황, 통계 분석
- 정확한 필드 매칭과 집계

#### VectorDB MCP
- 비정형 문서 검색
- 규정, 가이드라인, 회의록
- 의미적 유사성 기반 검색

#### LLM Direct Response
- 기술 동향 분석
- 배경 설명
- 일반 지식 기반 응답

---

## 2. 쿼리 작성 가이드

### 2.1 기본 원칙

#### 명확한 의도 표현
- ✅ 좋은 예: "한국선급이 아직 응답하지 않은 진행중 의제"
- ❌ 나쁜 예: "KR 의제"

#### 시간 범위 명시
- ✅ 좋은 예: "최근 3개월 동안 논의된 의제"
- ❌ 나쁜 예: "최근 의제" (모호함)
- 기본값: 날짜 미지정 시 **최근 30일** 적용

#### 조직/기관 명확히 지정
- ✅ 좋은 예: "Bureau Veritas의 승인 현황"
- ❌ 나쁜 예: "승인 현황" (어느 기관인지 불명확)
- 기본값: 기관 미지정 시 **KR (한국선급)** 적용

### 2.2 쿼리 범위 (Scope) 지정

#### 'all' - 모든 패널/기관
```
예시:
- "모든 패널의 진행중인 의제"
- "전체 기관의 응답 현황"
- "각 기관별 평균 응답시간"
```

#### 'one' - 단일 패널/기관
```
예시:
- "KR이 응답하지 않은 의제"
- "한국선급 평균 응답시간"
- "PL 패널의 최근 의제"
```

#### 'more' - 2개 이상 패널/기관
```
예시:
- "KR과 BV의 응답 비교"
- "한국, 중국, 일본의 승인율"
- "여러 기관의 미응답 의제"
```

### 2.3 지원 기관 코드

| 기관명 | 코드 | 다른 표현 |
|--------|------|-----------| 
| 한국선급 | KR | Korean Register, 한국 |
| Bureau Veritas | BV | 뷰로베리타스 |
| 중국선급 | CCS | China Classification Society, 중국 |
| American Bureau of Shipping | ABS | 미국선급 |
| DNV GL | DNV | - |
| Lloyd's Register | LR | 로이드 |
| 일본선급 | NK | Nippon Kaiji Kyokai |
| 이탈리아선급 | RINA | Registro Italiano Navale |
| 러시아선급 | RS | Russian Maritime Register |
| 인도선급 | IRS | Indian Register of Shipping |
| 폴란드선급 | PRS | Polish Register of Shipping |
| 터키선급 | TL | Türk Loydu |

### 2.4 날짜 표현

#### 상대적 날짜
- 오늘, 어제
- 이번주, 지난주
- 이번달, 지난달
- 최근 N일/주/개월
- 3개월, 6개월, 1년

#### 절대적 날짜
- 2024-01-01
- 2024년 1월 1일
- 2024.01.01

### 2.5 주요 쿼리 카테고리

#### 의제 상태 조회
```
- "진행중인 의제"
- "완료되지 않은 의제"
- "마감일이 임박한 의제"
- "오늘 응답해야 하는 의제"
```

#### 기관별 응답 현황
```
- "[기관]이 응답하지 않은 의제"
- "[기관]이 응답해야 하는 의제"
- "[기관]의 응답 키워드"
```

#### 통계 및 분석
```
- "[기관] 평균 응답시간"
- "월별 의제 수"
- "패널별 의제 분포"
- "승인/반려 통계"
```

#### 키워드 검색
```
- "IMO 관련 의제"
- "사이버 보안 키워드 의제"
- "디지털 전환 관련 논의"
```

---

## 3. 기술 구현 가이드

### 3.1 LLM 파라미터 추출

Claude가 추출해야 하는 파라미터:
```json
{
    "query": "원본 쿼리",
    "extracted_dates": {
        "start": "2024-01-01",
        "end": "2024-12-31",
        "days": "30"
    },
    "extracted_keywords": ["keyword1", "keyword2"],
    "query_scope": "all|one|more"
}
```

### 3.2 데이터베이스 스키마

```sql
-- 의제 정보
agenda_all (
    agenda_code,        -- PL25016a
    subject,           -- 제목
    sender_organization, -- 발신 기관
    response_org,      -- 응답 필요 기관 (쉼표 구분)
    decision_status,   -- ongoing/completed/pending
    deadline,          -- 마감일
    sent_time         -- 발송 시간
)

-- 응답 정보
agenda_responses_content (
    agenda_code,
    sender_organization,  -- 응답한 기관
    body,               -- 응답 내용
    keywords,           -- 추출된 키워드
    sent_time          -- 응답 시간
)
```

### 3.3 파라미터 처리 우선순위

1. LLM 추출 파라미터 (최우선)
2. 규칙 기반 추출
3. 템플릿 기본값
4. 시스템 기본값

### 3.4 SQL 생성 규칙

#### 플레이스홀더 변환
```sql
-- 템플릿
WHERE organization = {organization}

-- 변환 후 (organization = "KR")
WHERE organization = 'KR'
```

#### 날짜 조건 생성
```sql
-- 상대적 날짜 (30일)
sent_time >= DATE('now', '-30 days')

-- 절대적 날짜 범위
sent_time BETWEEN '2024-01-01' AND '2024-12-31'
```

### 3.5 벡터 검색 시스템

- **임베딩 모델**: text-embedding-3-large
- **차원**: 1536
- **유사도 메트릭**: Cosine
- **하이브리드 스코어링**: vector_score * 0.7 + keyword_score * 0.3
- **3% 허용 범위**: 최고 점수의 3% 이내 템플릿 추가 제시

### 3.6 성능 최적화

#### 인덱스 활용
- agenda_code (PRIMARY KEY)
- sent_time (날짜 조회)
- sender_organization (기관별 조회)
- decision_status (상태 필터링)

#### 쿼리 최적화
- 불필요한 JOIN 제거
- WHERE 절 순서 최적화
- LIMIT 적극 활용

#### 캐싱 전략
- 자주 사용되는 템플릿 캐싱
- 벡터 임베딩 캐싱
- 동의어 사전 메모리 캐싱

---

## 4. 템플릿 시스템

### 4.1 템플릿 구조 (v2.6+)

```json
{
    "template_id": "unique_identifier_v2",
    "template_version": "2.x",
    "template_category": "category_name",
    "query_info": {
        "natural_questions": ["질문1", "질문2", "질문3"],
        "keywords": ["키워드1", "키워드2"]
    },
    "routing_info": {  // v2.9부터 도입
        "route_to": "sql|vectordb|llm_direct",
        "reason": "라우팅 이유",
        "keyword_extraction": "키워드 추출 가이드"
    },
    "sql_template": {
        "query": "SQL 쿼리 또는 라우팅 안내",
        "system": "시스템 설명",
        "user": "사용자 설명"
    },
    "parameters": [
        {
            "name": "organization",
            "type": "string",
            "required": true,
            "default": "KR",
            "sql_builder": {
                "type": "string",
                "placeholder": "{organization}"
            }
        }
    ]
}
```

### 4.2 템플릿 카테고리

#### 기본 카테고리
- `agenda_search`: 의제 검색
- `agenda_status`: 상태 관리
- `organization_response`: 조직 응답
- `statistics`: 통계 분석

#### 고급 카테고리
- `agenda_analysis`: 의제 심층 분석
- `keyword_analysis`: 키워드 분석
- `data_quality`: 데이터 품질
- `deadline_analysis`: 마감일 분석

#### 특수 카테고리
- `llm_direct_response`: LLM 직접 응답
- `vectordb_search`: VectorDB 검색
- `panel_specific`: 패널 특화
- `organization_specific`: 조직 특화

### 4.3 템플릿 통계

| 버전 | 주요 기능 | SQL | VectorDB | LLM | 총합 |
|------|-----------|-----|----------|-----|------|
| v2.6 | 기본 기능 | ~20 | 0 | 0 | ~20 |
| v2.7 | 통계/분석 | 46 | 0 | 0 | 46 |
| v2.8 | 상세 분석 | 33 | 9 | 0 | 42 |
| v2.9 | 라우팅 | 11 | 15 | 3 | 29 |
| v2.10 | 품질/조직 | 40 | 0 | 0 | 40 |
| **합계** | | **~150** | **24** | **3** | **~177** |

---

## 5. 쿼리 라우팅 시스템

### 5.1 라우팅 결정 프로세스

1. **템플릿 매칭**: 쿼리와 가장 유사한 템플릿 찾기
2. **routing_info 확인**: 템플릿에 라우팅 정보가 있으면 해당 방식 사용
3. **패턴 매칭**: routing_info가 없으면 Query Router의 패턴 매칭 사용

### 5.2 라우팅 패턴

#### SQL Template 패턴
- 의제 정보: "진행중", "완료", "미응답"
- 응답 분석: "응답률", "평균 응답시간"
- 통계: "월별", "분기별", "키워드 분석"
- 상태 추적: "마감일", "최신 상태"

#### VectorDB MCP 패턴
- 문서 검색: "규정", "가이드라인", "절차서"
- 회의 정보: "회의 리스트", "회의 내용", "결정사항"
- PT 정보: "PT 리스트", "PT 참여기관", "PT 내용"
- 유사성 검색: "다른 패널", "유사한 논의"
- 전략 문서: "IACS 전략", "GPG 결정사항"

#### LLM Direct 패턴
- 기술 분석: "기술개발 동향", "기술 배경"
- 설명: "~에 대해 설명해줘"
- 분석: "관점", "전망"

---

## 6. VectorDB 통합

### 6.1 VectorDB MCP 호출이 필요한 쿼리 유형

#### 규정 및 문서 검색
```
- "UR 관련 규정 찾아줘"
- "IMO 가이드라인 검색"
- "IACS 절차서 내용"
- "선박 안전 규정 문서"
```

#### 개념적/주제별 검색
```
- "사이버 보안 관련 내용"
- "환경 규제 정보"
- "디지털 전환 가이드"
- "autonomous ship 규정"
```

### 6.2 VectorDB 쿼리 처리

```python
async def _handle_vectordb_query(self, request: EnhancedQueryRequest) -> QueryResponse:
    """VectorDB를 통한 문서 검색"""
    try:
        # VectorDB MCP 서버로 쿼리 전달
        vectordb_response = await self.vectordb_client.search(
            query=request.query,
            keywords=request.extracted_keywords,
            limit=10
        )
        
        return QueryResponse(
            status="success",
            query_type="vectordb_search",
            results=vectordb_response.results,
            metadata={
                "source": "vectordb",
                "query": request.query,
                "keywords": request.extracted_keywords
            }
        )
    except Exception as e:
        return QueryResponse(
            status="error",
            error=str(e)
        )
```

### 6.3 하이브리드 검색

일부 쿼리는 SQL과 VectorDB를 모두 사용해야 할 수 있습니다:

```python
async def _handle_hybrid_query(self, request: EnhancedQueryRequest) -> QueryResponse:
    """SQL + VectorDB 하이브리드 검색"""
    
    # 1. SQL 템플릿으로 구조화된 데이터 검색
    sql_results = await self._handle_sql_template_query(request)
    
    # 2. VectorDB로 관련 문서 검색
    vectordb_results = await self._handle_vectordb_query(request)
    
    # 3. 결과 병합
    return self._merge_results(sql_results, vectordb_results)
```

---

## 7. KR 템플릿 분석 및 업데이트

### 7.1 KR 특화 템플릿 현황

7개의 KR-specific 템플릿이 확인되었으며, 이들은 organization 파라미터화가 필요합니다:

1. **kr_no_response_ongoing_v2**: KR이 아직 응답하지 않은 진행중 의제
2. **kr_response_required_v2**: KR이 응답해야 하는 의제
3. **kr_agenda_issues_summary_v2**: KR 응답 필요 의제의 이슈 요약
4. **kr_agenda_keywords_v2**: KR 응답 필요 의제의 키워드
5. **kr_response_keywords_v2**: KR 응답의 키워드
6. **kr_avg_response_time_v2**: KR 평균 응답시간
7. **kr_response_time_exclude_creation_v2**: KR 평균 응답시간 (본인 생성 제외)

### 7.2 업데이트 방향

#### Organization 파라미터 추가
```json
{
  "name": "organization",
  "type": "string",
  "required": true,
  "default": "KR",
  "sql_builder": {
    "type": "string",
    "placeholder": "{organization}"
  }
}
```

#### SQL 쿼리 업데이트
- `r.sender_organization = 'KR'` → `r.sender_organization = {organization}`
- `response_org LIKE '%KR%'` → `response_org LIKE '%' || {organization} || '%'`
- `a.sender_organization != 'KR'` → `a.sender_organization != {organization}`

#### 템플릿 ID 업데이트
- `kr_no_response_ongoing_v2` → `org_no_response_ongoing_v2`
- `kr_response_required_v2` → `org_response_required_v2`
- 기타 동일한 패턴으로 변경

### 7.3 업데이트 이점

1. **재사용성**: 모든 기관에 대해 동일한 템플릿 사용 가능
2. **유지보수성**: 단일 템플릿으로 관리
3. **확장성**: 새로운 기관 추가 시 코드 수정 불필요
4. **일관성**: 모든 기관에 대해 동일한 쿼리 기능 제공

---

## 8. 버전 관리 및 히스토리

### 8.1 버전별 주요 변경사항

#### v2.6 - 기본 템플릿 (Base Templates)
- 핵심 기능 구현
- 기본적인 의제 조회
- 조직별 응답 관리
- 시간 기반 필터링

#### v2.7 - 통계 및 분석 확장 (46개 템플릿 추가)
- 고급 통계 기능
- PT(Project Team) 관련 쿼리
- 데이터 품질 검증
- 월별 응답률 통계

#### v2.8 - 의제 상세 분석 (33개 + VectorDB 9개)
- 의견 동의/반대 분석
- 상세 키워드 분석
- 조직 간 관계 분석
- VectorDB 라우팅 도입

#### v2.9 - 라우팅 시스템 도입 (SQL 11개, LLM 3개, VectorDB 15개)
- 3가지 처리 방식 명시적 구분
- LLM Direct Response 도입
- routing_info 메타데이터
- 통합 라우팅 시스템

#### v2.10 - 데이터 품질 및 조직 특화 (40개 SQL)
- 데이터 품질 검증 강화
- SDTP 패널 특화 기능
- KR 조직 특화 분석
- IACS 구조 정보

### 8.2 향후 계획

#### v2.11 (예정)
- 다국어 지원
- 복합 쿼리 최적화
- 실시간 데이터 통합

#### v2.12 (예정)
- AI 기반 템플릿 자동 생성
- 사용자 맞춤 템플릿
- 성능 최적화

### 8.3 템플릿 관리 지침

1. **새 템플릿 추가 시**:
   - 적절한 버전 선택
   - 기존 템플릿과 중복 확인
   - routing_info 명시 (필요시)
   - 테스트 케이스 작성

2. **버전 업그레이드 시**:
   - 이전 버전과의 호환성 유지
   - 변경 사항 문서화
   - 마이그레이션 가이드 제공

3. **템플릿 ID 규칙**:
   - `{기능}_{세부기능}_v2` 형식
   - 중복 ID 사용 금지
   - 의미 있는 이름 사용

---

## 디버깅 및 문제 해결

### 로그 설정
```python
import logging
logging.getLogger('modules.query_assistant').setLevel(logging.DEBUG)
```

### 주요 디버그 포인트
1. LLM 파라미터 추출 결과
2. 템플릿 매칭 점수
3. 생성된 SQL
4. 실행 시간

### 일반적인 문제
1. **템플릿 매칭 실패**: 키워드 부족, 임베딩 문제
2. **SQL 오류**: 플레이스홀더 미치환, 잘못된 날짜 형식
3. **성능 문제**: 인덱스 부재, 과도한 데이터

---

## 사용 예시

### SQL Template 쿼리
```
"KR이 응답하지 않은 진행중 의제"
→ SQL 실행: 구조화된 데이터 조회
```

### VectorDB 쿼리
```
"UR 규정 문서 찾아줘"
→ VectorDB 검색: 문서 내용 검색
```

### LLM Direct 쿼리
```
"자율운항선박 기술개발 동향 분석해줘"
→ LLM 직접 응답: 기술 동향 분석
```

### 하이브리드 쿼리
```
"최근 UR과 관련된 아젠다나 기관의 응답"
→ SQL + VectorDB: 두 가지 결과 병합
```

---

이 문서는 IACSGRAPH 쿼리 시스템의 모든 측면을 다루는 통합 가이드입니다.
지속적으로 업데이트되며, 새로운 기능이 추가될 때마다 이 문서에 반영됩니다.