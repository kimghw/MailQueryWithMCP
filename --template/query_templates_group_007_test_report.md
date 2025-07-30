# query_templates_group_007.json 테스트 보고서

**테스트 일시**: 2025-07-30T11:05:25.233052
**데이터베이스**: data/iacsgraph.db

## 요약

- **전체 템플릿 수**: 17
- **성공**: 16 (94.1%)
- **실패**: 1

### 카테고리별 결과

| 카테고리 | 전체 | 성공 | 실패 | 성공률 |
|----------|------|------|------|--------|
| keyword_search | 1 | 1 | 0 | 100.0% |
| related_analysis | 4 | 4 | 0 | 100.0% |
| specific_agenda | 4 | 4 | 0 | 100.0% |
| meeting | 3 | 3 | 0 | 100.0% |
| opinion_analysis | 2 | 2 | 0 | 100.0% |
| keyword_analysis | 1 | 0 | 1 | 0.0% |
| response_tracking | 2 | 2 | 0 | 100.0% |

## 상세 결과

### 1. ✅ recent_eg_related_content

**카테고리**: keyword_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: EG 관련 내용이 언급된 맥락을 분석하여 현재 진행 중인 Expert Group 활동을 파악해 주세요.

**자연어 질의**:
1. 최근 아젠다나 응답 중에서 EG 와 관련된 내용이 있나 (original)
2. 최근 의제나 회신에서 Expert Group 관련 내용이 있었나요? (similar1)
3. EG(전문가 그룹) 언급한 최근 안건이나 응답이 있는지 확인해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.subject, c.sent_time, c.agenda_panel, CASE WHEN c.body LIKE '%EG%' OR c.body LIKE '%Expert Group%' THEN 'Agenda' ELSE 'Response' END as source FROM agenda_chair c WHERE (c.body LIKE '%EG%' OR c.body LIKE '%Expert Group%' OR c.keywords LIKE '%EG%') AND {period_condition} UNION...
```

**실행 결과**: 4개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | subject | sent_time | agenda_panel | source |
|---|---|---|---|---|
| ENV25M005a | ENV25M005a: Urgent - Enviro... | 2025-07-20 00:45:24 | ENV | Agenda |
| PS25003pPLa | PS25003pPLa MSC 110 (18-27 ... | 2025-07-03 10:12:30+00:00 | PS | Agenda |
| PL25008eILa | PL25008eILa: IMO MSC 110 - ... | 2025-07-03 10:06:25+00:00 | PL | Agenda |

---

### 2. ✅ pl26034_issue_related_agendas

**카테고리**: related_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: PL26034의 주요 이슈를 분석하고 관련된 다른 의제들과의 연관성을 설명해 주세요.

**자연어 질의**:
1. PL26034 의 아젠다에서 주요 이슈와 관련된 아젠다 리스트를 제공해줘 (original)
2. PL26034 의제의 핵심 이슈와 연관된 다른 의제들을 찾아주세요 (similar1)
3. PL26034 안건의 주요 쟁점과 관련 있는 아젠다 목록을 보여줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
WITH target_agenda AS (SELECT keywords, subject, body FROM agenda_chair WHERE agenda_code = 'PL26034' LIMIT 1) SELECT c.agenda_code, c.subject, c.keywords, c.sent_time, c.agenda_panel FROM agenda_chair c, target_agenda t WHERE c.agenda_code != 'PL26034' AND (c.keywords LIKE '%' || t.keywords || '%' ...
```

**실행 결과**: 0개 행 반환

---

### 3. ✅ pl25934_ur_content

**카테고리**: specific_agenda
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: PL25934에서 UR 관련 내용을 분석하여 어떤 통일규칙이 논의되고 있는지 설명해 주세요.

**자연어 질의**:
1. PL25934 에서 UR과 관련된 내용이 있냐? (original)
2. PL25934 의제에 통일규칙(UR) 관련 내용이 포함되어 있나요? (similar1)
3. PL25934 안건에서 UR 언급된 부분이 있는지 확인해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.subject, c.body, c.keywords FROM agenda_chair c WHERE c.agenda_code = 'PL25934' AND (c.body LIKE '%UR%' OR c.body LIKE '%Unified Requirement%' OR c.keywords LIKE '%UR%') ORDER BY c.agenda_version DESC LIMIT 1
```

**실행 결과**: 0개 행 반환

---

### 4. ✅ pl25302_imo_content

**카테고리**: specific_agenda
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: PL25302에서 IMO 관련 내용을 분석하여 어떤 IMO 규정이나 지침이 논의되고 있는지 설명해 주세요.

**자연어 질의**:
1. PL25302 에서 IMO관련된 내용이 있나? (original)
2. PL25302 의제에 국제해사기구(IMO) 관련 내용이 포함되어 있나요? (similar1)
3. PL25302 안건에서 IMO 언급된 부분이 있는지 확인해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.subject, c.body, c.keywords FROM agenda_chair c WHERE c.agenda_code = 'PL25302' AND (c.body LIKE '%IMO%' OR c.keywords LIKE '%IMO%') ORDER BY c.agenda_version DESC LIMIT 1
```

**실행 결과**: 0개 행 반환

---

### 5. ✅ pl25016_completed_status

**카테고리**: specific_agenda
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: PL25016의 완료 여부와 현재 상태를 설명하고, 완료되었다면 최종 결과를 요약해 주세요.

**자연어 질의**:
1. PL25016 의제는 현재 종료되었는가? (original)
2. PL25016 안건이 완료되었나요? (similar1)
3. PL25016이 이미 마무리되었는지 확인해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, decision_status, sent_time, sent_time, deadline, CASE WHEN deadline IS NOT NULL AND deadline <= datetime('now') THEN 'Yes' ELSE 'No' END as is_completed FROM agenda_chair WHERE agenda_code = 'PL25016' ORDER BY agenda_version DESC LIMIT 1
```

**실행 결과**: 0개 행 반환

---

### 6. ✅ pl25034_issue_summary

**카테고리**: specific_agenda
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: PL25034의 내용을 분석하여 핵심 이슈와 기술적 쟁점을 파악하고 중요도를 평가해 주세요.

**자연어 질의**:
1. PL25034 아젠다의 중요 이슈는 뭐지? (original)
2. PL25034 의제의 핵심 쟁점이 무엇인가요? (similar1)
3. PL25034 안건에서 다루는 주요 이슈를 알려줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, subject, body, keywords, sent_time, agenda_panel FROM agenda_chair WHERE agenda_code = 'PL25034' ORDER BY agenda_version DESC LIMIT 1
```

**실행 결과**: 0개 행 반환

---

### 7. ✅ pl25034_previous_discussion

**카테고리**: related_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: PL25034와 관련된 이전 논의들을 분석하여 주제의 발전 과정과 논의 배경을 설명해 주세요.

**자연어 질의**:
1. PL25034와 관련해서 이전에 논의된 적이 있나? (original)
2. PL25034 주제가 과거에 다뤄진 적이 있나요? (similar1)
3. PL25034와 유사한 내용이 이전에 논의되었는지 확인해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
WITH target_info AS (SELECT keywords, subject, sent_time, agenda_panel FROM agenda_chair WHERE agenda_code = 'PL25034' LIMIT 1) SELECT c.agenda_code, c.subject, c.keywords, c.sent_time, c.agenda_panel FROM agenda_chair c, target_info t WHERE c.sent_time < t.sent_time AND (c.keywords LIKE '%' || t.ke...
```

**실행 결과**: 0개 행 반환

---

### 8. ✅ pl25034_other_panel_discussion

**카테고리**: related_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: PL25034와 관련하여 다른 패널에서 진행 중인 논의를 분석하고 패널 간 협력 필요성을 평가해 주세요.

**자연어 질의**:
1. PL25034와 관련해서 다른 패널에서 논의되고 있는 패널이 있나? (original)
2. PL25034 주제가 다른 패널에서도 다뤄지고 있나요? (similar1)
3. PL25034와 유사한 내용을 논의하는 다른 위원회가 있는지 확인해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
WITH target_info AS (SELECT keywords, subject, agenda_panel FROM agenda_chair WHERE agenda_code = 'PL25034' LIMIT 1) SELECT c.agenda_panel, COUNT(*) as agenda_count, GROUP_CONCAT(c.agenda_code) as related_agendas FROM agenda_chair c, target_info t WHERE c.agenda_panel != t.agenda_panel AND c.deadlin...
```

**실행 결과**: 0개 행 반환

---

### 9. ✅ pl25034_other_panel_agendas

**카테고리**: related_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: PL25034와 관련된 다른 패널의 의제들을 분석하여 공통 이슈와 차이점을 설명해 주세요.

**자연어 질의**:
1. PL25034와 관련해서 다른 패널에서 논의되고 있는 아젠다가 있나? (original)
2. PL25034 주제와 연관된 다른 패널의 의제들을 찾아주세요 (similar1)
3. PL25034와 유사한 내용의 타 패널 안건이 있는지 확인해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
WITH target_info AS (SELECT keywords, subject, agenda_panel FROM agenda_chair WHERE agenda_code = 'PL25034' LIMIT 1) SELECT c.agenda_code, c.subject, c.keywords, c.sent_time, c.agenda_panel, c.decision_status FROM agenda_chair c, target_info t WHERE c.agenda_panel != t.agenda_panel AND (c.keywords L...
```

**실행 결과**: 0개 행 반환

---

### 10. ✅ recent_meeting_list_panel

**카테고리**: meeting
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 최근 진행된 회의들을 패널별로 정리하고 주요 안건을 요약해 주세요.

**자연어 질의**:
1. 최근 진행된 회의 리스트 (original)
2. 최근에 개최된 회의 목록을 보여주세요 (similar1)
3. 지난 기간 동안 진행된 미팅들이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT subject, sent_time, agenda_panel, body FROM agenda_chair WHERE mail_type = 'NOTIFICATION' AND (LOWER(subject) LIKE '%meeting%' OR LOWER(subject) LIKE '%회의%' OR LOWER(body) LIKE '%minutes%') AND {period_condition} ORDER BY sent_time DESC
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| subject | sent_time | agenda_panel | body |
|---|---|---|---|
| GEN25M002a: Technical Commi... | 2025-06-30 00:45:24 | GEN | Subject: Technical Committe... |

---

### 11. ✅ recent_meeting_key_issues

**카테고리**: meeting
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 회의에서 논의된 주요 이슈와 결정사항을 분석하여 각 패널의 주요 성과를 정리해 주세요.

**자연어 질의**:
1. 최근 진행된 회의의 주요 이슈 및 결정사항은? (original)
2. 최근 회의에서 다뤄진 핵심 안건과 결정사항을 보여주세요 (similar1)
3. 지난 미팅의 중요 이슈와 결과가 뭐였나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT subject, body, sent_time, agenda_panel FROM agenda_chair WHERE mail_type = 'NOTIFICATION' AND (LOWER(subject) LIKE '%minutes%' OR LOWER(subject) LIKE '%decision%' OR LOWER(subject) LIKE '%outcome%' OR LOWER(body) LIKE '%decision%') AND {period_condition} ORDER BY sent_time DESC
```

**실행 결과**: 0개 행 반환

---

### 12. ✅ agenda_meeting_alignment_check

**카테고리**: meeting
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 의제 내용과 이전 회의 결정사항을 비교하여 일관성과 부합 여부를 평가해 주세요.

**자연어 질의**:
1. {agenda} 가 최근 회의 결과와 부합하는가? (original)
2. {agenda} 의제가 최근 회의 결정사항과 일치하나요? (similar1)
3. {agenda} 안건이 지난 미팅 결과와 맞는지 확인해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
WITH target_agenda AS (SELECT agenda_panel, sent_time, keywords, subject FROM agenda_chair WHERE agenda_base_version = '{agenda}' LIMIT 1) SELECT c.subject, c.body, c.sent_time FROM agenda_chair c, target_agenda t WHERE c.agenda_panel = t.agenda_panel AND c.mail_type = 'NOTIFICATION' AND (LOWER(c.su...
```

**실행 결과**: 0개 행 반환

---

### 13. ✅ agenda_opinion_analysis

**카테고리**: opinion_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 모든 기관의 응답을 분석하여 주요 입장을 분류하고, 합의점과 대립점을 파악하여 향후 논의 방향을 제시해 주세요.

**자연어 질의**:
1. {agenda} 지금 까지 응답한 의견을 분석해줘 (original)
2. {agenda} 의제에 대한 모든 기관의 응답을 분석해주세요 (similar1)
3. {agenda} 안건의 각 조직별 의견을 종합 분석해줘 (similar2)
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

### 14. ✅ mail_content_agenda_opinion_comparison

**카테고리**: opinion_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 제공된 메일 내용과 기존 응답들을 비교 분석하여 새로운 관점이나 상충되는 의견을 파악해 주세요.

**자연어 질의**:
1. {mail_content} 가 {agenda}에서 지금 까지 응답한 의견과 동일한 부분 상반되는 부분 검토해줘 (original)
2. {mail_content}의 내용이 {agenda} 의제의 기존 응답들과 어떻게 다른지 비교해주세요 (similar1)
3. {mail_content}와 {agenda} 안건의 타 기관 의견 비교 분석해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)
  - `mail_content` (string)

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

### 15. ❌ recent_org_keyword_perspective

**카테고리**: keyword_analysis
**상태**: 실패
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 해당 조직이 키워드 관련 이슈에 대해 보인 일관된 관점과 입장 변화를 분석해 주세요.

**자연어 질의**:
1. 최근 {organization}에서 {keywords} 관련해서 어떤 관점을 갖고 있는가? (original)
2. {organization}이 최근 {keywords}에 대해 어떤 입장을 보이고 있나요? (similar1)
3. {organization}의 {keywords} 관련 최근 견해가 뭐인가요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string)
  - `keywords` (array)
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `keywords_condition, organization, period_condition`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.subject, c.sent_time, r.{organization} as opinion FROM agenda_chair c JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE r.{organization} IS NOT NULL AND ({keywords_condition}) AND {period_condition} ORDER BY c.sent_time DESC
```

**오류 내용**: Unsubstituted placeholders: ['organization', 'organization']

**실행 시도한 쿼리**:
```sql
SELECT c.agenda_code, c.subject, c.sent_time, r.{organization} as opinion FROM agenda_chair c JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE r.{organization} IS NOT NULL AND ((keywords LIKE '%PR%' OR subject LIKE '%PR%' OR keywords LIKE '%EG%' OR subject LIKE '%EG%')) AND sent_time >= DATE('now', '-30 days') ORDER BY c.sent_time DESC
```

---

### 16. ✅ sdtp_ongoing_responded_organizations

**카테고리**: response_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: SDTP 진행 중인 의제별 응답 현황을 분석하고 응답률을 계산해 주세요.

**자연어 질의**:
1. 진행 중인 의제에서 SDTP 에서 현재 응답을 한 기관은? (original)
2. SDTP 패널의 진행중인 안건에 이미 회신한 조직들을 보여주세요 (similar1)
3. 선박설계기술패널에서 현재 진행 중인 의제에 답변한 기관 리스트가 필요해요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT 
                    c.agenda_code,
                    c.agenda_base_version,
                    c.subject,
                    c.deadline,
                    GROUP_CONCAT(
                        CASE 
                            WHEN rc.ABS IS NOT NULL THEN 'ABS'
                        ...
```

**실행 결과**: 0개 행 반환

---

### 17. ✅ sdtp_ongoing_not_responded_organizations

**카테고리**: response_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: SDTP 의제별 미응답 기관들을 분석하고 긴급도에 따라 정리해 주세요.

**자연어 질의**:
1. SDTP 에서 현재 응답을 아직 하지 않은 기관은? (original)
2. SDTP 패널에서 미응답 상태인 조직들을 보여주세요 (similar1)
3. 선박설계기술패널의 진행 의제에 아직 답변 안 한 기관이 어디인가요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
WITH sdtp_ongoing AS (
                    SELECT 
                        c.agenda_code,
                        c.agenda_base_version,
                        c.subject,
                        c.deadline,
                        CASE WHEN rc.ABS IS NULL THEN 'ABS' END as ABS_pending,
            ...
```

**실행 결과**: 0개 행 반환

---


## 테스트 설정

- **파일**: query_templates_group_007.json
- **테스트 일시**: 2025-07-30T11:05:25.233052
- **데이터베이스 경로**: data/iacsgraph.db
