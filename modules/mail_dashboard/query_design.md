# Email Dashboard 모듈 요구사항

## 1. 데이터 저장 구조

### email_dashboard 모듈 추가
기존 인프라를 최대한 활용하여 다음 3개의 테이블을 생성합니다.

### 테이블 구조

#### 1) email_agendas_chair (의장 발송 아젠다)
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| panel_id | string | 패널 식별자 |
| agenda_no | string | 아젠다 번호 (Primary Key) |
| send_time | timestamp | 발송 시간 |
| deadline | timestamp | 응답 마감 시간 |
| mail_type | string | 메일 유형 (REQUEST, RESPONSE, NOTIFICATION, COMPLETED, OTHER) |
| decision_status | string | 결정 상태 ( created, comment, consolidated, review, decision) |
| body_content | text | 메일 본문 내용 |

#### 2) email_agenda_member_responses (멤버 응답 내용)
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| agenda_no | string | 아젠다 번호 (Primary Key, Foreign Key) |
| ABS | text | ABS 응답 내용 (NULL 가능) |
| BV | text | BV 응답 내용 (NULL 가능) |
| CCS | text | CCS 응답 내용 (NULL 가능) |
| CRS | text | CRS 응답 내용 (NULL 가능) |
| DNV | text | DNV 응답 내용 (NULL 가능) |
| IRS | text | IRS 응답 내용 (NULL 가능) |
| KR | text | KR 응답 내용 (NULL 가능) |
| NK | text | NK 응답 내용 (NULL 가능) |
| PRS | text | PRS 응답 내용 (NULL 가능) |
| RINA | text | RINA 응답 내용 (NULL 가능) |
| IL | text | IL 응답 내용 (NULL 가능) |

#### 3) email_agenda_member_response_times (멤버 응답 시간)
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| agenda_no | string | 아젠다 번호 (Primary Key, Foreign Key) |
| ABS | timestamp | ABS 수신 시간 (NULL 가능) |
| BV | timestamp | BV 수신 시간 (NULL 가능) |
| CCS | timestamp | CCS 수신 시간 (NULL 가능) |
| CRS | timestamp | CRS 수신 시간 (NULL 가능) |
| DNV | timestamp | DNV 수신 시간 (NULL 가능) |
| IRS | timestamp | IRS 수신 시간 (NULL 가능) |
| KR | timestamp | KR 수신 시간 (NULL 가능) |
| NK | timestamp | NK 수신 시간 (NULL 가능) |
| PRS | timestamp | PRS 수신 시간 (NULL 가능) |
| RINA | timestamp | RINA 수신 시간 (NULL 가능) |
| IL | timestamp | IL 수신 시간 (NULL 가능) |

## 2. 데이터 처리 로직

### 이메일 분류 및 저장

#### 아젠다 메일 처리
- **대상**: 의장이 발송한 아젠다 메일
- **저장 위치**: `email_agendas_chair` 테이블
- **저장 내용**: 패널 ID, 아젠다 번호, 발송 시간, 마감 시간, 메일 유형, 상태, 본문
- **처리 시**: 동시에 `email_agenda_member_responses`와 `email_agenda_member_response_times`에 해당 agenda_no로 빈 레코드 생성

#### 코멘트 메일 처리
- **대상**: 멤버 기관이 발송한 응답 메일
- **처리 순서**:
  1. 발신 기관 식별 (ABS, BV, CCS 등 중 하나)
  2. 해당 agenda_no 확인
  3. `email_agenda_member_responses`의 해당 기관 컬럼에 응답 내용 UPDATE
  4. `email_agenda_member_response_times`의 해당 기관 컬럼에 수신 시간 UPDATE
  5. 중복 응답 시 기존 내용을 덮어쓰기 (최신 응답만 유지)

## 3. 검색 기능 요구사항

### 3.1 기본 검색 기능

#### 기간별 아젠다 조회
- 특정 기간에 생성된 아젠다 목록 (send_time 기준)
- 특정 기간에 마감되는 아젠다 목록 (deadline 기준)
- 특정 패널의 아젠다 목록 (panel_id 필터)

#### 응답 현황 조회
- 특정 기간 내 각 멤버들이 응답한 아젠다 목록 및 응답 내용
- 특정 기간 내 기관별(KR, ABS, BV 등) 응답 건수 및 내용
- 현재 미완료 아젠다 목록 (deadline > 현재시간 AND decision_status = 'PENDING')

#### 진행중 아젠다 분석
- 데드라인이 지나지 않은 아젠다별 응답/미응답 멤버 구분
  - 응답: 해당 기관 컬럼이 NOT NULL
  - 미응답: 해당 기관 컬럼이 NULL
- 응답한 기관들의 메일 내용 조회

### 3.2 고급 검색 기능

#### 통계 조회
- 기관별 응답률 통계 (전체 아젠다 대비 응답 건수)
- 기관별 평균 응답 소요 시간 (응답 시간 - 발송 시간)
- 아젠다별 응답 완료율 (11개 기관 중 응답 기관 수)

#### 알림 기능용 조회
- 데드라인 임박 미응답 아젠다 (예: 24시간 이내)
  - 각 기관별 미응답 아젠다만 추출
- 특정 기관의 미응답 아젠다 목록
- 오늘 발송된 아젠다 목록
- 응답 독촉 대상 (데드라인 50% 경과 & 응답률 50% 미만)

#### 상세 분석
- 특정 아젠다의 응답 타임라인 (시간순 응답 현황)
- 기관별 응답 패턴 분석
  - 평균 응답 시간
  - 응답률
  - 주/월별 응답 추이
- 재촉 메일(REMINDER) 발송 대상 자동 추출

### 3.3 대시보드 표시용 조회

#### 실시간 현황
- 진행중인 아젠다 수 (PENDING 상태)
- 오늘 마감 아젠다 수
- 전체 응답률 (총 응답 수 / (아젠다 수 × 11개 기관))
- 기관별 미응답 건수

#### 기간별 분석
- 월별/주별 아젠다 발송 추이
- 기관별 응답 성과 (응답률, 평균 응답 시간)
- 평균 처리 시간 변화 추이
- 메일 유형별(AGENDA/REMINDER/FINAL_CALL) 발송 통계

## 4. 데이터 무결성 및 성능 고려사항

### 데이터 무결성
- 아젠다 생성 시 자동으로 응답 테이블에 빈 레코드 생성 (트리거 사용)
- 응답 내용은 UPDATE만 허용 (INSERT 방지)
- 삭제는 CASCADE 설정으로 연관 데이터 동시 삭제

### 인덱스 전략
#### 단일 인덱스
- `agenda_no` (모든 테이블의 Primary/Foreign Key)
- `send_time` (발송일 기준 검색)
- `deadline` (마감일 기준 검색)
- `decision_status` (상태별 필터링)
- `panel_id` (패널별 조회)

#### 복합 인덱스
- `(deadline, decision_status)` - 미완료 임박 아젠다 조회
- `(panel_id, send_time)` - 패널별 기간 조회
- `(decision_status, deadline)` - 진행중 아젠다 마감순 정렬

### 쿼리 최적화 팁
- 기관별 응답 여부는 CASE WHEN 구문 활용
- 응답률 계산은 뷰(View) 생성 고려
- 대시보드용 통계는 캐싱 적용 권장

## 5. 추가 개선 제안

### 향후 확장 고려사항
1. **응답 이력 관리**: 현재는 최신 응답만 저장하지만, 향후 모든 응답 이력 저장 필요 시 별도 이력 테이블 추가
2. **파일 첨부**: 응답에 첨부 파일이 있을 경우를 위한 첨부 파일 테이블 추가
3. **알림 로그**: 리마인더 발송 이력 관리를 위한 로그 테이블
4. **기관 관리**: 기관 정보(이메일, 담당자 등) 관리를 위한 마스터 테이블

### 보안 고려사항
- 메일 본문 암호화 저장 검토
- 접근 권한별 조회 범위 제한
- 개인정보 마스킹 처리