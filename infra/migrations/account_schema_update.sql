-- Account 모듈을 위한 스키마 확장
-- accounts 테이블에 필요한 필드 추가

-- 기존 accounts 테이블에 새로운 컬럼 추가
ALTER TABLE accounts ADD COLUMN email TEXT;
ALTER TABLE accounts ADD COLUMN enrollment_file_path TEXT;
ALTER TABLE accounts ADD COLUMN enrollment_file_hash TEXT;
ALTER TABLE accounts ADD COLUMN oauth_client_id TEXT;
ALTER TABLE accounts ADD COLUMN oauth_client_secret TEXT; -- 암호화된 데이터
ALTER TABLE accounts ADD COLUMN oauth_tenant_id TEXT;
ALTER TABLE accounts ADD COLUMN oauth_redirect_uri TEXT;
ALTER TABLE accounts ADD COLUMN status TEXT NOT NULL DEFAULT 'INACTIVE';
ALTER TABLE accounts ADD COLUMN auth_type TEXT;
ALTER TABLE accounts ADD COLUMN delegated_permissions TEXT; -- JSON 형태

-- 기존 인덱스 외 추가 인덱스
CREATE INDEX IF NOT EXISTS idx_accounts_email ON accounts (email);
CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts (status);
CREATE INDEX IF NOT EXISTS idx_accounts_enrollment_path ON accounts (enrollment_file_path);

-- 감사 로그 테이블 추가
CREATE TABLE IF NOT EXISTS account_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,
    action TEXT NOT NULL,
    old_values TEXT, -- JSON 형태
    new_values TEXT, -- JSON 형태
    changed_by TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts (id)
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_account_id ON account_audit_logs (account_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON account_audit_logs (timestamp);
