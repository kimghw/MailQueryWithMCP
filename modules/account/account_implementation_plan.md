# Account 모듈 구현 계획서 (3단계)

## 1. 개요

Account 모듈은 enrollment 파일과 데이터베이스 간의 계정 동기화, 계정 생명주기 관리, OAuth 클라이언트 정보 관리를 담당하는 핵심 모듈입니다.

### 1.1 주요 책임
- enrollment/*.yaml 파일 스캔 및 DB 동기화
- 계정 CRUD 및 상태 관리 (ACTIVE, INACTIVE, LOCKED, REAUTH_REQUIRED)
- 개별 계정별 OAuth 클라이언트 정보 관리
- 계정 변경 이력 추적 및 감사 로그

### 1.2 유즈케이스
- **UC-1**: enrollment 파일 동기화
- **UC-1.1**: 신규 계정 등록
- **UC-1.2**: 기존 계정 정보 업데이트  
- **UC-1.3**: 제거된 계정 비활성화
- **UC-1.4**: 계정 상태 관리

## 2. 아키텍처 설계

### 2.1 모듈 구조
```
modules/account/
├── __init__.py
├── account_orchestrator.py      # 계정 관리 오케스트레이터
├── account_schema.py            # 계정 관련 Pydantic 모델
├── account_sync_service.py      # enrollment 동기화 서비스
├── account_repository.py       # 계정 데이터 액세스
├── account_validator.py        # 계정 데이터 검증
├── _account_helpers.py          # 헬퍼 함수들 (350줄 제한 대응)
└── README.md
```

### 2.2 의존성 관계
```
account_orchestrator.py (진입점)
├── account_sync_service.py     # enrollment 파일 처리
├── account_repository.py       # 데이터베이스 작업
├── account_validator.py        # 데이터 검증
└── _account_helpers.py         # 유틸리티 함수
```

### 2.3 외부 의존성
- `infra.core.database` - DB 연결 관리
- `infra.core.logger` - 로깅
- `infra.core.config` - 설정 관리

## 3. 데이터 모델 설계

### 3.1 데이터베이스 스키마 (infra 수정 필요)
```sql
-- accounts 테이블 수정 필요
CREATE TABLE accounts (
    id TEXT PRIMARY KEY,              -- UUID
    email TEXT UNIQUE NOT NULL,       -- 계정 이메일
    name TEXT,                        -- 사용자 이름
    
    -- OAuth 클라이언트 정보 (계정별 관리)
    tenant_id TEXT,                   -- Azure AD 테넌트 ID
    client_id TEXT,                   -- Azure AD 클라이언트 ID  
    client_secret TEXT,               -- 암호화된 클라이언트 시크릿
    oauth_scopes TEXT DEFAULT 'User.Read,Mail.Read,offline_access', -- 요청 스코프
    
    -- 계정 상태 관리
    status TEXT DEFAULT 'INACTIVE',   -- ACTIVE, INACTIVE, LOCKED, REAUTH_REQUIRED
    error_message TEXT,               -- 마지막 오류 메시지
    
    -- 토큰 정보
    access_token TEXT,                -- 암호화된 액세스 토큰
    refresh_token TEXT,               -- 암호화된 리프레시 토큰  
    token_expires_at TIMESTAMP,       -- 토큰 만료 시간
    
    -- 동기화 정보
    enrollment_file_path TEXT,        -- 원본 enrollment 파일 경로
    enrollment_file_hash TEXT,        -- 파일 내용 해시 (변경 감지용)
    last_sync_at TIMESTAMP,           -- 마지막 동기화 시간
    last_authenticated_at TIMESTAMP,  -- 마지막 인증 시간
    
    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 추가
CREATE INDEX idx_accounts_email ON accounts(email);
CREATE INDEX idx_accounts_status ON accounts(status);
CREATE INDEX idx_accounts_enrollment_path ON accounts(enrollment_file_path);
```

### 3.2 Pydantic 모델
```python
# account_schema.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime
from enum import Enum

class AccountStatus(str, Enum):
    """계정 상태"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE" 
    LOCKED = "LOCKED"
    REAUTH_REQUIRED = "REAUTH_REQUIRED"

class AccountOAuthConfig(BaseModel):
    """계정별 OAuth 설정"""
    tenant_id: str = Field(..., description="Azure AD 테넌트 ID")
    client_id: str = Field(..., description="Azure AD 클라이언트 ID")
    client_secret: str = Field(..., description="Azure AD 클라이언트 시크릿")
    oauth_scopes: str = Field(
        default="User.Read,Mail.Read,offline_access", 
        description="OAuth 요청 스코프"
    )

class AccountEnrollmentData(BaseModel):
    """enrollment 파일 데이터"""
    email: EmailStr = Field(..., description="계정 이메일")
    name: Optional[str] = Field(None, description="사용자 이름")
    oauth_config: AccountOAuthConfig = Field(..., description="OAuth 설정")

class AccountTokenInfo(BaseModel):
    """계정 토큰 정보"""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None  
    token_expires_at: Optional[datetime] = None

class AccountRecord(BaseModel):
    """계정 DB 레코드"""
    id: str = Field(..., description="계정 UUID")
    email: EmailStr = Field(..., description="계정 이메일")
    name: Optional[str] = None
    
    # OAuth 정보
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    oauth_scopes: str = "User.Read,Mail.Read,offline_access"
    
    # 상태 정보
    status: AccountStatus = AccountStatus.INACTIVE
    error_message: Optional[str] = None
    
    # 토큰 정보 (조회시에만 포함)
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    
    # 동기화 정보
    enrollment_file_path: Optional[str] = None
    enrollment_file_hash: Optional[str] = None
    last_sync_at: Optional[datetime] = None
    last_authenticated_at: Optional[datetime] = None
    
    created_at: datetime
    updated_at: datetime

class AccountSyncResult(BaseModel):
    """동기화 결과"""
    total_files: int = Field(..., description="처리된 파일 수")
    created_accounts: int = Field(..., description="신규 생성된 계정 수")
    updated_accounts: int = Field(..., description="업데이트된 계정 수")
    deactivated_accounts: int = Field(..., description="비활성화된 계정 수")
    errors: list[str] = Field(default_factory=list, description="오류 목록")

class AccountQueryFilter(BaseModel):
    """계정 조회 필터"""
    email: Optional[str] = None
    status: Optional[AccountStatus] = None
    name_contains: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
```

## 4. 구체적 구현 계획

### 4.1 AccountOrchestrator (account_orchestrator.py)
```python
from infra.core import get_database, get_logger, get_config
from .account_sync_service import AccountSyncService
from .account_repository import AccountRepository
from .account_validator import AccountValidator
from .account_schema import AccountSyncResult, AccountQueryFilter, AccountRecord

class AccountOrchestrator:
    """계정 관리 오케스트레이터 - 모든 계정 관련 작업의 진입점"""
    
    def __init__(self):
        self.db_manager = get_database()
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.sync_service = AccountSyncService()
        self.repository = AccountRepository()
        self.validator = AccountValidator()
    
    async def account_sync_all_enrollment_files(self) -> AccountSyncResult:
        """모든 enrollment 파일과 DB 동기화"""
        try:
            self.logger.info("Starting enrollment files synchronization")
            
            # enrollment 디렉터리 스캔
            enrollment_data = await self.sync_service.account_sync_scan_enrollment_files()
            
            result = AccountSyncResult(total_files=len(enrollment_data))
            
            async with self.db_manager.get_connection() as conn:
                async with conn.begin():  # 트랜잭션 처리
                    
                    # 1. 각 enrollment 파일 처리
                    for file_path, account_data in enrollment_data.items():
                        try:
                            # 데이터 검증
                            validated_data = self.validator.account_validate_enrollment_data(account_data)
                            
                            # 기존 계정 조회
                            existing_account = await self.repository.account_get_by_email(conn, validated_data.email)
                            
                            if existing_account:
                                # 기존 계정 업데이트
                                if await self._account_should_update(existing_account, validated_data, file_path):
                                    await self.repository.account_update_from_enrollment(
                                        conn, existing_account.id, validated_data, file_path
                                    )
                                    result.updated_accounts += 1
                                    self.logger.info(f"Updated account: {validated_data.email}")
                            else:
                                # 신규 계정 생성
                                new_account_id = await self.repository.account_create_from_enrollment(
                                    conn, validated_data, file_path
                                )
                                result.created_accounts += 1
                                self.logger.info(f"Created account: {validated_data.email} with ID: {new_account_id}")
                        
                        except Exception as e:
                            error_msg = f"Failed to process {file_path}: {str(e)}"
                            result.errors.append(error_msg)
                            self.logger.error(error_msg)
                    
                    # 2. DB에 있지만 enrollment에 없는 계정 비활성화
                    active_emails = {data.email for data in enrollment_data.values()}
                    deactivated = await self.repository.account_deactivate_missing_enrollments(conn, active_emails)
                    result.deactivated_accounts = deactivated
            
            self.logger.info(f"Synchronization completed: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Enrollment synchronization failed: {str(e)}")
            raise
    
    async def account_get_by_email(self, email: str) -> Optional[AccountRecord]:
        """이메일로 계정 조회"""
        async with self.db_manager.get_connection() as conn:
            return await self.repository.account_get_by_email(conn, email)
    
    async def account_get_by_id(self, account_id: str) -> Optional[AccountRecord]:
        """ID로 계정 조회"""
        async with self.db_manager.get_connection() as conn:
            return await self.repository.account_get_by_id(conn, account_id)
    
    async def account_list_with_filter(self, filters: AccountQueryFilter) -> list[AccountRecord]:
        """필터를 적용한 계정 목록 조회"""
        async with self.db_manager.get_connection() as conn:
            return await self.repository.account_list_with_filter(conn, filters)
    
    async def account_update_status(self, account_id: str, status: AccountStatus, error_message: Optional[str] = None) -> bool:
        """계정 상태 업데이트"""
        async with self.db_manager.get_connection() as conn:
            return await self.repository.account_update_status(conn, account_id, status, error_message)
    
    async def account_update_oauth_config(self, account_id: str, oauth_config: AccountOAuthConfig) -> bool:
        """계정 OAuth 설정 업데이트"""
        # 데이터 검증
        validated_config = self.validator.account_validate_oauth_config(oauth_config)
        
        async with self.db_manager.get_connection() as conn:
            return await self.repository.account_update_oauth_config(conn, account_id, validated_config)
    
    def _account_should_update(self, existing: AccountRecord, new_data: AccountEnrollmentData, file_path: str) -> bool:
        """계정 업데이트 필요 여부 판단"""
        # 파일 경로가 다르거나 내용이 변경되었는지 확인
        if existing.enrollment_file_path != file_path:
            return True
        
        # OAuth 설정 변경 확인
        if (existing.tenant_id != new_data.oauth_config.tenant_id or
            existing.client_id != new_data.oauth_config.client_id or
            existing.client_secret != new_data.oauth_config.client_secret):
            return True
        
        # 사용자 이름 변경 확인
        if existing.name != new_data.name:
            return True
        
        return False
```

### 4.2 AccountSyncService (account_sync_service.py)
```python
import os
import yaml
import hashlib
from pathlib import Path
from typing import Dict, Any
from .account_schema import AccountEnrollmentData
from ._account_helpers import AccountFileHelpers

class AccountSyncService:
    """enrollment 파일 동기화 서비스"""
    
    def __init__(self):
        from infra.core import get_config, get_logger
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.enrollment_dir = Path("enrollment")
    
    async def account_sync_scan_enrollment_files(self) -> Dict[str, AccountEnrollmentData]:
        """enrollment 디렉터리의 모든 .yaml 파일 스캔"""
        enrollment_data = {}
        
        if not self.enrollment_dir.exists():
            self.logger.warning(f"Enrollment directory not found: {self.enrollment_dir}")
            return enrollment_data
        
        # .yaml 파일들 스캔
        yaml_files = list(self.enrollment_dir.glob("*.yaml"))
        self.logger.info(f"Found {len(yaml_files)} enrollment files")
        
        for file_path in yaml_files:
            try:
                # 파일 내용 읽기 및 파싱
                account_data = await self._account_sync_parse_enrollment_file(file_path)
                if account_data:
                    enrollment_data[str(file_path)] = account_data
                    
            except Exception as e:
                self.logger.error(f"Failed to parse enrollment file {file_path}: {str(e)}")
                continue
        
        return enrollment_data
    
    async def _account_sync_parse_enrollment_file(self, file_path: Path) -> Optional[AccountEnrollmentData]:
        """단일 enrollment 파일 파싱"""
        try:
            # 파일 읽기
            content = file_path.read_text(encoding='utf-8')
            
            # YAML 파싱
            yaml_data = yaml.safe_load(content)
            
            # 필수 필드 확인
            if not AccountFileHelpers.account_validate_yaml_structure(yaml_data):
                self.logger.error(f"Invalid YAML structure in {file_path}")
                return None
            
            # Pydantic 모델로 변환
            account_data = AccountEnrollmentData(**yaml_data)
            
            self.logger.debug(f"Successfully parsed enrollment file: {file_path}")
            return account_data
            
        except yaml.YAMLError as e:
            self.logger.error(f"YAML parsing error in {file_path}: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error parsing {file_path}: {str(e)}")
            return None
    
    def account_sync_calculate_file_hash(self, file_path: Path) -> str:
        """파일 내용 해시 계산 (변경 감지용)"""
        try:
            content = file_path.read_bytes()
            return hashlib.sha256(content).hexdigest()
        except Exception as e:
            self.logger.error(f"Failed to calculate hash for {file_path}: {str(e)}")
            return ""
```

### 4.3 AccountRepository (account_repository.py)
```python
import uuid
from datetime import datetime
from typing import Optional, List
from .account_schema import (
    AccountEnrollmentData, AccountRecord, AccountStatus, 
    AccountOAuthConfig, AccountQueryFilter
)
from ._account_helpers import AccountCryptoHelpers

class AccountRepository:
    """계정 데이터 액세스 레이어"""
    
    def __init__(self):
        from infra.core import get_logger
        self.logger = get_logger(__name__)
        self.crypto = AccountCryptoHelpers()
    
    async def account_get_by_email(self, conn, email: str) -> Optional[AccountRecord]:
        """이메일로 계정 조회"""
        query = "SELECT * FROM accounts WHERE email = ?"
        row = await conn.execute(query, (email,)).fetchone()
        
        if row:
            return self._account_row_to_record(row)
        return None
    
    async def account_get_by_id(self, conn, account_id: str) -> Optional[AccountRecord]:
        """ID로 계정 조회"""
        query = "SELECT * FROM accounts WHERE id = ?"
        row = await conn.execute(query, (account_id,)).fetchone()
        
        if row:
            return self._account_row_to_record(row)
        return None
    
    async def account_create_from_enrollment(self, conn, enrollment_data: AccountEnrollmentData, file_path: str) -> str:
        """enrollment 데이터로부터 신규 계정 생성"""
        account_id = str(uuid.uuid4())
        now = datetime.now()
        
        # 클라이언트 시크릿 암호화
        encrypted_secret = self.crypto.account_encrypt_sensitive_data(enrollment_data.oauth_config.client_secret)
        
        query = """
            INSERT INTO accounts (
                id, email, name, tenant_id, client_id, client_secret, oauth_scopes,
                status, enrollment_file_path, last_sync_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        await conn.execute(query, (
            account_id,
            enrollment_data.email,
            enrollment_data.name,
            enrollment_data.oauth_config.tenant_id,
            enrollment_data.oauth_config.client_id,
            encrypted_secret,
            enrollment_data.oauth_config.oauth_scopes,
            AccountStatus.INACTIVE.value,
            file_path,
            now,
            now,
            now
        ))
        
        # 감사 로그 기록
        await self._account_log_audit(conn, account_id, "create", "account", None, enrollment_data.email)
        
        return account_id
    
    async def account_update_from_enrollment(self, conn, account_id: str, enrollment_data: AccountEnrollmentData, file_path: str) -> bool:
        """enrollment 데이터로 기존 계정 업데이트"""
        now = datetime.now()
        
        # 클라이언트 시크릿 암호화
        encrypted_secret = self.crypto.account_encrypt_sensitive_data(enrollment_data.oauth_config.client_secret)
        
        query = """
            UPDATE accounts SET 
                name = ?, tenant_id = ?, client_id = ?, client_secret = ?, 
                oauth_scopes = ?, enrollment_file_path = ?, last_sync_at = ?, updated_at = ?
            WHERE id = ?
        """
        
        cursor = await conn.execute(query, (
            enrollment_data.name,
            enrollment_data.oauth_config.tenant_id,
            enrollment_data.oauth_config.client_id,
            encrypted_secret,
            enrollment_data.oauth_config.oauth_scopes,
            file_path,
            now,
            now,
            account_id
        ))
        
        if cursor.rowcount > 0:
            # 감사 로그 기록
            await self._account_log_audit(conn, account_id, "update", "account", None, enrollment_data.email)
            return True
        return False
    
    async def account_update_status(self, conn, account_id: str, status: AccountStatus, error_message: Optional[str] = None) -> bool:
        """계정 상태 업데이트"""
        now = datetime.now()
        
        query = """
            UPDATE accounts SET 
                status = ?, error_message = ?, updated_at = ?
            WHERE id = ?
        """
        
        cursor = await conn.execute(query, (status.value, error_message, now, account_id))
        
        if cursor.rowcount > 0:
            # 감사 로그 기록
            await self._account_log_audit(conn, account_id, "status_change", "account", None, status.value)
            return True
        return False
    
    async def account_list_with_filter(self, conn, filters: AccountQueryFilter) -> List[AccountRecord]:
        """필터를 적용한 계정 목록 조회"""
        where_clauses = []
        params = []
        
        if filters.email:
            where_clauses.append("email LIKE ?")
            params.append(f"%{filters.email}%")
        
        if filters.status:
            where_clauses.append("status = ?")
            params.append(filters.status.value)
        
        if filters.name_contains:
            where_clauses.append("name LIKE ?")
            params.append(f"%{filters.name_contains}%")
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        query = f"""
            SELECT * FROM accounts 
            WHERE {where_clause}
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """
        
        params.extend([filters.limit, filters.offset])
        
        rows = await conn.execute(query, params).fetchall()
        return [self._account_row_to_record(row) for row in rows]
    
    async def account_deactivate_missing_enrollments(self, conn, active_emails: set[str]) -> int:
        """enrollment에 없는 활성 계정들을 비활성화"""
        if not active_emails:
            return 0
        
        # 현재 활성 상태인 계정들 중 enrollment에 없는 계정들 조회
        placeholders = ",".join("?" for _ in active_emails)
        query = f"""
            SELECT id, email FROM accounts 
            WHERE status = 'ACTIVE' AND email NOT IN ({placeholders})
        """
        
        rows = await conn.execute(query, list(active_emails)).fetchall()
        
        if not rows:
            return 0
        
        # 비활성화 처리
        account_ids = [row['id'] for row in rows]
        update_query = f"""
            UPDATE accounts SET 
                status = 'INACTIVE', 
                error_message = 'Removed from enrollment', 
                updated_at = ?
            WHERE id IN ({",".join("?" for _ in account_ids)})
        """
        
        now = datetime.now()
        await conn.execute(update_query, [now] + account_ids)
        
        # 감사 로그 기록
        for row in rows:
            await self._account_log_audit(conn, row['id'], "deactivate", "account", "ACTIVE", row['email'])
        
        return len(account_ids)
    
    def _account_row_to_record(self, row) -> AccountRecord:
        """DB 행을 AccountRecord로 변환"""
        row_dict = dict(row)
        
        # 암호화된 데이터 복호화 (필요시)
        if row_dict.get('client_secret'):
            row_dict['client_secret'] = self.crypto.account_decrypt_sensitive_data(row_dict['client_secret'])
        
        return AccountRecord(**row_dict)
    
    async def _account_log_audit(self, conn, account_id: str, action: str, entity_type: str, old_value: Optional[str], new_value: Optional[str]):
        """감사 로그 기록"""
        query = """
            INSERT INTO audit_logs (account_id, action, entity_type, entity_id, old_value, new_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        await conn.execute(query, (
            account_id, action, entity_type, account_id, old_value, new_value, datetime.now()
        ))
```

## 5. infra 수정사항

### 5.1 database.py 수정 필요
현재 database.py에서 accounts 테이블 스키마를 업데이트해야 합니다:

```python
# infra/core/database.py 수정 필요사항

# 1. accounts 테이블 스키마 업데이트
UPDATED_ACCOUNTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    tenant_id TEXT,
    client_id TEXT,
    client_secret TEXT,
    oauth_scopes TEXT DEFAULT 'User.Read,Mail.Read,offline_access',
    status TEXT DEFAULT 'INACTIVE',
    error_message TEXT,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    enrollment_file_path TEXT,
    enrollment_file_hash TEXT,
    last_sync_at TIMESTAMP,
    last_authenticated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_accounts_email ON accounts(email);
CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status);
CREATE INDEX IF NOT EXISTS idx_accounts_enrollment_path ON accounts(enrollment_file_path);
"""

# 2. 데이터베이스 초기화 스크립트에 accounts 스키마 포함 필요
```

### 5.2 config.py 수정 필요
```python
# infra/core/config.py에 추가 필요
class Config:
    # 기존 설정들...
    
    @property
    def enrollment_directory(self) -> str:
        """enrollment 파일 디렉터리 경로"""
        return os.getenv("ENROLLMENT_DIRECTORY", "enrollment")
    
    @property  
    def encryption_key(self) -> str:
        """데이터 암호화 키 (환경변수에서 가져오거나 생성)"""
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            # 개발환경에서는 고정 키 사용 (프로덕션에서는 반드시 환경변수 설정)
            key = "dev-encryption-key-32-chars-long"
        return key
```

### 5.3 oauth_client.py 수정 필요
현재 oauth_client.py는 고정된 클라이언트 설정을 사용하지만, account별 동적 설정이 필요합니다:

```python
# infra/core/oauth_client.py 수정 필요
class OAuthClient:
    def __init__(self):
        self.config = get_config()
    
    async def get_authorization_url(self, tenant_id: str, client_id: str, scopes: str, redirect_uri: str, state: str) -> str:
        """계정별 OAuth 인증 URL 생성"""
        # 기존 고정 설정 대신 매개변수로 받은 값 사용
        pass
    
    async def exchange_code_for_tokens(self, auth_code: str, tenant_id: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
        """계정별 OAuth 토큰 교환"""
        # 기존 고정 설정 대신 매개변수로 받은 값 사용
        pass
```

### 5.4 token_service.py 수정 필요
현재 토큰 서비스도 계정별 OAuth 설정을 고려해야 합니다:

```python
# infra/core/token_service.py 수정 필요  
class TokenService:
    async def refresh_access_token(self, account_id: str) -> dict:
        """계정별 토큰 갱신"""
        # 1. DB에서 계정 정보 조회 (OAuth 설정 포함)
        # 2. 계정별 OAuth 설정으로 토큰 갱신
        # 3. 새 토큰을 DB에 저장
        pass
```

## 6. 추가 구현 파일들

### 6.1 AccountValidator (account_validator.py)
```python
from typing import Optional
from .account_schema import AccountEnrollmentData, AccountOAuthConfig
from infra.core.exceptions import ValidationError

class AccountValidator:
    """계정 데이터 검증"""
    
    def __init__(self):
        from infra.core import get_logger
        self.logger = get_logger(__name__)
    
    def account_validate_enrollment_data(self, data: dict) -> AccountEnrollmentData:
        """enrollment 데이터 검증"""
        try:
            # Pydantic 모델로 검증
            validated_data = AccountEnrollmentData(**data)
            
            # 추가 비즈니스 로직 검증
            self._account_validate_email_format(validated_data.email)
            self._account_validate_oauth_config(validated_data.oauth_config)
            
            return validated_data
            
        except Exception as e:
            raise ValidationError(f"Invalid enrollment data: {str(e)}")
    
    def account_validate_oauth_config(self, oauth_config: AccountOAuthConfig) -> AccountOAuthConfig:
        """OAuth 설정 검증"""
        # tenant_id 형식 검증
        if not oauth_config.tenant_id or len(oauth_config.tenant_id) < 10:
            raise ValidationError("Invalid tenant_id format")
        
        # client_id 형식 검증  
        if not oauth_config.client_id or len(oauth_config.client_id) < 10:
            raise ValidationError("Invalid client_id format")
        
        # client_secret 검증
        if not oauth_config.client_secret or len(oauth_config.client_secret) < 10:
            raise ValidationError("Invalid client_secret format")
        
        # 스코프 검증
        required_scopes = {'User.Read', 'Mail.Read', 'offline_access'}
        provided_scopes = set(oauth_config.oauth_scopes.split(','))
        if not required_scopes.issubset(provided_scopes):
            raise ValidationError(f"Missing required scopes: {required_scopes - provided_scopes}")
        
        return oauth_config
    
    def _account_validate_email_format(self, email: str):
        """이메일 형식 추가 검증"""
        # Pydantic EmailStr로 기본 검증은 완료
        # 도메인 블랙리스트 검증 등 추가 로직
        blocked_domains = ['spam.com', 'temp.com']
        domain = email.split('@')[1].lower()
        if domain in blocked_domains:
            raise ValidationError(f"Email domain {domain} is not allowed")
```

### 6.2 AccountHelpers (_account_helpers.py)
```python
import hashlib
import base64
from cryptography.fernet import Fernet
from typing import Dict, Any, Optional

class AccountFileHelpers:
    """파일 관련 헬퍼 함수"""
    
    @staticmethod
    def account_validate_yaml_structure(yaml_data: Dict[str, Any]) -> bool:
        """YAML 파일 구조 검증"""
        required_fields = ['email', 'oauth_config']
        oauth_required_fields = ['tenant_id', 'client_id', 'client_secret']
        
        # 최상위 필드 확인
        for field in required_fields:
            if field not in yaml_data:
                return False
        
        # oauth_config 필드 확인
        oauth_config = yaml_data.get('oauth_config', {})
        for field in oauth_required_fields:
            if field not in oauth_config:
                return False
        
        return True
    
    @staticmethod
    def account_calculate_enrollment_hash(file_content: str) -> str:
        """enrollment 파일 내용 해시 계산"""
        return hashlib.sha256(file_content.encode('utf-8')).hexdigest()

class AccountCryptoHelpers:
    """암호화 관련 헬퍼 함수"""
    
    def __init__(self):
        from infra.core import get_config
        self.config = get_config()
        self._cipher = None
    
    def _get_cipher(self) -> Fernet:
        """암호화 객체 가져오기 (레이지 로딩)"""
        if self._cipher is None:
            # 환경변수에서 키 가져오거나 생성
            key = self.config.encryption_key
            # 32바이트 키를 base64로 인코딩
            if len(key) != 32:
                key = key.ljust(32)[:32]  # 32바이트로 맞춤
            encoded_key = base64.urlsafe_b64encode(key.encode())
            self._cipher = Fernet(encoded_key)
        return self._cipher
    
    def account_encrypt_sensitive_data(self, data: str) -> str:
        """민감한 데이터 암호화"""
        if not data:
            return ""
        
        cipher = self._get_cipher()
        encrypted_bytes = cipher.encrypt(data.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
    
    def account_decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """민감한 데이터 복호화"""
        if not encrypted_data:
            return ""
        
        try:
            cipher = self._get_cipher()
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_bytes = cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            # 복호화 실패 시 로그 기록
            from infra.core import get_logger
            logger = get_logger(__name__)
            logger.error(f"Failed to decrypt sensitive data: {str(e)}")
            return ""

class AccountAuditHelpers:
    """감사 로그 관련 헬퍼 함수"""
    
    @staticmethod
    def account_create_audit_message(action: str, old_value: Optional[str], new_value: Optional[str]) -> str:
        """감사 로그 메시지 생성"""
        if action == "create":
            return f"Account created: {new_value}"
        elif action == "update":
            return f"Account updated: {old_value} -> {new_value}"
        elif action == "status_change":
            return f"Status changed: {old_value} -> {new_value}"
        elif action == "deactivate":
            return f"Account deactivated: {new_value}"
        else:
            return f"Action: {action}"
```

## 7. 호출 스택 다이어그램

### 7.1 계정 동기화 플로우
```
main/api_gateway.py
    ↓
AccountOrchestrator.account_sync_all_enrollment_files()
    ↓
AccountSyncService.account_sync_scan_enrollment_files()
    ↓ (각 파일별)
AccountSyncService._account_sync_parse_enrollment_file()
    ↓
AccountValidator.account_validate_enrollment_data()
    ↓
AccountRepository.account_get_by_email() (기존 계정 확인)
    ↓ (신규 생성 시)
AccountRepository.account_create_from_enrollment()
    ↓ (기존 계정 업데이트 시)  
AccountRepository.account_update_from_enrollment()
    ↓
AccountRepository.account_deactivate_missing_enrollments()
```

### 7.2 계정 조회 플로우
```
main/api_gateway.py
    ↓
AccountOrchestrator.account_get_by_email()
    ↓
AccountRepository.account_get_by_email()
    ↓
AccountRepository._account_row_to_record()
    ↓
AccountCryptoHelpers.account_decrypt_sensitive_data()
```

## 8. 현재 인프라와의 부정합 사항

### 8.1 데이터베이스 스키마 불일치
**문제**: 현재 `infra/migrations/initial_schema.sql`의 accounts 테이블이 OAuth 클라이언트 정보를 저장할 필드가 부족합니다.

**해결방안**: 
- `enrollment_file_path`, `enrollment_file_hash` 필드 추가
- OAuth 관련 필드 (`tenant_id`, `client_id`, `client_secret`, `oauth_scopes`) 추가
- 인덱스 추가

### 8.2 OAuth 클라이언트 고정 설정
**문제**: 현재 `infra/core/oauth_client.py`가 환경변수의 고정된 클라이언트 설정을 사용합니다.

**해결방안**:
- 메서드에 계정별 OAuth 설정을 매개변수로 받도록 수정
- 동적 클라이언트 설정 지원

### 8.3 토큰 서비스 한계
**문제**: 현재 `infra/core/token_service.py`가 단일 OAuth 설정을 가정합니다.

**해결방안**:
- 계정별 OAuth 설정을 사용한 토큰 갱신 로직 추가
- account 모듈과의 연동 강화

### 8.4 환경변수 부족
**문제**: 암호화 키, enrollment 디렉터리 경로 등 설정이 부족합니다.

**해결방안**:
- `.env` 파일에 `ENCRYPTION_KEY`, `ENROLLMENT_DIRECTORY` 추가
- `infra/core/config.py`에 해당 설정값 추가

## 9. 구현 순서 및 일정

### 9.1 Phase 1: 기반 수정 (1일)
1. **infra 수정**
   - `database.py` - accounts 테이블 스키마 업데이트
   - `config.py` - 암호화 키, enrollment 디렉터리 설정 추가
   - `oauth_client.py` - 동적 클라이언트 설정 지원
   - `token_service.py` - 계정별 토큰 갱신 로직

2. **환경설정 수정**
   - `.env.example` - 새로운 환경변수 추가
   - 마이그레이션 스크립트 업데이트

### 9.2 Phase 2: Account 모듈 기본 구조 (1일)
1. **스키마 및 헬퍼 구현**
   - `account_schema.py` - Pydantic 모델 정의
   - `_account_helpers.py` - 유틸리티 함수들
   - `account_validator.py` - 데이터 검증 로직

### 9.3 Phase 3: 핵심 서비스 구현 (1.5일)
1. **데이터 액세스 레이어**
   - `account_repository.py` - DB CRUD 구현
   - 암호화/복호화 로직 구현
   - 감사 로그 기록 로직

2. **동기화 서비스**
   - `account_sync_service.py` - enrollment 파일 처리
   - YAML 파싱 및 검증

### 9.4 Phase 4: 오케스트레이터 구현 (1일)
1. **account_orchestrator.py**
   - 전체 동기화 플로우
   - 계정 조회/관리 기능
   - 트랜잭션 처리

### 9.5 Phase 5: 통합 테스트 (0.5일)
1. **enrollment 파일 테스트**
   - 실제 enrollment 파일로 동기화 테스트
   - 암호화/복호화 테스트
   - 오류 처리 테스트

## 10. 테스트 시나리오

### 10.1 기본 동기화 테스트
```bash
# 1. enrollment 파일 생성
echo "
email: test@example.com
name: Test User
oauth_config:
  tenant_id: test-tenant-id
  client_id: test-client-id
  client_secret: test-client-secret
  oauth_scopes: User.Read,Mail.Read,offline_access
" > enrollment/test.yaml

# 2. 동기화 실행
python -c "
import asyncio
from modules.account.account_orchestrator import AccountOrchestrator
async def test():
    orchestrator = AccountOrchestrator()
    result = await orchestrator.account_sync_all_enrollment_files()
    print(result)
asyncio.run(test())
"
```

### 10.2 계정 상태 변경 테스트
```python
# 계정 상태 업데이트 테스트
async def test_status_update():
    orchestrator = AccountOrchestrator()
    
    # 계정 조회
    account = await orchestrator.account_get_by_email("test@example.com")
    
    # 상태 변경
    success = await orchestrator.account_update_status(
        account.id, 
        AccountStatus.ACTIVE
    )
    print(f"Status update: {success}")
```

## 11. 주의사항 및 체크포인트

### 11.1 보안 고려사항
- ✅ **클라이언트 시크릿 암호화**: Fernet 암호화 사용
- ✅ **토큰 안전 저장**: 데이터베이스에 암호화된 형태로 저장
- ✅ **파일 접근 권한**: enrollment 디렉터리 접근 권한 확인
- ✅ **로그 마스킹**: 민감한 정보 로그에 노출 방지

### 11.2 성능 고려사항
- ✅ **트랜잭션 처리**: 동기화 작업을 트랜잭션으로 묶기
- ✅ **배치 처리**: 대량 계정 처리 시 메모리 효율성
- ✅ **인덱스 활용**: 이메일, 상태별 조회 최적화
- ✅ **레이지 로딩**: 암호화 객체 등 필요시에만 생성

### 11.3 에러 처리
- ✅ **파일 파싱 오류**: 개별 파일 오류가 전체 동기화를 중단하지 않도록
- ✅ **DB 연결 오류**: 재시도 로직 및 적절한 예외 전파
- ✅ **암호화 오류**: 복호화 실패 시 안전한 처리
- ✅ **검증 오류**: 명확한 오류 메시지 제공

### 11.4 코드 품질
- ✅ **350줄 제한**: 각 파일의 라인 수 확인
- ✅ **명명 규칙**: `account_` prefix 일관성 유지
- ✅ **타입 힌트**: 모든 함수/메서드에 타입 힌트 추가
- ✅ **문서화**: docstring 및 주석 충실히 작성

## 12. 완료 기준

### 12.1 기능 완료 기준
- [ ] enrollment 파일 스캔 및 파싱 성공
- [ ] 신규 계정 생성 및 기존 계정 업데이트 성공
- [ ] 제거된 계정 비활성화 성공
- [ ] 계정 상태 관리 기능 정상 동작
- [ ] OAuth 클라이언트 정보 암호화 저장/조회 성공

### 12.2 품질 완료 기준
- [ ] 모든 파일 350줄 이하 유지
- [ ] 단위 테스트 시나리오 통과
- [ ] 코드 리뷰 완료
- [ ] 문서화 완료 (README.md)

이 구현 계획서에 따라 Account 모듈을 구현하면 enrollment 파일과 데이터베이스 간의 안전하고 효율적인 계정 동기화가 가능하며, 향후 인증 모듈과의 연동도 원활하게 진행할 수 있습니다.
