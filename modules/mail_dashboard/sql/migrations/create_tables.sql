-- Email Dashboard 모듈 테이블 생성 스크립트
-- 버전: 4.0.0
-- 생성일: 2025-01-04
-- 변경사항: 미처리 이벤트 저장 테이블 추가

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

-- 4. 미처리 이벤트 테이블 (신규)
-- 4. 미처리 이벤트 테이블 (신규)
CREATE TABLE IF NOT EXISTS email_events_unprocessed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    mail_id TEXT,
    sender_type TEXT,
    sender_organization TEXT,
    agenda_no TEXT,
    send_time TIMESTAMP,
    subject TEXT,
    summary TEXT,
    keywords TEXT, -- JSON 배열로 저장
    mail_type TEXT,
    decision_status TEXT,
    has_deadline BOOLEAN DEFAULT FALSE,
    deadline TIMESTAMP,
    unprocessed_reason TEXT NOT NULL, -- 미처리 사유
    raw_event_data TEXT NOT NULL, -- 전체 이벤트 JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP
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

-- 미처리 이벤트 테이블 인덱스 (신규)
CREATE INDEX IF NOT EXISTS idx_unprocessed_event_id 
ON email_events_unprocessed (event_id);

CREATE INDEX IF NOT EXISTS idx_unprocessed_sender_org 
ON email_events_unprocessed (sender_organization);

CREATE INDEX IF NOT EXISTS idx_unprocessed_agenda_no 
ON email_events_unprocessed (agenda_no);

CREATE INDEX IF NOT EXISTS idx_unprocessed_reason 
ON email_events_unprocessed (unprocessed_reason);

CREATE INDEX IF NOT EXISTS idx_unprocessed_processed 
ON email_events_unprocessed (processed);

CREATE INDEX IF NOT EXISTS idx_unprocessed_created_at 
ON email_events_unprocessed (created_at);
