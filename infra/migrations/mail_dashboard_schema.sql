-- Email Dashboard 모듈을 위한 데이터베이스 스키마
-- 3개의 테이블로 구성: email_agendas_chair, email_agenda_member_responses, email_agenda_member_status_times

-- 1. 이메일 패널 정보 테이블
CREATE TABLE IF NOT EXISTS email_agendas_chair (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    panel_id TEXT NOT NULL UNIQUE,
    agenda_no TEXT NOT NULL UNIQUE,
    send_time TIMESTAMP NOT NULL,
    deadline TIMESTAMP NOT NULL,
    mail_type TEXT NOT NULL,
    decision_status TEXT NOT NULL DEFAULT 'PENDING',
    body_content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 제약조건
    CONSTRAINT chk_mail_type CHECK (mail_type IN ('BALLOT', 'INFORMATION', 'REQUEST', 'NOTIFICATION')),
    CONSTRAINT chk_decision_status CHECK (decision_status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'))
);

-- 2. 패널 응답 내용 테이블 (각 기관의 응답 텍스트)
CREATE TABLE IF NOT EXISTS email_agenda_member_responses (  -- 오타 수정: reponses → responses
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agenda_no TEXT NOT NULL,
    sequence_no INTEGER NOT NULL,
    -- 각 기관의 응답 내용 (텍스트)
    ABS TEXT,
    BV TEXT,
    CCS TEXT,
    CRS TEXT,
    DNV TEXT,
    IRS TEXT,
    KR TEXT,
    NK TEXT,
    PRS TEXT,
    IL TEXT,
    TL TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 외래키 제약 (테이블명 수정)
    FOREIGN KEY (agenda_no) REFERENCES email_agendas_chair (agenda_no) ON DELETE CASCADE,
    -- 복합 유니크 제약 (agenda_no + sequence_no)
    UNIQUE (agenda_no, sequence_no)
);

-- 3. 패널 응답 시간 테이블 (각 기관의 응답 수신 시간)
CREATE TABLE IF NOT EXISTS email_agenda_member_status_times (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agenda_no TEXT NOT NULL,
    sequence_no INTEGER NOT NULL,
    -- 각 기관의 응답 수신 시간
    ABS TIMESTAMP,
    BV TIMESTAMP,
    CCS TIMESTAMP,
    CRS TIMESTAMP,
    DNV TIMESTAMP,
    IRS TIMESTAMP,
    KR TIMESTAMP,
    NK TIMESTAMP,
    PRS TIMESTAMP,
    IL TIMESTAMP,
    TL TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 외래키 제약 (테이블명 수정)
    FOREIGN KEY (agenda_no) REFERENCES email_agendas_chair (agenda_no) ON DELETE CASCADE,
    -- 복합 유니크 제약 (agenda_no + sequence_no)
    UNIQUE (agenda_no, sequence_no)
);

-- 인덱스 생성 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_panel_id ON email_agendas_chair (panel_id);
CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_agenda_no ON email_agendas_chair (agenda_no);
CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_send_time ON email_agendas_chair (send_time);
CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_deadline ON email_agendas_chair (deadline);
CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_mail_type ON email_agendas_chair (mail_type);
CREATE INDEX IF NOT EXISTS idx_email_agendas_chair_decision_status ON email_agendas_chair (decision_status);

CREATE INDEX IF NOT EXISTS idx_email_agenda_member_responses_agenda_no ON email_agenda_member_responses (agenda_no);
CREATE INDEX IF NOT EXISTS idx_email_agenda_member_responses_agenda_sequence ON email_agenda_member_responses (agenda_no, sequence_no);

CREATE INDEX IF NOT EXISTS idx_email_agenda_member_status_times_agenda_no ON email_agenda_member_status_times (agenda_no);
CREATE INDEX IF NOT EXISTS idx_email_agenda_member_status_times_agenda_sequence ON email_agenda_member_status_times (agenda_no, sequence_no);