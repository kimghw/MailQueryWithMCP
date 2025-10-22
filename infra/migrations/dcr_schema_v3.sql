-- DCR Schema V3: 명확한 Azure/DCR 분리
-- Azure Portal 용어 그대로 사용 + 모든 테이블에 dcr_ 접두사

-- 1) Azure 인증 정보 (Azure Portal에서 생성한 앱)
CREATE TABLE IF NOT EXISTS dcr_azure_auth (
    application_id TEXT PRIMARY KEY,      -- Azure Application (client) ID
    client_secret TEXT NOT NULL,          -- Azure Client Secret (암호화)
    tenant_id TEXT NOT NULL,              -- Azure Tenant ID
    redirect_uri TEXT,                    -- Azure에 등록된 Redirect URI
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2) Azure 사용자 토큰 (Azure AD에서 받은 실제 토큰)
CREATE TABLE IF NOT EXISTS dcr_azure_tokens (
    object_id TEXT PRIMARY KEY,           -- Azure User Object ID
    application_id TEXT NOT NULL,         -- 어느 Azure 앱으로 받았는지
    access_token TEXT NOT NULL,           -- Azure Access Token (암호화)
    refresh_token TEXT,                   -- Azure Refresh Token (암호화)
    expires_at DATETIME NOT NULL,
    scope TEXT,
    user_email TEXT,
    user_name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES dcr_azure_auth(application_id)
);

CREATE INDEX IF NOT EXISTS idx_dcr_azure_tokens_expires ON dcr_azure_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_dcr_azure_tokens_email ON dcr_azure_tokens(user_email);

-- 3) DCR 클라이언트 (Claude AI가 등록한 가상 클라이언트)
CREATE TABLE IF NOT EXISTS dcr_clients (
    dcr_client_id TEXT PRIMARY KEY,       -- dcr_xxx (DCR 서버가 생성)
    dcr_client_secret TEXT NOT NULL,      -- DCR 클라이언트 시크릿 (암호화)
    dcr_client_name TEXT,
    dcr_redirect_uris TEXT,               -- JSON array
    dcr_grant_types TEXT,                 -- JSON array
    dcr_requested_scope TEXT,
    azure_application_id TEXT NOT NULL,   -- 어느 Azure 앱을 사용하는지
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (azure_application_id) REFERENCES dcr_azure_auth(application_id)
);

-- 4) DCR 토큰 (DCR 서버가 발급한 토큰)
CREATE TABLE IF NOT EXISTS dcr_tokens (
    dcr_token_value TEXT PRIMARY KEY,     -- Bearer 토큰 (암호화)
    dcr_client_id TEXT NOT NULL,          -- 어느 DCR 클라이언트 토큰인지
    dcr_token_type TEXT NOT NULL,         -- 'Bearer', 'authorization_code', 'refresh'
    dcr_status TEXT DEFAULT 'active',     -- 'active', 'expired', 'revoked'
    azure_object_id TEXT,                 -- 어느 Azure 사용자 토큰인지 (null = 로그인 전)
    expires_at DATETIME NOT NULL,
    issued_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,                        -- JSON (PKCE, redirect_uri, state 등)
    FOREIGN KEY (dcr_client_id) REFERENCES dcr_clients(dcr_client_id) ON DELETE CASCADE,
    FOREIGN KEY (azure_object_id) REFERENCES dcr_azure_tokens(object_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_dcr_tokens_expires ON dcr_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_dcr_tokens_client_status ON dcr_tokens(dcr_client_id, dcr_status);
CREATE INDEX IF NOT EXISTS idx_dcr_tokens_object_id ON dcr_tokens(azure_object_id);
CREATE INDEX IF NOT EXISTS idx_dcr_tokens_type ON dcr_tokens(dcr_token_type);
