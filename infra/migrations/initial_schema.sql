-- 초기 데이터베이스 스키마

-- 계정 정보 테이블
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL UNIQUE,
    user_name TEXT NOT NULL,
    email TEXT,

    -- Enrollment 파일 관련
    enrollment_file_path TEXT,
    enrollment_file_hash TEXT,

    -- OAuth 설정
    oauth_client_id TEXT,
    oauth_client_secret TEXT,
    oauth_tenant_id TEXT,
    oauth_redirect_uri TEXT,

    -- 계정 상태 및 인증 타입
    status TEXT DEFAULT 'active',
    auth_type TEXT DEFAULT 'Authorization Code Flow',

    -- 위임된 권한 (JSON 형태)
    delegated_permissions TEXT,

    -- 토큰 정보
    access_token TEXT,
    refresh_token TEXT,
    token_expiry TIMESTAMP,

    -- 임시 인증 세션 (JSON 형태: state, session_id, auth_url, expires_at 등)
    temp_auth_session TEXT,

    -- 메타데이터
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_sync_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 메일 히스토리 테이블 (사용 안함 - 주석 처리)
-- CREATE TABLE IF NOT EXISTS mail_history (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     account_id INTEGER NOT NULL,
--     message_id TEXT NOT NULL UNIQUE,
--     received_time TIMESTAMP NOT NULL,
--     subject TEXT,
--     sender TEXT,
--     keywords TEXT, -- JSON 형태의 텍스트
--     processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     content_hash TEXT, -- 중복 메일 검사를 위한 내용 해시
--     FOREIGN KEY (account_id) REFERENCES accounts (id)
-- );

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

-- 계정 감사 로그 테이블
CREATE TABLE IF NOT EXISTS account_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    old_values TEXT,
    new_values TEXT,
    changed_by TEXT,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts (id)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts (user_id);
CREATE INDEX IF NOT EXISTS idx_accounts_email ON accounts (email);
CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts (status);
CREATE INDEX IF NOT EXISTS idx_accounts_enrollment_hash ON accounts (enrollment_file_hash);
CREATE INDEX IF NOT EXISTS idx_account_audit_logs_account_id ON account_audit_logs (account_id);
CREATE INDEX IF NOT EXISTS idx_account_audit_logs_timestamp ON account_audit_logs (timestamp);
CREATE INDEX IF NOT EXISTS idx_account_audit_logs_action ON account_audit_logs (action);
-- mail_history 인덱스 (사용 안함 - 주석 처리)
-- CREATE INDEX IF NOT EXISTS idx_mail_history_message_id ON mail_history (message_id);
-- CREATE INDEX IF NOT EXISTS idx_mail_history_received_time ON mail_history (received_time);
-- CREATE INDEX IF NOT EXISTS idx_mail_history_content_hash ON mail_history (content_hash);
CREATE INDEX IF NOT EXISTS idx_processing_logs_run_id ON processing_logs (run_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_timestamp ON processing_logs (timestamp);
