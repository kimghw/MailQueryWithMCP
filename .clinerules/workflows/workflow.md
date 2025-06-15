# IACSGRAPH 프로젝트 작업 순서 계획

## 현재 상태
- [x] 프로젝트 문서 작성 (usecase.md, implementation_plan.md)
- [x] 환경설정 파일 (.env, .env.example)
- [x] Git 저장소 설정 및 초기 커밋
- [x] .gitignore 설정 (enrollment/ 제외)

## Phase 1: 프로젝트 기반 구조 설정 (1-2일)

### 1.1 디렉터리 구조 생성
```bash
mkdir -p infra/core
mkdir -p infra/migrations
mkdir -p modules/{account,auth,mail_query,mail_processor,mail_history,keyword_extractor}
mkdir -p main
mkdir -p scheduler
mkdir -p data
mkdir -p logs
```

### 1.2 패키지 관리 설정 (uv)
- [ ] `pyproject.toml` 생성
- [ ] uv를 이용한 가상환경 생성
- [ ] 기본 의존성 설치 (asyncio, aiohttp, pydantic, etc.)

### 1.3 기본 __init__.py 파일 생성
- [ ] 모든 모듈 디렉터리에 `__init__.py` 생성

### 1.4 SQLite 스키마 생성
- [ ] `infra/migrations/initial_schema.sql` 구현
- [ ] 테이블 생성 스크립트 작성

## Phase 2: 인프라 레이어 구현 (2-3일)

### 2.1 Core 인프라 구현 (전역 서비스만)
- [x] `infra/core/config.py` - 환경설정 로드 (레이지 싱글톤)
- [x] `infra/core/database.py` - SQLite 연결 관리 (레이지 싱글톤)
- [x] `infra/core/kafka_client.py` - Kafka 연결 관리 (레이지 싱글톤)
- [x] `infra/core/exceptions.py` - 표준 예외 클래스 정의

### 2.2 OAuth 및 토큰 관리
- [x] `infra/core/oauth_client.py` - OAuth 클라이언트
- [x] `infra/core/token_service.py` - 토큰 관리 서비스 (레이지 싱글톤)

### 2.3 기본 스키마 정의
- [x] 각 모듈별 `schema.py` 기본 구조 생성 (Pydantic v2 모델)
- [x] 모듈별 독립적인 스키마 정의 (상호 참조 없음)

### 2.4 데이터베이스 초기화 및 로깅 (추가 작업)
- [ ] `infra/core/logger.py` - 구조화된 로깅 시스템 구현
- [ ] `infra/core/db_initializer.py` - 데이터베이스 초기화 스크립트 실행 기능
- [ ] `main.py` (또는 진입점)에서 초기화 로직 호출

## Phase 3: Account 모듈 구현 (2일)

### 3.1 Account 기본 구조
- [ ] `modules/account/schema.py` - Account 모델 정의
- [ ] `modules/account/sync_service.py` - enrollment 파일 스캔

### 3.2 Account Orchestrator
- [ ] `modules/account/orchestrator.py` - 계정 관리 로직
- [ ] DB CRUD 기능 구현
- [ ] enrollment 동기화 기능

### 3.3 테스트 및 검증
- [ ] enrollment 파일 읽기 테스트
- [ ] DB 저장/조회 테스트

## Phase 4: Auth 모듈 구현 (완료)

### 4.1 OAuth 인증 플로우
- [x] `modules/auth/orchestrator.py` - 인증 오케스트레이터 구현 완료
- [x] `modules/auth/web_server.py` - 로컬 웹서버 (리디렉션 처리) 구현 완료

### 4.2 인증 테스트
- [x] 실제 Azure AD와 연동하여 토큰 발급 및 저장 테스트 완료
- [x] `infra.core.token_service`를 통한 토큰 자동 갱신 기능 검증 완료

## Phase 5: Keyword Extractor 모듈 구현 (1-2일) - 순서 변경

### 5.1 OpenAI 연동 (모듈 내부)
- [ ] `modules/keyword_extractor/openai_service.py` - OpenAI API 클라이언트 (모듈 내부)
- [ ] `modules/keyword_extractor/orchestrator.py` - 키워드 추출 로직 (독립적)

### 5.2 텍스트 처리
- [ ] HTML 태그 제거 로직
- [ ] 키워드 추출 프롬프트 최적화
- [ ] 복잡한 키워드 추출 알고리즘 구현

## Phase 6: Mail Query 모듈 구현 (2-3일)

### 6.1 Graph API 클라이언트 (모듈 내부)
- [ ] `modules/mail_query/graph_client.py` - Graph API 호출 (모듈 내부)
- [ ] `modules/mail_query/filter_builder.py` - OData 필터 생성

### 6.2 Mail Query Orchestrator (독립적)
- [ ] `modules/mail_query/orchestrator.py` - 메일 조회 로직 (완전 독립적)
- [ ] 페이징 처리 (20개씩 배치)
- [ ] 조회 로그 기록

### 6.3 테스트
- [ ] 실제 Graph API 호출 테스트
- [ ] 필터링 테스트 (날짜, 발신자 등)

## Phase 7: Mail Processor 모듈 구현 (3일) - 완전 독립적

### 7.1 완전 독립적 메일 처리 로직
- [ ] `modules/mail_processor/orchestrator.py` - 메일 처리 오케스트레이터 (완전 독립적)
- [ ] `modules/mail_processor/filter_service.py` - 발신자 필터링
- [ ] `modules/mail_processor/_helpers.py` - 헬퍼 함수 (350줄 제한 대응)

### 7.2 자체 Graph API 호출 구현
- [ ] `_fetch_mails_from_graph()` - Graph API 직접 호출 (자체 구현)
- [ ] `_get_active_accounts()` - DB에서 직접 활성 계정 조회
- [ ] `_extract_keywords_simple()` - 간단한 키워드 추출 (자체 구현)

### 7.3 Kafka 이벤트 발행
- [ ] 이벤트 스키마 정의
- [ ] Kafka Producer 구현
- [ ] 이벤트 발행 로직

### 7.4 배치 처리
- [ ] 20개씩 메일 처리 로직
- [ ] 비동기 병렬 처리 구현
- [ ] 계정별 에러 처리

## Phase 8: Mail History 모듈 구현 (1-2일)

### 8.1 히스토리 관리
- [ ] `modules/mail_history/orchestrator.py` - 히스토리 조회/관리
- [ ] `modules/mail_history/cleanup_service.py` - 자동 정리 기능

### 8.2 검색 기능
- [ ] 다양한 필터 조건 구현
- [ ] 페이징 처리

## Phase 9: API Gateway 및 통합 (1일) - 단순화

### 9.1 단순 API Gateway 구현
- [ ] `main/api_gateway.py` - 단순 라우팅만 담당 (비즈니스 로직 없음)
- [ ] `main/request_handler.py` - 요청 처리 및 라우팅
- [ ] `main/response_formatter.py` - 응답 형식 통일

### 9.2 모듈 통합 테스트
- [ ] 각 모듈이 독립적으로 동작하는지 확인
- [ ] API Gateway를 통한 단순 라우팅 테스트
- [ ] 모듈 간 데이터 흐름 검증 (함수 주입 없음)

## Phase 10: 스케줄러 구현 (1일)

### 10.1 스케줄러 서비스
- [ ] `scheduler/main.py` - APScheduler 기반 스케줄링
- [ ] 5분마다 메일 처리 작업
- [ ] 일일 정리 작업

## Phase 11: 통합 테스트 및 최적화 (2-3일)

### 11.1 전체 플로우 테스트
- [ ] 계정 동기화 → 인증 → 메일 조회 → 처리 → 이벤트 발행 전체 플로우
- [ ] 대용량 메일 처리 테스트
- [ ] 에러 상황 처리 테스트

### 11.2 성능 최적화
- [ ] 메모리 사용량 최적화
- [ ] DB 쿼리 최적화
- [ ] 비동기 처리 최적화

### 11.3 모니터링 및 로깅
- [ ] 구조화된 로깅 구현
- [ ] 에러 처리 및 추적
- [ ] 성능 메트릭 수집

## Phase 12: 문서화 및 배포 준비 (1일)

### 12.1 문서 작성
- [ ] 각 모듈별 README.md 작성
- [ ] 설치 및 실행 가이드
- [ ] API 문서

### 12.2 배포 준비
- [ ] Docker 설정 (선택사항)
- [ ] 환경별 설정 분리
- [ ] 프로덕션 체크리스트

## 일일 작업 추천 순서

### Day 1-2: 기반 설정
1. 디렉터리 구조 생성
2. pyproject.toml 및 의존성 설정
3. Core 인프라 (config, database) 구현

### Day 3-4: Account & Auth
1. Account 모듈 구현
2. enrollment 동기화 테스트
3. Auth 모듈 기본 구조

### Day 5-7: 인증 및 토큰 관리
1. OAuth 플로우 완성
2. 토큰 자동 갱신 구현
3. 실제 Azure AD 연동 테스트

### Day 8-9: 키워드 추출 (순서 변경)
1. OpenAI 연동 (모듈 내부)
2. 키워드 추출 로직 (독립적)
3. 텍스트 처리 최적화

### Day 10-12: 메일 조회
1. Graph API 클라이언트 구현 (모듈 내부)
2. Mail Query 모듈 완성 (독립적)
3. 페이징 및 필터링 테스트

### Day 13-15: 메일 처리 및 이벤트 (완전 독립적)
1. Mail Processor 완전 독립적 구현 (자체 Graph API 호출, 간단 키워드 추출)
2. Kafka 이벤트 발행
3. 배치 처리 로직 및 계정별 에러 처리

### Day 16: 히스토리 관리
1. Mail History 모듈 구현
2. 히스토리 검색 및 정리 기능

### Day 17: API Gateway 및 통합 (단순화)
1. 단순 라우팅 API Gateway 구현
2. 모듈 독립성 검증
3. 통합 테스트

### Day 18: 스케줄러 구현
1. APScheduler 기반 스케줄러
2. 주기적 메일 처리 작업
3. 자동 정리 작업

### Day 19: 통합 테스트 및 최적화
1. 전체 플로우 테스트
2. 성능 최적화
3. 에러 처리 검증

### Day 20: 문서화 및 마무리
1. 문서 작성
2. 최종 테스트
3. 배포 준비

## 중요 체크포인트

### 매일 확인사항
- [ ] 파일당 350줄 제한 준수
- [ ] 모듈 간 순환 참조 없음
- [ ] 비동기 함수 await 처리
- [ ] 에러 처리 및 로깅 추가

### 주간 확인사항
- [ ] 전체 아키텍처 일관성 확인
- [ ] 성능 및 메모리 사용량 체크
- [ ] 보안 요소 (토큰, API 키) 확인
- [ ] Git 커밋 및 문서 업데이트

### 완료 기준
각 Phase는 다음 조건을 만족해야 완료:
1. 해당 모듈의 기본 기능 동작
2. 단위 테스트 통과 (또는 수동 검증 완료)
3. 다음 Phase에 필요한 인터페이스 제공
4. 문서 및 README 업데이트
