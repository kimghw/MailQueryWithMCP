# query_templates_group_003.json 테스트 보고서

**테스트 일시**: 2025-07-30T11:05:25.205188
**데이터베이스**: data/iacsgraph.db

## 요약

- **전체 템플릿 수**: 17
- **성공**: 17 (100.0%)
- **실패**: 0

### 카테고리별 결과

| 카테고리 | 전체 | 성공 | 실패 | 성공률 |
|----------|------|------|------|--------|
| statistics | 7 | 7 | 0 | 100.0% |
| sender_analysis | 3 | 3 | 0 | 100.0% |
| agenda_status | 2 | 2 | 0 | 100.0% |
| deadline_tracking | 2 | 2 | 0 | 100.0% |
| keyword_search | 1 | 1 | 0 | 100.0% |
| data_quality | 1 | 1 | 0 | 100.0% |
| response_tracking | 1 | 1 | 0 | 100.0% |

## 상세 결과

### 1. ✅ kr_average_response_time_mail

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: KR의 응답 시간을 분석하고 다른 주요 조직들과 비교하여 개선이 필요한 부분을 제시해 주세요.

**자연어 질의**:
1. 응답매일 중 KR 평균 응듭 시간 (original)
2. 한국선급의 메일 응답 평균 시간을 보여주세요 (similar1)
3. KR이 메일 회신하는데 평균 얼마나 걸리나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT 'KR' as organization, 
COUNT(*) as response_count, 
AVG(JULIANDAY(rt.KR) - JULIANDAY(c.sent_time)) as avg_response_days, 
MIN(JULIANDAY(rt.KR) - JULIANDAY(c.sent_time)) as min_days, 
MAX(JULIANDAY(rt.KR) - JULIANDAY(c.sent_time)) as max_days 
FROM agenda_chair c 
JOIN agenda_responses_receive...
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| organization | response_count | avg_response_days | min_days | max_days |
|---|---|---|---|---|
| KR | 0 | None | None | None |

---

### 2. ✅ kr_average_response_time_excluding_creation

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: KR의 순수 응답 성과를 분석하고 응답 시간 단축 방안을 제시해 주세요.

**자연어 질의**:
1. 아젠다 생성을 제외하고 KR 평균 응답시간 (original)
2. 의제 생성 건을 빼고 한국선급의 평균 응답 시간을 보여주세요 (similar1)
3. KR이 직접 만든 의제 제외하고 응답 시간이 얼마나 되나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `organization` (string) - 기본값: KR
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT 'KR' as organization, 
COUNT(*) as response_count, 
AVG(JULIANDAY(rt.KR) - JULIANDAY(c.sent_time)) as avg_response_days 
FROM agenda_chair c 
JOIN agenda_responses_receivedtime rt ON c.agenda_base_version = rt.agenda_base_version 
WHERE rt.KR IS NOT NULL 
AND c.sender_organization != 'KR' 
AN...
```

**실행 결과**: 1개 행 반환

**샘플 데이터** (최대 3행):

| organization | response_count | avg_response_days |
|---|---|---|
| KR | 0 | None |

---

### 3. ✅ other_type_sender_list

**카테고리**: sender_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: OTHER 타입 발신자들의 특징을 분석하고 적절한 분류 방안을 제시해 주세요.

**자연어 질의**:
1. other 타입의 발신자 목록 (original)
2. 기타(other) 유형의 발신자들을 보여주세요 (similar1)
3. other 타입으로 분류된 발신 기관이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT DISTINCT sender_organization, sender_type, COUNT(*) as mail_count FROM agenda_chair WHERE sender_type = 'OTHER' GROUP BY sender_organization ORDER BY mail_count DESC
```

**실행 결과**: 0개 행 반환

---

### 4. ✅ recent_updated_chair_agendas

**카테고리**: agenda_status
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 최근 업데이트된 의장 의제들의 변경 사유와 패턴을 분석해 주세요.

**자연어 질의**:
1. 최근 업데이트된 chair agenda 10개 (original)
2. 최근에 수정된 의장 의제 10개를 보여주세요 (similar1)
3. 가장 최근 업데이트된 의장 안건 10건 확인해줘 (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, sent_time, sent_time, agenda_panel FROM agenda_chair WHERE sender_type = 'CHAIR' AND sent_time IS NOT NULL ORDER BY sent_time DESC LIMIT 10
```

**실행 결과**: 10개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | sent_time | agenda_panel |
|---|---|---|---|---|
| TEST2025002a | TEST2025002 | TEST2025002a: 긴급 검토 - 사이버보안... | 2025-07-26 02:25:23 | TEST |
| TEST2025001a | TEST2025001 | TEST2025001a: 테스트 의제 - AI 기... | 2025-07-22 02:25:23 | TEST |
| ENV25M005a | ENV25M005 | ENV25M005a: Urgent - Enviro... | 2025-07-20 00:45:24 | ENV |

---

### 5. ✅ no_deadline_chair_agendas

**카테고리**: deadline_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 마감일이 없는 의장 의제들의 특징과 목적을 분석해 주세요.

**자연어 질의**:
1. 마감일이 없는 chair agenda (original)
2. 마감 기한이 설정되지 않은 의장 의제들을 보여주세요 (similar1)
3. 데드라인 없는 의장 안건들이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, sent_time, mail_type, agenda_panel FROM agenda_chair WHERE sender_type = 'CHAIR' AND (has_deadline = 0 OR deadline IS NULL) ORDER BY sent_time DESC
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | sent_time | mail_type |
|---|---|---|---|---|
| PL25008eILa | PL25008e | PL25008eILa: IMO MSC 110 - ... | 2025-07-03 10:06:25+00:00 | NOTIFICATION |
| PL24033_ILf | PL24033 | [자동생성] PL24033 | 2025-06-30 00:12:01+00:00 | REQUEST |
| Multilateral | Multilateral_20250617_121836 | [Multilateral] New SDTP Sec... | 2025-06-17 12:18:36+00:00 | NOTIFICATION |

*참고: 전체 6개 컬럼 중 5개만 표시*

---

### 6. ✅ active_time_agenda_statistics

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 시간대별 발송 패턴을 분석하여 업무 패턴과 시차를 고려한 최적의 발송 시간을 제안해 주세요.

**자연어 질의**:
1. 가장 활발한 시간대의 agenda 발송 통계 (original)
2. 의제가 가장 많이 발송되는 시간대를 보여주세요 (similar1)
3. 어느 시간대에 아젠다 발송이 가장 활발한가요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT strftime('%H', sent_time) as hour, COUNT(*) as count FROM agenda_chair WHERE {period_condition} GROUP BY hour ORDER BY count DESC
```

**실행 결과**: 3개 행 반환

**샘플 데이터** (최대 3행):

| hour | count |
|---|---|
| 00 | 3 |
| 10 | 2 |
| 02 | 2 |

---

### 7. ✅ unknown_type_sender_info

**카테고리**: sender_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: UNKNOWN 발신자들의 패턴을 분석하여 실제 소속을 추정하고 분류 개선 방안을 제시해 주세요.

**자연어 질의**:
1. UNKNOWN 타입의 발신자 정보 (original)
2. 미확인(UNKNOWN) 발신자들의 정보를 보여주세요 (similar1)
3. UNKNOWN으로 분류된 발신 기관이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT sender_organization, sender_address, subject, sent_time, COUNT(*) OVER (PARTITION BY sender_organization) as sender_count FROM agenda_chair WHERE sender_type = 'UNKNOWN' ORDER BY sent_time DESC
```

**실행 결과**: 0개 행 반환

---

### 8. ✅ msc_110_related_agendas

**카테고리**: keyword_search
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: MSC 110 관련 의제들의 주요 의제와 결정사항을 정리해 주세요.

**자연어 질의**:
1. MSC 110 관련 agenda 찾기 (original)
2. MSC 110과 관련된 의제들을 보여주세요 (similar1)
3. 해사안전위원회 110차 회의 관련 안건이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음
- 선택 파라미터:
  - `keywords` (array) - 기본값: ['MSC 110', 'MSC110']

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

### 9. ✅ monthly_response_rate_statistics

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 월별 응답률 추이를 분석하여 계절적 패턴이나 특이점을 파악하고 응답률 향상 방안을 제시해 주세요.

**자연어 질의**:
1. 각 월별 응답률 통계 (original)
2. 월별 응답률 통계를 보여주세요 (similar1)
3. 매월 응답률이 어떻게 되나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT strftime('%Y-%m', c.sent_time) as month, COUNT(DISTINCT c.agenda_base_version) as total_sent, COUNT(DISTINCT r.agenda_base_version) as responded, ROUND(COUNT(DISTINCT r.agenda_base_version) * 100.0 / COUNT(DISTINCT c.agenda_base_version), 2) as response_rate FROM agenda_chair c LEFT JOIN agen...
```

**실행 결과**: 4개 행 반환

**샘플 데이터** (최대 3행):

| month | total_sent | responded | response_rate |
|---|---|---|---|
| 2025-07 | 2 | 2 | 100.0 |
| 2025-06 | 4 | 4 | 100.0 |
| 2025-05 | 8 | 8 | 100.0 |

---

### 10. ✅ sender_address_mismatch_cases

**카테고리**: sender_analysis
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 발신자 정보 불일치 케이스를 분석하여 원인을 파악하고 데이터 정합성 개선 방안을 제시해 주세요.

**자연어 질의**:
1. sender와 sender_address가 다른 경우 (original)
2. 발신자명과 발신 주소가 일치하지 않는 경우를 보여주세요 (similar1)
3. sender와 이메일 주소가 다른 케이스가 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT sender_organization, sender_address, subject, sent_time, sender_type FROM agenda_chair WHERE sender_organization != SUBSTR(sender_address, 1, INSTR(sender_address, '@') - 1) ORDER BY sent_time DESC
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| sender_organization | sender_address | subject | sent_time | sender_type |
|---|---|---|---|---|
| IACS | chair@iacs.org | TEST2025002a: 긴급 검토 - 사이버보안... | 2025-07-26 02:25:23 | CHAIR |
| IACS | chair@iacs.org | TEST2025001a: 테스트 의제 - AI 기... | 2025-07-22 02:25:23 | CHAIR |
| ABS | SDTPChair@eagle.org | PS25003pPLa MSC 110 (18-27 ... | 2025-07-03 10:12:30+00:00 | CHAIR |

---

### 11. ✅ agenda_base_version_mismatch

**카테고리**: data_quality
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 버전 변경된 의제들의 패턴을 분석하여 주요 변경 사유를 파악해 주세요.

**자연어 질의**:
1. agenda_base와 agenda_version이 다른 경우 (original)
2. 기본 버전과 현재 버전이 다른 의제들을 보여주세요 (similar1)
3. agenda_base와 version이 일치하지 않는 케이스가 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, agenda_version, subject, sent_time, sent_time FROM agenda_chair WHERE agenda_base_version != agenda_version ORDER BY sent_time DESC
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | agenda_version | subject | sent_time |
|---|---|---|---|---|
| TEST2025002a | TEST2025002 | a | TEST2025002a: 긴급 검토 - 사이버보안... | 2025-07-26 02:25:23 |
| TEST2025001a | TEST2025001 | a | TEST2025001a: 테스트 의제 - AI 기... | 2025-07-22 02:25:23 |
| ENV25M005a | ENV25M005 | 1 | ENV25M005a: Urgent - Enviro... | 2025-07-20 00:45:24 |

---

### 12. ✅ error_reason_pending_count

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 주요 오류 원인을 분석하고 각 오류 유형별 해결 방안을 제시해 주세요.

**자연어 질의**:
1. error_reason별 pending 건수 (original)
2. 오류 사유별로 대기 중인 건수를 보여주세요 (similar1)
3. 에러 이유별 펜딩 통계가 어떻게 되나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT error_reason, COUNT(*) as count, ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM agenda_pending), 2) as percentage FROM agenda_pending WHERE error_reason IS NOT NULL GROUP BY error_reason ORDER BY count DESC
```

**실행 결과**: 2개 행 반환

**샘플 데이터** (최대 3행):

| error_reason | count | percentage |
|---|---|---|
| no_agenda_base_version | 6 | 75.0 |
| unknown_sender_type | 2 | 25.0 |

---

### 13. ✅ agenda_code_latest_status

**카테고리**: agenda_status
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 의제별 현재 상태를 분석하여 진행이 지연되고 있는 의제들을 파악해 주세요.

**자연어 질의**:
1. agenda_code별 최신 상태 (original)
2. 각 의제 코드별로 현재 상태를 보여주세요 (similar1)
3. 아젠다 코드별 최신 상태가 어떻게 되나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, MAX(agenda_version) as latest_version, decision_status, subject, sent_time, agenda_panel FROM agenda_chair GROUP BY agenda_code ORDER BY sent_time DESC
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | latest_version | decision_status | subject | sent_time |
|---|---|---|---|---|
| TEST2025002a | a | ongoing | TEST2025002a: 긴급 검토 - 사이버보안... | 2025-07-26 02:25:23 |
| TEST2025001a | a | created | TEST2025001a: 테스트 의제 - AI 기... | 2025-07-22 02:25:23 |
| ENV25M005a | 1 | completed | ENV25M005a: Urgent - Enviro... | 2025-07-20 00:45:24 |

*참고: 전체 6개 컬럼 중 5개만 표시*

---

### 14. ✅ weekday_agenda_statistics

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 요일별 발송 패턴을 분석하여 업무 특성과 효율적인 의제 처리 방안을 제시해 주세요.

**자연어 질의**:
1. 요일별 agenda 발송 통계 (original)
2. 각 요일별로 의제 발송 통계를 보여주세요 (similar1)
3. 무슨 요일에 아젠다가 가장 많이 발송되나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터:
  - `period` (period) - 기본값: {'type': 'relative', 'days': 90}

**플레이스홀더**: `period_condition`

**SQL 쿼리**:
```sql
SELECT CASE strftime('%w', sent_time) WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday' WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday' WHEN '6' THEN 'Saturday' END as weekday, COUNT(*) as count FROM agenda_chair WHERE {period_condition} GROUP BY strftim...
```

**실행 결과**: 5개 행 반환

**샘플 데이터** (최대 3행):

| weekday | count |
|---|---|
| Sunday | 1 |
| Monday | 2 |
| Tuesday | 1 |

---

### 15. ✅ quarterly_agenda_statistics

**카테고리**: statistics
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 분기별 발송 추이를 분석하여 계절적 패턴과 업무량 변화를 설명해 주세요.

**자연어 질의**:
1. 각 분기별 agenda 발송 현황 (original)
2. 분기별 의제 발송 통계를 보여주세요 (similar1)
3. 각 분기마다 아젠다 발송량이 어떻게 되나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT strftime('%Y', sent_time) || '-Q' || ((strftime('%m', sent_time) - 1) / 3 + 1) as quarter, COUNT(*) as count FROM agenda_chair GROUP BY quarter ORDER BY quarter DESC
```

**실행 결과**: 2개 행 반환

**샘플 데이터** (최대 3행):

| quarter | count |
|---|---|
| 2025-Q3 | 5 |
| 2025-Q2 | 35 |

---

### 16. ✅ deadline_urgency_created_agendas

**카테고리**: deadline_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 촉박하게 생성된 의제들의 특징과 긴급 생성 사유를 분석해 주세요.

**자연어 질의**:
1. 마감일 대비 가장 촉박하게 생성된 agenda (original)
2. 생성일과 마감일이 가장 가까운 의제들을 보여주세요 (similar1)
3. 급하게 만들어진 촉박한 마감 안건들이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, sent_time, deadline, JULIANDAY(deadline) - JULIANDAY(sent_time) as days_given, agenda_panel FROM agenda_chair WHERE has_deadline = 1 AND deadline IS NOT NULL AND sent_time IS NOT NULL ORDER BY days_given ASC LIMIT 20
```

**실행 결과**: 19개 행 반환

**샘플 데이터** (최대 3행):

| agenda_code | agenda_base_version | subject | sent_time | deadline |
|---|---|---|---|---|
| ENV25M005a | ENV25M005 | ENV25M005a: Urgent - Enviro... | 2025-07-20 00:45:24 | 2025-07-25 00:45:24 |
| PS25003pPLa | PS25003p | PS25003pPLa MSC 110 (18-27 ... | 2025-07-03 10:12:30+00:00 | 2025-07-09 23:59:59+00:00 |
| PL25011_ILa | PL25011 | PL25011_ILa IACS/Industry M... | 2025-05-05 19:07:42+00:00 | 2025-05-12 23:59:59+00:00 |

*참고: 전체 7개 컬럼 중 5개만 표시*

---

### 17. ✅ response_org_designated_agendas

**카테고리**: response_tracking
**상태**: 성공
**Note**: 
**라우팅 타입**: sql
**에이전트 처리**: 조회 결과를 분석하여 요청사항에 맞게 정리해 주세요.

**자연어 질의**:
1. response_org가 지정된 agenda (original)
2. 응답 기관이 특별히 지정된 의제들을 보여주세요 (similar1)
3. 특정 기관에게 답변 요청한 안건이 뭐가 있나요? (similar2)
   ... 외 2개

**파라미터 정보**:
- 필수 파라미터: 없음

**플레이스홀더**: 없음

**SQL 쿼리**:
```sql
SELECT agenda_code, agenda_base_version, subject, sent_time, 
                       body as content, agenda_panel
                FROM agenda_chair
                WHERE mail_type = 'REQUEST'
                AND (body LIKE '%specific organization%' OR body LIKE '%designated%' 
                     ...
```

**실행 결과**: 0개 행 반환

---


## 테스트 설정

- **파일**: query_templates_group_003.json
- **테스트 일시**: 2025-07-30T11:05:25.205188
- **데이터베이스 경로**: data/iacsgraph.db
