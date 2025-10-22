-- DCR OAuth 2.0 통합 스키마 V2
-- 단일 테이블로 모든 OAuth 데이터 관리
-- RFC 7591 (Dynamic Client Registration) 및 RFC 6749 (OAuth 2.0) 준수

-- 통합 OAuth 테이블
CREATE TABLE IF NOT EXISTS dcr_oauth (
    -- 핵심 필드
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_type TEXT NOT NULL,          -- 'client', 'auth_code', 'access', 'refresh'
    token_value TEXT NOT NULL,         -- 실제 토큰/ID 값 (암호화)

    -- 연결 정보
    client_id TEXT,                    -- 참조용 클라이언트 ID
    secret_value TEXT,                 -- client_secret (token_type='client'일 때만)

    -- 토큰 메타데이터
    scope TEXT,
    expires_at DATETIME,
    used_at DATETIME,                  -- auth_code 일회용 체크
    revoked_at DATETIME,               -- 무효화 시점

    -- Azure 매핑
    azure_client_id TEXT,              -- Azure 앱 클라이언트 ID
    azure_client_secret TEXT,          -- Azure 앱 클라이언트 시크릿 (암호화)
    azure_tenant_id TEXT,              -- Azure 테넌트 ID
    azure_access_token TEXT,           -- Azure 토큰 (암호화)
    azure_refresh_token TEXT,          -- Azure 리프레시 토큰 (암호화)

    -- 추가 데이터 (JSON)
    metadata TEXT,                     -- redirect_uris, grant_types, state 등 JSON 저장

    -- 타임스탬프
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 성능 최적화 인덱스
CREATE INDEX IF NOT EXISTS idx_token_type ON dcr_oauth (token_type);
CREATE INDEX IF NOT EXISTS idx_token_value ON dcr_oauth (token_value);
CREATE INDEX IF NOT EXISTS idx_client_id ON dcr_oauth (client_id);
CREATE INDEX IF NOT EXISTS idx_expires_at ON dcr_oauth (expires_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_token ON dcr_oauth (token_type, token_value);
CREATE INDEX IF NOT EXISTS idx_azure_client ON dcr_oauth (azure_client_id);

-- 기존 테이블에서 데이터 마이그레이션 (선택)
-- 이미 기존 테이블이 있는 경우에만 실행

-- 1. 클라이언트 마이그레이션
-- INSERT INTO dcr_oauth (token_type, token_value, client_id, secret_value, azure_client_id, azure_client_secret, azure_tenant_id, scope, metadata, created_at)
-- SELECT
--     'client' as token_type,
--     client_id as token_value,
--     client_id,
--     client_secret as secret_value,
--     azure_client_id,
--     azure_client_secret,
--     azure_tenant_id,
--     scope,
--     json_object('client_name', client_name, 'redirect_uris', redirect_uris, 'grant_types', grant_types) as metadata,
--     created_at
-- FROM dcr_clients WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='dcr_clients');

-- 2. 액세스 토큰 마이그레이션
-- INSERT INTO dcr_oauth (token_type, token_value, client_id, scope, expires_at, azure_access_token, azure_refresh_token, created_at, revoked_at)
-- SELECT
--     'access' as token_type,
--     access_token as token_value,
--     client_id,
--     scope,
--     expires_at,
--     azure_access_token,
--     azure_refresh_token,
--     created_at,
--     revoked_at
-- FROM dcr_tokens WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='dcr_tokens');

-- 3. Authorization code 마이그레이션
-- INSERT INTO dcr_oauth (token_type, token_value, client_id, scope, expires_at, used_at, metadata, created_at)
-- SELECT
--     'auth_code' as token_type,
--     code as token_value,
--     client_id,
--     scope,
--     expires_at,
--     used_at,
--     json_object('redirect_uri', redirect_uri, 'state', state, 'azure_auth_code', azure_auth_code) as metadata,
--     created_at
-- FROM dcr_auth_codes WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='dcr_auth_codes');

-- 기존 테이블 삭제 (옵션 - 마이그레이션 확인 후 실행)
-- DROP TABLE IF EXISTS dcr_clients;
-- DROP TABLE IF EXISTS dcr_tokens;
-- DROP TABLE IF EXISTS dcr_auth_codes;