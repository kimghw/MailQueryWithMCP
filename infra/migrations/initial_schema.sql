-- 초기 데이터베이스 스키마

-- 계정 정보 테이블
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL UNIQUE,
    user_name TEXT NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    token_expiry TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_sync_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 메일 히스토리 테이블
CREATE TABLE IF NOT EXISTS mail_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    message_id TEXT NOT NULL UNIQUE,
    received_time TIMESTAMP NOT NULL,
    subject TEXT,
    sender TEXT,
    keywords TEXT, -- JSON 형태의 텍스트
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content_hash TEXT, -- 중복 메일 검사를 위한 내용 해시
    FOREIGN KEY (account_id) REFERENCES accounts (id)
);

-- 처리 로그 테이블
CREATE TABLE IF NOT EXISTS processing_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    account_id INTEGER,
    log_level TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts (id)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts (user_id);
CREATE INDEX IF NOT EXISTS idx_mail_history_message_id ON mail_history (message_id);
CREATE INDEX IF NOT EXISTS idx_mail_history_received_time ON mail_history (received_time);
CREATE INDEX IF NOT EXISTS idx_mail_history_content_hash ON mail_history (content_hash);
CREATE INDEX IF NOT EXISTS idx_processing_logs_run_id ON processing_logs (run_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_timestamp ON processing_logs (timestamp);

-- Email Dashboard 모듈을 위한 데이터베이스 스키마
-- 4개의 테이블로 구성: email_panels, panel_decisions, panel_responses, panel_response_times

-- 1. 이메일 패널 정보 테이블
CREATE TABLE IF NOT EXISTS email_panels (
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

-- 2. 패널 결정 사항 테이블 (각 기관의 투표/결정 여부)
CREATE TABLE IF NOT EXISTS panel_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agenda_no TEXT NOT NULL,
    -- 각 기관의 결정 여부 (TRUE/FALSE, 초기값은 FALSE)
    ABS BOOLEAN NOT NULL DEFAULT FALSE,
    BV BOOLEAN NOT NULL DEFAULT FALSE,
    CCS BOOLEAN NOT NULL DEFAULT FALSE,
    CRS BOOLEAN NOT NULL DEFAULT FALSE,
    DNV BOOLEAN NOT NULL DEFAULT FALSE,
    IRS BOOLEAN NOT NULL DEFAULT FALSE,
    KR BOOLEAN NOT NULL DEFAULT FALSE,
    NK BOOLEAN NOT NULL DEFAULT FALSE,
    PRS BOOLEAN NOT NULL DEFAULT FALSE,
    RINA BOOLEAN NOT NULL DEFAULT FALSE,
    IL BOOLEAN NOT NULL DEFAULT FALSE,
    TL BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 외래키 제약
    FOREIGN KEY (agenda_no) REFERENCES email_panels (agenda_no) ON DELETE CASCADE,
    -- 유니크 제약 (agenda_no당 하나의 레코드만)
    UNIQUE (agenda_no)
);

-- 3. 패널 응답 내용 테이블 (각 기관의 응답 텍스트)
CREATE TABLE IF NOT EXISTS panel_responses (
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
    
    -- 외래키 제약
    FOREIGN KEY (agenda_no) REFERENCES email_panels (agenda_no) ON DELETE CASCADE,
    -- 복합 유니크 제약 (agenda_no + sequence_no)
    UNIQUE (agenda_no, sequence_no)
);

-- 4. 패널 응답 시간 테이블 (각 기관의 응답 수신 시간)
CREATE TABLE IF NOT EXISTS panel_response_times (
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
    
    -- 외래키 제약
    FOREIGN KEY (agenda_no) REFERENCES email_panels (agenda_no) ON DELETE CASCADE,
    -- 복합 유니크 제약 (agenda_no + sequence_no)
    UNIQUE (agenda_no, sequence_no)
);

-- 인덱스 생성 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_email_panels_panel_id ON email_panels (panel_id);
CREATE INDEX IF NOT EXISTS idx_email_panels_agenda_no ON email_panels (agenda_no);
CREATE INDEX IF NOT EXISTS idx_email_panels_send_time ON email_panels (send_time);
CREATE INDEX IF NOT EXISTS idx_email_panels_deadline ON email_panels (deadline);
CREATE INDEX IF NOT EXISTS idx_email_panels_mail_type ON email_panels (mail_type);
CREATE INDEX IF NOT EXISTS idx_email_panels_decision_status ON email_panels (decision_status);

CREATE INDEX IF NOT EXISTS idx_panel_decisions_agenda_no ON panel_decisions (agenda_no);

CREATE INDEX IF NOT EXISTS idx_panel_responses_agenda_no ON panel_responses (agenda_no);
CREATE INDEX IF NOT EXISTS idx_panel_responses_agenda_sequence ON panel_responses (agenda_no, sequence_no);

CREATE INDEX IF NOT EXISTS idx_panel_response_times_agenda_no ON panel_response_times (agenda_no);
CREATE INDEX IF NOT EXISTS idx_panel_response_times_agenda_sequence ON panel_response_times (agenda_no, sequence_no);

-- 뷰 생성 (자주 사용되는 조회를 위한 뷰)
-- 패널별 응답 현황 요약 뷰
CREATE VIEW IF NOT EXISTS v_panel_response_summary AS
SELECT 
    p.panel_id,
    p.agenda_no,
    p.mail_type,
    p.decision_status,
    p.send_time,
    p.deadline,
    -- 각 기관의 응답 여부 집계
    CAST(d.ABS + d.BV + d.CCS + d.CRS + d.DNV + d.IRS + d.KR + d.NK + d.PRS + d.RINA + d.IL + d.TL AS INTEGER) as total_responses,
    12 as total_organizations,
    CASE 
        WHEN CAST(d.ABS + d.BV + d.CCS + d.CRS + d.DNV + d.IRS + d.KR + d.NK + d.PRS + d.RINA + d.IL + d.TL AS INTEGER) = 12 THEN 'COMPLETE'
        WHEN CAST(d.ABS + d.BV + d.CCS + d.CRS + d.DNV + d.IRS + d.KR + d.NK + d.PRS + d.RINA + d.IL + d.TL AS INTEGER) > 0 THEN 'PARTIAL'
        ELSE 'NONE'
    END as response_status
FROM email_panels p
LEFT JOIN panel_decisions d ON p.agenda_no = d.agenda_no;

-- 마감 임박 패널 뷰 (24시간 이내)
CREATE VIEW IF NOT EXISTS v_upcoming_deadlines AS
SELECT 
    p.*,
    CASE 
        WHEN julianday(p.deadline) - julianday(CURRENT_TIMESTAMP) <= 1 THEN 'URGENT'
        WHEN julianday(p.deadline) - julianday(CURRENT_TIMESTAMP) <= 3 THEN 'SOON'
        ELSE 'NORMAL'
    END as urgency_level,
    ROUND((julianday(p.deadline) - julianday(CURRENT_TIMESTAMP)) * 24, 2) as hours_remaining
FROM email_panels p
WHERE p.decision_status NOT IN ('COMPLETED', 'CANCELLED')
  AND p.deadline > CURRENT_TIMESTAMP
ORDER BY p.deadline ASC;