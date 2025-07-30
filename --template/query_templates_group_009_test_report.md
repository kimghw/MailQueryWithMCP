# query_templates_group_009.json 테스트 보고서

**테스트 일시**: 2025-07-30T11:05:25.248791
**데이터베이스**: data/iacsgraph.db

## 요약

- **전체 템플릿 수**: 13
- **성공**: 13 (100.0%)
- **실패**: 0

### 카테고리별 결과

| 카테고리 | 전체 | 성공 | 실패 | 성공률 |
|----------|------|------|------|--------|
| meeting | 2 | 2 | 0 | 100.0% |
| project_team | 6 | 6 | 0 | 100.0% |
| response_tracking | 2 | 2 | 0 | 100.0% |
| keyword_analysis | 3 | 3 | 0 | 100.0% |

## 상세 결과

### 1. ✅ agenda_meeting_attendance_by_date

**카테고리**: meeting
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 각 기관의 회의 참석 가능 여부를 날짜별로 분석하여 최적의 회의 일정을 제안해 주세요.

**자연어 질의**:
1. {agenda} 에서 날짜별 회의에 참석할 수 있는 기관과 참석할 수 있는 기관을 정리해줘 (original)
2. {agenda} 의제의 회의 일정별로 참석 가능한 기관들을 정리해주세요 (similar1)
3. {agenda} 회의 날짜별 참석 가능/불가능 기관 리스트를 보여줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.subject, c.body, r.* FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.agenda_base_version = '{agenda}' AND (LOWER(c.subject) LIKE '%meeting%' OR LOWER(c.body) LIKE '%attendance%' OR LOWER(c.body) LIKE '%particip...
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | subject | body | agenda_base_version | ABS |
|---|---|---|---|---|
| PL24005_ILc | PL24005_ILc: Email thread d... | PL24005_ILc: Email thread d... | PL24005 | PL24005_ABc: Email thread d... |

*참고: 전체 19개 컬럼 중 5개만 표시*

---

### 2. ✅ agenda_org_attendance_summary

**카테고리**: meeting
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 각 기관의 회의 참석 가능 여부를 표로 정리하고 참석률이 높은 일정을 추천해 주세요.

**자연어 질의**:
1. {agenda} 에서 기관별 회의 참석 가능여부 정리해줘 (original)
2. {agenda} 의제 회의에 각 기관이 참석 가능한지 정리해주세요 (similar1)
3. {agenda} 미팅에 어떤 조직이 참가할 수 있는지 확인해줘 (similar2)
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

### 3. ✅ current_pt_list_panel

**카테고리**: project_team
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 현재 진행 중인 Project Team들을 패널별로 분류하고 각 팀의 목표와 진행 상황을 정리해 주세요.

**자연어 질의**:
1. 현재 진행 중인 PT 리스트 (original)
2. 현재 활동 중인 프로젝트 팀 목록을 보여주세요 (similar1)
3. 진행 중인 PT들이 어떤 것들이 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, subject, keywords, sent_time, agenda_panel, decision_status FROM agenda_chair WHERE (LOWER(subject) LIKE '%project team%' OR LOWER(subject) LIKE '%pt %' OR keywords LIKE '%PT%') AND deadline IS NOT NULL AND deadline > datetime('now') ORDER BY agenda_panel, sent_time DESC
```

**실행 결과**: 0개 행 반환

---

### 4. ✅ current_pt_participating_orgs_detail

**카테고리**: project_team
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 각 Project Team의 참여 기관 구성을 분석하여 협력 네트워크를 시각화해 주세요.

**자연어 질의**:
1. 현재 진행 중인 PT의 참여기관 (original)
2. 활동 중인 프로젝트 팀에 참여하는 기관들을 보여주세요 (similar1)
3. 진행 중인 PT별 참가 조직이 어디어디인가요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.subject as pt_name, c.agenda_panel, r.* FROM agenda_chair c JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE (LOWER(c.subject) LIKE '%project team%' OR LOWER(c.subject) LIKE '%pt %') AND c.deadline IS NOT NULL AND c.deadline > datetime('n...
```

**실행 결과**: 0개 행 반환

---

### 5. ✅ current_pt_participants_info

**카테고리**: project_team
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: Project Team 참여자들의 전문성을 분석하여 각 팀의 역량을 평가해 주세요.

**자연어 질의**:
1. 현재 진행 중인 PT의 참여자 정보 알려줘 (original)
2. 활동 중인 프로젝트 팀 참가자들의 정보를 보여주세요 (similar1)
3. 진행 중인 PT별 참여 인원이 누구누구인가요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, subject, body, agenda_panel FROM agenda_chair WHERE (LOWER(subject) LIKE '%project team%' OR LOWER(subject) LIKE '%pt %') AND (LOWER(body) LIKE '%participant%' OR LOWER(body) LIKE '%member%' OR LOWER(body) LIKE '%expert%') AND deadline IS NOT NULL AND deadline > datetime('now') O...
```

**실행 결과**: 0개 행 반환

---

### 6. ✅ current_pt_key_content

**카테고리**: project_team
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 각 Project Team의 핵심 업무를 분석하여 예상되는 영향과 기대 효과를 평가해 주세요.

**자연어 질의**:
1. 현재 진행 중인 PT의 중요 내용은 (original)
2. 활동 중인 프로젝트 팀의 핵심 업무 내용을 보여주세요 (similar1)
3. 진행 중인 PT들의 주요 과제가 뭐인가요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, subject, body, keywords, agenda_panel, sent_time FROM agenda_chair WHERE (LOWER(subject) LIKE '%project team%' OR LOWER(subject) LIKE '%pt %') AND deadline IS NOT NULL AND deadline > datetime('now') AND mail_type = 'REQUEST' ORDER BY agenda_panel, sent_time DESC
```

**실행 결과**: 0개 행 반환

---

### 7. ✅ recent_completed_pt_list_panel

**카테고리**: project_team
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 완료된 Project Team들의 성과를 패널별로 분석하고 주요 성공 사례를 정리해 주세요.

**자연어 질의**:
1. 최근 완료된 PT 리스트 알려줘 (original)
2. 최근에 종료된 프로젝트 팀 목록을 보여주세요 (similar1)
3. 완료된 PT들이 어떤 것들이 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, subject, keywords, sent_time, agenda_panel FROM agenda_chair WHERE (LOWER(subject) LIKE '%project team%' OR LOWER(subject) LIKE '%pt %') AND deadline IS NOT NULL AND deadline <= datetime('now') AND sent_time >= datetime('now', '-90 days') ORDER BY sent_time DESC
```

**실행 결과**: 0개 행 반환

---

### 8. ✅ recent_completed_pt_achievements

**카테고리**: project_team
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 완료된 Project Team들의 주요 성과와 산출물을 분석하여 IACS에 미친 영향을 평가해 주세요.

**자연어 질의**:
1. 최근 완료된 PT의 주요 내용 알려줘 (original)
2. 최근 종료된 프로젝트 팀의 핵심 성과를 보여주세요 (similar1)
3. 완료된 PT들이 달성한 주요 결과가 뭐인가요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, subject, body, keywords, sent_time, agenda_panel FROM agenda_chair WHERE (LOWER(subject) LIKE '%project team%' OR LOWER(subject) LIKE '%pt %') AND deadline IS NOT NULL AND deadline <= datetime('now') AND (LOWER(body) LIKE '%final%' OR LOWER(body) LIKE '%result%' OR LOWER(body) LI...
```

**실행 결과**: 0개 행 반환

---

### 9. ✅ agenda_asking_response_orgs

**카테고리**: response_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 각 기관의 응답을 분석하여 다른 기관에게 답변을 요구한 사례와 그 이유를 파악해 주세요.

**자연어 질의**:
1. {agenda} 에서 다른 기관에 답변을 요구한 기관이 있는가? (original)
2. {agenda} 의제에서 타 기관에 응답을 요청한 조직이 있나요? (similar1)
3. {agenda}에서 다른 기관에게 회신을 요구한 곳이 있는지 확인해줘 (similar2)
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

### 10. ✅ agenda_clarification_requests

**카테고리**: response_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 의장 메일(chair_body)과 각 기관의 응답 내용을 상세히 분석하여 다음 사항을 파악해 주세요:
1. 특정 기관에게 명확화(clarification), 추가 설명, 구체적 답변을 요구하는 내용이 있는지 확인
2. 요구사항이 있다면 어떤 기관이 어떤 기관에게 무엇을...

**자연어 질의**:
1. {agenda} 에서 다른 기관에 답변 또는 명확화를 요구하는 내용이 있나? (original)
2. {agenda} 의제에서 타 기관에 설명을 요청한 내용이 있나요? (similar1)
3. {agenda}에서 다른 조직에게 명확한 답변을 요구한 부분이 있는지 확인해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `agenda` (string)

**플레이스홀더**: `agenda`

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.agenda_base_version, c.subject, c.body as chair_body, c.sent_time, c.sender_organization, c.decision_status, c.agenda_panel, r.ABS, r.BV, r.CCS, r.CRS, r.DNV, r.IRS, r.KR, r.NK, r.PRS, r.RINA, r.IL, r.TL, r.LR FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agen...
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | chair_body | sent_time |
|---|---|---|---|---|
| PL24005_ILc | PL24005 | PL24005_ILc: Email thread d... | PL24005_ILc: Email thread d... | 2025-05-16 18:03:26+00:00 |

*참고: 전체 21개 컬럼 중 5개만 표시*

---

### 11. ✅ 3months_keyword_analysis_panel

**카테고리**: keyword_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 3개월간 키워드 트렌드를 패널별로 분석하여 각 패널의 주요 관심사와 전체적인 동향을 파악해 주세요.

**자연어 질의**:
1. 3개월 내 주요 키워드 분석해줘 (original)
2. 최근 3개월간 자주 언급된 키워드를 분석해주세요 (similar1)
3. 지난 90일 동안의 주요 단어들이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT keywords, agenda_panel, COUNT(*) as frequency FROM agenda_chair WHERE keywords IS NOT NULL AND keywords != '' AND sent_time >= datetime('now', '-3 months') GROUP BY keywords, agenda_panel ORDER BY frequency DESC LIMIT 50
```

**실행 결과**: 36개 행 반환

**샘플 데이터** (최대 3행):

| keywords | agenda_panel | frequency |
|---|---|---|
| ["3D", "Model", "Exchange",... | PL | 1 |
| ["AI", "안전", "자동화", "선박"] | TEST | 1 |
| ["EGDH", "IMO", "SDTP", "re... | PL | 1 |

---

### 12. ✅ last_year_keyword_analysis_detail

**카테고리**: keyword_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 작년 키워드 트렌드를 월별로 분석하여 연간 주요 이슈의 변화 패턴과 계절적 특성을 설명해 주세요.

**자연어 질의**:
1. 작년 주요 키워드 분석해줘 (original)
2. 지난해 자주 언급된 키워드를 분석해주세요 (similar1)
3. 작년도 핵심 단어들이 뭐가 있었나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT keywords, strftime('%m', sent_time) as month, COUNT(*) as frequency FROM agenda_chair WHERE keywords IS NOT NULL AND keywords != '' AND strftime('%Y', sent_time) = strftime('%Y', 'now', '-1 year') GROUP BY keywords, month ORDER BY frequency DESC LIMIT 50
```

**실행 결과**: 0개 행 반환

---

### 13. ✅ 2025_keyword_analysis_current

**카테고리**: keyword_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 2025년 현재까지의 키워드 트렌드를 분석하여 올해의 주요 이슈와 각 패널의 우선순위를 파악하고 향후 전망을 제시해 주세요.

**자연어 질의**:
1. 2025년 주요 키워드 분석해줘 (original)
2. 2025년에 자주 언급된 키워드를 분석해주세요 (similar1)
3. 올해 들어 핵심 단어들이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT keywords, agenda_panel, COUNT(*) as frequency FROM agenda_chair WHERE keywords IS NOT NULL AND keywords != '' AND strftime('%Y', sent_time) = '2025' GROUP BY keywords, agenda_panel ORDER BY frequency DESC LIMIT 50
```

**실행 결과**: 40개 행 반환

**샘플 데이터** (최대 3행):

| keywords | agenda_panel | frequency |
|---|---|---|
| ["3D", "Model", "Exchange",... | PL | 1 |
| ["AI", "안전", "자동화", "선박"] | TEST | 1 |
| ["EGDH", "IMO", "SDTP", "re... | PL | 1 |

---


## 테스트 설정

- **파일**: query_templates_group_009.json
- **테스트 일시**: 2025-07-30T11:05:25.248791
- **데이터베이스 경로**: data/iacsgraph.db
