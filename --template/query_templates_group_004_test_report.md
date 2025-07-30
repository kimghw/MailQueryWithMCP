# query_templates_group_004.json 테스트 보고서

**테스트 일시**: 2025-07-30T11:05:25.212142
**데이터베이스**: data/iacsgraph.db

## 요약

- **전체 템플릿 수**: 12
- **성공**: 12 (100.0%)
- **실패**: 0

### 카테고리별 결과

| 카테고리 | 전체 | 성공 | 실패 | 성공률 |
|----------|------|------|------|--------|
| organization_info | 5 | 5 | 0 | 100.0% |
| meeting | 2 | 2 | 0 | 100.0% |
| keyword_analysis | 3 | 3 | 0 | 100.0% |
| agenda_status | 2 | 2 | 0 | 100.0% |

## 상세 결과

### 1. ✅ iacs_panel_structure

**카테고리**: organization_info
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: IACS 패널 구조와 각 패널의 역할, 활동 수준을 분석하여 설명해 주세요.

**자연어 질의**:
1. IACS의 내부의 패널 구성은 어떻게 되나? (original)
2. IACS 패널들이 어떻게 구성되어 있나요? (similar1)
3. 국제선급연합회의 위원회 구조를 보여주세요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT DISTINCT agenda_panel, COUNT(DISTINCT agenda_code) as agenda_count FROM agenda_chair GROUP BY agenda_panel ORDER BY agenda_count DESC
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| agenda_panel | agenda_count |
|---|---|
| PL | 28 |
| JWG-CS | 3 |
| TEST | 2 |

---

### 2. ✅ kr_participating_panels

**카테고리**: organization_info
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: KR이 참여하는 패널들의 활동 수준을 분석하고 주요 활동 패널을 파악해 주세요.

**자연어 질의**:
1. KR이 참여하는 패널은 (original)
2. 한국선급이 참여하고 있는 패널들을 보여주세요 (similar1)
3. KR이 활동하는 위원회가 어디어디인가요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR

**플레이스홀더**: `organization`

**SQL 쿼리**:
```sql
SELECT DISTINCT c.agenda_panel, COUNT(DISTINCT c.agenda_base_version) as activity_count FROM (SELECT agenda_panel, agenda_base_version FROM agenda_chair WHERE sender_organization = '{organization}' UNION SELECT c.agenda_panel, r.agenda_base_version FROM agenda_responses_content r JOIN agenda_chair c...
```

**실행 결과**: 2개 행 반환

**샘플 데이터** (최대 3행):

| agenda_panel | activity_count |
|---|---|
| PL | 5 |
| TEC | 1 |

---

### 3. ✅ kr_chair_panels

**카테고리**: organization_info
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: KR이 의장으로 있는 패널과 의장으로서의 활동을 분석해 주세요.

**자연어 질의**:
1. KR이 의장으로 있는 패널은? (original)
2. 한국선급이 의장직을 맡고 있는 패널을 보여주세요 (similar1)
3. KR이 chair로 활동하는 위원회가 어디인가요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT DISTINCT agenda_panel, COUNT(*) as chair_agenda_count 
FROM agenda_chair 
WHERE sender_organization = 'KR' 
AND sender_type = 'CHAIR' 
GROUP BY agenda_panel 
ORDER BY chair_agenda_count DESC
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_panel | chair_agenda_count |
|---|---|
| TEC | 1 |

---

### 4. ✅ recent_meeting_list

**카테고리**: meeting
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 최근 진행된 회의들의 일정과 주요 안건을 정리해 주세요.

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
SELECT DISTINCT subject, sent_time, agenda_panel FROM agenda_chair WHERE mail_type = 'NOTIFICATION' AND (LOWER(subject) LIKE '%meeting%' OR LOWER(subject) LIKE '%회의%') AND {period_condition} ORDER BY sent_time DESC
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| subject | sent_time | agenda_panel |
|---|---|---|
| GEN25M002a: Technical Commi... | 2025-06-30 00:45:24 | GEN |

---

### 5. ✅ recent_meeting_issues_decisions

**카테고리**: meeting
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 회의에서 논의된 주요 이슈와 결정사항을 분석하여 핵심 내용을 요약해 주세요.

**자연어 질의**:
1. 최근 진행된 회의의 주요 이슈 및 결정사항은? (original)
2. 최근 회의에서 다뤄진 주요 안건과 결정사항을 보여주세요 (similar1)
3. 지난 미팅의 핵심 이슈와 결과가 뭐였나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT c.subject, c.body, c.sent_time, c.agenda_panel FROM agenda_chair c WHERE c.mail_type = 'NOTIFICATION' AND (LOWER(c.subject) LIKE '%meeting minutes%' OR LOWER(c.subject) LIKE '%회의록%' OR LOWER(c.subject) LIKE '%decision%') AND {period_condition} ORDER BY c.sent_time DESC
```

**실행 결과**: 0개 행 반환

---

### 6. ✅ 3months_keyword_analysis

**카테고리**: keyword_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 3개월간 주요 키워드의 트렌드를 분석하여 현재 IACS의 관심사와 우선순위를 파악해 주세요.

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
SELECT keywords, COUNT(*) as frequency FROM agenda_chair WHERE keywords IS NOT NULL AND keywords != '' AND sent_time >= datetime('now', '-3 months') GROUP BY keywords ORDER BY frequency DESC LIMIT 50
```

**실행 결과**: 36개 행 반환

**샘플 데이터** (최대 3행):

| keywords | frequency |
|---|---|
| ["회의", "기술위원회", "부산", "규정검토"] | 1 |
| ["사이버보안", "규정", "개정", "긴급"] | 1 |
| ["ship", "data", "quality",... | 1 |

---

### 7. ✅ last_year_keyword_analysis

**카테고리**: keyword_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 작년 키워드 트렌드를 분석하여 연간 주요 이슈의 변화와 패턴을 설명해 주세요.

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
SELECT keywords, COUNT(*) as frequency, strftime('%m', sent_time) as month FROM agenda_chair WHERE keywords IS NOT NULL AND keywords != '' AND strftime('%Y', sent_time) = strftime('%Y', 'now', '-1 year') GROUP BY keywords ORDER BY frequency DESC LIMIT 50
```

**실행 결과**: 0개 행 반환

---

### 8. ✅ 2025_keyword_analysis

**카테고리**: keyword_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 2025년 현재까지의 키워드 트렌드를 분석하여 올해의 주요 이슈와 향후 전망을 제시해 주세요.

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
SELECT keywords, COUNT(*) as frequency FROM agenda_chair WHERE keywords IS NOT NULL AND keywords != '' AND strftime('%Y', sent_time) = '2025' GROUP BY keywords ORDER BY frequency DESC LIMIT 50
```

**실행 결과**: 40개 행 반환

**샘플 데이터** (최대 3행):

| keywords | frequency |
|---|---|
| ["회의", "기술위원회", "부산", "규정검토"] | 1 |
| ["사이버보안", "규정", "개정", "긴급"] | 1 |
| ["ship", "data", "quality",... | 1 |

---

### 9. ✅ sdtp_completed_agenda_results

**카테고리**: agenda_status
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: SDTP 완료 의제들의 주요 결과와 영향을 분석해 주세요.

**자연어 질의**:
1. SDTP 에서 발행된 의제 중 완료된 의제의 결과 (original)
2. SDTP 패널에서 완료 처리된 의제들의 결과를 보여주세요 (similar1)
3. 선박설계기술패널 완료 안건의 최종 결과가 뭐인가요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, sent_time, deadline, keywords 
FROM agenda_chair 
WHERE agenda_panel = 'SDTP' 
AND decision_status = 'completed'
AND {period_condition}
ORDER BY sent_time DESC
```

**실행 결과**: 0개 행 반환

---

### 10. ✅ recent_sdtp_discussed_agendas

**카테고리**: agenda_status
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: SDTP에서 최근 논의된 의제들의 주요 주제와 트렌드를 분석해 주세요.

**자연어 질의**:
1. 최근 SDTP 에서 논의 되었던 의제 목록 (original)
2. SDTP 패널에서 최근 다뤄진 의제들을 보여주세요 (similar1)
3. 선박설계기술패널 최근 안건 리스트가 뭐인가요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, sent_time, decision_status, keywords FROM agenda_chair WHERE agenda_panel = 'SDTP' AND {period_condition} ORDER BY sent_time DESC
```

**실행 결과**: 0개 행 반환

---

### 11. ✅ iacs_member_count

**카테고리**: organization_info
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 조회 결과를 분석하여 요청사항에 맞게 정리해 주세요.

**자연어 질의**:
1. IACS 멤버의 수는 ? (original)
2. IACS에 소속된 회원사가 몇 개인가요? (similar1)
3. 국제선급연합회 멤버 수를 알려주세요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT COUNT(DISTINCT organization) as member_count
                FROM (
                    SELECT DISTINCT sender_organization as organization
                    FROM agenda_chair
                    WHERE sender_organization IN ('ABS', 'BV', 'CCS', 'CRS', 'DNV', 'IRS', 'KR', 'LR', 'NK', 'PRS',...
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| member_count |
|---|
| 5 |

---

### 12. ✅ iacs_member_composition

**카테고리**: organization_info
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 조회 결과를 분석하여 요청사항에 맞게 정리해 주세요.

**자연어 질의**:
1. IACS 멤버 구성은 어떻게 되나? (original)
2. IACS 회원사들의 구성을 보여주세요 (similar1)
3. 국제선급연합회 멤버들이 어떤 선급들인가요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT DISTINCT sender_organization as organization_code,
                       sender_organization as organization_name,
                       CASE sender_organization
                           WHEN 'ABS' THEN 'USA'
                           WHEN 'BV' THEN 'France'
                           WH...
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| organization_code | organization_name | country | organization_type |
|---|---|---|---|
| ABS | ABS | USA | MEMBER |
| BV | BV | France | MEMBER |
| DNV | DNV | Norway | MEMBER |

---


## 테스트 설정

- **파일**: query_templates_group_004.json
- **테스트 일시**: 2025-07-30T11:05:25.212142
- **데이터베이스 경로**: data/iacsgraph.db
