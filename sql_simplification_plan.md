# SQL Generator 단순화 작업 계획

## 목표
복잡한 SQL builder 타입 시스템을 제거하고 단순한 파라미터 바인딩 방식으로 전환

## 현재 문제점
1. 불필요하게 복잡한 builder 타입 시스템 (period, keywords, column, string, number 등)
2. 하드코딩된 기본값 ('title' 문제)
3. 누락된 'column' 타입 처리로 인한 {organization} 플레이스홀더 미치환
4. 중복된 로직과 복잡한 조건 생성

## 구현 방안: 방안 C (여러 번 실행 + 결과 병합)

### Phase 1: 기본 구조 변경 (우선순위: 높음)

#### 1.1 템플릿 구조 변경
- [ ] 템플릿 파라미터에 `multi_query` 플래그 추가
- [ ] keywords (array) → keyword (string) 변경
- [ ] sql_builder 섹션 제거 또는 단순화

**변경 예시:**
```json
// Before
{
  "parameters": [{
    "name": "keywords",
    "type": "array",
    "sql_builder": {
      "type": "keywords",
      "field": "subject",
      "placeholder": "{keyword_condition}"
    }
  }]
}

// After
{
  "parameters": [{
    "name": "keyword",
    "type": "string",
    "multi_query": true,
    "description": "검색 키워드"
  }]
}
```

#### 1.2 SQL Generator 단순화
- [ ] `_build_sql_conditions()` 메서드 제거
- [ ] 단순 파라미터 치환 방식으로 변경
- [ ] 다중 쿼리 생성 로직 추가

**주요 변경사항:**
```python
# services/sql_generator.py
- builder 타입별 복잡한 조건 생성 로직 제거
- 단순 문자열 치환 방식 구현
- multi_query 파라미터 처리 추가
```

### Phase 2: 다중 쿼리 실행 지원 (우선순위: 높음)

#### 2.1 Query Processor 개선
- [ ] 다중 쿼리 실행 메서드 추가
- [ ] 결과 병합 및 중복 제거 로직 구현
- [ ] 병렬 실행 옵션 추가

**구현 위치:**
- `modules/query_assistant/services/query_processor.py`
- `modules/query_assistant/mcp_server_enhanced.py`

#### 2.2 결과 병합 전략
- [ ] 중복 제거 기준 정의 (agenda_code, id 등)
- [ ] 정렬 기준 유지
- [ ] 메타데이터 추가 (query_count, unique_count)

### Phase 3: 템플릿 마이그레이션 (우선순위: 중간)

#### 3.1 템플릿 자동 변환 스크립트
- [ ] 기존 템플릿 백업
- [ ] sql_builder 제거 및 SQL 수정
- [ ] 파라미터 타입 변경 (array → string + multi_query)

**스크립트 위치:**
- `modules/templates/scripts/migrate_templates.py`

#### 3.2 변환 대상 템플릿
1. keywords 사용 템플릿 (약 50개)
2. organization 동적 컬럼 템플릿 (3-4개)
3. 복잡한 period 조건 템플릿

### Phase 4: 테스트 및 검증 (우선순위: 높음)

#### 4.1 단위 테스트
- [ ] 단일 키워드 테스트
- [ ] 다중 키워드 테스트
- [ ] 중복 제거 테스트
- [ ] 성능 테스트

#### 4.2 통합 테스트
- [ ] 100개 쿼리 테스트 재실행
- [ ] 에러율 감소 확인
- [ ] 성능 비교 (이전 vs 이후)

### Phase 5: 문서화 (우선순위: 낮음)

#### 5.1 개발자 가이드
- [ ] 새로운 템플릿 작성 방법
- [ ] 파라미터 바인딩 규칙
- [ ] multi_query 사용법

#### 5.2 마이그레이션 가이드
- [ ] 기존 템플릿 변환 방법
- [ ] 주의사항 및 제약사항

## 예상 일정

1. **Week 1**: Phase 1 (기본 구조 변경)
2. **Week 2**: Phase 2 (다중 쿼리 실행)
3. **Week 3**: Phase 3 (템플릿 마이그레이션)
4. **Week 4**: Phase 4-5 (테스트 및 문서화)

## 기대 효과

1. **코드 단순화**: SQL builder 복잡도 50% 감소
2. **유지보수성**: 명확한 파라미터 바인딩으로 디버깅 용이
3. **확장성**: 새로운 파라미터 타입 추가 용이
4. **성능**: 불필요한 조건 생성 로직 제거로 성능 개선

## 위험 요소 및 대응

1. **다중 쿼리 성능 저하**
   - 대응: 병렬 실행 및 결과 캐싱

2. **기존 템플릿 호환성**
   - 대응: 점진적 마이그레이션, 이전 버전 지원

3. **중복 제거 정확성**
   - 대응: 테이블별 고유 키 매핑 정의

## 다음 단계

1. 이 계획에 대한 검토 및 승인
2. Phase 1 구현 시작
3. 프로토타입으로 일부 템플릿 테스트