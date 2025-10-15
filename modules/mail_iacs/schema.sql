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

-- ============================================================================
-- 도구별 스키마 테이블 (각 도구마다 별도 테이블)
-- ============================================================================

-- search_agenda 도구 스키마 테이블
CREATE TABLE IF NOT EXISTS iacs_tool_search_agenda (
    parameter_name TEXT PRIMARY KEY,              -- 파라미터 이름
    parameter_type TEXT NOT NULL,                 -- 파라미터 타입 (string, array, object 등)
    is_required TEXT NOT NULL CHECK(is_required IN ('required', 'optional'))  -- 필수/옵션
);

-- search_responses 도구 스키마 테이블
CREATE TABLE IF NOT EXISTS iacs_tool_search_responses (
    parameter_name TEXT PRIMARY KEY,              -- 파라미터 이름
    parameter_type TEXT NOT NULL,                 -- 파라미터 타입
    is_required TEXT NOT NULL CHECK(is_required IN ('required', 'optional'))
);

-- insert_info 도구 스키마 테이블
CREATE TABLE IF NOT EXISTS iacs_tool_insert_info (
    parameter_name TEXT PRIMARY KEY,              -- 파라미터 이름
    parameter_type TEXT NOT NULL,                 -- 파라미터 타입
    is_required TEXT NOT NULL CHECK(is_required IN ('required', 'optional'))
);

-- insert_default_value 도구 스키마 테이블
CREATE TABLE IF NOT EXISTS iacs_tool_insert_default_value (
    parameter_name TEXT PRIMARY KEY,              -- 파라미터 이름
    parameter_type TEXT NOT NULL,                 -- 파라미터 타입
    is_required TEXT NOT NULL CHECK(is_required IN ('required', 'optional'))
);

-- 기본 데이터 삽입 (sdtp 패널)
INSERT OR IGNORE INTO iacs_default_value (panel_name) VALUES ('sdtp');

-- ============================================================================
-- 초기 스키마 데이터 삽입
-- ============================================================================

-- search_agenda 초기 데이터
INSERT OR IGNORE INTO iacs_tool_search_agenda (parameter_name, parameter_type, is_required) VALUES
('start_date', 'string', 'optional'),
('end_date', 'string', 'optional'),
('agenda_code', 'string', 'optional'),
('panel_name', 'string', 'required');

-- search_responses 초기 데이터
INSERT OR IGNORE INTO iacs_tool_search_responses (parameter_name, parameter_type, is_required) VALUES
('agenda_code', 'string', 'required'),
('panel_name', 'string', 'optional'),
('send_address', 'array', 'optional');

-- insert_info 초기 데이터
INSERT OR IGNORE INTO iacs_tool_insert_info (parameter_name, parameter_type, is_required) VALUES
('chair_address', 'string', 'required'),
('panel_name', 'string', 'required'),
('kr_panel_member', 'string', 'required');

-- insert_default_value 초기 데이터
INSERT OR IGNORE INTO iacs_tool_insert_default_value (parameter_name, parameter_type, is_required) VALUES
('panel_name', 'string', 'required');
