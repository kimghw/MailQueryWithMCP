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
CREATE INDEX IF NOT EXISTS idx_processing_logs_run_id ON processing_logs (run_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_timestamp ON processing_logs (timestamp);
