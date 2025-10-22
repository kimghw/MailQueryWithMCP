# DCR 데이터베이스 스키마 최적화

## 현재 스키마 (3개 테이블)

### 문제점
- 테이블이 너무 많음 (dcr_clients, dcr_tokens, dcr_auth_codes)
- 복잡한 JOIN 필요
- Authorization code는 임시 데이터인데 별도 테이블 사용
- 관리 복잡도 증가

### 기존 구조
```sql
-- 3개의 분리된 테이블
dcr_clients (18개 컬럼) - 클라이언트 정보
dcr_tokens (13개 컬럼) - 액세스/리프레시 토큰
dcr_auth_codes (11개 컬럼) - 임시 인증 코드
```

## 최적화된 스키마 (1개 통합 테이블)

### 장점
✅ **단순성**: 1개 테이블로 모든 OAuth 데이터 관리
✅ **성능**: JOIN 없이 단일 쿼리로 처리
✅ **유연성**: token_type으로 데이터 구분
✅ **확장성**: 새로운 토큰 타입 추가 용이

### 새로운 구조: `dcr_oauth` 테이블

```sql
CREATE TABLE dcr_oauth (
    -- 핵심 필드
    id INTEGER PRIMARY KEY,
    token_type TEXT NOT NULL,      -- 'client', 'auth_code', 'access', 'refresh'
    token_value TEXT NOT NULL,     -- 실제 토큰/ID 값 (암호화)

    -- 연결 정보
    client_id TEXT,                -- 참조용 클라이언트 ID

    -- 토큰 메타데이터
    scope TEXT,
    expires_at DATETIME,
    used_at DATETIME,              -- auth_code 일회용 체크
    revoked_at DATETIME,           -- 무효화 시점

    -- Azure 매핑
    azure_access_token TEXT,       -- Azure 토큰 (암호화)
    azure_refresh_token TEXT,

    -- 타임스탬프
    created_at DATETIME,
    updated_at DATETIME
);
```

## 데이터 타입별 사용 방식

### 1. CLIENT (클라이언트 등록)
```sql
-- token_type = 'client'
-- token_value = client_id (예: 'dcr_xxx...')
-- secret_value = client_secret (암호화)
-- redirect_uris, grant_types 등 JSON으로 저장
```

### 2. AUTH_CODE (인증 코드)
```sql
-- token_type = 'auth_code'
-- token_value = authorization_code
-- expires_at = 10분 후
-- used_at = 사용 시 타임스탬프 (일회용)
```

### 3. ACCESS_TOKEN (액세스 토큰)
```sql
-- token_type = 'access'
-- token_value = access_token (암호화)
-- expires_at = 1시간 후
-- azure_access_token = 매핑된 Azure 토큰
```

### 4. REFRESH_TOKEN (리프레시 토큰)
```sql
-- token_type = 'refresh'
-- token_value = refresh_token (암호화)
-- expires_at = 30일 후
```

## 성능 최적화

### 인덱스
```sql
CREATE INDEX idx_token_type ON dcr_oauth (token_type);
CREATE INDEX idx_token_value ON dcr_oauth (token_value);
CREATE INDEX idx_client_id ON dcr_oauth (client_id);
CREATE INDEX idx_expires_at ON dcr_oauth (expires_at);
CREATE UNIQUE INDEX idx_unique_token ON dcr_oauth (token_type, token_value);
```

### 쿼리 성능 비교

#### 기존 (3개 테이블)
```sql
-- Bearer 토큰 검증 (JOIN 필요)
SELECT t.*, c.azure_client_id
FROM dcr_tokens t
JOIN dcr_clients c ON t.client_id = c.client_id
WHERE t.access_token = ? AND t.revoked_at IS NULL
```

#### 최적화 (1개 테이블)
```sql
-- Bearer 토큰 검증 (단일 쿼리)
SELECT * FROM dcr_oauth
WHERE token_type = 'access' AND token_value = ?
  AND revoked_at IS NULL AND expires_at > CURRENT_TIMESTAMP
```

## 마이그레이션 전략

### 단계별 전환
1. **새 테이블 생성**: `dcr_oauth` 생성
2. **데이터 마이그레이션**:
   - dcr_clients → dcr_oauth (token_type='client')
   - dcr_tokens → dcr_oauth (token_type='access'/'refresh')
   - dcr_auth_codes → dcr_oauth (token_type='auth_code')
3. **코드 전환**: DCRServiceV2 사용
4. **기존 테이블 삭제**: 검증 후 제거

### 마이그레이션 스크립트
```sql
-- 클라이언트 마이그레이션
INSERT INTO dcr_oauth (token_type, token_value, client_id, ...)
SELECT 'client', client_id, client_id, ...
FROM dcr_clients;

-- 토큰 마이그레이션
INSERT INTO dcr_oauth (token_type, token_value, client_id, ...)
SELECT 'access', access_token, client_id, ...
FROM dcr_tokens;
```

## 예상 효과

| 측면 | 기존 (3테이블) | 최적화 (1테이블) | 개선율 |
|------|---------------|-----------------|--------|
| **테이블 수** | 3개 | 1개 | -67% |
| **총 컬럼 수** | 42개 | 20개 | -52% |
| **JOIN 필요** | 자주 필요 | 불필요 | -100% |
| **쿼리 복잡도** | 높음 | 낮음 | 단순화 |
| **유지보수** | 복잡 | 단순 | 크게 개선 |

## 보안 고려사항

1. **암호화 필드**:
   - `token_value` (모든 토큰)
   - `secret_value` (클라이언트 시크릿)
   - `azure_access_token`, `azure_refresh_token`

2. **자동 정리**:
   - 만료된 토큰 주기적 삭제
   - `cleanup_expired_tokens()` 메서드 제공

3. **일회용 보장**:
   - Authorization code는 `used_at` 체크로 재사용 방지

## 결론

**단일 테이블 스키마**로 전환하면:
- ✅ 관리가 단순해짐
- ✅ 성능이 향상됨
- ✅ 확장이 용이함
- ✅ 코드가 깔끔해짐

특히 DCR같은 단순한 OAuth 서버에는 **1개 테이블이 최적**입니다.