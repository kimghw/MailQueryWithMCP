-- IACS Panel Chair 관리 스키마
-- IACS: 의장이 멤버들에게 아젠다를 발행하고 멤버들이 응답하는 시스템

-- 패널 의장 및 멤버 정보 테이블
CREATE TABLE IF NOT EXISTS iacs_panel_chair (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chair_address TEXT NOT NULL,              -- 의장 이메일 주소
    panel_name TEXT NOT NULL,                 -- 패널 이름 (예: sdtp)
    kr_panel_member TEXT NOT NULL,            -- 한국 패널 멤버 이메일 주소
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 제약조건: panel_name과 chair_address 조합은 유니크
    CONSTRAINT uq_panel_chair UNIQUE (panel_name, chair_address)
);

-- 기본값 설정 테이블
CREATE TABLE IF NOT EXISTS iacs_default_value (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    panel_name TEXT NOT NULL UNIQUE,          -- 기본 패널 이름
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_iacs_panel_name ON iacs_panel_chair(panel_name);
CREATE INDEX IF NOT EXISTS idx_iacs_chair_address ON iacs_panel_chair(chair_address);
CREATE INDEX IF NOT EXISTS idx_iacs_kr_panel_member ON iacs_panel_chair(kr_panel_member);

-- 기본 데이터 삽입 (sdtp 패널)
INSERT OR IGNORE INTO iacs_default_value (panel_name) VALUES ('sdtp');

-- 스키마 버전 기록
INSERT OR REPLACE INTO schema_versions (module_name, version, applied_at)
VALUES ('mail_iacs', '1.0.0', CURRENT_TIMESTAMP);
