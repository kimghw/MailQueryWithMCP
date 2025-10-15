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

-- 도구 스키마 정보 테이블
CREATE TABLE IF NOT EXISTS iacs_tool_schema (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL UNIQUE,               -- 도구 이름
    parameter_name TEXT NOT NULL,                 -- 파라미터 이름
    parameter_type TEXT NOT NULL,                 -- 파라미터 타입 (string, array, object 등)
    is_required TEXT NOT NULL CHECK(is_required IN ('required', 'optional')),  -- 필수/옵션
    description TEXT,                             -- 설명
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 제약조건: tool_name + parameter_name 조합은 유니크
    CONSTRAINT uq_tool_parameter UNIQUE (tool_name, parameter_name)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_tool_name ON iacs_tool_schema(tool_name);

-- 기본 데이터 삽입 (sdtp 패널)
INSERT OR IGNORE INTO iacs_default_value (panel_name) VALUES ('sdtp');

-- search_agenda 도구 스키마 초기 데이터
INSERT OR IGNORE INTO iacs_tool_schema (tool_name, parameter_name, parameter_type, is_required, description) VALUES
('search_agenda', 'start_date', 'string', 'optional', '시작 날짜 (ISO 형식, 기본값: 현재) [서버 필터]'),
('search_agenda', 'end_date', 'string', 'optional', '종료 날짜 (ISO 형식, 기본값: 3개월 전) [서버 필터]'),
('search_agenda', 'agenda_code', 'string', 'optional', '아젠다 코드 키워드 (옵션) [서버 필터]'),
('search_agenda', 'panel_name', 'string', 'required', '패널 이름 (필수, 예: sdtp)');

-- search_responses 도구 스키마 초기 데이터
INSERT OR IGNORE INTO iacs_tool_schema (tool_name, parameter_name, parameter_type, is_required, description) VALUES
('search_responses', 'agenda_code', 'string', 'required', '아젠다 코드 전체 (필수, 예: PL24016a) [서버 필터]'),
('search_responses', 'panel_name', 'string', 'optional', '패널 이름 (옵션, 없으면 기본 패널 사용)'),
('search_responses', 'send_address', 'array', 'optional', '발신자 주소 리스트 (옵션) [클라이언트 필터]');

-- insert_info 도구 스키마 초기 데이터
INSERT OR IGNORE INTO iacs_tool_schema (tool_name, parameter_name, parameter_type, is_required, description) VALUES
('insert_info', 'chair_address', 'string', 'required', '의장 이메일 주소'),
('insert_info', 'panel_name', 'string', 'required', '패널 이름 (예: sdtp)'),
('insert_info', 'kr_panel_member', 'string', 'required', '한국 패널 멤버 이메일 주소');

-- insert_default_value 도구 스키마 초기 데이터
INSERT OR IGNORE INTO iacs_tool_schema (tool_name, parameter_name, parameter_type, is_required, description) VALUES
('insert_default_value', 'panel_name', 'string', 'required', '기본 패널 이름');
