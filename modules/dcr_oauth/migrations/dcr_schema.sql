-- DCR (Dynamic Client Registration) 스키마
-- RFC 7591 준수 동적 클라이언트 등록 지원

-- DCR 등록된 클라이언트 테이블
CREATE TABLE IF NOT EXISTS dcr_clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- RFC 7591 필수 필드
    client_id TEXT NOT NULL UNIQUE,
    client_secret TEXT NOT NULL,
    client_id_issued_at INTEGER NOT NULL,  -- Unix timestamp
    client_secret_expires_at INTEGER DEFAULT 0,  -- 0 = never expires

    -- RFC 7591 선택 필드
    client_name TEXT,
    redirect_uris TEXT,  -- JSON array
    token_endpoint_auth_method TEXT DEFAULT 'client_secret_post',
    grant_types TEXT,  -- JSON array
    response_types TEXT,  -- JSON array
    scope TEXT,
    contacts TEXT,  -- JSON array

    -- Azure AD 매핑 정보
    azure_client_id TEXT NOT NULL,
    azure_client_secret TEXT NOT NULL,
    azure_tenant_id TEXT NOT NULL,

    -- 세션 및 토큰 관리
    registration_access_token TEXT NOT NULL,

    -- 메타데이터
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP
);

-- DCR 클라이언트별 발급된 토큰 테이블
CREATE TABLE IF NOT EXISTS dcr_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL,
    user_id TEXT,  -- 연결된 사용자 (선택)

    -- 토큰 정보
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_type TEXT DEFAULT 'Bearer',
    expires_at TIMESTAMP NOT NULL,
    scope TEXT,

    -- Azure AD에서 받은 실제 토큰
    azure_access_token TEXT,
    azure_refresh_token TEXT,
    azure_token_expiry TIMESTAMP,

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP,

    FOREIGN KEY (client_id) REFERENCES dcr_clients (client_id) ON DELETE CASCADE
);

-- Authorization Code 임시 저장 테이블
CREATE TABLE IF NOT EXISTS dcr_auth_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    client_id TEXT NOT NULL,
    user_id TEXT,

    -- PKCE 지원
    code_challenge TEXT,
    code_challenge_method TEXT,

    redirect_uri TEXT NOT NULL,
    scope TEXT,

    -- Azure AD 매핑
    azure_auth_code TEXT,
    state TEXT,

    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (client_id) REFERENCES dcr_clients (client_id) ON DELETE CASCADE
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_dcr_clients_client_id ON dcr_clients (client_id);
CREATE INDEX IF NOT EXISTS idx_dcr_clients_azure_client_id ON dcr_clients (azure_client_id);
CREATE INDEX IF NOT EXISTS idx_dcr_clients_is_active ON dcr_clients (is_active);
CREATE INDEX IF NOT EXISTS idx_dcr_tokens_client_id ON dcr_tokens (client_id);
CREATE INDEX IF NOT EXISTS idx_dcr_tokens_access_token ON dcr_tokens (access_token);
CREATE INDEX IF NOT EXISTS idx_dcr_tokens_expires_at ON dcr_tokens (expires_at);
CREATE INDEX IF NOT EXISTS idx_dcr_auth_codes_code ON dcr_auth_codes (code);
CREATE INDEX IF NOT EXISTS idx_dcr_auth_codes_client_id ON dcr_auth_codes (client_id);
CREATE INDEX IF NOT EXISTS idx_dcr_auth_codes_expires_at ON dcr_auth_codes (expires_at);
