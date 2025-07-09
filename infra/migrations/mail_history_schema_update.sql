-- mail_history 테이블 스키마 업데이트
-- keywords, content_hash 컬럼 제거
-- 생성일: 2025-01-09

-- 기존 데이터 백업을 위한 임시 테이블 생성
CREATE TABLE IF NOT EXISTS mail_history_backup AS 
SELECT * FROM mail_history;

-- 새로운 mail_history 테이블 생성 (단순화된 스키마)
DROP TABLE IF EXISTS mail_history_new;
CREATE TABLE mail_history_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    message_id TEXT NOT NULL UNIQUE,
    received_time TIMESTAMP NOT NULL,
    subject TEXT,
    sender TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts (id)
);

-- 기존 데이터를 새 테이블로 복사 (keywords, content_hash 제외)
INSERT INTO mail_history_new (
    id, account_id, message_id, received_time, 
    subject, sender, processed_at
)
SELECT 
    id, account_id, message_id, received_time,
    subject, sender, processed_at
FROM mail_history;

-- 기존 테이블 삭제 및 새 테이블로 교체
DROP TABLE mail_history;
ALTER TABLE mail_history_new RENAME TO mail_history;

-- 인덱스 재생성
CREATE INDEX IF NOT EXISTS idx_mail_history_message_id ON mail_history (message_id);
CREATE INDEX IF NOT EXISTS idx_mail_history_received_time ON mail_history (received_time);
CREATE INDEX IF NOT EXISTS idx_mail_history_account_id ON mail_history (account_id);

-- 백업 테이블 정리 (필요시 주석 해제)
-- DROP TABLE IF EXISTS mail_history_backup;
