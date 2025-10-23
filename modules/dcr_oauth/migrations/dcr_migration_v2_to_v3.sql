-- DCR V2 → V3 마이그레이션 스크립트
-- 기존 테이블(dcr_clients, dcr_tokens, dcr_azure)에서 새 테이블로 데이터 이동

-- 1) Azure 앱 정보 추출 (환경변수에서 가져와서 수동 INSERT 필요)
-- 실행 예시:
-- INSERT INTO dcr_azure_auth (application_id, client_secret, tenant_id, redirect_uri)
-- VALUES ('your-azure-app-id', 'encrypted-secret', 'common', 'http://localhost:8000/oauth/azure_callback');

-- 2) dcr_azure → dcr_azure_tokens 마이그레이션
INSERT INTO dcr_azure_tokens (
    object_id,
    application_id,
    access_token,
    refresh_token,
    expires_at,
    scope,
    user_email,
    user_name,
    created_at,
    updated_at
)
SELECT
    principal_id,                    -- object_id로 이름 변경
    (SELECT application_id FROM dcr_azure_auth LIMIT 1),  -- Azure 앱 ID (수동 설정 필요)
    azure_access_token,              -- access_token
    azure_refresh_token,             -- refresh_token
    azure_token_expiry,              -- expires_at로 이름 변경
    granted_scope,                   -- scope
    user_email,
    user_name,
    created_at,
    updated_at
FROM dcr_azure
WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='dcr_azure');

-- 3) dcr_clients 마이그레이션 (컬럼명 변경)
INSERT INTO dcr_clients (
    dcr_client_id,
    dcr_client_secret,
    dcr_client_name,
    dcr_redirect_uris,
    dcr_grant_types,
    dcr_requested_scope,
    azure_application_id,
    created_at,
    updated_at
)
SELECT
    client_id,                       -- dcr_client_id로 이름 변경
    client_secret,                   -- dcr_client_secret로 이름 변경
    client_name,                     -- dcr_client_name으로 이름 변경
    redirect_uris,                   -- dcr_redirect_uris로 이름 변경
    grant_types,                     -- dcr_grant_types로 이름 변경
    requested_scope,                 -- dcr_requested_scope로 이름 변경
    azure_client_id,                 -- azure_application_id로 이름 변경
    created_at,
    updated_at
FROM dcr_clients
WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='dcr_clients');

-- 4) dcr_tokens 마이그레이션 (컬럼명 변경)
INSERT INTO dcr_tokens (
    dcr_token_value,
    dcr_client_id,
    dcr_token_type,
    dcr_status,
    azure_object_id,
    expires_at,
    issued_at,
    metadata
)
SELECT
    token_value,                     -- dcr_token_value로 이름 변경
    client_id,                       -- dcr_client_id로 이름 변경
    CASE token_type
        WHEN 'Bearer' THEN 'Bearer'
        WHEN 'authorization_code' THEN 'authorization_code'
        WHEN 'refresh_token' THEN 'refresh'
        ELSE token_type
    END,                             -- dcr_token_type로 이름 변경
    status,                          -- dcr_status로 이름 변경
    principal_id,                    -- azure_object_id로 이름 변경
    expires_at,
    issued_at,
    metadata
FROM dcr_tokens
WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='dcr_tokens');

-- 5) 기존 테이블 백업 (선택사항)
-- ALTER TABLE dcr_clients RENAME TO dcr_clients_old;
-- ALTER TABLE dcr_tokens RENAME TO dcr_tokens_old;
-- ALTER TABLE dcr_azure RENAME TO dcr_azure_old;

-- 6) 기존 테이블 삭제 (마이그레이션 확인 후 실행)
-- DROP TABLE IF EXISTS dcr_clients_old;
-- DROP TABLE IF EXISTS dcr_tokens_old;
-- DROP TABLE IF EXISTS dcr_azure_old;
