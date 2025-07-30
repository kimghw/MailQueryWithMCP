# query_templates_group_008.json 테스트 보고서

**테스트 일시**: 2025-07-30T11:05:25.240102
**데이터베이스**: data/iacsgraph.db

## 요약

- **전체 템플릿 수**: 21
- **성공**: 20 (95.2%)
- **실패**: 1

### 카테고리별 결과

| 카테고리 | 전체 | 성공 | 실패 | 성공률 |
|----------|------|------|------|--------|
| agenda_info | 1 | 1 | 0 | 100.0% |
| progress_tracking | 1 | 1 | 0 | 100.0% |
| response_drafting | 1 | 1 | 0 | 100.0% |
| meeting | 3 | 3 | 0 | 100.0% |
| related_analysis | 2 | 2 | 0 | 100.0% |
| strategy | 1 | 1 | 0 | 100.0% |
| decision_tracking | 1 | 1 | 0 | 100.0% |
| trend_analysis | 2 | 2 | 0 | 100.0% |
| regulation_search | 4 | 4 | 0 | 100.0% |
| keyword_search | 2 | 2 | 0 | 100.0% |
| expert_group | 2 | 2 | 0 | 100.0% |
| technical_info | 1 | 0 | 1 | 0.0% |

## 상세 결과

### 1. ✅ agenda_explanation

**카테고리**: agenda_info
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 의제의 배경과 목적을 설명하고, 주요 논의 사항과 중요성을 분석해 주세요.

**자연어 질의**:
1. {agenda} 에 대해서 설명해줘 (original)
2. {agenda} 의제가 어떤 내용인지 설명해주세요 (similar1)
3. {agenda} 안건에 대해 자세히 알려줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
SELECT agenda_code, subject, body, keywords, sent_time, sender_organization, deadline, decision_status, agenda_panel FROM agenda_chair WHERE agenda_base_version = '{agenda}' ORDER BY agenda_version DESC LIMIT 1
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | subject | body | keywords | sent_time |
|---|---|---|---|---|
| PL24005_ILc | PL24005_ILc: Email thread d... | PL24005_ILc: Email thread d... | ["SDTP", "URs", "spreadshee... | 2025-05-16 18:03:26+00:00 |

*참고: 전체 9개 컬럼 중 5개만 표시*

---

### 2. ✅ recent_progress_status

**카테고리**: progress_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 최근 진행 현황을 분석하여 전체적인 업무 흐름과 처리 효율성을 평가해 주세요.

**자연어 질의**:
1. 최근 진행 현황은? (original)
2. 최근 업무 진행 상황을 알려주세요 (similar1)
3. 요즘 진행되고 있는 현황이 어떻게 되나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT 'Total Agendas' as metric, COUNT(*) as count FROM agenda_chair WHERE sent_time >= datetime('now', '-30 days') UNION ALL SELECT 'Ongoing' as metric, COUNT(*) as count FROM agenda_chair WHERE deadline IS NOT NULL AND deadline > datetime('now') AND sent_time >= datetime('now', '-30 days') UNION ...
```

**실행 결과**: 4개 행 반환

**샘플 데이터** (최대 3행):

| metric | count |
|---|---|
| Total Agendas | 5 |
| Ongoing | 2 |
| Completed | 2 |

---

### 3. ✅ kr_opinion_based_reply_draft

**카테고리**: response_drafting
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: KR의 과거 입장을 분석하여 일관성 있고 전문적인 회신 메일 초안을 작성해 주세요. 기술적 근거와 안전성을 강조하면서도 협력적인 톤을 유지해 주세요.

**자연어 질의**:
1. 지난 KR의 의견을 바탕으로 {agenda}에 대한 회신 메일을 작성해줘 (original)
2. 이전 한국선급 입장을 참고하여 {agenda} 응답 메일 초안을 만들어주세요 (similar1)
3. 과거 KR 의견 기반으로 {agenda} 회신 작성해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
WITH target_agenda AS (SELECT keywords, subject, agenda_panel FROM agenda_chair WHERE agenda_base_version = '{agenda}' LIMIT 1) SELECT c.agenda_code, c.subject, r.KR as kr_opinion, c.sent_time FROM agenda_chair c JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version JOIN t...
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | subject | kr_opinion | sent_time |
|---|---|---|---|
| PL25016_ILa | PL25016_ILa: IMO Expert Gro... | PL25016_KRa: IMO Expert Gro... | 2025-06-05 23:04:26+00:00 |
| PL25015_ILa | PL25015_ILa: Recommendation... | PL25015_KRa: Recommendation... | 2025-06-05 16:14:33+00:00 |
| PL25007bILa | PL25007bILa IMO FAL Corresp... | PL25007bKRa IMO FAL Corresp... | 2025-06-02 21:14:13+00:00 |

---

### 4. ✅ recent_main_meeting_content

**카테고리**: meeting
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 회의의 주요 논의 내용을 의제별로 정리하고 중요한 결정사항을 강조해 주세요.

**자연어 질의**:
1. 최근 진행 한 회의의 주요 회의 내용은? (original)
2. 최근 개최된 회의의 핵심 내용을 보여주세요 (similar1)
3. 지난 미팅에서 다룬 주요 안건이 뭐였나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 30}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT subject, body, sent_time, agenda_panel FROM agenda_chair WHERE mail_type = 'NOTIFICATION' AND (LOWER(subject) LIKE '%meeting%' OR LOWER(subject) LIKE '%minutes%') AND LOWER(body) LIKE '%agenda%' AND {period_condition} ORDER BY sent_time DESC LIMIT 5
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| subject | body | sent_time | agenda_panel |
|---|---|---|---|
| GEN25M002a: Technical Commi... | Subject: Technical Committe... | 2025-06-30 00:45:24 | GEN |

---

### 5. ✅ recent_video_meeting_results

**카테고리**: meeting
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 화상회의 결과를 분석하여 주요 결정사항과 후속 조치를 정리해 주세요.

**자연어 질의**:
1. 최근에 화상회의 결과 알려줘 (original)
2. 최근 진행된 비디오 회의 결과를 보여주세요 (similar1)
3. 지난 온라인 미팅 결과가 어떻게 되나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 60}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT subject, body, sent_time, agenda_panel FROM agenda_chair WHERE mail_type = 'NOTIFICATION' AND (LOWER(subject) LIKE '%video%' OR LOWER(subject) LIKE '%virtual%' OR LOWER(subject) LIKE '%online%' OR LOWER(body) LIKE '%video conference%') AND {period_condition} ORDER BY sent_time DESC
```

**실행 결과**: 0개 행 반환

---

### 6. ✅ upcoming_meetings

**카테고리**: meeting
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 예정된 회의 일정을 정리하고 각 회의의 중요도와 준비 사항을 안내해 주세요.

**자연어 질의**:
1. 향후 예정된 회의 알려줘 (original)
2. 앞으로 예정된 회의 일정을 보여주세요 (similar1)
3. 다가오는 미팅 스케줄이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT subject, body, sent_time, agenda_panel FROM agenda_chair WHERE mail_type = 'NOTIFICATION' AND (LOWER(subject) LIKE '%upcoming%' OR LOWER(subject) LIKE '%scheduled%' OR LOWER(subject) LIKE '%planned%' OR LOWER(subject) LIKE '%예정%' OR LOWER(body) LIKE '%will be held%') ORDER BY sent_time DESC
```

**실행 결과**: 3개 행 반환

**샘플 데이터** (최대 3행):

| subject | body | sent_time | agenda_panel |
|---|---|---|---|
| ENV25M005a: Urgent - Enviro... | URGENT NOTICE\n\nAn emergen... | 2025-07-20 00:45:24 | ENV |
| GEN25M002a: Technical Commi... | Subject: Technical Committe... | 2025-06-30 00:45:24 | GEN |
| PL25M001a: IACS Annual Meet... | Dear Members,\n\nThis is to... | 2025-06-15 00:45:24 | PL |

---

### 7. ✅ recent_agenda_related_other_panel

**카테고리**: related_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 다른 패널에서 논의된 유사 이슈를 분석하여 패널 간 협력 가능성과 일관된 대응 방안을 제시해 주세요.

**자연어 질의**:
1. 최근 {agenda}와 관련해서 다른 패널에서 같은 이슈로 논의된게 있나? (original)
2. {agenda} 주제가 최근 다른 패널에서도 다뤄졌나요? (similar1)
3. {agenda}와 비슷한 이슈를 타 패널에서 논의했는지 확인해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
WITH target_info AS (SELECT keywords, subject, agenda_panel FROM agenda_chair WHERE agenda_base_version = '{agenda}' LIMIT 1) SELECT c.agenda_code, c.subject, c.keywords, c.sent_time, c.agenda_panel FROM agenda_chair c, target_info t WHERE c.agenda_panel != t.agenda_panel AND c.sent_time >= datetime...
```

**실행 결과**: 0개 행 반환

---

### 8. ✅ sdtp_strategy_goals

**카테고리**: strategy
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: SDTP의 전략적 목표와 역할을 분석하여 구체적인 실행 방안을 제시해 주세요.

**자연어 질의**:
1. IACS의 전략에서 SDTP가 달성해야할 목표는 뭐지? (original)
2. IACS 전략상 SDTP 패널의 목표가 무엇인가요? (similar1)
3. 선박설계기술패널이 달성해야 할 전략적 목표를 알려주세요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT subject, body, keywords, sent_time FROM agenda_chair WHERE (LOWER(subject) LIKE '%strategy%' OR LOWER(subject) LIKE '%strategic%' OR LOWER(body) LIKE '%sdtp%strategy%' OR LOWER(body) LIKE '%strategic%goal%') AND agenda_panel IN ('GPG', 'COUNCIL', 'SDTP') ORDER BY sent_time DESC LIMIT 10
```

**실행 결과**: 0개 행 반환

---

### 9. ✅ recent_sdtp_gpg_decisions

**카테고리**: decision_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: GPG의 SDTP 관련 결정사항을 분석하여 SDTP가 수행해야 할 후속 조치를 정리해 주세요.

**자연어 질의**:
1. 최근 SDTP와 관련해서 GPG에서 결정된 사항이 있나? (original)
2. GPG에서 SDTP 관련해서 최근 결정한 내용이 있나요? (similar1)
3. General Policy Group이 SDTP에 대해 내린 최근 결정사항을 알려주세요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT subject, body, sent_time, agenda_panel FROM agenda_chair WHERE agenda_panel = 'GPG' AND (LOWER(body) LIKE '%sdtp%' OR LOWER(subject) LIKE '%sdtp%' OR LOWER(body) LIKE '%ship design%') AND (LOWER(subject) LIKE '%decision%' OR LOWER(subject) LIKE '%agreed%' OR LOWER(body) LIKE '%decided%') AND ...
```

**실행 결과**: 0개 행 반환

---

### 10. ✅ agenda_technology_trend_analysis

**카테고리**: trend_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 의제와 관련된 기술 동향을 분석하여 현재 산업의 발전 방향과 미래 전망을 제시해 주세요.

**자연어 질의**:
1. {agenda}와 관련해서 현재 기술개발 동향 분석해줘 (original)
2. {agenda} 의제와 관련된 최신 기술 트렌드를 분석해주세요 (similar1)
3. {agenda} 주제의 현재 기술 발전 현황이 어떻게 되나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
WITH target_keywords AS (SELECT keywords FROM agenda_chair WHERE agenda_base_version = '{agenda}' LIMIT 1) SELECT c.agenda_code, c.subject, c.keywords, c.sent_time, c.agenda_panel FROM agenda_chair c, target_keywords t WHERE c.keywords LIKE '%' || t.keywords || '%' AND c.sent_time >= datetime('now',...
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | subject | keywords | sent_time | agenda_panel |
|---|---|---|---|---|
| PL24005_ILc | PL24005_ILc: Email thread d... | ["SDTP", "URs", "spreadshee... | 2025-05-16 18:03:26+00:00 | PL |

---

### 11. ✅ keywords_technology_trend_analysis

**카테고리**: trend_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 키워드와 관련된 기술 동향을 분석하여 현재 주요 이슈와 향후 발전 방향을 제시해 주세요.

**자연어 질의**:
1. {keywords} 관련해서 기술개발 동향 분석해줘 (original)
2. {keywords}에 대한 최신 기술 트렌드를 분석해주세요 (similar1)
3. {keywords} 분야의 현재 기술 발전 현황이 어떻게 되나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `keywords` (array)

**플레이스홀더**: `keywords_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, subject, keywords, sent_time, agenda_panel FROM agenda_chair WHERE ({keywords_condition}) AND sent_time >= datetime('now', '-180 days') ORDER BY sent_time DESC LIMIT 30
```

**실행 결과**: 13개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | subject | keywords | sent_time | agenda_panel |
|---|---|---|---|---|
| ENV25M005a | ENV25M005a: Urgent - Enviro... | ["conference", "urgent", "e... | 2025-07-20 00:45:24 | ENV |
| PL25M001a | PL25M001a: IACS Annual Meet... | ["meeting", "annual", "Pari... | 2025-06-15 00:45:24 | PL |
| PL25016_ILa | PL25016_ILa: IMO Expert Gro... | ["EGDH", "IMO", "SDTP", "re... | 2025-06-05 23:04:26+00:00 | PL |

---

### 12. ✅ agenda_ur_related_content_detail

**카테고리**: regulation_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 의제에서 언급된 UR을 찾아 해당 통일규칙의 내용과 적용 방법을 설명해 주세요.

**자연어 질의**:
1. {agenda}와 관련해서 UR 에 관련된 내용이 뭐지? (original)
2. {agenda} 의제에서 통일규칙(UR) 관련 내용을 찾아주세요 (similar1)
3. {agenda}와 관련된 UR 규정이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.subject, c.body as agenda_body, r.* FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_base_version = '{agenda}' ORDER BY c.agenda_version DESC LIMIT 1
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | subject | agenda_body | agenda_base_version | ABS |
|---|---|---|---|---|
| PL24005_ILc | PL24005_ILc: Email thread d... | PL24005_ILc: Email thread d... | PL24005 | PL24005_ABc: Email thread d... |

*참고: 전체 19개 컬럼 중 5개만 표시*

---

### 13. ✅ keywords_ur_related_content

**카테고리**: regulation_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 키워드와 관련된 UR들을 분석하여 적용되는 통일규칙과 요구사항을 정리해 주세요.

**자연어 질의**:
1. {keywords} 관련해서 UR에 관련된 내용이 뭐가 있지? (original)
2. {keywords}와 관련된 통일규칙(UR)을 찾아주세요 (similar1)
3. {keywords} 분야의 UR 규정이 어떤 게 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `keywords` (array)

**플레이스홀더**: `keywords_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, subject, body, keywords FROM agenda_chair WHERE ({keywords_condition}) AND (body LIKE '%UR%' OR body LIKE '%Unified Requirement%') ORDER BY sent_time DESC LIMIT 20
```

**실행 결과**: 11개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | subject | body | keywords |
|---|---|---|---|
| ENV25M005a | ENV25M005a: Urgent - Enviro... | URGENT NOTICE\n\nAn emergen... | ["conference", "urgent", "e... |
| PL25M001a | PL25M001a: IACS Annual Meet... | Dear Members,\n\nThis is to... | ["meeting", "annual", "Pari... |
| PL25016_ILa | PL25016_ILa: IMO Expert Gro... | PL25016_ILa: IMO Expert Gro... | ["EGDH", "IMO", "SDTP", "re... |

---

### 14. ✅ agenda_pr_related_content

**카테고리**: regulation_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 의제에서 언급된 PR을 찾아 해당 절차요건의 내용과 적용 방법을 설명해 주세요.

**자연어 질의**:
1. {agenda}와 관련해서 PR 에 관련된 내용이 뭐지? (original)
2. {agenda} 의제에서 절차요건(PR) 관련 내용을 찾아주세요 (similar1)
3. {agenda}와 관련된 PR 규정이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.subject, c.body as agenda_body, r.* FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_base_version = '{agenda}' ORDER BY c.agenda_version DESC LIMIT 1
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | subject | agenda_body | agenda_base_version | ABS |
|---|---|---|---|---|
| PL24005_ILc | PL24005_ILc: Email thread d... | PL24005_ILc: Email thread d... | PL24005 | PL24005_ABc: Email thread d... |

*참고: 전체 19개 컬럼 중 5개만 표시*

---

### 15. ✅ keywords_pr_related_content

**카테고리**: regulation_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 키워드와 관련된 PR들을 분석하여 적용되는 절차요건과 준수사항을 정리해 주세요.

**자연어 질의**:
1. {keywords} 관련해서 PR에 관련된 내용이 뭐가 있지? (original)
2. {keywords}와 관련된 절차요건(PR)을 찾아주세요 (similar1)
3. {keywords} 분야의 PR 규정이 어떤 게 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `keywords` (array)

**플레이스홀더**: `keywords_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, subject, body, keywords FROM agenda_chair WHERE ({keywords_condition}) AND (body LIKE '%PR%' OR body LIKE '%Procedural Requirement%') ORDER BY sent_time DESC LIMIT 20
```

**실행 결과**: 10개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | subject | body | keywords |
|---|---|---|---|
| PL25016_ILa | PL25016_ILa: IMO Expert Gro... | PL25016_ILa: IMO Expert Gro... | ["EGDH", "IMO", "SDTP", "re... |
| PL25007bILa | PL25007bILa IMO FAL Corresp... | PL25007bILa IMO FAL Corresp... | ["IMO", "digitalization", "... |
| PL24005_ILc | PL24005_ILc: Email thread d... | PL24005_ILc: Email thread d... | ["SDTP", "URs", "spreadshee... |

---

### 16. ✅ agenda_similar_discussion_other_panels

**카테고리**: related_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 다른 패널의 유사 논의를 분석하여 공통된 접근 방식과 차별화된 관점을 정리해 주세요.

**자연어 질의**:
1. {agenda} 에서 다른 패널에서 유사한 논의가 진행된적 있는지? (original)
2. {agenda} 주제가 다른 패널에서도 논의된 적이 있나요? (similar1)
3. {agenda}와 비슷한 내용을 타 위원회에서 다룬 적이 있는지 확인해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
WITH target_info AS (SELECT keywords, subject, agenda_panel FROM agenda_chair WHERE agenda_base_version = '{agenda}' LIMIT 1) SELECT c.agenda_code, c.subject, c.keywords, c.sent_time, c.agenda_panel, c.decision_status FROM agenda_chair c, target_info t WHERE c.agenda_panel != t.agenda_panel AND (c.k...
```

**실행 결과**: 0개 행 반환

---

### 17. ✅ autonomous_ship_agendas

**카테고리**: keyword_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 자율운항선박 관련 의제들을 분석하여 기술 발전 단계와 규제 논의 현황을 정리해 주세요.

**자연어 질의**:
1. 자율운항선박에 대해서 논의되고 있는 {agenda} 검색해줘 (original)
2. 자율운항선박 관련 의제들을 찾아주세요 (similar1)
3. MASS(자율운항선박)에 대한 논의 안건이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, keywords, sent_time, agenda_panel, decision_status FROM agenda_chair WHERE (LOWER(subject) LIKE '%autonomous%' OR LOWER(subject) LIKE '%mass%' OR LOWER(body) LIKE '%autonomous ship%' OR LOWER(body) LIKE '%자율운항%' OR keywords LIKE '%MASS%') ORDER BY se...
```

**실행 결과**: 4개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | keywords | sent_time |
|---|---|---|---|---|
| PS25003pPLa | PS25003p | PS25003pPLa MSC 110 (18-27 ... | ["SDTP", "MASS", "cybersecu... | 2025-07-03 10:12:30+00:00 |
| PL25017_ILa | PL25017 | PL25017_ILa - ISO TC8 SC26 ... | ["ISO", "TC8", "SC26", "IAC... | 2025-06-09 18:28:07+00:00 |
| PL25008cILa | PL25008c | PL25008cILa: IMO MSC 110 Pa... | ["MASS", "cybersecurity", "... | 2025-05-13 21:17:53+00:00 |

*참고: 전체 7개 컬럼 중 5개만 표시*

---

### 18. ✅ remote_ship_agendas

**카테고리**: keyword_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 원격운항선박 관련 의제들을 분석하여 기술적 과제와 안전 규정 논의 현황을 정리해 주세요.

**자연어 질의**:
1. 원격운항선박에 대해서 논의되고 있는 {agenda} 검색해줘 (original)
2. 원격운항선박 관련 의제들을 찾아주세요 (similar1)
3. 원격 제어 선박에 대한 논의 안건이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, keywords, sent_time, agenda_panel, decision_status FROM agenda_chair WHERE (LOWER(subject) LIKE '%remote%' OR LOWER(body) LIKE '%remote control%' OR LOWER(body) LIKE '%remote operation%' OR LOWER(body) LIKE '%원격운항%' OR keywords LIKE '%remote%ship%') ...
```

**실행 결과**: 0개 행 반환

---

### 19. ✅ sdtp_eg_work_list

**카테고리**: expert_group
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: SDTP의 Expert Group 활동을 분석하여 주요 작업 내용과 성과를 정리해 주세요.

**자연어 질의**:
1. SDTP 에서 진행된 EG 작업 알려줘 (original)
2. SDTP 패널의 Expert Group 활동 목록을 보여주세요 (similar1)
3. 선박설계기술패널에서 진행한 EG 작업이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, subject, body, sent_time, decision_status FROM agenda_chair WHERE agenda_panel = 'SDTP' AND (LOWER(subject) LIKE '%expert group%' OR LOWER(subject) LIKE '%eg %' OR LOWER(body) LIKE '%expert group%' OR keywords LIKE '%EG%') ORDER BY sent_time DESC
```

**실행 결과**: 0개 행 반환

---

### 20. ✅ sdtp_eg_progress_details

**카테고리**: expert_group
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: SDTP Expert Group의 진행 상황을 분석하여 주요 마일스톤과 달성 사항을 정리해 주세요.

**자연어 질의**:
1. SDTP 에서 진행된 EG의 주요 진행 사항에 대해서 설명해줘 (original)
2. SDTP Expert Group의 진행 상황을 상세히 설명해주세요 (similar1)
3. 선박설계기술패널 EG 작업 진척도가 어떻게 되나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT subject, body, keywords, sent_time, decision_status FROM agenda_chair WHERE agenda_panel = 'SDTP' AND (LOWER(subject) LIKE '%expert group%' OR LOWER(subject) LIKE '%eg %') AND (LOWER(body) LIKE '%progress%' OR LOWER(body) LIKE '%status%' OR LOWER(body) LIKE '%update%') ORDER BY sent_time DESC...
```

**실행 결과**: 0개 행 반환

---

### 21. ❌ keyword_technical_background

**카테고리**: technical_info
**상태**: 실패
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 키워드가 언급된 의제들을 분석하여 기술적 배경과 발전 과정을 설명해 주세요.

**자연어 질의**:
1. {keyword} 에 대한 기술 배경이 뭐지? (original)
2. 이 키워드의 기술적 배경 설명을 찾아주세요 (similar1)
3. 특정 기술 용어가 논의된 맥락과 배경이 궁금합니다 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `keyword` (string)
  - `period` (period) - 기본값: {'type': 'relative', 'days': 365}

**플레이스홀더**: `keyword, period_condition`

**SQL 쿼리**:
```sql
SELECT 
                    c.agenda_code,
                    c.agenda_base_version,
                    c.subject,
                    c.agenda_panel,
                    c.sent_time,
                    c.body as content,
                    c.keywords
                FROM agenda_chair c
        ...
```

**오류 내용**: Unsubstituted placeholders: ['keyword', 'keyword', 'keyword']

**실행 시도한 쿼리**:
```sql
SELECT 
                    c.agenda_code,
                    c.agenda_base_version,
                    c.subject,
                    c.agenda_panel,
                    c.sent_time,
                    c.body as content,
                    c.keywords
                FROM agenda_chair c
                WHERE (c.subject LIKE '%{keyword}%' 
                    OR c.body LIKE '%{keyword}%' 
                    OR c.keywords LIKE '%{keyword}%')
                AND sent_time >= DATE('now', '-30 d...
```

---


## 테스트 설정

- **파일**: query_templates_group_008.json
- **테스트 일시**: 2025-07-30T11:05:25.240102
- **데이터베이스 경로**: data/iacsgraph.db
