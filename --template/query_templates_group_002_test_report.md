# query_templates_group_002.json 테스트 보고서

**테스트 일시**: 2025-07-30T11:05:25.194486
**데이터베이스**: data/iacsgraph.db

## 요약

- **전체 템플릿 수**: 24
- **성공**: 24 (100.0%)
- **실패**: 0

### 카테고리별 결과

| 카테고리 | 전체 | 성공 | 실패 | 성공률 |
|----------|------|------|------|--------|
| keyword_search | 5 | 5 | 0 | 100.0% |
| statistics | 4 | 4 | 0 | 100.0% |
| agenda_status | 7 | 7 | 0 | 100.0% |
| mail_type | 1 | 1 | 0 | 100.0% |
| deadline_tracking | 3 | 3 | 0 | 100.0% |
| response_tracking | 3 | 3 | 0 | 100.0% |
| panel_statistics | 1 | 1 | 0 | 100.0% |

## 상세 결과

### 1. ✅ recent_eg_discussed_agendas

**카테고리**: keyword_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: EG 관련 의제들을 분석하여 주요 논의 사항과 결정사항을 정리해 주세요.

**자연어 질의**:
1. 최근에 EG 관련해서 논의된 아젠다 찾아줘 (original)
2. EG(Expert Group) 관련 최근 논의 의제를 보여주세요 (similar1)
3. 전문가 그룹 관련 최근 안건들이 뭐가 있나요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}
- 선택 파라미터:
  - `keywords` (array) - 기본값: ['EG', 'Expert Group']

**플레이스홀더**: `keywords_condition, period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, keywords, sent_time, decision_status, agenda_panel FROM agenda_chair WHERE {period_condition} AND ({keywords_condition}) ORDER BY sent_time DESC
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | keywords | sent_time |
|---|---|---|---|---|
| ENV25M005a | ENV25M005 | ENV25M005a: Urgent - Enviro... | ["conference", "urgent", "e... | 2025-07-20 00:45:24 |

*참고: 전체 7개 컬럼 중 5개만 표시*

---

### 2. ✅ yearly_monthly_agenda_response_status

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 월별 의제 발송 및 응답 현황을 분석하여 추이를 설명해 주세요. 특히 응답률이 낮은 달이나 급격한 변화가 있는 시점을 주목해 주세요.

**자연어 질의**:
1. 올해 월별 agenda 발송 및 그 아젠다에 대한 응답 현황 (original)
2. 올해 각 월별로 의제 발송과 응답 현황을 보여주세요 (similar1)
3. 금년도 월별 아젠다 발송량과 응답률 통계를 알려주세요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT strftime('%Y-%m', sent_time) as month, COUNT(DISTINCT c.agenda_base_version) as sent_count, COUNT(DISTINCT CASE WHEN r.agenda_base_version IS NOT NULL THEN c.agenda_base_version END) as responded_count FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agend...
```

**실행 결과**: 4개 행 반환

**샘플 데이터** (최대 3행):

| month | sent_count | responded_count |
|---|---|---|
| 2025-04 | 5 | 5 |
| 2025-05 | 21 | 21 |
| 2025-06 | 9 | 9 |

---

### 3. ✅ recent_24hours_sent_agendas

**카테고리**: agenda_status
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 24시간 이내 발송된 의제들의 긴급도와 주요 내용을 분석해 주세요.

**자연어 질의**:
1. 최근 24시간 이내에 발송한 agenda 가 있나요? (original)
2. 지난 24시간 동안 발송된 의제가 있는지 확인해주세요 (similar1)
3. 어제부터 오늘까지 보낸 아젠다가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, sender_organization, sent_time, agenda_panel FROM agenda_chair WHERE sent_time >= datetime('now', '-1 day') ORDER BY sent_time DESC
```

**실행 결과**: 0개 행 반환

---

### 4. ✅ recent_24hours_received_mails

**카테고리**: mail_type
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 24시간 이내 수신된 메일들을 유형별로 분류하고 중요도를 평가해 주세요.

**자연어 질의**:
1. 최근 24시간 이내에 수신한 메일이 있나요? (original)
2. 지난 24시간 동안 받은 메일이 있는지 확인해주세요 (similar1)
3. 어제부터 오늘까지 수신한 이메일이 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, subject, sender_organization, sent_time, mail_type, agenda_panel FROM agenda_chair WHERE sent_time >= datetime('now', '-1 day') ORDER BY sent_time DESC
```

**실행 결과**: 0개 행 반환

---

### 5. ✅ pending_agenda_error_reasons

**카테고리**: agenda_status
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 오류 이유별로 발생 빈도를 분석하고 각 오류 유형에 대한 해결 방안을 제시해 주세요.

**자연어 질의**:
1. 처리되지 않은 pending agenda의 오류 이유들 (original)
2. 대기 중인 의제들의 처리 안 된 이유를 보여주세요 (similar1)
3. 펜딩 상태 아젠다의 에러 원인들이 뭐가 있나요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT error_reason, COUNT(*) as count FROM agenda_pending WHERE error_reason IS NOT NULL AND error_reason != '' GROUP BY error_reason ORDER BY count DESC
```

**실행 결과**: 2개 행 반환

**샘플 데이터** (최대 3행):

| error_reason | count |
|---|---|
| no_agenda_base_version | 6 |
| unknown_sender_type | 2 |

---

### 6. ✅ vessel_asset_inventory_agendas

**카테고리**: keyword_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: Vessel Asset Inventory 관련 의제들의 주요 논의 사항과 진행 상황을 정리해 주세요.

**자연어 질의**:
1. Vessel Asset Inventory 관련 agenda (original)
2. 선박 자산 목록 관련 의제들을 보여주세요 (similar1)
3. Vessel Asset Inventory에 대한 안건들이 뭐가 있나요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음
- 선택 파라미터:
  - `keywords` (array) - 기본값: ['Vessel Asset Inventory', 'asset inventory']

**플레이스홀더**: `keywords_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, keywords, sent_time, decision_status, agenda_panel FROM agenda_chair WHERE ({keywords_condition}) ORDER BY sent_time DESC
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

### 7. ✅ keyword_related_agendas

**카테고리**: keyword_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 검색된 의제들을 주제별로 분류하고 주요 논의 사항을 정리해 주세요.

**자연어 질의**:
1. {keywords} 관련 agenda (original)
2. {keywords}에 대한 의제들을 보여주세요 (similar1)
3. {keywords} 관련된 안건들이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `keywords` (array)

**플레이스홀더**: `keywords_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, keywords, sent_time, decision_status, agenda_panel FROM agenda_chair WHERE ({keywords_condition}) ORDER BY sent_time DESC
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

### 8. ✅ recent_consolidated_status_agendas

**카테고리**: agenda_status
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 통합된 의제들의 패턴을 분석하여 어떤 유형의 의제들이 주로 통합되는지 설명해 주세요.

**자연어 질의**:
1. 최근 consolidated 상태의 agenda 목록 (original)
2. 통합 완료된 최근 의제들을 보여주세요 (similar1)
3. consolidated 상태인 아젠다 리스트가 필요해요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, sender_organization, sent_time, agenda_panel FROM agenda_chair WHERE decision_status = 'consolidated' AND {period_condition} ORDER BY sent_time DESC
```

**실행 결과**: 0개 행 반환

---

### 9. ✅ multilateral_recent_agendas

**카테고리**: agenda_status
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 다자간 협의 의제들의 주요 주제와 참여 패턴을 분석해 주세요.

**자연어 질의**:
1. MULTILATERAL의 최근 아젠다 리스트 (original)
2. 다자간 협의 관련 최근 의제들을 보여주세요 (similar1)
3. MULTILATERAL 유형의 최근 안건 목록이 필요해요 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, sender_organization, sent_time, decision_status, agenda_panel FROM agenda_chair WHERE mail_type = 'MULTILATERAL' AND {period_condition} ORDER BY sent_time DESC
```

**실행 결과**: 0개 행 반환

---

### 10. ✅ deadline_within_week_agendas

**카테고리**: deadline_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 마감이 임박한 의제들을 우선순위별로 정리하고 대응 전략을 제시해 주세요.

**자연어 질의**:
1. 마감일이 일주일 이내인 agenda (original)
2. 7일 이내에 마감되는 의제들을 보여주세요 (similar1)
3. 일주일 안에 답변해야 하는 안건이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, deadline, JULIANDAY(deadline) - JULIANDAY('now') as days_remaining, agenda_panel FROM agenda_chair WHERE has_deadline = 1 AND deadline BETWEEN datetime('now') AND datetime('now', '+7 days') ORDER BY deadline ASC
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | deadline | days_remaining |
|---|---|---|---|---|
| TEST2025002a | TEST2025002 | TEST2025002a: 긴급 검토 - 사이버보안... | 2025-08-05 02:25:23 | 6.013863448984921 |

*참고: 전체 6개 컬럼 중 5개만 표시*

---

### 11. ✅ deadline_within_three_days_agendas

**카테고리**: deadline_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 긴급 대응이 필요한 의제들을 식별하고 즉시 처리해야 할 사항을 강조해 주세요.

**자연어 질의**:
1. 마감일이 삼일 이내인 agenda (original)
2. 3일 이내에 마감되는 의제들을 보여주세요 (similar1)
3. 사흘 안에 답변해야 하는 안건이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, deadline, ROUND((JULIANDAY(deadline) - JULIANDAY('now')) * 24) as hours_remaining, agenda_panel FROM agenda_chair WHERE has_deadline = 1 AND deadline BETWEEN datetime('now') AND datetime('now', '+3 days') ORDER BY deadline ASC
```

**실행 결과**: 0개 행 반환

---

### 12. ✅ today_response_required_agendas

**카테고리**: deadline_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 오늘 마감인 의제들의 긴급도를 평가하고 즉시 대응해야 할 우선순위를 제시해 주세요.

**자연어 질의**:
1. 오늘 응답해야 하는 agenda (original)
2. 오늘까지 답변해야 하는 의제들을 보여주세요 (similar1)
3. 오늘이 마감인 안건들이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, deadline, agenda_panel FROM agenda_chair WHERE has_deadline = 1 AND DATE(deadline) = DATE('now') ORDER BY deadline ASC
```

**실행 결과**: 0개 행 반환

---

### 13. ✅ cyber_keyword_agendas

**카테고리**: keyword_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 사이버 관련 의제들의 주요 주제와 보안 이슈를 분석해 주세요.

**자연어 질의**:
1. 키워드에 'cyber'가 포함된 agenda (original)
2. 사이버 관련 의제들을 보여주세요 (similar1)
3. cyber 키워드가 들어간 안건들이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음
- 선택 파라미터:
  - `keywords` (array) - 기본값: ['cyber', 'cybersecurity']

**플레이스홀더**: `keywords_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, keywords, sent_time, decision_status, agenda_panel FROM agenda_chair WHERE ({keywords_condition}) ORDER BY sent_time DESC
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

### 14. ✅ recent_month_created_chair_agendas

**카테고리**: agenda_status
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 의장이 생성한 의제들의 주요 목적과 패널별 분포를 분석해 주세요.

**자연어 질의**:
1. 최근 한 달간 생성된 chair agenda (original)
2. 지난 30일간 의장이 생성한 의제들을 보여주세요 (similar1)
3. 최근 한 달 동안 만들어진 의장 안건이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, sender_organization, sent_time, agenda_panel FROM agenda_chair WHERE sender_type = 'CHAIR' AND sent_time >= datetime('now', '-30 days') ORDER BY sent_time DESC
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | sender_organization | sent_time |
|---|---|---|---|---|
| TEST2025002a | TEST2025002 | TEST2025002a: 긴급 검토 - 사이버보안... | IACS | 2025-07-26 02:25:23 |
| TEST2025001a | TEST2025001 | TEST2025001a: 테스트 의제 - AI 기... | IACS | 2025-07-22 02:25:23 |
| ENV25M005a | ENV25M005 | ENV25M005a: Urgent - Enviro... | ABS | 2025-07-20 00:45:24 |

*참고: 전체 6개 컬럼 중 5개만 표시*

---

### 15. ✅ no_response_agendas

**카테고리**: response_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 무응답 의제들의 특징을 분석하고 응답률을 높일 수 있는 방안을 제시해 주세요.

**자연어 질의**:
1. 아직 아무도 응답하지 않은 agenda (original)
2. 아무 기관도 회신하지 않은 의제들을 보여주세요 (similar1)
3. 응답이 전혀 없는 안건들이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT c.agenda_code, c.agenda_base_version, c.subject, c.sent_time, c.deadline, c.agenda_panel FROM agenda_chair c LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version WHERE c.mail_type = 'REQUEST' AND r.agenda_base_version IS NULL ORDER BY c.deadline ASC
```

**실행 결과**: 0개 행 반환

---

### 16. ✅ recent_attachment_agendas

**카테고리**: agenda_status
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 첨부파일이 있는 의제들의 특징과 파일 유형별 분포를 분석해 주세요.

**자연어 질의**:
1. 최근 첨부 파일이 있는 agenda 목록 (original)
2. 첨부파일이 포함된 최근 의제들을 보여주세요 (similar1)
3. 첨부 문서가 있는 최근 안건들이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, hasAttachments, sent_time, agenda_panel FROM agenda_chair WHERE hasAttachments = 1 AND {period_condition} ORDER BY sent_time DESC
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | hasAttachments | sent_time |
|---|---|---|---|---|
| TEST2025002a | TEST2025002 | TEST2025002a: 긴급 검토 - 사이버보안... | 1 | 2025-07-26 02:25:23 |

*참고: 전체 6개 컬럼 중 5개만 표시*

---

### 17. ✅ digital_transformation_agendas

**카테고리**: keyword_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 디지털 전환 관련 의제들의 주요 동향과 각 패널의 접근 방식을 분석해 주세요.

**자연어 질의**:
1. Digital Transformation 관련 agenda (original)
2. 디지털 전환 관련 의제들을 보여주세요 (similar1)
3. Digital Transformation에 대한 안건들이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음
- 선택 파라미터:
  - `keywords` (array) - 기본값: ['Digital Transformation', 'digitalization']

**플레이스홀더**: `keywords_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, keywords, sent_time, decision_status, agenda_panel FROM agenda_chair WHERE ({keywords_condition}) ORDER BY sent_time DESC
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

### 18. ✅ recent_24hours_responded_organizations

**카테고리**: response_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 조회 결과를 분석하여 요청사항에 맞게 정리해 주세요.

**자연어 질의**:
1. 최근 24시간 이내에 응답한 기관이 있나요? (original)
2. 지난 24시간 동안 회신한 조직들을 보여주세요 (similar1)
3. 오늘 응답한 기관 리스트가 필요합니다 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT DISTINCT c.agenda_code, c.subject, c.sent_time as agenda_sent,
                       CASE 
                           WHEN r.ABS IS NOT NULL THEN 'ABS'
                           WHEN r.BV IS NOT NULL THEN 'BV'
                           WHEN r.CCS IS NOT NULL THEN 'CCS'
                    ...
```

**실행 결과**: 0개 행 반환

---

### 19. ✅ recent_weblink_agendas

**카테고리**: agenda_status
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 조회 결과를 분석하여 요청사항에 맞게 정리해 주세요.

**자연어 질의**:
1. 최근 webLink가 있는 agenda 목록 (original)
2. 웹링크가 포함된 최근 의제들을 보여주세요 (similar1)
3. URL이 있는 최신 안건 리스트가 필요합니다 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 30}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, sent_time, agenda_panel,
                       body as content
                FROM agenda_chair
                WHERE (body LIKE '%http://%' OR body LIKE '%https://%')
                AND {period_condition}
                ORDER BY sent_time DESC
```

**실행 결과**: 0개 행 반환

---

### 20. ✅ organization_average_response_time

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 조회 결과를 분석하여 요청사항에 맞게 정리해 주세요.

**자연어 질의**:
1. 조직별 평균 응답 소요 시간 (original)
2. 각 기관의 평균 회신 시간을 보여주세요 (similar1)
3. 선급별 응답 속도 통계가 필요합니다 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
WITH org_responses AS (
                    SELECT c.agenda_base_version, c.sent_time as agenda_sent,
                           'ABS' as org, r.ABS as response FROM agenda_chair c
                    JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version
                  ...
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| organization | response_count | avg_response_days |
|---|---|---|
| KR | 5 | 67.86216437490657 |
| ABS | 12 | 74.21925677456117 |
| BV | 12 | 75.25991649681237 |

---

### 21. ✅ completed_pending_processing_time

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 기관별 응답 처리 시간을 분석하여 가장 빠른 기관과 가장 느린 기관을 파악하고, 전체적인 응답 속도 패턴을 설명해 주세요.

**자연어 질의**:
1. 각 기관의 의제 응답 처리 시간 통계 (original)
2. 기관별 평균 응답 소요 시간을 보여주세요 (similar1)
3. 각 기관이 의제에 응답하는데 걸린 시간 통계가 필요합니다 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT 
    org_name,
    COUNT(*) as total_responses,
    AVG(response_days) as avg_response_days,
    MIN(response_days) as min_response_days,
    MAX(response_days) as max_response_days
FROM (
    SELECT 
        CASE 
            WHEN rt.ABS IS NOT NULL THEN 'ABS'
            WHEN rt.BV IS NOT N...
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| org_name | total_responses | avg_response_days | min_response_days | max_response_days |
|---|---|---|---|---|
| IL | 1 | 0.0 | 0.0 | 0.0 |

---

### 22. ✅ slowest_responding_organization

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 가장 늦게 응답한 케이스들을 분석하여 지연 원인과 패턴을 파악해 주세요.

**자연어 질의**:
1. 가장 늦게 응답한 조직과 agenda (original)
2. 응답이 가장 지연된 기관과 해당 의제를 보여주세요 (similar1)
3. 어떤 조직이 어떤 안건에 가장 늦게 답변했나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
WITH response_times AS (
                    SELECT 
                        c.agenda_code,
                        c.agenda_base_version,
                        c.subject,
                        c.sent_time,
                        c.agenda_panel,
                        CASE 
                   ...
```

**실행 결과**: 10개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | sent_time | agenda_panel |
|---|---|---|---|---|
| JWG-SDT25001a | JWG-SDT25001a | JWG-SDT25001a: IACS Recomme... | 2025-05-21 20:28:10+00:00 | JWG-SDT |
| PL25008dILa | PL25008d | PL25008dILa: IMO MSC 110/5 ... | 2025-05-17 02:19:59+00:00 | PL |
| PL25016_ILa | PL25016 | PL25016_ILa: IMO Expert Gro... | 2025-06-05 23:04:26+00:00 | PL |

*참고: 전체 8개 컬럼 중 5개만 표시*

---

### 23. ✅ recent_updated_responses

**카테고리**: response_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 최근 3일간 업데이트된 응답들을 분석하고 주요 내용을 요약해 주세요.

**자연어 질의**:
1. 최근 3일간 업데이트된 응답 내용 (original)
2. 지난 3일 동안 수정된 응답들을 보여주세요 (similar1)
3. 최근 72시간 내 업데이트된 회신 내용이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
WITH recent_responses AS (
                    SELECT 
                        c.agenda_code,
                        c.agenda_base_version,
                        c.subject,
                        c.agenda_panel,
                        CASE 
                            WHEN rt.ABS >= datetime('n...
```

**실행 결과**: 0개 행 반환

---

### 24. ✅ panel_agenda_statistics

**카테고리**: panel_statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 패널별 활동 현황을 분석하여 가장 활발한 패널과 상대적으로 활동이 적은 패널을 파악하고, 각 패널의 특징을 설명해 주세요.

**자연어 질의**:
1. 최근 패널 별 agenda 수를 집계해주세요 (original)
2. 패널별 의제 개수 통계를 보여주세요 (similar1)
3. 각 패널의 아젠다 수를 집계해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT agenda_panel, COUNT(*) as agenda_count, ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM agenda_chair WHERE {period_condition}), 2) as percentage FROM agenda_chair WHERE {period_condition} GROUP BY agenda_panel ORDER BY agenda_count DESC
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| agenda_panel | agenda_count | percentage |
|---|---|---|
| PL | 2 | 28.57 |
| TEST | 2 | 28.57 |
| ENV | 1 | 14.29 |

---


## 테스트 설정

- **파일**: query_templates_group_002.json
- **테스트 일시**: 2025-07-30T11:05:25.194486
- **데이터베이스 경로**: data/iacsgraph.db
