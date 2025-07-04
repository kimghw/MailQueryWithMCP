-- Email Dashboard 모듈 테이블 생성 스크립트
-- 버전: 3.0.0
-- 생성일: 2025-01-04
-- 변경사항: agenda_sequence/agenda_version 제거, round_version만 유지

-- 1. 의장 발송 아젠다 정보 테이블
CREATE TABLE IF NOT EXISTS email_agendas_chair (
    panel_id TEXT NOT NULL,
    agenda_no TEXT NOT NULL PRIMARY KEY,
    round_no TEXT,
    round_version TEXT,
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

-- 2. 멤버 기관 응답 내용 테이블
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

-- 3. 멤버 기관 응답 시간 테이블
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

-- 기본 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_panel_id ON email_agendas_chair (panel_id);
CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_send_time ON email_agendas_chair (send_time);
CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_deadline ON email_agendas_chair (deadline);
CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_mail_type ON email_agendas_chair (mail_type);
CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_decision_status ON email_agendas_chair (decision_status);
CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_round_no ON email_agendas_chair (round_no);

-- 복합 인덱스 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_deadline_status 
ON email_agendas_chair (deadline, decision_status);

CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_panel_time 
ON email_agendas_chair (panel_id, send_time);

CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_status_deadline 
ON email_agendas_chair (decision_status, deadline);

CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_round_version 
ON email_agendas_chair (panel_id, round_no, round_version);

-- 응답 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_email_agenda_member_responses_agenda_no 
ON email_agenda_member_responses (agenda_no);

CREATE INDEX IF NOT EXISTS idx_email_agenda_member_response_times_agenda_no 
ON email_agenda_member_response_times (agenda_no);