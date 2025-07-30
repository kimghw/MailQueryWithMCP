# query_templates_group_006.json 테스트 보고서

**테스트 일시**: 2025-07-30T11:05:25.225790
**데이터베이스**: data/iacsgraph.db

## 요약

- **전체 템플릿 수**: 21
- **성공**: 17 (81.0%)
- **실패**: 4

### 카테고리별 결과

| 카테고리 | 전체 | 성공 | 실패 | 성공률 |
|----------|------|------|------|--------|
| attachment_analysis | 1 | 0 | 1 | 0.0% |
| specific_agenda | 6 | 6 | 0 | 100.0% |
| opinion_analysis | 8 | 5 | 3 | 62.5% |
| related_analysis | 2 | 2 | 0 | 100.0% |
| keyword_analysis | 2 | 2 | 0 | 100.0% |
| regulation_search | 1 | 1 | 0 | 100.0% |
| statistics | 1 | 1 | 0 | 100.0% |

## 상세 결과

### 1. ❌ kr_response_required_attachment_analysis

**카테고리**: attachment_analysis
**상태**: 실패
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 첨부파일의 유형과 중요도를 분석하여 우선적으로 검토해야 할 파일들을 식별하고 대응 방안을 제시해 주세요.

**자연어 질의**:
1. KR이 응답해야하는 의제에 대한 첨부파일 분석해줘 (original)
2. 한국선급이 회신해야 할 의제들의 첨부파일 내용을 분석해주세요 (similar1)
3. KR 응답 필요한 안건들의 첨부 문서가 어떤 내용인지 알려줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string)

**플레이스홀더**: `organization`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.agenda_base_version, c.subject, c.deadline, c.agenda_panel FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.hasAttachments = 1 AND c.mail_type = 'REQUEST' AND c.has_deadline = 1 AND c.deadline > datetime('now') ...
```

**오류 내용**: Unsubstituted placeholders: ['organization', 'organization']

**실행 시도한 쿼리**:
```sql
SELECT c.agenda_code, c.agenda_base_version, c.subject, c.deadline, c.agenda_panel FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.hasAttachments = 1 AND c.mail_type = 'REQUEST' AND c.has_deadline = 1 AND c.deadline > datetime('now') AND (r.{organization} IS NULL OR r.{organization} = '') ORDER BY c.deadline ASC
```

---

### 2. ✅ pl25023_attachment_check

**카테고리**: specific_agenda
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: PL25023 의제의 첨부파일 정보를 분석하고 파일의 중요성을 평가해 주세요.

**자연어 질의**:
1. PL25023 에 첨부파일이 있어? (original)
2. PL25023 의제에 첨부된 파일이 있나요? (similar1)
3. PL25023 안건에 첨부 문서가 포함되어 있는지 확인해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, hasAttachments FROM agenda_chair WHERE agenda_code = 'PL25023' ORDER BY agenda_version DESC LIMIT 1
```

**실행 결과**: 0개 행 반환

---

### 3. ✅ specific_agenda_attachment_check

**카테고리**: specific_agenda
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 의제의 첨부파일 정보를 분석하고 파일의 중요성을 평가해 주세요.

**자연어 질의**:
1. {agenda}에서 첨부 파일이 있나? (original)
2. {agenda} 의제에 첨부된 파일이 있나요? (similar1)
3. {agenda} 안건에 첨부 문서가 포함되어 있는지 확인해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, hasAttachments, sent_time FROM agenda_chair WHERE agenda_base_version = '{agenda}' ORDER BY agenda_version DESC LIMIT 1
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | hasAttachments | sent_time |
|---|---|---|---|---|
| PL24005_ILc | PL24005 | PL24005_ILc: Email thread d... | 0 | 2025-05-16 18:03:26+00:00 |

---

### 4. ❌ specific_agenda_org_opinion

**카테고리**: opinion_analysis
**상태**: 실패
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 해당 조직의 의견을 분석하여 주요 입장과 근거를 정리해 주세요.

**자연어 질의**:
1. {agenda} 에서 {organization}의 의견은? (original)
2. {agenda} 의제에 대한 {organization}의 입장이 뭐인가요? (similar1)
3. {agenda} 안건에서 {organization}이 어떤 의견을 제시했나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)
  - `organization` (string)

**플레이스홀더**: `agenda, organization`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.subject, r.{organization} as opinion FROM agenda_chair c JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_base_version = '{agenda}' AND r.{organization} IS NOT NULL ORDER BY c.agenda_version DESC LIMIT 1
```

**오류 내용**: Unsubstituted placeholders: ['organization', 'organization']

**실행 시도한 쿼리**:
```sql
SELECT c.agenda_code, c.subject, r.{organization} as opinion FROM agenda_chair c JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_base_version = 'PL24005' AND r.{organization} IS NOT NULL ORDER BY c.agenda_version DESC LIMIT 1
```

---

### 5. ❌ agenda_organization_opinion_short

**카테고리**: opinion_analysis
**상태**: 실패
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 조직의 핵심 의견을 간단명료하게 요약해 주세요.

**자연어 질의**:
1. {agenda}에서 {organization} 의견은 뭐지? (original)
2. {agenda} 의제에 {organization}이 뭐라고 했나요? (similar1)
3. {agenda} 안건의 {organization} 응답 내용이 뭐야? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)
  - `organization` (string)

**플레이스홀더**: `agenda, organization`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.subject, r.{organization} as opinion, c.sent_time FROM agenda_chair c JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_base_version = '{agenda}' AND r.{organization} IS NOT NULL ORDER BY c.agenda_version DESC LIMIT 1
```

**오류 내용**: Unsubstituted placeholders: ['organization', 'organization']

**실행 시도한 쿼리**:
```sql
SELECT c.agenda_code, c.subject, r.{organization} as opinion, c.sent_time FROM agenda_chair c JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_base_version = 'PL24005' AND r.{organization} IS NOT NULL ORDER BY c.agenda_version DESC LIMIT 1
```

---

### 6. ✅ pl25023_dnv_opinion

**카테고리**: specific_agenda
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: DNV의 의견을 분석하여 기술적 입장과 근거를 설명해 주세요.

**자연어 질의**:
1. PL25023 에서 DNV 의견은 뭐지? (original)
2. PL25023 의제에 DNV가 뭐라고 응답했나요? (similar1)
3. PL25023 안건에 대한 DNV의 입장이 어떻게 되나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.subject, r.DNV as dnv_opinion, c.sent_time FROM agenda_chair c JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_code = 'PL25023' AND r.DNV IS NOT NULL ORDER BY c.agenda_version DESC LIMIT 1
```

**실행 결과**: 0개 행 반환

---

### 7. ✅ pl24024_abs_opinion

**카테고리**: specific_agenda
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: ABS의 의견을 분석하여 기술적 입장과 근거를 설명해 주세요.

**자연어 질의**:
1. PL24024 에서 ABS 의견은 뭐지? (original)
2. PL24024 의제에 ABS가 뭐라고 응답했나요? (similar1)
3. PL24024 안건에 대한 ABS의 입장이 어떻게 되나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.subject, r.ABS as abs_opinion, c.sent_time FROM agenda_chair c JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_code = 'PL24024' AND r.ABS IS NOT NULL ORDER BY c.agenda_version DESC LIMIT 1
```

**실행 결과**: 0개 행 반환

---

### 8. ✅ pl25024_related_agendas

**카테고리**: related_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: PL25024와 관련된 의제들을 분석하여 주제별 연관성과 논의 흐름을 설명해 주세요.

**자연어 질의**:
1. PL25024 과 관련된 다른 의제들 검토해 줄래? (original)
2. PL25024와 연관된 다른 의제들을 찾아주세요 (similar1)
3. PL25024 안건과 관련 있는 다른 아젠다가 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
WITH target_agenda AS (SELECT keywords, subject, agenda_panel FROM agenda_chair WHERE agenda_code = 'PL25024' LIMIT 1) SELECT c.agenda_code, c.subject, c.keywords, c.sent_time, c.agenda_panel FROM agenda_chair c, target_agenda t WHERE c.agenda_code != 'PL25024' AND (c.keywords LIKE '%' || t.keywords...
```

**실행 결과**: 0개 행 반환

---

### 9. ✅ agenda_org_agreement_with_reason

**카테고리**: opinion_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: {organization}의 의견과 다른 기관들의 의견을 비교 분석하여 동의하는 기관들과 그 근거를 파악해 주세요.

**자연어 질의**:
1. {agenda} 에서 {organization} 의견에 동의한 기관과 근거는? (original)
2. {agenda} 의제에서 {organization}의 입장에 찬성한 기관들과 그 이유를 보여주세요 (similar1)
3. {agenda}에서 {organization} 의견에 동조하는 조직과 근거가 뭐인가요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)
  - `organization` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, r.* FROM agenda_chair c JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_base_version = '{agenda}' ORDER BY c.agenda_version DESC LIMIT 1
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | ABS | BV | CCS |
|---|---|---|---|---|
| PL24005_ILc | PL24005 | PL24005_ABc: Email thread d... | PL24005_BVc: Email thread d... | None |

*참고: 전체 17개 컬럼 중 5개만 표시*

---

### 10. ✅ pl25023_dnv_agreement_analysis

**카테고리**: specific_agenda
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: DNV의 의견과 다른 기관들의 의견을 비교 분석하여 DNV에 동의하는 기관들과 그 근거를 파악해 주세요.

**자연어 질의**:
1. PL25023 에서 DNV 의견에 동의한 기관과 근거는? (original)
2. PL25023 의제에서 DNV의 입장에 찬성한 기관들과 이유를 보여주세요 (similar1)
3. PL25023에서 DNV와 같은 의견인 조직들이 어디인가요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.subject, r.* FROM agenda_chair c JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_code = 'PL25023' ORDER BY c.agenda_version DESC LIMIT 1
```

**실행 결과**: 0개 행 반환

---

### 11. ✅ agenda_org_disagreement_with_reason

**카테고리**: opinion_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: {organization}의 의견과 다른 기관들의 의견을 비교 분석하여 반대하거나 다른 입장을 가진 기관들과 그 근거를 파악해 주세요.

**자연어 질의**:
1. {agenda} 에서 {organization} 의견에 동의하지 않은 기관과 근거는? (original)
2. {agenda} 의제에서 {organization}의 입장에 반대한 기관들과 그 이유를 보여주세요 (similar1)
3. {agenda}에서 {organization} 의견과 다른 입장인 조직과 근거가 뭐인가요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)
  - `organization` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, r.* FROM agenda_chair c JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_base_version = '{agenda}' ORDER BY c.agenda_version DESC LIMIT 1
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | ABS | BV | CCS |
|---|---|---|---|---|
| PL24005_ILc | PL24005 | PL24005_ABc: Email thread d... | PL24005_BVc: Email thread d... | None |

*참고: 전체 17개 컬럼 중 5개만 표시*

---

### 12. ✅ pl25023_dnv_disagreement_analysis

**카테고리**: specific_agenda
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: DNV의 의견과 다른 기관들의 의견을 비교 분석하여 DNV에 반대하거나 다른 입장을 가진 기관들과 그 근거를 파악해 주세요.

**자연어 질의**:
1. PL25023 에서 DNV 의견에 동의하지 않은 기관과 근거는? (original)
2. PL25023 의제에서 DNV의 입장에 반대한 기관들과 이유를 보여주세요 (similar1)
3. PL25023에서 DNV와 다른 의견인 조직들이 어디인가요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.subject, r.* FROM agenda_chair c JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_code = 'PL25023' ORDER BY c.agenda_version DESC LIMIT 1
```

**실행 결과**: 0개 행 반환

---

### 13. ✅ agenda_multiple_org_opinions

**카테고리**: opinion_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 요청된 기관들의 의견을 비교 분석하여 공통점과 차이점을 정리해 주세요.

**자연어 질의**:
1. {agenda} 에서 {organization}, {organization}, {organization} 의견은? (original)
2. {agenda} 의제에 대한 {organization}, {organization}, {organization}의 입장들을 보여주세요 (similar1)
3. {agenda} 안건에서 {organization}, {organization}, {organization}이 각각 어떤 의견을 제시했나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)
  - `organization` (array)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.subject, r.* FROM agenda_chair c JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_base_version = '{agenda}' ORDER BY c.agenda_version DESC LIMIT 1
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | subject | agenda_base_version | ABS | BV |
|---|---|---|---|---|
| PL24005_ILc | PL24005_ILc: Email thread d... | PL24005 | PL24005_ABc: Email thread d... | PL24005_BVc: Email thread d... |

*참고: 전체 18개 컬럼 중 5개만 표시*

---

### 14. ✅ agenda_keywords_extraction

**카테고리**: keyword_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 의제의 키워드를 분석하여 주요 주제와 기술적 초점을 파악해 주세요.

**자연어 질의**:
1. {agenda} 에서 키워드는? (original)
2. {agenda} 의제의 주요 키워드를 보여주세요 (similar1)
3. {agenda} 안건에서 핵심 단어들이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
SELECT agenda_code, subject, keywords, body FROM agenda_chair WHERE agenda_base_version = '{agenda}' ORDER BY agenda_version DESC LIMIT 1
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | subject | keywords | body |
|---|---|---|---|
| PL24005_ILc | PL24005_ILc: Email thread d... | ["SDTP", "URs", "spreadshee... | PL24005_ILc: Email thread d... |

---

### 15. ✅ agenda_response_keywords

**카테고리**: keyword_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 모든 기관의 응답에서 자주 언급된 키워드를 분석하여 공통 관심사와 주요 쟁점을 파악해 주세요.

**자연어 질의**:
1. {agenda} 에서 응답들의 주요 키워드는 (original)
2. {agenda} 의제에 대한 각 기관 응답의 핵심 키워드를 보여주세요 (similar1)
3. {agenda} 안건 응답들에서 자주 언급된 단어가 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.subject, r.* FROM agenda_chair c JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_base_version = '{agenda}' ORDER BY c.agenda_version DESC LIMIT 1
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | subject | agenda_base_version | ABS | BV |
|---|---|---|---|---|
| PL24005_ILc | PL24005_ILc: Email thread d... | PL24005 | PL24005_ABc: Email thread d... | PL24005_BVc: Email thread d... |

*참고: 전체 18개 컬럼 중 5개만 표시*

---

### 16. ✅ agenda_related_keyword_agendas

**카테고리**: related_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 의제의 키워드와 관련된 SDTP 의제들을 분석하여 주제적 연관성과 논의 흐름을 설명해 주세요.

**자연어 질의**:
1. {agenda} 의 주요 키워드와 연관된 SDTP 에서의 아젠다가 있는가? (original)
2. {agenda} 의제의 키워드와 관련된 SDTP 패널의 다른 의제들을 찾아주세요 (similar1)
3. {agenda}의 핵심 단어가 포함된 SDTP 안건들이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
WITH target_keywords AS (SELECT keywords FROM agenda_chair WHERE agenda_base_version = '{agenda}' LIMIT 1) SELECT c.agenda_code, c.subject, c.keywords, c.sent_time FROM agenda_chair c, target_keywords t WHERE c.agenda_panel = 'SDTP' AND c.agenda_code != '{agenda}' AND c.keywords LIKE '%' || t.keywor...
```

**실행 결과**: 0개 행 반환

---

### 17. ✅ agenda_kr_agreement_issues

**카테고리**: opinion_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: KR의 의견과 다른 기관들의 의견을 비교 분석하여 KR에 동의하는 기관들과 동의 이슈를 파악해 주세요.

**자연어 질의**:
1. {agenda} 에서 KR의 의견에 동의한 이슈와 기관은 (original)
2. {agenda} 의제에서 한국선급 입장에 찬성한 기관들과 주요 이슈를 보여주세요 (similar1)
3. {agenda}에서 KR과 같은 의견인 조직과 동의 사항이 뭐인가요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.subject, r.* FROM agenda_chair c JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_base_version = '{agenda}' AND r.KR IS NOT NULL ORDER BY c.agenda_version DESC LIMIT 1
```

**실행 결과**: 0개 행 반환

---

### 18. ✅ agenda_kr_disagreement_issues

**카테고리**: opinion_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: KR의 의견과 다른 기관들의 의견을 비교 분석하여 KR에 반대하는 기관들과 대립 이슈를 파악해 주세요.

**자연어 질의**:
1. {agenda} 에서 KR의 의견에 반대한 기관과 이슈는 무엇인가? (original)
2. {agenda} 의제에서 한국선급 입장에 반대한 기관들과 주요 쟁점을 보여주세요 (similar1)
3. {agenda}에서 KR과 다른 의견인 조직과 반대 사항이 뭐인가요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.subject, r.* FROM agenda_chair c JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_base_version = '{agenda}' AND r.KR IS NOT NULL ORDER BY c.agenda_version DESC LIMIT 1
```

**실행 결과**: 0개 행 반환

---

### 19. ✅ agenda_ur_related_content

**카테고리**: regulation_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 의제에서 UR 관련 내용을 찾아 어떤 통일규칙이 논의되고 있는지 분석해 주세요.

**자연어 질의**:
1. 최근 {agenda} 에서 UR과 관련된 아젠다나 기관의 응답이 있었나? (original)
2. {agenda} 의제에서 통일규칙(UR) 관련 내용이나 응답이 있었나요? (similar1)
3. {agenda} 안건에서 UR 언급한 기관이나 내용이 있는지 확인해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.subject, c.body, r.* FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_base_version = '{agenda}' AND (c.body LIKE '%UR%' OR c.body LIKE '%Unified Requirement%' OR c.keywords LIKE '%UR%') ORDER BY c.agenda_...
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | subject | body | agenda_base_version | ABS |
|---|---|---|---|---|
| PL24005_ILc | PL24005_ILc: Email thread d... | PL24005_ILc: Email thread d... | PL24005 | PL24005_ABc: Email thread d... |

*참고: 전체 19개 컬럼 중 5개만 표시*

---

### 20. ❌ agenda_multiple_organizations_opinions

**카테고리**: opinion_analysis
**상태**: 실패
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 3개 조직의 의견을 비교 분석하여 공통점과 차이점을 정리해 주세요.

**자연어 질의**:
1. {agenda} 에서 {organization},{organization},{organization} 의견은? (original)
2. 특정 의제에 대한 여러 기관의 의견을 한번에 보여주세요 (similar1)
3. 하나의 안건에 대해 3개 조직의 입장을 비교하고 싶어요 (similar2)
   ... 외 3개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)
  - `organization1` (string)
  - `organization2` (string)
  - `organization3` (string)

**플레이스홀더**: `agenda, organization1, organization2, organization3`

**SQL 쿼리**:
```sql
SELECT 
                    c.agenda_code,
                    c.agenda_base_version,
                    c.subject,
                    c.body as content,
                    rc.{organization1} as {organization1}_opinion,
                    rc.{organization2} as {organization2}_opinion,
          ...
```

**오류 내용**: Unsubstituted placeholders: ['organization1', 'organization1', 'organization2', 'organization2', 'organization3', 'organization3', 'organization1', 'organization1', 'organization2', 'organization2', 'organization3', 'organization3']

**실행 시도한 쿼리**:
```sql
SELECT 
                    c.agenda_code,
                    c.agenda_base_version,
                    c.subject,
                    c.body as content,
                    rc.{organization1} as {organization1}_opinion,
                    rc.{organization2} as {organization2}_opinion,
                    rc.{organization3} as {organization3}_opinion,
                    rt.{organization1} as {organization1}_response_time,
                    rt.{organization2} as {organization2}_response_tim...
```

---

### 21. ✅ agenda_fastest_response_organization

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 가장 빨리 응답한 조직과 그 의견을 분석하여 신속한 응답의 이유를 추정해 주세요.

**자연어 질의**:
1. {agenda} 에서 회신을 가장 빠른 기관의 의견은? (original)
2. 이 의제에 가장 먼저 응답한 조직의 의견을 보여주세요 (similar1)
3. 특정 안건에서 최초 응답 기관의 입장이 궁금합니다 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
WITH response_times AS (
                    SELECT 
                        c.agenda_code,
                        c.agenda_base_version,
                        c.subject,
                        c.sent_time,
                        CASE 
                            WHEN rt.ABS IS NOT NULL THEN 'A...
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | sent_time | org |
|---|---|---|---|---|
| PL24005_ILc | PL24005 | PL24005_ILc: Email thread d... | 2025-05-16 18:03:26+00:00 | ABS |

*참고: 전체 7개 컬럼 중 5개만 표시*

---


## 테스트 설정

- **파일**: query_templates_group_006.json
- **테스트 일시**: 2025-07-30T11:05:25.225790
- **데이터베이스 경로**: data/iacsgraph.db
