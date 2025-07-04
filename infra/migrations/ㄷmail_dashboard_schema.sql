-- Email Dashboard 모듈을 위한 데이터베이스 스키마
-- 의장 아젠다와 멤버 응답을 관리하는 3개 테이블

-- 1. 의장 발송 아젠다 정보 테이블
CREATE TABLE IF NOT EXISTS email_agendas_chair (
    panel_id TEXT NOT NULL,
    agenda_no TEXT NOT NULL PRIMARY KEY,
    round_no TEXT,
    agenda_sequence INTEGER,
    send_time TIMESTAMP NOT NULL,
    deadline TIMESTAMP,
    mail_type TEXT NOT NULL,
    decision_status TEXT NOT NULL DEFAULT 'created',
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 제약조건
    CHECK (mail_type IN ('REQUEST', 'RESPONSE', 'NOTIFICATION', 'COMPLETED', 'OTHER')),
    CHECK (decision_status IN ('created', 'comment', 'consolidated', 'review', 'decision'))
);

-- 2. 멤버 기관 응답 내용 테이블 (각 기관의 응답 텍스트)
CREATE TABLE IF NOT EXISTS email_agenda_member_responses (
    agenda_no TEXT NOT NULL PRIMARY KEY,
    -- 11개 기관의 응답 내용 (텍스트)
    ABS TEXT,
    BV TEXT,
    CCS TEXT,
    CRS TEXT,
    DNV TEXT,
    IRS TEXT,
    KR TEXT,
    NK TEXT,
    PRS TEXT,
    RINA TEXT,
    IL TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 외래키 제약
    FOREIGN KEY (agenda_no) REFERENCES email_agendas_chair (agenda_no) ON DELETE CASCADE
);

-- 3. 멤버 기관 응답 시간 테이블 (각 기관의 응답 수신 시간)
CREATE TABLE IF NOT EXISTS email_agenda_member_response_times (
    agenda_no TEXT NOT NULL PRIMARY KEY,
    -- 11개 기관의 응답 수신 시간
    ABS TIMESTAMP,
    BV TIMESTAMP,
    CCS TIMESTAMP,
    CRS TIMESTAMP,
    DNV TIMESTAMP,
    IRS TIMESTAMP,
    KR TIMESTAMP,
    NK TIMESTAMP,
    PRS TIMESTAMP,
    RINA TIMESTAMP,
    IL TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 외래키 제약
    FOREIGN KEY (agenda_no) REFERENCES email_agendas_chair (agenda_no) ON DELETE CASCADE
);

-- 인덱스 생성 (성능 최적화)

-- 기본 조회 인덱스
CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_panel_id ON email_agendas_chair (panel_id);
CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_send_time ON email_agendas_chair (send_time);
CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_deadline ON email_agendas_chair (deadline);
CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_mail_type ON email_agendas_chair (mail_type);
CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_decision_status ON email_agendas_chair (decision_status);
CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_round_no ON email_agendas_chair (round_no);

-- 복합 인덱스 (대시보드 쿼리 최적화)
CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_deadline_status 
ON email_agendas_chair (deadline, decision_status);

CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_panel_time 
ON email_agendas_chair (panel_id, send_time);

CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_status_deadline 
ON email_agendas_chair (decision_status, deadline);

CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_round_sequence 
ON email_agendas_chair (panel_id, round_no, agenda_sequence);

-- 응답 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_email_agenda_member_responses_agenda_no 
ON email_agenda_member_responses (agenda_no);

CREATE INDEX IF NOT EXISTS idx_email_agenda_member_response_times_agenda_no 
ON email_agenda_member_response_times (agenda_no);

-- 스키마 버전 기록
INSERT OR REPLACE INTO schema_versions (module_name, version, applied_at) 
VALUES ('email_dashboard', '1.0.0', CURRENT_TIMESTAMP);

-- 주석 추가 (SQLite 스타일 주석)
-- 
-- email_agendas_chair: 의장이 발송한 아젠다 정보
-- - panel_id: 패널 식별자 (예: "PANEL001")
-- - agenda_no: 아젠다 고유 번호 (예: "AGENDA-2025-001")
-- - round_no: 회차 번호 (예: "016")
-- - agenda_sequence: 같은 회차 내 순서 (1, 2, 3...)
-- - send_time: 아젠다 발송 시간
-- - deadline: 응답 마감 시간
-- - mail_type: 메일 유형 (REQUEST, RESPONSE, NOTIFICATION, COMPLETED, OTHER)
-- - decision_status: 결정 상태 (created, comment, consolidated, review, decision)
-- - summary: 아젠다 요약 내용
--
-- email_agenda_member_responses: 11개 기관의 응답 내용
-- - 각 기관별로 TEXT 컬럼 (ABS, BV, CCS, CRS, DNV, IRS, KR