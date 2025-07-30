# query_templates_group_005.json 테스트 보고서

**테스트 일시**: 2025-07-30T11:05:25.217361
**데이터베이스**: data/iacsgraph.db

## 요약

- **전체 템플릿 수**: 21
- **성공**: 21 (100.0%)
- **실패**: 0

### 카테고리별 결과

| 카테고리 | 전체 | 성공 | 실패 | 성공률 |
|----------|------|------|------|--------|
| keyword_analysis | 5 | 5 | 0 | 100.0% |
| keyword_search | 1 | 1 | 0 | 100.0% |
| deadline_tracking | 1 | 1 | 0 | 100.0% |
| response_tracking | 3 | 3 | 0 | 100.0% |
| mail_type | 3 | 3 | 0 | 100.0% |
| meeting | 1 | 1 | 0 | 100.0% |
| statistics | 3 | 3 | 0 | 100.0% |
| specific_agenda | 3 | 3 | 0 | 100.0% |
| attachment_analysis | 1 | 1 | 0 | 100.0% |

## 상세 결과

### 1. ✅ sdtp_kr_required_issues_opinions

**카테고리**: keyword_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: SDTP에서 KR이 응답해야 할 의제들의 핵심 이슈를 파악하고, 다른 기관들의 의견을 분석하여 KR의 대응 전략을 제안해 주세요.

**자연어 질의**:
1. KR이 응답해야하는 의제에서 의제들의 주요 이슈 및 다른 기관의 의견 정리 (original)
2. SDTP에서 한국선급이 회신해야 할 안건의 핵심 내용과 타 기관 입장 요약해줘 (similar1)
3. SDTP 패널에서 KR이 답변 필요한 의제들의 주요 쟁점과 다른 기관들의 견해를 보여주세요 (similar2)
   ... 외 3개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR

**플레이스홀더**: `organization`

**SQL 쿼리**:
```sql
WITH org_pending AS (SELECT c.agenda_base_version, c.subject, c.keywords, c.body as agenda_content, c.deadline FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_panel = 'SDTP' AND c.mail_type = 'REQUEST' AND c.has_deadline = 1 AN...
```

**실행 결과**: 0개 행 반환

---

### 2. ✅ sdtp_kr_required_keywords

**카테고리**: keyword_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: SDTP에서 KR이 응답해야 할 의제들의 키워드를 분석하여 현재 중점적으로 다뤄야 할 기술 분야를 파악해 주세요.

**자연어 질의**:
1. KR이 응답해야하는 의제들의 주요 키워드 (original)
2. SDTP에서 한국선급이 회신 필요한 안건들의 핵심 키워드를 보여주세요 (similar1)
3. SDTP 패널에서 KR 응답 대기 중인 의제들의 주요 단어들이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR

**플레이스홀더**: `organization`

**SQL 쿼리**:
```sql
WITH org_pending AS (SELECT c.keywords FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_panel = 'SDTP' AND c.mail_type = 'REQUEST' AND c.has_deadline = 1 AND c.deadline > datetime('now') AND (r.{organization} IS NULL OR r.{organ...
```

**실행 결과**: 0개 행 반환

---

### 3. ✅ sdtp_kr_required_response_keywords

**카테고리**: keyword_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: SDTP에서 다른 기관들의 응답 키워드를 분석하여 주요 기술적 관심사와 입장을 파악하고 KR의 차별화된 대응 방안을 제시해 주세요.

**자연어 질의**:
1. KR이 응답해야 하는 의제들의 회신 중 주요 키워드 (original)
2. SDTP에서 KR 응답 필요 의제에 대한 타 기관 회신의 핵심 키워드를 보여주세요 (similar1)
3. 선박설계기술패널에서 우리가 답변해야 할 안건의 타사 응답 키워드 분석해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR

**플레이스홀더**: `organization`

**SQL 쿼리**:
```sql
WITH org_pending AS (SELECT c.agenda_base_version FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_panel = 'SDTP' AND c.mail_type = 'REQUEST' AND c.has_deadline = 1 AND c.deadline > datetime('now') AND (r.{organization} IS NULL ...
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| source | responding_orgs |
|---|---|
| Multiple Organizations | None |

---

### 4. ✅ sdtp_keyword_search_agendas

**카테고리**: keyword_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: SDTP에서 검색된 의제들을 분석하여 해당 주제에 대한 논의 동향을 설명해 주세요.

**자연어 질의**:
1. 최근 논의된 의제들 중에 {keywords} 에 대해서 논의되고 있는 의제 (original)
2. SDTP에서 {keywords} 관련해서 최근에 다뤄진 의제들을 보여주세요 (similar1)
3. 선박설계기술패널에서 {keywords}에 대한 논의가 있었던 안건들을 찾아주세요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `keywords` (array)
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `keywords_condition, period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, keywords, sent_time, decision_status FROM agenda_chair WHERE agenda_panel = 'SDTP' AND {period_condition} AND ({keywords_condition}) ORDER BY sent_time DESC
```

**실행 결과**: 0개 행 반환

---

### 5. ✅ kr_urgent_response_required

**카테고리**: deadline_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 긴급 대응이 필요한 의제들을 분류하고 각각의 우선순위와 대응 전략을 제시해 주세요.

**자연어 질의**:
1. KR이 긴급하게 응답을 해야 하는 의제 (original)
2. 한국선급이 시급히 회신해야 할 의제들을 보여주세요 (similar1)
3. KR이 급하게 답변해야 하는 안건들이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR

**플레이스홀더**: `organization`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.agenda_base_version, c.subject, c.deadline, CASE WHEN c.deadline < datetime('now') THEN 'OVERDUE' ELSE 'URGENT' END as status, JULIANDAY(c.deadline) - JULIANDAY('now') as days_remaining, c.agenda_panel FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_...
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | deadline | status |
|---|---|---|---|---|
| JWG-CS25001d | JWG-CS25001d | JWG-CS25001d: 28th JWG-CS M... | 2025-05-09 23:59:59+00:00 | OVERDUE |
| PL25011_ILa | PL25011 | PL25011_ILa IACS/Industry M... | 2025-05-12 23:59:59+00:00 | OVERDUE |
| PL24016_ILg | PL24016 | PL24016_ILg: PT PC09 Recomm... | 2025-05-14 23:59:59+00:00 | OVERDUE |

*참고: 전체 7개 컬럼 중 5개만 표시*

---

### 6. ✅ sdtp_kr_response_required

**카테고리**: response_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: SDTP에서 KR이 응답해야 할 의제들의 중요도와 기술적 영향을 평가해 주세요.

**자연어 질의**:
1. SDTP 에서 KR이 응답해야 하는 의제 (original)
2. SDTP 패널에서 한국선급이 회신해야 할 의제들을 보여주세요 (similar1)
3. 선박설계기술패널에서 KR 답변이 필요한 안건 리스트 확인해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR

**플레이스홀더**: `organization`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.agenda_base_version, c.subject, c.deadline, c.sent_time FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_panel = 'SDTP' AND c.mail_type = 'REQUEST' AND c.has_deadline = 1 AND c.deadline > datetime('now') ...
```

**실행 결과**: 0개 행 반환

---

### 7. ✅ recent_sdtp_chair_mails

**카테고리**: mail_type
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: SDTP 의장의 최근 활동과 주요 관심사를 분석해 주세요.

**자연어 질의**:
1. 최근 SDTP 의장이 최근 보낸 메일 목록 (original)
2. SDTP 패널 의장이 최근 발송한 메일들을 보여주세요 (similar1)
3. 선박설계기술패널 체어가 보낸 최근 이메일 리스트가 뭐인가요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, subject, sent_time, mail_type, has_deadline, deadline FROM agenda_chair WHERE agenda_panel = 'SDTP' AND sender_type = 'CHAIR' AND {period_condition} ORDER BY sent_time DESC
```

**실행 결과**: 0개 행 반환

---

### 8. ✅ sdtp_chair_response_required_mails

**카테고리**: mail_type
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: SDTP 의장이 요청한 의제들의 중요도와 긴급성을 평가해 주세요.

**자연어 질의**:
1. 최근 SDTP 의장이 보낸 메일 중 응답이 필요한 의제 목록 (original)
2. SDTP 의장이 발송한 메일 중 회신이 필요한 것들을 보여주세요 (similar1)
3. 선박설계기술패널 체어가 보낸 답변 요청 메일이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, sent_time, deadline, JULIANDAY(deadline) - JULIANDAY('now') as days_remaining FROM agenda_chair WHERE agenda_panel = 'SDTP' AND sender_type = 'CHAIR' AND mail_type = 'REQUEST' AND has_deadline = 1 ORDER BY deadline ASC
```

**실행 결과**: 0개 행 반환

---

### 9. ✅ sdtp_chair_mail_keywords

**카테고리**: keyword_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: SDTP 의장의 키워드 분석을 통해 현재 패널의 주요 기술적 관심사와 방향성을 파악해 주세요.

**자연어 질의**:
1. SDTP 의장이 보낸 메일의 키워드들 알려줘 (original)
2. SDTP 패널 의장 메일에서 자주 언급된 키워드를 보여주세요 (similar1)
3. 선박설계기술패널 체어 메일의 주요 단어들이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT keywords, COUNT(*) as frequency FROM agenda_chair WHERE agenda_panel = 'SDTP' AND sender_type = 'CHAIR' AND keywords IS NOT NULL AND keywords != '' GROUP BY keywords ORDER BY frequency DESC LIMIT 30
```

**실행 결과**: 0개 행 반환

---

### 10. ✅ recent_meeting_notification_mails

**카테고리**: meeting
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 최근 회의 일정을 정리하고 각 회의의 주요 안건을 파악해 주세요.

**자연어 질의**:
1. 최근 회의 개최관련 해서 알림을 준 메일 (original)
2. 최근 회의 일정을 알려준 통지 메일들을 보여주세요 (similar1)
3. 회의 개최 공지 메일이 최근에 뭐가 있었나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, subject, sent_time, body, agenda_panel FROM agenda_chair WHERE mail_type = 'NOTIFICATION' AND (LOWER(subject) LIKE '%meeting%' OR LOWER(subject) LIKE '%회의%' OR LOWER(body) LIKE '%meeting notice%') AND {period_condition} ORDER BY sent_time DESC
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | subject | sent_time | body | agenda_panel |
|---|---|---|---|---|
| GEN25M002a | GEN25M002a: Technical Commi... | 2025-06-30 00:45:24 | Subject: Technical Committe... | GEN |

---

### 11. ✅ recent_chair_mail_content

**카테고리**: mail_type
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 각 패널 의장의 메일 내용을 분석하여 주요 이슈와 요청사항을 정리해 주세요.

**자연어 질의**:
1. 최근 의장이 보낸 메일 내용 줘 (original)
2. 최근 의장들이 발송한 메일의 상세 내용을 보여주세요 (similar1)
3. 체어가 보낸 최근 이메일 본문이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_panel, agenda_code, subject, body, sent_time FROM agenda_chair WHERE sender_type = 'CHAIR' AND sent_time >= datetime('now', '-30 days') ORDER BY sent_time DESC LIMIT 20
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| agenda_panel | agenda_code | subject | body | sent_time |
|---|---|---|---|---|
| TEST | TEST2025002a | TEST2025002a: 긴급 검토 - 사이버보안... | 새로운 사이버보안 위협에 대응하기 위한 규정 개정... | 2025-07-26 02:25:23 |
| TEST | TEST2025001a | TEST2025001a: 테스트 의제 - AI 기... | AI 기반 선박 안전 시스템에 대한 각 기관의 의... | 2025-07-22 02:25:23 |
| ENV | ENV25M005a | ENV25M005a: Urgent - Enviro... | URGENT NOTICE\n\nAn emergen... | 2025-07-20 00:45:24 |

---

### 12. ✅ sdtp_kr_response_rate_recent

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: SDTP에서 KR의 응답률을 다른 주요 조직과 비교하고 개선 방안을 제시해 주세요.

**자연어 질의**:
1. 최근 발행한 의제 중 SDTP 패널에서 한국선급 응답율 (original)
2. SDTP에서 최근 KR의 응답률이 어떻게 되나요? (similar1)
3. 선박설계기술패널에서 한국선급 최근 회신율을 보여주세요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `organization, period_condition`

**SQL 쿼리**:
```sql
SELECT COUNT(DISTINCT c.agenda_base_version) as total_agendas, COUNT(DISTINCT CASE WHEN r.{organization} IS NOT NULL THEN c.agenda_base_version END) as responded_agendas, ROUND(COUNT(DISTINCT CASE WHEN r.{organization} IS NOT NULL THEN c.agenda_base_version END) * 100.0 / COUNT(DISTINCT c.agenda_bas...
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| total_agendas | responded_agendas | response_rate |
|---|---|---|
| 0 | 0 | None |

---

### 13. ✅ sdtp_kr_response_rate_period

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 지정된 기간의 SDTP 응답률을 분석하여 시간에 따른 변화와 개선 사항을 파악해 주세요.

**자연어 질의**:
1. {period} 발행한 의제 중 SDTP 패널에서 한국선급 응답율 (original)
2. SDTP에서 {period} 기간 동안 KR의 응답률이 어떻게 되나요? (similar1)
3. 선박설계기술패널에서 {period} 한국선급 회신율을 보여주세요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR
  - `period` (period)

**플레이스홀더**: `organization, period_condition`

**SQL 쿼리**:
```sql
SELECT COUNT(DISTINCT c.agenda_base_version) as total_agendas, COUNT(DISTINCT CASE WHEN r.{organization} IS NOT NULL THEN c.agenda_base_version END) as responded_agendas, ROUND(COUNT(DISTINCT CASE WHEN r.{organization} IS NOT NULL THEN c.agenda_base_version END) * 100.0 / COUNT(DISTINCT c.agenda_bas...
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| total_agendas | responded_agendas | response_rate |
|---|---|---|
| 0 | 0 | None |

---

### 14. ✅ sdtp_kr_response_rate_yearly

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 올해 SDTP에서 KR의 월별 응답률 추이를 분석하고 개선이 필요한 부분을 제시해 주세요.

**자연어 질의**:
1. 올해 발행한 의제 중 SDTP 패널에서 한국선급 응답율 (original)
2. SDTP에서 올해 KR의 응답률이 어떻게 되나요? (similar1)
3. 선박설계기술패널에서 금년도 한국선급 회신율을 보여주세요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR

**플레이스홀더**: `organization`

**SQL 쿼리**:
```sql
SELECT strftime('%Y-%m', c.sent_time) as month, COUNT(DISTINCT c.agenda_base_version) as total, COUNT(DISTINCT CASE WHEN r.{organization} IS NOT NULL THEN c.agenda_base_version END) as responded, ROUND(COUNT(DISTINCT CASE WHEN r.{organization} IS NOT NULL THEN c.agenda_base_version END) * 100.0 / CO...
```

**실행 결과**: 0개 행 반환

---

### 15. ✅ recent_sdtp_keywords

**카테고리**: keyword_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: SDTP 패널의 키워드 트렌드를 분석하여 현재 주요 기술적 관심사와 향후 방향을 제시해 주세요.

**자연어 질의**:
1. 최근 SDTP 패널에서 논의되었던 의제의 주요 키워드 출력 해줘 (original)
2. SDTP에서 최근 자주 언급된 키워드들을 보여주세요 (similar1)
3. 선박설계기술패널 최근 핵심 단어들이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT keywords, COUNT(*) as frequency FROM agenda_chair WHERE agenda_panel = 'SDTP' AND keywords IS NOT NULL AND keywords != '' AND {period_condition} GROUP BY keywords ORDER BY frequency DESC LIMIT 30
```

**실행 결과**: 0개 행 반환

---

### 16. ✅ sdtp_kr_no_attachment_response_required

**카테고리**: response_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 첨부파일이 포함된 미응답 의제들의 중요도를 평가하고 우선 검토가 필요한 파일들을 식별해 주세요.

**자연어 질의**:
1. 최근 마감되지 않거나 KR이 응답하지 않은 의제 중에서 의장에 첨부파일을 송부한 의제 (original)
2. SDTP에서 KR 미응답 의제 중 의장이 첨부파일을 보낸 건들을 보여주세요 (similar1)
3. 선박설계기술패널에서 우리가 답변 안 한 안건 중 첨부 있는 것들이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR

**플레이스홀더**: `organization`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.agenda_base_version, c.subject, c.deadline, c.sent_time FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_panel = 'SDTP' AND c.sender_type = 'CHAIR' AND c.hasAttachments = 1 AND c.mail_type = 'REQUEST' AND...
```

**실행 결과**: 0개 행 반환

---

### 17. ✅ pl25016_agenda_status

**카테고리**: specific_agenda
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: PL25016 의제의 현재 진행 상황과 다음 단계를 설명해 주세요.

**자연어 질의**:
1. PL25016 의제가 현재 진행 중인가? (original)
2. PL25016 안건이 아직 진행되고 있나요? (similar1)
3. PL25016의 현재 상태가 어떻게 되나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, decision_status, sent_time, sent_time, deadline FROM agenda_chair WHERE agenda_code = 'PL25016' ORDER BY sent_time DESC LIMIT 1
```

**실행 결과**: 0개 행 반환

---

### 18. ✅ specific_agenda_status

**카테고리**: specific_agenda
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 의제의 현재 진행 상황과 다음 단계를 설명해 주세요.

**자연어 질의**:
1. {agenda} 의제가 현재 진행 중인가? (original)
2. {agenda} 안건이 아직 진행되고 있나요? (similar1)
3. {agenda}의 현재 상태가 어떻게 되나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, decision_status, sent_time, sent_time, deadline, agenda_panel FROM agenda_chair WHERE agenda_base_version = '{agenda}' ORDER BY sent_time DESC LIMIT 1
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | decision_status | sent_time |
|---|---|---|---|---|
| PL24005_ILc | PL24005 | PL24005_ILc: Email thread d... | created | 2025-05-16 18:03:26+00:00 |

*참고: 전체 7개 컬럼 중 5개만 표시*

---

### 19. ✅ kr_response_required_attachment_check

**카테고리**: attachment_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 첨부파일이 포함된 의제들의 중요도를 평가하고 파일 검토의 우선순위를 제시해 주세요.

**자연어 질의**:
1. KR이 응답해야하는 의제 중 의장이 보낸 메일이 첨부가 있는지 확인 (original)
2. 한국선급이 회신해야 할 의제 중 의장이 첨부파일을 포함한 건들을 보여주세요 (similar1)
3. KR 응답 필요한 안건 중에 체어가 파일 첨부한 게 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR

**플레이스홀더**: `organization`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.agenda_base_version, c.subject, c.deadline, c.agenda_panel FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.sender_type = 'CHAIR' AND c.hasAttachments = 1 AND c.mail_type = 'REQUEST' AND c.has_deadline = 1 AND c...
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | deadline | agenda_panel |
|---|---|---|---|---|
| TEST2025002a | TEST2025002 | TEST2025002a: 긴급 검토 - 사이버보안... | 2025-08-05 02:25:23 | TEST |

---

### 20. ✅ kr_sdtp_recent_responses

**카테고리**: response_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: KR이 SDTP에서 응답한 내역을 분석하고 주요 입장과 의견을 정리해 주세요.

**자연어 질의**:
1. 최근 KR에서 SDTP 에서 응답한 내역 (original)
2. 한국선급이 SDTP 패널에서 최근 응답한 내용을 보여주세요 (similar1)
3. KR이 선박설계기술패널에서 회신한 최신 내역이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR
  - `panel` (string) - 기본값: SDTP
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT 
    c.agenda_code,
    c.agenda_base_version,
    c.subject,
    c.sent_time,
    rt.KR as response_time,
    JULIANDAY(rt.KR) - JULIANDAY(c.sent_time) as response_days
FROM agenda_chair c
JOIN agenda_responses_receivedtime rt ON c.agenda_base_version = rt.agenda_base_version
WHERE c.agenda_...
```

**실행 결과**: 0개 행 반환

---

### 21. ✅ specific_agenda_kr_response_check

**카테고리**: specific_agenda
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: KR의 응답 여부를 확인하고, 응답 내용이 있다면 요약해 주세요.

**자연어 질의**:
1. PL25015 의제에서 KR이 응답을 하였는가? (original)
2. PL25015 안건에 한국선급이 회신했나요? (similar1)
3. KR이 PL25015 의제에 답변을 제출했는지 확인해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
SELECT 
    c.agenda_code,
    c.agenda_base_version,
    c.subject,
    c.sent_time,
    c.deadline,
    CASE WHEN rt.KR IS NOT NULL THEN 'Yes' ELSE 'No' END as kr_responded,
    rt.KR as kr_response_time
FROM agenda_chair c
LEFT JOIN agenda_responses_receivedtime rt ON c.agenda_base_version = rt.a...
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | sent_time | deadline |
|---|---|---|---|---|
| PL24005_ILc | PL24005 | PL24005_ILc: Email thread d... | 2025-05-16 18:03:26+00:00 | 2025-06-03 23:59:59+00:00 |

*참고: 전체 7개 컬럼 중 5개만 표시*

---


## 테스트 설정

- **파일**: query_templates_group_005.json
- **테스트 일시**: 2025-07-30T11:05:25.217361
- **데이터베이스 경로**: data/iacsgraph.db
