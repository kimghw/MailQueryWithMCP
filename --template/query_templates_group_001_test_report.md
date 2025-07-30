# query_templates_group_001.json 테스트 보고서

**테스트 일시**: 2025-07-30T11:05:25.179620
**데이터베이스**: data/iacsgraph.db

## 요약

- **전체 템플릿 수**: 32
- **성공**: 32 (100.0%)
- **실패**: 0

### 카테고리별 결과

| 카테고리 | 전체 | 성공 | 실패 | 성공률 |
|----------|------|------|------|--------|
| agenda_status | 7 | 7 | 0 | 100.0% |
| response_tracking | 5 | 5 | 0 | 100.0% |
| statistics | 6 | 6 | 0 | 100.0% |
| keyword_analysis | 4 | 4 | 0 | 100.0% |
| keyword_search | 7 | 7 | 0 | 100.0% |
| mail_type | 3 | 3 | 0 | 100.0% |

## 상세 결과

### 1. ✅ recent_ongoing_agendas_all_panels

**카테고리**: agenda_status
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 각 아젠다별로 메일 내용(content)을 요약하고 주요 키워드를 추출해 주세요. 특히 마감일이 임박한 의제들의 핵심 내용과 요구사항을 강조하여 정리해 주세요.

**자연어 질의**:
1. 최근 모든 패널에서 진행되고 있는 의제 목록 (original)
2. 현재 모든 패널에서 진행 중인 의제들을 보여주세요 (similar1)
3. 전체 패널의 진행중인 안건 리스트가 필요합니다 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, sender_organization, sent_time, decision_status, agenda_panel, deadline, body as content, keywords FROM agenda_chair WHERE deadline IS NOT NULL AND deadline > datetime('now') AND {period_condition} ORDER BY sent_time DESC
```

**실행 결과**: 3개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | sender_organization | sent_time |
|---|---|---|---|---|
| TEST2025002a | TEST2025002 | TEST2025002a: 긴급 검토 - 사이버보안... | IACS | 2025-07-26 02:25:23 |
| TEST2025001a | TEST2025001 | TEST2025001a: 테스트 의제 - AI 기... | IACS | 2025-07-22 02:25:23 |
| GEN25M002a | GEN25M002 | GEN25M002a: Technical Commi... | DNV | 2025-06-30 00:45:24 |

*참고: 전체 10개 컬럼 중 5개만 표시*

---

### 2. ✅ recent_incomplete_agendas_all_panels

**카테고리**: agenda_status
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 미완료 의제들에 대해서 의제 리스트와 주요 이슈를 요약해서 제공해 주세요.

**자연어 질의**:
1. 최근 모든 패널에서 완료되지 않은 의제 리스트 (original)
2. 모든 패널의 미완료 의제 목록을 보여주세요 (similar1)
3. 아직 완료 안 된 전체 안건들이 뭐가 있나요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, sender_organization, sent_time, decision_status, agenda_panel, deadline FROM agenda_chair WHERE deadline IS NOT NULL AND deadline > datetime('now') AND {period_condition} ORDER BY sent_time DESC
```

**실행 결과**: 3개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | sender_organization | sent_time |
|---|---|---|---|---|
| TEST2025002a | TEST2025002 | TEST2025002a: 긴급 검토 - 사이버보안... | IACS | 2025-07-26 02:25:23 |
| TEST2025001a | TEST2025001 | TEST2025001a: 테스트 의제 - AI 기... | IACS | 2025-07-22 02:25:23 |
| GEN25M002a | GEN25M002 | GEN25M002a: Technical Commi... | DNV | 2025-06-30 00:45:24 |

*참고: 전체 8개 컬럼 중 5개만 표시*

---

### 3. ✅ recent_3months_discussed_agendas

**카테고리**: agenda_status
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 3개월간의 의제들을 패널별, 월별로 분석하여 트렌드를 설명해 주세요.

**자연어 질의**:
1. 최근 3개월 동안 논의 되었던 의제 목록 (original)
2. 지난 3개월간 다뤄진 모든 의제들을 보여주세요 (similar1)
3. 최근 90일 동안의 아젠다 리스트가 필요합니다 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, sender_organization, sent_time, decision_status, agenda_panel FROM agenda_chair WHERE {period_condition} ORDER BY sent_time DESC
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | sender_organization | sent_time |
|---|---|---|---|---|
| TEST2025002a | TEST2025002 | TEST2025002a: 긴급 검토 - 사이버보안... | IACS | 2025-07-26 02:25:23 |
| TEST2025001a | TEST2025001 | TEST2025001a: 테스트 의제 - AI 기... | IACS | 2025-07-22 02:25:23 |
| ENV25M005a | ENV25M005 | ENV25M005a: Urgent - Enviro... | ABS | 2025-07-20 00:45:24 |

*참고: 전체 7개 컬럼 중 5개만 표시*

---

### 4. ✅ kr_no_response_ongoing_agendas

**카테고리**: response_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: KR이 긴급히 응답해야 할 의제들을 우선순위별로 정리해 주세요. 마감일이 임박한 의제를 특히 강조해 주세요.

**자연어 질의**:
1. 진행되고 있는 의제들 중에서 KR 이 아직 응답하지 않는 의제 (original)
2. KR이 아직 회신하지 않은 진행중인 의제들을 보여주세요 (similar1)
3. 한국선급이 응답 안 한 ongoing 상태의 안건이 뭐가 있나요 (similar2)
   ... 외 4개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `organization, period_condition`

**SQL 쿼리**:
```sql
SELECT DISTINCT c.agenda_code, c.agenda_base_version, c.subject, c.body, c.sent_time, c.deadline, c.agenda_panel FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.deadline IS NOT NULL AND c.deadline > datetime('now') AND c.mail_type = '...
```

**실행 결과**: 2개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | body | sent_time |
|---|---|---|---|---|
| TEST2025002a | TEST2025002 | TEST2025002a: 긴급 검토 - 사이버보안... | 새로운 사이버보안 위협에 대응하기 위한 규정 개정... | 2025-07-26 02:25:23 |
| TEST2025001a | TEST2025001 | TEST2025001a: 테스트 의제 - AI 기... | AI 기반 선박 안전 시스템에 대한 각 기관의 의... | 2025-07-22 02:25:23 |

*참고: 전체 7개 컬럼 중 5개만 표시*

---

### 5. ✅ kr_response_required_agendas

**카테고리**: response_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: KR이 응답해야 할 의제들을 긴급도에 따라 분류하고 주요 내용을 요약해 주세요.

**자연어 질의**:
1. KR이 응답을 해야 하는 의제 (original)
2. 한국선급이 회신해야 할 의제들을 보여주세요 (similar1)
3. KR 답변이 필요한 안건 리스트 확인해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `organization, period_condition`

**SQL 쿼리**:
```sql
SELECT DISTINCT c.agenda_code, c.agenda_base_version, c.subject, c.body, c.deadline, c.sent_time, c.agenda_panel FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.mail_type = 'REQUEST' AND c.has_deadline = 1 AND c.deadline > datetime('n...
```

**실행 결과**: 2개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | body | deadline |
|---|---|---|---|---|
| TEST2025002a | TEST2025002 | TEST2025002a: 긴급 검토 - 사이버보안... | 새로운 사이버보안 위협에 대응하기 위한 규정 개정... | 2025-08-05 02:25:23 |
| TEST2025001a | TEST2025001 | TEST2025001a: 테스트 의제 - AI 기... | AI 기반 선박 안전 시스템에 대한 각 기관의 의... | 2025-08-28 02:25:23 |

*참고: 전체 7개 컬럼 중 5개만 표시*

---

### 6. ✅ pending_agenda_count

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 대기 중인 의제 현황을 제공해 주세요.

**자연어 질의**:
1. 처리 대기 중인 agenda의 수는? (original)
2. 대기 중인 의제가 몇 개인가요? (similar1)
3. 펜딩 상태의 아젠다 개수를 알려주세요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 30}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_panel, COUNT(*) as pending_count, GROUP_CONCAT(DISTINCT agenda_base_version) as agenda_list FROM agenda_chair WHERE mail_type = 'REQUEST' AND has_deadline = 1 AND deadline > datetime('now') AND {period_condition} GROUP BY agenda_panel ORDER BY pending_count DESC
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_panel | pending_count | agenda_list |
|---|---|---|
| TEST | 2 | TEST2025001,TEST2025002 |

---

### 7. ✅ kr_required_issues_and_opinions

**카테고리**: keyword_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 각 의제별로 핵심 이슈를 파악하고, 다른 기관들의 의견을 찬성/반대/중립으로 분류해 주세요.

**자연어 질의**:
1. KR이 응답해야하는 의제에서 의제들의 주요 이슈 및 다른 기관의 의견 정리 (original)
2. 한국선급이 회신해야 할 안건의 핵심 내용과 타 기관 입장 요약해줘 (similar1)
3. KR이 답변 필요한 의제들의 주요 쟁점과 다른 기관들의 견해를 보여주세요 (similar2)
   ... 외 4개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `organization, period_condition`

**SQL 쿼리**:
```sql
WITH org_pending AS (SELECT c.agenda_base_version, c.subject, c.keywords, c.body as agenda_content, c.deadline, c.agenda_panel FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.mail_type = 'REQUEST' AND c.has_deadline = 1 AND c.deadline...
```

**실행 결과**: 2개 행 반환

**샘플 데이터** (최대 3행):

| agenda_base_version | subject | keywords | agenda_content | deadline |
|---|---|---|---|---|
| TEST2025002 | TEST2025002a: 긴급 검토 - 사이버보안... | ["사이버보안", "규정", "개정", "긴급"] | 새로운 사이버보안 위협에 대응하기 위한 규정 개정... | 2025-08-05 02:25:23 |
| TEST2025001 | TEST2025001a: 테스트 의제 - AI 기... | ["AI", "안전", "자동화", "선박"] | AI 기반 선박 안전 시스템에 대한 각 기관의 의... | 2025-08-28 02:25:23 |

*참고: 전체 16개 컬럼 중 5개만 표시*

---

### 8. ✅ kr_required_agendas_keywords

**카테고리**: keyword_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 출력값을 정리해서 제공해 주세요.

**자연어 질의**:
1. KR이 응답해야하는 의제들의 주요 키워드 (original)
2. 한국선급이 회신 필요한 안건들의 핵심 키워드를 보여주세요 (similar1)
3. KR 응답 대기 중인 의제들의 주요 단어들이 뭐가 있나요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `organization, period_condition`

**SQL 쿼리**:
```sql
SELECT c.agenda_base_version, c.subject, c.keywords FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.mail_type = 'REQUEST' AND c.has_deadline = 1 AND c.deadline > datetime('now') AND (r.{organization} IS NULL OR r.{organization} = '') ...
```

**실행 결과**: 2개 행 반환

**샘플 데이터** (최대 3행):

| agenda_base_version | subject | keywords |
|---|---|---|
| TEST2025002 | TEST2025002a: 긴급 검토 - 사이버보안... | ["사이버보안", "규정", "개정", "긴급"] |
| TEST2025001 | TEST2025001a: 테스트 의제 - AI 기... | ["AI", "안전", "자동화", "선박"] |

---

### 9. ✅ kr_required_other_org_keywords

**카테고리**: keyword_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 다른 기관들의 응답에서 자주 언급된 키워드를 분석하여 주요 관심사와 쟁점을 파악하고, KR의 응답 전략 수립에 참고할 수 있도록 정리해 주세요.

**자연어 질의**:
1. KR이 응답해야 하는 의제들 중에서 다른 기관의 회신 중 중요 키워드 (original)
2. KR 응답 필요 의제에서 타 기관들이 언급한 주요 키워드를 보여주세요 (similar1)
3. 우리가 답변해야 할 안건의 타사 응답에서 핵심 단어들 분석해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `organization, period_condition`

**SQL 쿼리**:
```sql
WITH org_pending AS (SELECT c.agenda_base_version FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.mail_type = 'REQUEST' AND c.has_deadline = 1 AND c.deadline > datetime('now') AND (r.{organization} IS NULL OR r.{organization} = '') AN...
```

**실행 결과**: 0개 행 반환

---

### 10. ✅ keyword_search_agendas

**카테고리**: keyword_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 검색된 의제들을 주제별로 분류하고 주요 논의 사항을 요약해 주세요.

**자연어 질의**:
1. 최근 논의된 의제들 중에 {keywords} 에 대해서 논의되고 있는 의제 (original)
2. {keywords} 관련해서 최근에 다뤄진 의제들을 보여주세요 (similar1)
3. {keywords}에 대한 논의가 있었던 안건들을 찾아주세요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `keywords` (array) - 기본값: ['UR', 'PR', 'EG', 'IMO', 'GPG']

**플레이스홀더**: `keywords_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, keywords, sent_time, decision_status, agenda_panel FROM agenda_chair WHERE sent_time >= datetime('now', '-90 days') AND ({keywords_condition}) ORDER BY sent_time DESC
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | keywords | sent_time |
|---|---|---|---|---|
| ENV25M005a | ENV25M005 | ENV25M005a: Urgent - Enviro... | ["conference", "urgent", "e... | 2025-07-20 00:45:24 |
| PL25M001a | PL25M001 | PL25M001a: IACS Annual Meet... | ["meeting", "annual", "Pari... | 2025-06-15 00:45:24 |
| PL25016_ILa | PL25016 | PL25016_ILa: IMO Expert Gro... | ["EGDH", "IMO", "SDTP", "re... | 2025-06-05 23:04:26+00:00 |

*참고: 전체 7개 컬럼 중 5개만 표시*

---

### 11. ✅ recent_meeting_notification_mails

**카테고리**: mail_type
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 회의 일정과 주요 안건을 정리하여 달력 형식으로 보여주세요.

**자연어 질의**:
1. 최근 회의 개최관련 해서 알림을 준 메일 (original)
2. 최근 회의 공지 메일들을 보여주세요 (similar1)
3. 회의 개최 안내 메일 리스트가 필요합니다 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_base_version, subject, sent_time, sender_organization, body, agenda_panel FROM agenda_chair WHERE mail_type = 'NOTIFICATION' AND (subject LIKE '%meeting%' OR subject LIKE '%conference%' OR subject LIKE '%회의%' OR body LIKE '%meeting%' OR body LIKE '%conference%') AND {period_condition} ...
```

**실행 결과**: 2개 행 반환

**샘플 데이터** (최대 3행):

| agenda_base_version | subject | sent_time | sender_organization | body |
|---|---|---|---|---|
| ENV25M005 | ENV25M005a: Urgent - Enviro... | 2025-07-20 00:45:24 | ABS | URGENT NOTICE\n\nAn emergen... |
| GEN25M002 | GEN25M002a: Technical Commi... | 2025-06-30 00:45:24 | DNV | Subject: Technical Committe... |

*참고: 전체 6개 컬럼 중 5개만 표시*

---

### 12. ✅ yearly_agenda_count_all_panels

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 테이블로 제공해 주세요.

**자연어 질의**:
1. 올해 모든 패널의 아젠다 갯수 (original)
2. 올해 발행된 전체 의제 수를 알려주세요 (similar1)
3. 2025년 총 아젠다 개수가 궁금합니다 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_panel, COUNT(*) as agenda_count FROM agenda_chair WHERE strftime('%Y', sent_time) = strftime('%Y', 'now') GROUP BY agenda_panel ORDER BY agenda_count DESC
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| agenda_panel | agenda_count |
|---|---|
| PL | 28 |
| JWG-CS | 3 |
| TEST | 2 |

---

### 13. ✅ yearly_created_agendas

**카테고리**: agenda_status
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 올해 생성된 의제들의 주요 주제와 트렌드를 분석해 주세요.

**자연어 질의**:
1. 올해 생성된 아젠다가 무엇인가요? (original)
2. 올해 새로 만들어진 의제들을 보여주세요 (similar1)
3. 2025년에 발행된 안건 목록이 필요합니다 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_base_version, subject, sent_time FROM agenda_chair WHERE strftime('%Y', sent_time) = strftime('%Y', 'now') ORDER BY sent_time DESC
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| agenda_base_version | subject | sent_time |
|---|---|---|
| TEST2025002 | TEST2025002a: 긴급 검토 - 사이버보안... | 2025-07-26 02:25:23 |
| TEST2025001 | TEST2025001a: 테스트 의제 - AI 기... | 2025-07-22 02:25:23 |
| ENV25M005 | ENV25M005a: Urgent - Enviro... | 2025-07-20 00:45:24 |

---

### 14. ✅ organization_mail_count

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 조직별 활동성을 제공해 주세요.

**자연어 질의**:
1. 각 조직별로 보낸 메일 수를 집게해 주세요 (original)
2. 기관별 메일 발송 건수를 보여주세요 (similar1)
3. 각 선급별로 보낸 이메일 통계가 필요합니다 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
WITH org_responses AS (SELECT 'ABS' as org, COUNT(*) as response_count FROM agenda_responses_content WHERE ABS IS NOT NULL AND ABS != '' UNION ALL SELECT 'BV', COUNT(*) FROM agenda_responses_content WHERE BV IS NOT NULL AND BV != '' UNION ALL SELECT 'CCS', COUNT(*) FROM agenda_responses_content WHER...
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| organization | response_count |
|---|---|
| DNV | 13 |
| IRS | 13 |
| NK | 13 |

---

### 15. ✅ recent_5_agendas

**카테고리**: agenda_status
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 최근 5개 의제의 주요 내용을 간략히 요약해 주세요.

**자연어 질의**:
1. 최근에 생성된 agenda 5개를 보여주세요 (original)
2. 가장 최근 의제 5개를 확인하고 싶어요 (similar1)
3. 최신 아젠다 5건 리스트 보여줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, sender_organization, sent_time, decision_status, deadline, agenda_panel FROM agenda_chair ORDER BY sent_time DESC LIMIT 5
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | sender_organization | sent_time |
|---|---|---|---|---|
| TEST2025002a | TEST2025002 | TEST2025002a: 긴급 검토 - 사이버보안... | IACS | 2025-07-26 02:25:23 |
| TEST2025001a | TEST2025001 | TEST2025001a: 테스트 의제 - AI 기... | IACS | 2025-07-22 02:25:23 |
| ENV25M005a | ENV25M005 | ENV25M005a: Urgent - Enviro... | ABS | 2025-07-20 00:45:24 |

*참고: 전체 8개 컬럼 중 5개만 표시*

---

### 16. ✅ recent_notification_mails

**카테고리**: mail_type
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 공지사항 메일들을 중요도별로 분류하여 핵심 내용을 정리해 주세요.

**자연어 질의**:
1. 최근 notification 타입의 메일만 조회해 주세요 (original)
2. 최근 공지사항 메일들을 보여주세요 (similar1)
3. NOTIFICATION 유형의 최신 메일 리스트가 필요해요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_base_version, subject, sender_organization, sent_time, body, agenda_panel FROM agenda_chair WHERE mail_type = 'NOTIFICATION' AND {period_condition} ORDER BY sent_time DESC
```

**실행 결과**: 3개 행 반환

**샘플 데이터** (최대 3행):

| agenda_base_version | subject | sender_organization | sent_time | body |
|---|---|---|---|---|
| ENV25M005 | ENV25M005a: Urgent - Enviro... | ABS | 2025-07-20 00:45:24 | URGENT NOTICE\n\nAn emergen... |
| PL25008e | PL25008eILa: IMO MSC 110 - ... | ABS | 2025-07-03 10:06:25+00:00 | PL25008eILa: IMO MSC 110 - ... |
| GEN25M002 | GEN25M002a: Technical Commi... | DNV | 2025-06-30 00:45:24 | Subject: Technical Committe... |

*참고: 전체 6개 컬럼 중 5개만 표시*

---

### 17. ✅ panel_agenda_count

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 패널별 활동성을 분석하고 가장 활발한 패널과 그 이유를 설명해 주세요.

**자연어 질의**:
1. 최근 패널 별 agenda 수를 집게해주세요 (original)
2. 패널별 의제 개수 통계를 보여주세요 (similar1)
3. 각 패널에서 발행한 아젠다 수를 알려줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_panel, COUNT(CASE WHEN mail_type = 'REQUEST' THEN 1 END) as request_count, COUNT(CASE WHEN mail_type = 'NOTIFICATION' THEN 1 END) as notification_count, COUNT(*) as total_count FROM agenda_chair WHERE {period_condition} GROUP BY agenda_panel ORDER BY total_count DESC
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| agenda_panel | request_count | notification_count | total_count |
|---|---|---|---|
| PL | 1 | 1 | 2 |
| TEST | 2 | 0 | 2 |
| ENV | 0 | 1 | 1 |

---

### 18. ✅ imo_related_agendas

**카테고리**: keyword_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 아젠다의 body를 요약하고 IMO에서 관련 내용을 어떻게 다루고 있는지 참조 자료를 검색해서 처리해 주세요.

**자연어 질의**:
1. 최근 IMO와 관련된 agenda를 모두 찾아주세요 (original)
2. IMO 관련 의제들을 검색해주세요 (similar1)
3. 국제해사기구 관련 안건 리스트가 필요합니다 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `keyword` (string) - 기본값: IMO

**플레이스홀더**: `keyword`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, keywords, body, sent_time, decision_status, agenda_panel FROM agenda_chair WHERE keywords LIKE '%' || {keyword} || '%' AND sent_time >= datetime('now', '-180 days') ORDER BY sent_time DESC
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | keywords | body |
|---|---|---|---|---|
| ENV25M005a | ENV25M005 | ENV25M005a: Urgent - Enviro... | ["conference", "urgent", "e... | URGENT NOTICE\n\nAn emergen... |
| PL25008eILa | PL25008e | PL25008eILa: IMO MSC 110 - ... | ["IMO", "MSC", "IACS", "Obs... | PL25008eILa: IMO MSC 110 - ... |
| PL25018_ILa | PL25018 | PL25018_ILa: IMO NCSR 12 Gu... | ["IMO", "NCSR", "software",... | PL25018_ILa: IMO NCSR 12 Gu... |

*참고: 전체 8개 컬럼 중 5개만 표시*

---

### 19. ✅ ur_revision_requirement_agendas

**카테고리**: keyword_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: UR 재개정 의제들을 분류하고 각 개정사항의 영향도를 분석해 주세요.

**자연어 질의**:
1. 최근 UR 관련해서 재개정 요구사항과 관련된 아젠다를 찾아줘 (original)
2. UR 개정 관련 의제들을 보여주세요 (similar1)
3. 통일규칙 재개정 요구사항이 있는 안건 검색해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `keyword` (string) - 기본값: UR

**플레이스홀더**: `keyword`

**SQL 쿼리**:
```sql
SELECT agenda_base_version, subject, body FROM agenda_chair WHERE keywords LIKE '%' || {keyword} || '%' AND sent_time >= datetime('now', '-180 days') ORDER BY sent_time DESC
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| agenda_base_version | subject | body |
|---|---|---|
| ENV25M005 | ENV25M005a: Urgent - Enviro... | URGENT NOTICE\n\nAn emergen... |
| PS25003p | PS25003pPLa MSC 110 (18-27 ... | PS25003pPLa MSC 110 (18-27 ... |
| GEN25M002 | GEN25M002a: Technical Commi... | Subject: Technical Committe... |

---

### 20. ✅ pr_revision_requirement_agendas

**카테고리**: keyword_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: PR 재개정 의제들을 분류하고 각 개정사항의 영향도를 분석해 주세요.

**자연어 질의**:
1. 최근 PR 관련해서 재개정 요구사항과 관련된 아젠다를 찾아줘 (original)
2. PR 개정 관련 의제들을 보여주세요 (similar1)
3. 절차요건 재개정 요구사항이 있는 안건 검색해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `keyword` (string) - 기본값: PR

**플레이스홀더**: `keyword`

**SQL 쿼리**:
```sql
SELECT agenda_base_version, subject, body FROM agenda_chair WHERE keywords LIKE '%' || {keyword} || '%' AND sent_time >= datetime('now', '-180 days') ORDER BY sent_time DESC
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| agenda_base_version | subject | body |
|---|---|---|
| PL25016 | PL25016_ILa: IMO Expert Gro... | PL25016_ILa: IMO Expert Gro... |
| PL24005 | PL24005_ILc: Email thread d... | PL24005_ILc: Email thread d... |
| PL25013 | PL25013_ILa:3rd IACS Safe D... | PL25013_ILa:3rd IACS Safe D... |

---

### 21. ✅ agenda_search_by_keywords

**카테고리**: keyword_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 아젠다별로 키워드가 어떤 맥락에서 논의되고 있는지 분석해 주세요.

**자연어 질의**:
1. {keywords} 관련 agenda (original)
2. {keywords}와 연관된 의제를 찾아주세요 (similar1)
3. {keywords}에 대한 아젠다 목록을 보여주세요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `keywords` (array) - 기본값: ['keyword1', 'keyword2']
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `keywords_condition, period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, body, keywords, agenda_panel, sent_time FROM agenda_chair WHERE {keywords_condition} AND {period_condition} ORDER BY sent_time DESC
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | body | keywords |
|---|---|---|---|---|
| ENV25M005a | ENV25M005 | ENV25M005a: Urgent - Enviro... | URGENT NOTICE\n\nAn emergen... | ["conference", "urgent", "e... |

*참고: 전체 7개 컬럼 중 5개만 표시*

---

### 22. ✅ kr_pending_response_agendas

**카테고리**: response_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 미응답 의제들을 마감일 임박 순서로 정리하고, 각 의제의 중요 내용과 응답한 기관들의 내용을 요약해서 정리해 주세요.

**자연어 질의**:
1. 진행되고 있는 의제들 중에서 KR이 아직 응답하지 않는 의제 (original)
2. KR이 아직 회신하지 않은 진행중인 안건을 보여주세요 (similar1)
3. 한국선급이 응답 대기중인 의제 목록을 알려주세요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `organization, period_condition`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.agenda_base_version, c.subject, c.body, c.agenda_panel, c.sent_time, c.deadline, r.ABS, r.BV, r.CCS, r.CRS, r.DNV, r.IRS, r.KR, r.LR, r.NK, r.PRS, r.RINA, r.IL, r.TL 
FROM agenda_chair c 
LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version 
W...
```

**실행 결과**: 2개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | body | agenda_panel |
|---|---|---|---|---|
| TEST2025002a | TEST2025002 | TEST2025002a: 긴급 검토 - 사이버보안... | 새로운 사이버보안 위협에 대응하기 위한 규정 개정... | TEST |
| TEST2025001a | TEST2025001 | TEST2025001a: 테스트 의제 - AI 기... | AI 기반 선박 안전 시스템에 대한 각 기관의 의... | TEST |

*참고: 전체 20개 컬럼 중 5개만 표시*

---

### 23. ✅ kr_required_agendas_other_org_keywords

**카테고리**: keyword_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 타 기관 응답에서 추출된 키워드를 빈도순으로 정리하고, 주요 이슈와 관심사를 분석해 주세요.

**자연어 질의**:
1. KR이 응답해야 하는 의제들 중에서 다른 기관의 회신 중 중요 키워드 (original)
2. KR 응답 필요 의제에서 타 기관들이 언급한 주요 키워드를 보여주세요 (similar1)
3. 한국선급이 답변해야 할 안건의 다른 조직 응답 키워드를 분석해줘 (similar2)
   ... 외 4개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `organization, period_condition`

**SQL 쿼리**:
```sql
WITH org_pending AS (SELECT c.agenda_base_version, c.agenda_code, c.subject FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.mail_type = 'REQUEST' AND c.has_deadline = 1 AND c.deadline > datetime('now') AND r.{organization} IS NULL AND...
```

**실행 결과**: 2개 행 반환

**샘플 데이터** (최대 3행):

| agenda_base_version | agenda_code | subject | ABS | BV |
|---|---|---|---|---|
| TEST2025002 | TEST2025002a | TEST2025002a: 긴급 검토 - 사이버보안... | None | None |
| TEST2025001 | TEST2025001a | TEST2025001a: 테스트 의제 - AI 기... | None | None |

*참고: 전체 16개 컬럼 중 5개만 표시*

---

### 24. ✅ kr_required_agendas_other_org_opinions

**카테고리**: response_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 각 의제별로 핵심 이슈를 정리하고, 기관별 의견의 찬반과 주요 논점을 분석해 주세요. 특히 의견이 대립되는 부분을 중점적으로 파악해 주세요.

**자연어 질의**:
1. KR이 응답해야하는 의제에서 의제들의 주요 이슈 및 다른 기관의 의견 정리 (original)
2. 한국선급이 회신해야 할 안건의 핵심 내용과 타 기관 입장 요약해줘 (similar1)
3. KR이 답변 필요한 의제들의 주요 쟁점과 다른 기관들의 견해를 보여주세요 (similar2)
   ... 외 4개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `organization, period_condition`

**SQL 쿼리**:
```sql
WITH org_pending AS (SELECT c.agenda_base_version, c.agenda_code, c.subject, c.body, c.keywords, c.agenda_panel FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.mail_type = 'REQUEST' AND c.has_deadline = 1 AND c.deadline > datetime('no...
```

**실행 결과**: 2개 행 반환

**샘플 데이터** (최대 3행):

| agenda_base_version | agenda_code | subject | body | keywords |
|---|---|---|---|---|
| TEST2025001 | TEST2025001a | TEST2025001a: 테스트 의제 - AI 기... | AI 기반 선박 안전 시스템에 대한 각 기관의 의... | ["AI", "안전", "자동화", "선박"] |
| TEST2025002 | TEST2025002a | TEST2025002a: 긴급 검토 - 사이버보안... | 새로운 사이버보안 위협에 대응하기 위한 규정 개정... | ["사이버보안", "규정", "개정", "긴급"] |

*참고: 전체 19개 컬럼 중 5개만 표시*

---

### 25. ✅ kr_response_required_simple

**카테고리**: response_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 응답 필요 의제들을 마감일 기준으로 우선순위를 정하고, 시급한 안건을 별도로 표시해 주세요.

**자연어 질의**:
1. KR이 응답을 해야 하는 의제 (original)
2. 한국선급이 회신해야 할 안건 목록을 보여주세요 (similar1)
3. KR이 답변 필요한 의제들을 알려주세요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `organization, period_condition`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.agenda_base_version, c.subject, c.agenda_panel, c.deadline 
FROM agenda_chair c 
LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version 
WHERE c.mail_type = 'REQUEST' 
AND c.has_deadline = 1 
AND c.deadline > datetime('now') 
AND r.{organization...
```

**실행 결과**: 2개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | agenda_panel | deadline |
|---|---|---|---|---|
| TEST2025002a | TEST2025002 | TEST2025002a: 긴급 검토 - 사이버보안... | TEST | 2025-08-05 02:25:23 |
| TEST2025001a | TEST2025001 | TEST2025001a: 테스트 의제 - AI 기... | TEST | 2025-08-28 02:25:23 |

---

### 26. ✅ notification_mails_recent

**카테고리**: mail_type
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 알림 메일들을 주제별로 분류하고, 중요한 공지사항이나 회의 관련 알림을 별도로 표시해 주세요.

**자연어 질의**:
1. 최근 notification 타입의 메일만 조회해 주세요 (original)
2. 최근 알림 메일들을 보여주세요 (similar1)
3. NOTIFICATION 유형의 최신 메일 목록을 확인하고 싶습니다 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, sender_organization, sent_time, agenda_panel FROM agenda_chair WHERE mail_type = 'NOTIFICATION' AND {period_condition} ORDER BY sent_time DESC
```

**실행 결과**: 3개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | sender_organization | sent_time |
|---|---|---|---|---|
| ENV25M005a | ENV25M005 | ENV25M005a: Urgent - Enviro... | ABS | 2025-07-20 00:45:24 |
| PL25008eILa | PL25008e | PL25008eILa: IMO MSC 110 - ... | ABS | 2025-07-03 10:06:25+00:00 |
| GEN25M002a | GEN25M002 | GEN25M002a: Technical Commi... | DNV | 2025-06-30 00:45:24 |

*참고: 전체 6개 컬럼 중 5개만 표시*

---

### 27. ✅ organization_mail_statistics

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 조직별 활동성을 제공해 주세요.

**자연어 질의**:
1. 각 조직별로 보낸 메일 수를 집계해 주세요 (original)
2. 기관별 메일 발송 통계를 보여주세요 (similar1)
3. 각 조직이 발송한 메일 개수를 집계해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
WITH org_responses AS (SELECT 'ABS' as org, COUNT(*) as response_count FROM agenda_responses_content WHERE ABS IS NOT NULL AND ABS != '' UNION ALL SELECT 'BV', COUNT(*) FROM agenda_responses_content WHERE BV IS NOT NULL AND BV != '' UNION ALL SELECT 'CCS', COUNT(*) FROM agenda_responses_content WHER...
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| organization | response_count | percentage |
|---|---|---|
| DNV | 13 | 10.08 |
| IRS | 13 | 10.08 |
| NK | 13 | 10.08 |

---

### 28. ✅ pending_agendas_count

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 조회된 내용을 바탕으로 대기 중인 의제 수와 각 의제의 제목 및 마감일을 표로 정리해서 제공해 주세요.

**자연어 질의**:
1. 처리 대기 중인 agenda의 수는? (original)
2. 대기중인 의제가 몇 개야? (similar1)
3. 미처리 안건 개수 알려줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 30}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_base_version, subject, deadline, CAST((julianday(deadline) - julianday('now')) AS INTEGER) as days_remaining FROM agenda_chair WHERE mail_type = 'REQUEST' AND has_deadline = 1 AND deadline > datetime('now') AND decision_status != 'completed' AND {period_condition} ORDER BY deadline ASC
```

**실행 결과**: 2개 행 반환

**샘플 데이터** (최대 3행):

| agenda_base_version | subject | deadline | days_remaining |
|---|---|---|---|
| TEST2025002 | TEST2025002a: 긴급 검토 - 사이버보안... | 2025-08-05 02:25:23 | 6 |
| TEST2025001 | TEST2025001a: 테스트 의제 - AI 기... | 2025-08-28 02:25:23 | 29 |

---

### 29. ✅ pr_eg_related_agendas

**카테고리**: keyword_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: PR 의제들을 주제별로 분류하고, 주요 사항에 대해 요약해 주세요.

**자연어 질의**:
1. 최근 PR 관련해서 재개정 요구사항과 관련된 아젠다를 찾아줘 (original)
2. PR 재개정 관련 의제들을 보여주세요 (similar1)
3. 절차요건 개정과 관련된 최근 안건을 찾아주세요 (similar2)
   ... 외 4개

**파라미터 정보**:
- 필수 파라미터:
  - `keyword` (string) - 기본값: PR
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `keyword, period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, body, agenda_panel, sent_time, keywords FROM agenda_chair WHERE keywords LIKE '%' || {keyword} || '%' AND {period_condition} ORDER BY sent_time DESC
```

**실행 결과**: 0개 행 반환

---

### 30. ✅ recent_created_top5_agendas

**카테고리**: agenda_status
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 패널별로 의제 내용을 요약해서 정리해 주세요.

**자연어 질의**:
1. 최근에 생성된 agenda 5개를 보여주세요 (original)
2. 가장 최근 발행된 의제 5개를 알려주세요 (similar1)
3. 최신 아젠다 상위 5개를 확인하고 싶습니다 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `panel` (string) - 기본값: PL
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `panel, period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, body, agenda_panel, sent_time FROM agenda_chair WHERE agenda_panel = {panel} AND {period_condition} ORDER BY sent_time DESC LIMIT 5
```

**실행 결과**: 2개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | body | agenda_panel |
|---|---|---|---|---|
| PL25008eILa | PL25008e | PL25008eILa: IMO MSC 110 - ... | PL25008eILa: IMO MSC 110 - ... | PL |
| PL24033_ILf | PL24033 | [자동생성] PL24033 |  | PL |

*참고: 전체 6개 컬럼 중 5개만 표시*

---

### 31. ✅ recent_three_months_agendas

**카테고리**: agenda_status
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 최근 3개월간의 의제들을 패널별, 상태별로 분석하고 주요 트렌드를 파악해 주세요.

**자연어 질의**:
1. 최근 3개월 동안 논의 되었던 의제 목록 (original)
2. 지난 3개월간 진행된 의제들을 보여주세요 (similar1)
3. 최근 90일 동안의 아젠다 리스트를 확인하고 싶습니다 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, agenda_panel, sent_time, decision_status FROM agenda_chair WHERE mail_type = 'REQUEST' AND sent_time >= DATE('now', '-90 days') ORDER BY sent_time DESC
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | agenda_panel | sent_time |
|---|---|---|---|---|
| TEST2025002a | TEST2025002 | TEST2025002a: 긴급 검토 - 사이버보안... | TEST | 2025-07-26 02:25:23 |
| TEST2025001a | TEST2025001 | TEST2025001a: 테스트 의제 - AI 기... | TEST | 2025-07-22 02:25:23 |
| PL24033_ILf | PL24033 | [자동생성] PL24033 | PL | 2025-06-30 00:12:01+00:00 |

*참고: 전체 6개 컬럼 중 5개만 표시*

---

### 32. ✅ ur_revision_agendas

**카테고리**: keyword_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: UR 관련 의제들을 주제별로 분류하고, 주요 개정 사항이나 논의 내용을 요약해 주세요.

**자연어 질의**:
1. 최근 UR 관련해서 재개정 요구사항과 관련된 아젠다를 찾아줘 (original)
2. UR 재개정 관련 의제들을 보여주세요 (similar1)
3. 통일규칙 개정과 관련된 최근 안건을 찾아주세요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, agenda_panel, sent_time, keywords FROM agenda_chair WHERE (subject LIKE '%UR%' OR subject LIKE '%Unified Requirement%' OR body LIKE '%UR%' OR body LIKE '%Unified Requirement%' OR keywords LIKE '%UR%' OR keywords LIKE '%revision%' OR keywords LIKE '%a...
```

**실행 결과**: 4개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | agenda_panel | sent_time |
|---|---|---|---|---|
| ENV25M005a | ENV25M005 | ENV25M005a: Urgent - Enviro... | ENV | 2025-07-20 00:45:24 |
| PS25003pPLa | PS25003p | PS25003pPLa MSC 110 (18-27 ... | PS | 2025-07-03 10:12:30+00:00 |
| PL25008eILa | PL25008e | PL25008eILa: IMO MSC 110 - ... | PL | 2025-07-03 10:06:25+00:00 |

*참고: 전체 6개 컬럼 중 5개만 표시*

---


## 테스트 설정

- **파일**: query_templates_group_001.json
- **테스트 일시**: 2025-07-30T11:05:25.179620
- **데이터베이스 경로**: data/iacsgraph.db
