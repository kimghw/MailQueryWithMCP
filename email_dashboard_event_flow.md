# Email Dashboard 이벤트 분류 체계

## 📧 이벤트 처리 흐름

### 1. email.received 이벤트 수신
Kafka 토픽 `email.received`에서 이벤트를 수신하면 다음과 같이 처리됩니다:

```
email.received 이벤트
    ↓
EmailDashboardEventProcessor.process_email_event()
    ↓
1️⃣ agenda_all 테이블에 모든 이벤트 저장 (로그 목적)
    ↓
2️⃣ 이벤트 분류 시작
```

### 2. 이벤트 분류 기준

#### A. agenda_code 확인
```python
if not event.event_info.agenda_code:
    → agenda_pending 테이블에 저장 (reason: "no_agenda_code")
    → 처리 종료
```

#### B. sender_type에 따른 분류
```python
if event.event_info.sender_type == "CHAIR":
    → 의장 발송 메일 처리
elif event.event_info.sender_type == "MEMBER":
    → 멤버 응답 처리
else:
    → agenda_pending 테이블에 저장 (reason: "unknown_sender_type")
```

### 3. 의장 발송 메일 처리 (CHAIR)

```
CHAIR 타입 이벤트
    ↓
agenda_chair 테이블에 저장/업데이트
    ↓
agenda_responses_content 테이블 초기화 (모든 조직 NULL)
    ↓
agenda_responses_receivedtime 테이블 초기화 (모든 조직 NULL)
```

**저장되는 정보:**
- agenda_base_version (PK)
- agenda_code
- 발송 정보 (시간, 조직, 제목, 본문 등)
- 마감일 정보
- 패널/연도/번호 정보

### 4. 멤버 응답 처리 (MEMBER)

```
MEMBER 타입 이벤트
    ↓
응답 조직 확인 (response_org 또는 sender_organization)
    ↓
조직 코드 유효성 검증 (ORGANIZATIONS 리스트)
    ↓
해당 agenda_base_version이 agenda_chair에 존재하는지 확인
    ↓
존재하면: 응답 내용과 시간 업데이트
존재하지 않으면: agenda_pending (reason: "agenda_not_found")
```

**업데이트되는 정보:**
- agenda_responses_content 테이블의 해당 조직 컬럼
- agenda_responses_receivedtime 테이블의 해당 조직 컬럼
- agenda_chair의 decision_status 자동 업데이트

### 5. 테이블별 역할

#### 📊 agenda_all
- **목적**: 모든 이벤트의 원본 로그 보관
- **특징**: 중복 허용, 삭제 없음
- **용도**: 감사, 디버깅, 통계

#### 📋 agenda_chair
- **목적**: 의장이 발송한 아젠다 관리
- **특징**: agenda_base_version이 PK
- **상태**: created → comment → consolidated

#### ✅ agenda_responses_content
- **목적**: 각 조직의 응답 내용 저장
- **구조**: 조직별 컬럼 (ABS, BV, CCS, CRS, DNV, IRS, KR, LR, NK, PRS, RINA, IL, TL)

#### ⏰ agenda_responses_receivedtime
- **목적**: 각 조직의 응답 시간 기록
- **구조**: 조직별 컬럼 (응답 시간)

#### ⚠️ agenda_pending
- **목적**: 처리 실패한 이벤트 보관
- **이유**:
  - no_agenda_code: agenda_code 없음
  - invalid_organization: 유효하지 않은 조직
  - agenda_not_found: 해당 아젠다 없음
  - unknown_sender_type: 알 수 없는 발신자 타입
  - validation_error: 데이터 형식 오류
  - processing_error: 처리 중 오류

### 6. decision_status 자동 업데이트

```
응답 수 = 0 → "created"
응답 수 < 전체 조직 수 → "comment"
응답 수 = 전체 조직 수 → "consolidated"
```

### 7. 유효한 조직 코드 (ORGANIZATIONS)

```python
ORGANIZATIONS = [
    "ABS",   # American Bureau of Shipping
    "BV",    # Bureau Veritas
    "CCS",   # China Classification Society
    "CRS",   # Croatian Register of Shipping
    "DNV",   # Det Norske Veritas
    "IRS",   # Indian Register of Shipping
    "KR",    # Korean Register
    "LR",    # Lloyd's Register
    "NK",    # Nippon Kaiji Kyokai (ClassNK)
    "PRS",   # Polish Register of Shipping
    "RINA",  # Registro Italiano Navale
    "IL",    # IACS Limited
    "TL",    # Türk Loydu
]
```

### 8. 이벤트 재처리

미처리 이벤트는 다음과 같이 재처리할 수 있습니다:

```python
# 특정 이벤트 재시도
orchestrator.retry_pending_event(event_id)

# 모든 미처리 이벤트 재처리
service.process_pending_events()
```

## 🔍 디버깅 팁

1. **이벤트가 처리되지 않을 때**
   - agenda_all 테이블에서 event_id로 검색
   - agenda_pending 테이블에서 error_reason 확인

2. **응답이 기록되지 않을 때**
   - agenda_base_version 매칭 확인
   - 조직 코드 유효성 확인
   - agenda_chair 테이블에 해당 아젠다 존재 여부 확인

3. **중복 오류 발생 시**
   - event_id가 이미 agenda_all에 있는지 확인
   - processed 상태 확인
