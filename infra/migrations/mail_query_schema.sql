-- Mail Query 모듈용 데이터베이스 스키마 (단순화)
-- 메일 조회 기본 로그만 기록

-- 메일 조회 로그 테이블 (기본 로깅용)
CREATE TABLE IF NOT EXISTS query_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    query_type TEXT NOT NULL DEFAULT 'mail_query',
    odata_filter TEXT,
    select_fields TEXT,
    top INTEGER NOT NULL DEFAULT 50,
    skip INTEGER NOT NULL DEFAULT 0,
    result_count INTEGER NOT NULL DEFAULT 0,
    execution_time_ms INTEGER NOT NULL DEFAULT 0,
    has_error BOOLEAN NOT NULL DEFAULT FALSE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 기본 제약조건
    CONSTRAINT chk_query_type CHECK (query_type IN ('mail_query', 'mail_search')),
    CONSTRAINT chk_top_range CHECK (top > 0 AND top <= 1000),
    CONSTRAINT chk_skip_range CHECK (skip >= 0),
    CONSTRAINT chk_result_count CHECK (result_count >= 0),
    CONSTRAINT chk_execution_time CHECK (execution_time_ms >= 0)
);

-- 기본 인덱스 (성능용)
CREATE INDEX IF NOT EXISTS idx_query_logs_user_id ON query_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_created_at ON query_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_query_logs_query_type ON query_logs(query_type);
CREATE INDEX IF NOT EXISTS idx_query_logs_has_error ON query_logs(has_error);

-- 스키마 버전 테이블
CREATE TABLE IF NOT EXISTS schema_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_name TEXT NOT NULL UNIQUE,
    version TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 스키마 버전 기록
INSERT OR REPLACE INTO schema_versions (module_name, version, applied_at) 
VALUES ('mail_query', '1.0.0', CURRENT_TIMESTAMP);
