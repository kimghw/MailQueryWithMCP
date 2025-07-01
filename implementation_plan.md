# GraphAPIQuery 프로젝트 구현 계획서

## 1. 프로젝트 개요
Microsoft Graph API를 통해 메일 데이터를 조회하고 처리하는 시스템으로, SQLite를 사용한 계정 및 히스토리 관리와 Kafka를 통한 이벤트 발행을 구현합니다.

## 2. 아키텍처 구조 (개선된 독립 모듈 구조)

```
IACSGRAPH/
├── infra/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # 환경 설정 관리 (전역)
│   │   ├── database.py          # SQLite 연결 관리 (전역, 레이지 싱글톤)
│   │   ├── kafka_client.py      # Kafka 연결 관리 (전역, 레이지 싱글톤)
│   │   ├── token_service.py     # 전역 토큰 관리 서비스
│   │   ├── oauth_client.py      # OAuth 인증 클라이언트
│   │   └── exceptions.py        # 표준 예외 클래스
│   └── migrations/
│       ├── __init__.py
│       └── initial_schema.sql   # 초기 DB 스키마
│
├── modules/
│   ├── account/                 # UC-1: 계정 관리
│   │   ├── __init__.py
│   │   ├── orchestrator.py      # 계정 관리 오케스트레이터 (독립적)
│   │   ├── schema.py            # 계정 관련 Pydantic 모델
│   │   ├── sync_service.py      # enrollment 동기화
│   │   └── README.md
│   │
│   ├── auth/                    # UC-1.1, UC-1.2: 인증
│   │   ├── __init__.py
│   │   ├── orchestrator.py      # 인증 오케스트레이터 (독립적)
│   │   ├── schema.py            # 인증 관련 Pydantic 모델
│   │   ├── web_server.py        # 리디렉션 처리
│   │   └── README.md
│   │
│   ├── mail_query/              # UC-2: 메일 조회
│   │   ├── __init__.py
│   │   ├── orchestrator.py      # 메일 조회 오케스트레이터 (독립적)
│   │   ├── schema.py            # 메일 조회 관련 Pydantic 모델
│   │   ├── graph_client.py      # Graph API 클라이언트 (모듈 내부)
│   │   ├── filter_builder.py    # OData 필터 생성
│   │   └── README.md
│   │
│   ├── mail_processor/          # UC-3: 메일 처리
│   │   ├── __init__.py
│   │   ├── orchestrator.py      # 메일 처리 오케스트레이터 (완전 독립적)
│   │   ├── schema.py            # 메일 처리 관련 Pydantic 모델
│   │   ├── filter_service.py    # 발신자 필터링
│   │   ├── _helpers.py          # 헬퍼 함수 (350줄 제한 대응)
│   │   └── README.md
│   │
│   ├── mail_history/            # UC-4: 히스토리 관리
│   │   ├── __init__.py
│   │   ├── orchestrator.py      # 히스토리 관리 오케스트레이터 (독립적)
│   │   ├── schema.py            # 히스토리 관련 Pydantic 모델
│   │   ├── cleanup_service.py   # 자동 정리
│   │   └── README.md
│   │
│   └── keyword_extractor/       # UC-5: 키워드 추출
│       ├── __init__.py
│       ├── orchestrator.py      # 키워드 추출 오케스트레이터 (독립적)
│       ├── schema.py            # 키워드 관련 Pydantic 모델
│       ├── openai_service.py    # OpenAI API 연동 (모듈 내부)
│       └── README.md
│
├── main/
│   ├── __init__.py
│   ├── api_gateway.py           # 단순 라우팅만 담당
│   ├── request_handler.py       # 요청 처리 및 라우팅
│   └── response_formatter.py    # 응답 형식 통일
│
├── scheduler/
│   ├── __init__.py
│   └── main.py                  # 스케줄러 진입점
│
├── .env.example
├── pyproject.toml               # uv 패키지 관리
├── README.md
└── requirements.txt
```

### 개선 핵심 원칙
1. **모듈 완전 독립성**: 각 모듈이 필요한 기능을 자체 구현
2. **전역 서비스 최소화**: config, database, kafka, token_service만 전역 유지
3. **순환 참조 완전 제거**: 단방향 의존성만 허용
4. **YAGNI 원칙 적용**: 현재 필요한 기능만 구현
5. **350줄 제한**: 파일 크기 관리를 위한 헬퍼 클래스 분리

## 3. 모듈별 상세 설계

### 3.1 인프라 레이어 (infra/)

#### 3.1.1 Core 모듈
```python
# infra/core/config.py
class Config:
    """전역 설정 관리 (레이지 싱글톤)"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        - SQLite DB 경로
        - Kafka 연결 정보
        - OAuth 설정 (client_id, redirect_uri 등)
        - 로그 레벨 설정
    
# infra/core/database.py
class DatabaseManager:
    """SQLite 연결 관리 (레이지 싱글톤) - 연결만 관리"""
    _instance = None
    _connection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def get_connection(self):
        """연결 반환, 필요시 재연결"""
        if self._connection is None:
            self._connection = await self._create_connection()
        return self._connection
    
    async def execute_migration(self, migration_sql: str):
        """마이그레이션 실행"""
        conn = await self.get_connection()
        await conn.executescript(migration_sql)

# infra/core/kafka_client.py
class KafkaManager:
    """Kafka 연결 관리 (레이지 싱글톤) - 연결만 관리"""
    _instance = None
    _producer = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def get_producer(self):
        """Producer 반환, 필요시 재연결"""
        if self._producer is None:
            self._producer = await self._create_producer()
        return self._producer

# infra/core/token_service.py
class TokenService:
    """전역 토큰 관리 서비스 (레이지 싱글톤)"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.db_manager = DatabaseManager()
            cls._instance.oauth_client = OAuthClient()
        return cls._instance
    
    async def get_valid_token(self, account_id: str) -> str:
        """유효한 토큰 반환, 만료시 자동 갱신"""
        conn = await self.db_manager.get_connection()
        
        # 토큰 조회
        account = await self._get_account(conn, account_id)
        
        # 토큰 만료 확인
        if self._is_token_expired(account['token_expires_at']):
            # 토큰 갱신
            new_tokens = await self.oauth_client.refresh_token(
                account['refresh_token']
            )
            
            # DB 업데이트
            await self._update_tokens(conn, account_id, new_tokens)
            return new_tokens['access_token']
        
        return account['access_token']

# infra/core/oauth_client.py
class OAuthClient:
    """OAuth 인증 클라이언트"""
    def __init__(self):
        self.config = Config()
    
    async def refresh_token(self, refresh_token: str) -> dict:
        """토큰 갱신"""
        # Azure AD에 refresh_token으로 새 토큰 요청
        pass

# infra/core/exceptions.py
class IacsGraphException(Exception):
    """기본 예외 클래스"""
    pass

class AuthenticationError(IacsGraphException):
    """인증 관련 예외"""
    pass

class TokenExpiredError(AuthenticationError):
    """토큰 만료 예외"""
    pass

class DatabaseError(IacsGraphException):
    """데이터베이스 관련 예외"""
    pass

class ExternalAPIError(IacsGraphException):
    """외부 API 호출 예외"""
    pass
```

#### 3.1.2 SQLite 스키마
```sql
-- accounts 테이블
CREATE TABLE accounts (
    id TEXT PRIMARY KEY,  -- UUID
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    tenant_id TEXT,
    client_id TEXT,
    client_secret TEXT,  -- 암호화 저장
    status TEXT DEFAULT 'INACTIVE',  -- ACTIVE, INACTIVE, LOCKED, REAUTH_REQUIRED
    access_token TEXT,  -- 암호화 저장
    refresh_token TEXT,  -- 암호화 저장
    token_expires_at TIMESTAMP,
    last_sync_at TIMESTAMP,
    last_authenticated_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- mail_histories 테이블
CREATE TABLE mail_histories (
    id TEXT PRIMARY KEY,  -- Graph API 메일 ID
    account_id TEXT NOT NULL,
    sender_address TEXT NOT NULL,
    subject TEXT,
    preview TEXT,
    sent_time TIMESTAMP,
    keywords TEXT,  -- JSON 배열
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    UNIQUE(id, sender_address)
);

-- audit_logs 테이블
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT,
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    old_value TEXT,
    new_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- query_logs 테이블 (기본 로깅용)
CREATE TABLE query_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    query_type TEXT DEFAULT 'mail_query',
    odata_filter TEXT,
    select_fields TEXT,
    top INTEGER NOT NULL DEFAULT 50,
    skip INTEGER NOT NULL DEFAULT 0,
    result_count INTEGER NOT NULL DEFAULT 0,
    execution_time_ms INTEGER NOT NULL DEFAULT 0,
    has_error BOOLEAN NOT NULL DEFAULT FALSE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 모듈별 구현 계획

#### 3.2.1 Account 모듈 (UC-1)
```python
# modules/account/orchestrator.py
class AccountOrchestrator:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.sync_service = AccountSyncService()
    
    async def sync_accounts(self):
        """enrollment/*.yaml 파일과 DB 동기화"""
        conn = await self.db_manager.get_connection()
        
        # enrollment 디렉터리 스캔
        enrollment_files = await self.sync_service.scan_enrollment_files()
        
        # 각 파일 처리
        for file_path, account_data in enrollment_files.items():
            # DB에서 기존 계정 조회
            existing = await self._get_account_by_email(conn, account_data['email'])
            
            if existing:
                # 업데이트
                await self._update_account(conn, account_data)
            else:
                # 신규 생성
                await self._create_account(conn, account_data)
            
            # 감사 로그 기록
            await self._log_audit(conn, 'sync', account_data['email'])
        
        # DB에 있지만 enrollment에 없는 계정 처리
        await self._handle_removed_accounts(conn, enrollment_files)
```

**호출 스택:**
```
APIGateway.sync_accounts()
    → AccountOrchestrator.sync_accounts()
        → AccountSyncService.scan_enrollment_files()
        → AccountOrchestrator._get_account_by_email() (DB 직접 조회)
        → AccountOrchestrator._create_account() / _update_account() (DB 직접 작업)
        → AccountOrchestrator._log_audit() (DB 직접 기록)
```

#### 3.2.2 Auth 모듈 (UC-1.1)
```python
# modules/auth/orchestrator.py
class AuthOrchestrator:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.config = Config()
        self.web_server = LocalWebServer()
    
    async def authenticate_account(self, account_id: str):
        """신규 인증 플로우 - 사용자가 직접 로그인"""
        conn = await self.db_manager.get_connection()
        
        # 계정 정보 조회
        account = await self._get_account(conn, account_id)
        
        # OAuth 인증 URL 생성
        auth_url = self._generate_auth_url(account)
        
        # 로컬 웹서버 시작 (리디렉션 수신)
        auth_code = await self.web_server.start_and_wait_for_code()
        
        # 인증 코드로 토큰 교환
        tokens = await self._exchange_code_for_token(auth_code)
        
        # DB에 토큰 저장 및 상태 업데이트
        await self._save_tokens(conn, account_id, tokens)
        await self._update_account_status(conn, account_id, 'ACTIVE')
    
    async def _exchange_code_for_token(self, auth_code: str) -> dict:
        """인증 코드를 토큰으로 교환"""
        # Azure AD에 토큰 요청
        # 이 작업은 auth 모듈이 직접 수행 (최초 인증 시)
        pass
```

**호출 스택:**
```
APIGateway.authenticate_account(email)
    → APIGateway._get_account_by_email(email)
    → AuthOrchestrator.authenticate_account(account_id)
        → AuthOrchestrator._generate_auth_url()
        → LocalWebServer.start_and_wait_for_code()
        → AuthOrchestrator._exchange_code_for_token()
        → AuthOrchestrator._save_tokens() (DB 직접 작업)
        → AuthOrchestrator._update_account_status() (DB 직접 작업)
```

#### 3.2.3 Mail Query 모듈 (UC-2)
```python
# modules/mail_query/orchestrator.py
class MailQueryOrchestrator:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.graph_client = GraphAPIClient()
        self.filter_builder = ODataFilterBuilder()
        self.token_service = TokenService()
    
    async def query_mails(self, account_id: str, filters: dict):
        """메일 조회 및 필터링"""
        conn = await self.db_manager.get_connection()
        start_time = time.time()
        
        # 유효한 토큰 확보 (자동 갱신 포함)
        access_token = await self.token_service.get_valid_token(account_id)
        
        # OData 필터 생성
        odata_filter = self.filter_builder.build_filter(filters)
        
        # Graph API 호출
        all_messages = []
        async for page in self.graph_client.get_messages_paginated(
            access_token, odata_filter
        ):
            all_messages.extend(page['value'])
        
        # 조회 로그 기록
        execution_time = int((time.time() - start_time) * 1000)
        await self._log_query(
            conn, account_id, 'mail_query', 
            filters, len(all_messages), execution_time
        )
        
        return all_messages
```

**호출 스택:**
```
APIGateway.query_mails(email, filters)
    → APIGateway._get_account_by_email(email)
    → MailQueryOrchestrator.query_mails(account_id, filters)
        → TokenService.get_valid_token()
            → (TokenService 내부에서 자동 갱신 처리)
        → ODataFilterBuilder.build_filter()
        → GraphAPIClient.get_messages_paginated()
        → MailQueryOrchestrator._log_query() (DB 직접 작업)
```

#### 3.2.4 Mail Processor 모듈 (UC-3) - 완전 독립적 구현
```python
# modules/mail_processor/orchestrator.py
class MailProcessorOrchestrator:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.kafka_manager = KafkaManager()
        self.token_service = TokenService()
        self.filter_service = MailFilterService()
    
    async def process_new_mails(self):
        """독립적으로 새 메일 처리 및 이벤트 발행 - 함수 주입 없음"""
        conn = await self.db_manager.get_connection()
        producer = await self.kafka_manager.get_producer()
        
        # 1. DB에서 직접 활성 계정 조회
        active_accounts = await self._get_active_accounts(conn)
        
        for account in active_accounts:
            try:
                # 2. Graph API 직접 호출로 메일 조회
                mails = await self._fetch_mails_from_graph(account)
                
                for mail in mails:
                    # 발신자 필터링
                    if not self.filter_service.should_process(mail['from']['emailAddress']['address']):
                        continue
                    
                    # 중복 검사
                    if await self._is_duplicate(conn, mail['id'], mail['from']['emailAddress']['address']):
                        continue
                    
                    # 3. 간단한 키워드 추출 (자체 구현)
                    keywords = await self._extract_keywords_simple(mail['body']['content'])
                    
                    # DB 저장
                    await self._save_mail_history(conn, account['id'], mail, keywords)
                    
                    # Kafka 이벤트 발행
                    event = self._create_mail_event(account['id'], mail)
                    await producer.send('email.received', event)
                
                # 마지막 동기화 시간 업데이트
                await self._update_last_sync_time(conn, account['id'])
                
            except Exception as e:
                # 계정별 에러 처리
                await self._handle_account_error(conn, account['id'], str(e))
    
    async def _get_active_accounts(self, conn):
        """DB에서 직접 활성 계정 조회"""
        query = "SELECT * FROM accounts WHERE status = 'ACTIVE'"
        results = await conn.execute(query).fetchall()
        return [dict(row) for row in results]
    
    async def _fetch_mails_from_graph(self, account):
        """Graph API 직접 호출 - 자체 구현"""
        import aiohttp
        
        # 토큰 획득
        access_token = await self.token_service.get_valid_token(account['id'])
        
        # 마지막 동기화 이후 메일만 조회
        since_filter = ""
        if account.get('last_sync_at'):
            since_filter = f"&$filter=receivedDateTime ge {account['last_sync_at']}"
        
        # Graph API 호출
        url = f"https://graph.microsoft.com/v1.0/me/messages?$top=50{since_filter}"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('value', [])
                else:
                    raise Exception(f"Graph API 호출 실패: {response.status}")
    
    async def _extract_keywords_simple(self, text: str) -> List[str]:
        """간단한 키워드 추출 - 자체 구현"""
        import re
        
        # HTML 태그 제거
        clean_text = re.sub('<[^<]+?>', '', text)
        
        # 너무 짧으면 빈 리스트 반환
        if len(clean_text.strip()) < 10:
            return []
        
        # 간단한 키워드 추출 (한국어 단어 추출)
        korean_words = re.findall(r'[가-힣]{2,}', clean_text)
        
        # 빈도수 기준 상위 5개 반환
        from collections import Counter
        word_counts = Counter(korean_words)
        return [word for word, count in word_counts.most_common(5)]
    
    async def _update_last_sync_time(self, conn, account_id: str):
        """마지막 동기화 시간 업데이트"""
        from datetime import datetime
        query = "UPDATE accounts SET last_sync_at = ? WHERE id = ?"
        await conn.execute(query, (datetime.now(), account_id))
    
    async def _handle_account_error(self, conn, account_id: str, error_msg: str):
        """계정별 에러 처리"""
        query = "UPDATE accounts SET error_message = ?, updated_at = ? WHERE id = ?"
        await conn.execute(query, (error_msg, datetime.now(), account_id))

# modules/mail_processor/_helpers.py (350줄 제한 대응)
class MailProcessorHelpers:
    """Mail Processor 헬퍼 함수들"""
    
    @staticmethod
    def clean_email_content(html_content: str) -> str:
        """이메일 본문 정제"""
        import re
        # HTML 태그 제거
        clean = re.sub('<[^<]+?>', '', html_content)
        # 과도한 공백 정리
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()
    
    @staticmethod
    def extract_sender_domain(email_address: str) -> str:
        """발신자 도메인 추출"""
        if '@' in email_address:
            return email_address.split('@')[1].lower()
        return ''
    
    @staticmethod
    def create_mail_fingerprint(mail_id: str, sender: str) -> str:
        """메일 고유 식별자 생성"""
        import hashlib
        content = f"{mail_id}_{sender}"
        return hashlib.md5(content.encode()).hexdigest()
```

**개선된 호출 스택:**
```
Scheduler → APIGateway.process_all_accounts_mails()
    → MailProcessorOrchestrator.process_new_mails()
        → MailProcessorOrchestrator._get_active_accounts() (DB 직접 조회)
        → MailProcessorOrchestrator._fetch_mails_from_graph() (Graph API 직접 호출)
        → MailProcessorOrchestrator._extract_keywords_simple() (자체 키워드 추출)
        → MailProcessorOrchestrator._save_mail_history() (DB 직접 작업)
        → KafkaProducer.send()
```

#### 3.2.5 Kafka 이벤트 구조
```python
# modules/mail_processor/event_publisher.py
@dataclass
class MailReceivedEvent:
    event_type: str = "email_type"
    event_id: str
    account_id: str
    occurred_at: datetime
    api_endpoint: str = "/v1.0/me/messages"
    response_status: int = 200
    request_params: dict
    response_data: dict  # 전체 Graph API 응답
    response_timestamp: datetime
```

#### 3.2.6 Mail History 모듈 (UC-4)
```python
# modules/mail_history/orchestrator.py
class MailHistoryOrchestrator:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.cleanup_service = HistoryCleanupService()
    
    async def search_history(self, filters: dict):
        """히스토리 검색"""
        conn = await self.db_manager.get_connection()
        
        # 검색 조건 파싱
        where_clauses = []
        params = []
        
        if filters.get('account_email'):
            where_clauses.append("h.account_id = (SELECT id FROM accounts WHERE email = ?)")
            params.append(filters['account_email'])
        
        if filters.get('sender'):
            where_clauses.append("h.sender_address LIKE ?")
            params.append(f"%{filters['sender']}%")
        
        if filters.get('keywords'):
            where_clauses.append("h.keywords LIKE ?")
            params.append(f"%{filters['keywords']}%")
        
        # DB 쿼리 실행
        query = f"""
            SELECT h.*, a.email as account_email 
            FROM mail_histories h 
            LEFT JOIN accounts a ON h.account_id = a.id
            WHERE {' AND '.join(where_clauses) if where_clauses else '1=1'}
            ORDER BY h.sent_time DESC
            LIMIT {filters.get('limit', 100)}
        """
        
        results = await conn.execute(query, params).fetchall()
        return [dict(row) for row in results]
    
    async def cleanup_old_data(self, retention_days: int = 90):
        """오래된 데이터 정리"""
        conn = await self.db_manager.get_connection()
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        # 삭제 대상 조회
        delete_query = "SELECT COUNT(*) FROM mail_histories WHERE created_at < ?"
        count_result = await conn.execute(delete_query, (cutoff_date,)).fetchone()
        delete_count = count_result[0]
        
        if delete_count > 0:
            # 트랜잭션 내 삭제
            async with conn.begin():
                await conn.execute(
                    "DELETE FROM mail_histories WHERE created_at < ?",
                    (cutoff_date,)
                )
                
                # 삭제 로그 기록
                await conn.execute(
                    "INSERT INTO audit_logs (action, entity_type, old_value, created_at) VALUES (?, ?, ?, ?)",
                    ('cleanup', 'mail_histories', str(delete_count), datetime.now())
                )
        
        return delete_count
```

#### 3.2.7 Keyword Extractor 모듈 (UC-5)
```python
# modules/keyword_extractor/orchestrator.py
class KeywordExtractorOrchestrator:
    def __init__(self):
        self.openai_service = OpenAIService()
        self.config = Config()
    
    async def extract_keywords(self, text: str) -> List[str]:
        """메일 본문에서 키워드 추출"""
        try:
            # HTML 태그 제거 및 텍스트 정제
            clean_text = self._clean_text(text)
            
            # 너무 짧은 텍스트는 키워드 없음으로 처리
            if len(clean_text.strip()) < 10:
                return []
            
            # 프롬프트 생성
            prompt = f"""다음 이메일 본문에서 가장 중요한 키워드 5개를 한국어로 추출해줘:

{clean_text[:1000]}  # 첫 1000자만 사용

형식: keyword1, keyword2, keyword3, keyword4, keyword5
"""
            
            # OpenAI API 호출
            response = await self.openai_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100
            )
            
            # 응답 파싱
            keywords_text = response.choices[0].message.content.strip()
            keywords = [kw.strip() for kw in keywords_text.split(',')]
            
            # 상위 5개 키워드 반환 (빈 값 제거)
            return [kw for kw in keywords[:5] if kw]
            
        except Exception as e:
            # API 연결 실패 등의 경우 빈 리스트 반환
            print(f"키워드 추출 실패: {e}")
            return []
    
    def _clean_text(self, html_text: str) -> str:
        """HTML 태그 제거 및 텍스트 정제"""
        import re
        # HTML 태그 제거
        clean = re.sub('<[^<]+?>', '', html_text)
        # 과도한 공백 정리
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()
```

### 3.3 API Gateway 구현 (단순 라우팅만 담당)
```python
# main/api_gateway.py
class APIGateway:
    """단순 라우팅만 담당 - 비즈니스 로직 없음"""
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.account_orchestrator = AccountOrchestrator()
        self.auth_orchestrator = AuthOrchestrator()
        self.mail_query_orchestrator = MailQueryOrchestrator()
        self.mail_processor_orchestrator = MailProcessorOrchestrator()
        self.mail_history_orchestrator = MailHistoryOrchestrator()
        self.keyword_extractor_orchestrator = KeywordExtractorOrchestrator()
    
    async def sync_accounts(self):
        """계정 동기화 - 단순 위임"""
        return await self.account_orchestrator.sync_accounts()
    
    async def authenticate_account(self, email: str):
        """계정 인증 - 이메일로 계정 ID 조회 후 위임"""
        account = await self._get_account_by_email(email)
        if not account:
            raise ValueError(f"계정을 찾을 수 없습니다: {email}")
        return await self.auth_orchestrator.authenticate_account(account['id'])
    
    async def query_mails(self, email: str, filters: dict):
        """메일 조회 - 이메일로 계정 ID 조회 후 위임"""
        account = await self._get_account_by_email(email)
        if not account:
            raise ValueError(f"계정을 찾을 수 없습니다: {email}")
        return await self.mail_query_orchestrator.query_mails(account['id'], filters)
    
    async def process_all_accounts_mails(self):
        """모든 계정의 메일 처리 - 함수 주입 없이 직접 호출"""
        return await self.mail_processor_orchestrator.process_new_mails()
    
    async def extract_keywords(self, text: str):
        """키워드 추출 - 단순 위임"""
        return await self.keyword_extractor_orchestrator.extract_keywords(text)
    
    async def search_mail_history(self, filters: dict):
        """메일 히스토리 검색 - 단순 위임"""
        return await self.mail_history_orchestrator.search_history(filters)
    
    async def cleanup_old_history(self, retention_days: int = 90):
        """오래된 히스토리 정리 - 단순 위임"""
        return await self.mail_history_orchestrator.cleanup_old_data(retention_days)
    
    async def _get_account_by_email(self, email: str):
        """이메일로 계정 조회 - 최소한의 DB 조회만"""
        conn = await self.db_manager.get_connection()
        query = "SELECT * FROM accounts WHERE email = ?"
        result = await conn.execute(query, (email,)).fetchone()
        return dict(result) if result else None

# main/request_handler.py
class RequestHandler:
    """요청 처리 및 라우팅"""
    def __init__(self):
        self.api_gateway = APIGateway()
        self.response_formatter = ResponseFormatter()
    
    async def handle_request(self, request_type: str, params: dict):
        """요청 타입에 따른 처리"""
        handlers = {
            "sync_accounts": self.api_gateway.sync_accounts,
            "authenticate": lambda: self.api_gateway.authenticate_account(params["email"]),
            "query_mails": lambda: self.api_gateway.query_mails(params["email"], params.get("filters", {})),
            "process_mails": self.api_gateway.process_all_accounts_mails,
            "search_history": lambda: self.api_gateway.search_mail_history(params.get("filters", {})),
            "cleanup_history": lambda: self.api_gateway.cleanup_old_history(params.get("retention_days", 90))
        }
        
        handler = handlers.get(request_type)
        if not handler:
            raise ValueError(f"Unknown request type: {request_type}")
        
        try:
            result = await handler()
            return self.response_formatter.format_success(result)
        except Exception as e:
            return self.response_formatter.format_error(e)

# main/response_formatter.py
class ResponseFormatter:
    """응답 형식 통일"""
    def format_success(self, data):
        return {
            "status": "success",
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def format_error(self, error):
        return {
            "status": "error",
            "error": str(error),
            "error_type": type(error).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }
```

### 3.4 스케줄러 구현
```python
# scheduler/main.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from main.api_gateway import APIGateway

class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.api_gateway = APIGateway()
        
    def start(self):
        """스케줄러 시작"""
        self.scheduler.add_job(
            self.process_new_mails,
            'interval',
            minutes=5,
            id='process_new_mails'
        )
        
        self.scheduler.add_job(
            self.cleanup_old_history,
            'cron',
            hour=2,
            minute=0,
            id='cleanup_old_history'
        )
        
        self.scheduler.start()
    
    async def process_new_mails(self):
        """5분마다 새 메일 처리"""
        await self.api_gateway.process_all_accounts_mails()
    
    async def cleanup_old_history(self):
        """매일 새벽 2시 오래된 데이터 정리"""
        await self.api_gateway.cleanup_old_history()
```

## 4. 개선된 구현 순서 및 일정

### Phase 1: 기반 구조 (1주)
1. 프로젝트 구조 생성 및 설정 (uv 패키지 관리)
2. infra/core 모듈 구현 (config, database, kafka, token_service, oauth_client, exceptions)
3. SQLite 스키마 및 마이그레이션
4. 단순 API Gateway 구현 (라우팅만)

### Phase 2: 계정 관리 (1주)
1. Account 모듈 구현 (완전 독립적)
2. enrollment 파일 동기화
3. API Gateway 계정 관리 라우팅 추가

### Phase 3: 인증 시스템 (완료)
- **[x] Auth 모듈 구현 완료**: `modules/auth`에 독립 모듈로 구현되었습니다.
- **[x] OAuth 2.0 플로우 구현**: `auth_orchestrator`와 `auth_web_server`를 통해 인증 URL 생성, 콜백 처리, 토큰 교환 플로우가 완료되었습니다.
- **[x] TokenService 연동**: `infra.core.token_service`와 연동하여 토큰을 저장하고, 유효성 검사 및 자동 갱신을 처리합니다.

### Phase 4: 메일 조회 (진행 중)
1. Mail Query 모듈 구현 (독립적)
2. Graph API 클라이언트 (모듈 내부)
3. OData 필터 빌더
4. API Gateway 메일 조회 라우팅 추가

### Phase 5: 메일 처리 및 이벤트 (진행 예정)
1. Mail Processor 모듈 구현 (완전 독립적)
2. 자체 Graph API 호출 구현
3. 간단한 키워드 추출 구현 (자체)
4. Kafka 이벤트 발행
5. 스케줄러 구현

### Phase 6: 키워드 추출 (진행 예정)
1. Keyword Extractor 모듈 구현 (독립적)
2. OpenAI API 연동 (모듈 내부)
3. 복잡한 키워드 추출 로직

### Phase 7: 히스토리 관리 (진행 예정)
1. Mail History 모듈 구현 (독립적)
2. 히스토리 검색 및 관리
3. 자동 정리 기능

### Phase 8: 테스트 및 문서화 (지속)
1. /test/scenario 기반 시나리오 테스트
2. 성능 최적화
3. 모듈별 README.md 작성
4. 전체 문서 정리

### 주요 개선 사항:
- **Phase 5와 6 순서 변경**: Keyword Extractor를 먼저 구현하되, Mail Processor는 자체 간단 구현 사용
- **완전 독립적 구현**: 각 Phase에서 모듈이 자체적으로 필요한 기능 구현
- **함수 주입 제거**: 모듈 간 의존성 완전 제거
- **API Gateway 단순화**: 각 Phase에서 라우팅만 추가
- **시나리오 기반 테스트**: /test/scenario의 명시된 시나리오에 따라서만 테스트

## 5. 기술 스택

### 언어 및 프레임워크
- Python 3.11+
- Pydantic v2 (데이터 검증)
- aiohttp (비동기 HTTP)
- APScheduler (스케줄링)

### 데이터베이스
- SQLite3 (로컬 DB)
- SQLAlchemy (ORM, 선택사항)

### 메시징
- Kafka (이벤트 버스)
- aiokafka (비동기 Kafka 클라이언트)

### 외부 API
- Microsoft Graph API
- OpenAI API

### 개발 도구
- uv (패키지 관리)
- Black (코드 포맷팅)
- Ruff (린팅)
- pytest (테스트)

## 6. 보안 고려사항

1. **토큰 암호화**: cryptography 라이브러리 사용
2. **환경 변수**: python-dotenv로 관리
3. **SQL Injection 방지**: 파라미터화된 쿼리 사용
4. **API 키 관리**: .env 파일로 관리, .gitignore 추가

## 7. 성능 최적화

1. **비동기 처리**: asyncio 기반 구현
2. **연결 풀링**: SQLite 연결 재사용
3. **배치 처리**: 메일 조회 시 페이징
4. **캐싱**: 자주 사용되는 데이터 메모리 캐싱

## 8. 모니터링 및 로깅

1. **구조화된 로깅**: structlog 사용
2. **메트릭 수집**: OpenTelemetry
3. **에러 추적**: Sentry (선택사항)
4. **헬스체크**: 각 모듈별 상태 확인

## 9. 주의사항

1. **순환 참조 방지**: 모듈 간 단방향 의존성 유지
2. **350줄 제한**: 파일당 코드 라인 수 제한
3. **명명 규칙**: 모듈명을 prefix로 사용
4. **에러 처리**: 각 레이어별 적절한 예외 처리
