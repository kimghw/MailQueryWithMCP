# IACSGRAPH 프로젝트 작업 순서 계획

## 현재 상태
- [x] 프로젝트 문서 작성 (usecase.md, implementation_plan.md)
- [x] 환경설정 파일 (.env, .env.example)
- [x] Git 저장소 설정 및 초기 커밋
- [x] .gitignore 설정 (enrollment/ 제외)
- [x] 디렉터리 구조 생성 완료
- [x] `pyproject.toml` 및 uv 가상환경 설정 완료
- [x] `infra/core` 및 `modules/account` 핵심 기능 구현 완료

## Phase 1: 프로젝트 기반 구조 설정 (완료)

### 1.1 디렉터리 구조 생성
- [x] 모든 프로젝트 디렉터리 구조 생성 완료

### 1.2 패키지 관리 설정 (uv)
- [x] `pyproject.toml` 생성 및 의존성 정의 완료
- [x] uv를 이용한 가상환경 설정 완료

### 1.3 기본 __init__.py 파일 생성
- [x] 모든 모듈 디렉터리에 `__init__.py` 생성 완료

### 1.4 SQLite 스키마 생성
- [x] `infra/migrations/initial_schema.sql` 구현 완료
- [x] `database.py`에서 자동 스키마 생성 기능 구현 완료

## Phase 2: 인프라 레이어 구현 (완료)

### 2.1 Core 인프라 구현
- [x] `infra/core/config.py` - 환경설정 로드 기능 구현 완료
- [x] `infra/core/database.py` - SQLite 연결 및 트랜잭션 관리 구현 완료
- [x] `infra/core/logger.py` - 구조화된 로깅 시스템 구현 완료
- [x] `infra/core/exceptions.py` - 표준 예외 클래스 정의 완료
- [ ] `infra/core/kafka_client.py` - (향후 사용 예정)

### 2.2 OAuth 및 토큰 관리
- [ ] `infra/core/oauth_client.py` - (향후 `auth` 모듈에서 사용 예정)
- [ ] `infra/core/token_service.py` - (향후 `auth` 모듈에서 사용 예정)

## Phase 3: Account 모듈 구현 (완료)

### 3.1 Account 모듈 구현
- [x] `modules/account/account_schema.py` - Account 관련 Pydantic 모델 전체 정의 완료
- [x] `modules/account/account_repository.py` - DB CRUD 기능 구현 완료
- [x] `modules/account/_account_helpers.py` - 암호화 및 파일 처리 유틸리티 구현 완료
- [x] `modules/account/account_sync_service.py` - `enrollment` 파일 동기화 서비스 구현 완료
- [x] `modules/account/account_orchestrator.py` - 계정 관리 비즈니스 로직 구현 완료

### 3.2 기능 검증
- [x] `enrollment` 파일 기반 계정 생성/업데이트/비활성화 기능 수동 검증 완료
- [x] DB 저장/조회 및 민감 정보 암호화 검증 완료
- [x] 단위 테스트는 규칙에 따라 제거됨

## Phase 4: Auth 모듈 구현 (3일)

### 4.1 OAuth 인증 플로우
- [ ] `modules/auth/orchestrator.py` - 인증 오케스트레이터
- [ ] `modules/auth/web_server.py` - 로컬 웹서버 (리디렉션 처리)

### 4.2 인증 테스트
- [ ] 실제 Azure AD와 연동 테스트
- [ ] 토큰 발급 및 저장 테스트
- [ ] 토큰 자동 갱신 테스트

## Phase 4: Auth 모듈 구현 (3일)

### 4.1 OAuth 인증 플로우
- [ ] `modules/auth/orchestrator.py` - 인증 오케스트레이터
- [ ] `modules/auth/web_server.py` - 로컬 웹서버 (리디렉션 처리)

### 4.2 인증 테스트
- [ ] 실제 Azure AD와 연동 테스트
- [ ] 토큰 발급 및 저장 테스트
- [ ] 토큰 자동 갱신 테스트

## Phase 5: Mail Query 모듈 구현 (2-3일)

### 5.1 Graph API 클라이언트
- [ ] `modules/mail_query/graph_client.py` - Graph API 호출
- [ ] `modules/mail_query/filter_builder.py` - OData 필터 생성

### 5.2 Mail Query Orchestrator
- [ ] `modules/mail_query/orchestrator.py` - 메일 조회 로직
- [ ] 페이징 처리 (20개씩 배치)
- [ ] 조회 로그 기록

### 5.3 테스트
- [ ] 실제 Graph API 호출 테스트
- [ ] 필터링 테스트 (날짜, 발신자 등)

## Phase 6: Keyword Extractor 모듈 구현 (1-2일)

### 6.1 OpenAI 연동
- [ ] `modules/keyword_extractor/openai_service.py` - OpenAI API 클라이언트
- [ ] `modules/keyword_extractor/orchestrator.py` - 키워드 추출 로직

### 6.2 텍스트 처리
- [ ] HTML 태그 제거 로직
- [ ] 키워드 추출 프롬프트 최적화

## Phase 7: Mail Processor 모듈 구현 (3일)

### 7.1 메일 처리 로직
- [ ] `modules/mail_processor/orchestrator.py` - 메일 처리 오케스트레이터
- [ ] `modules/mail_processor/filter_service.py` - 발신자 필터링

### 7.2 Kafka 이벤트 발행
- [ ] 이벤트 스키마 정의
- [ ] Kafka Producer 구현
- [ ] 이벤트 발행 로직

### 7.3 배치 처리
- [ ] 20개씩 메일 처리 로직
- [ ] 비동기 병렬 처리 구현

## Phase 8: Mail History 모듈 구현 (1-2일)

### 8.1 히스토리 관리
- [ ] `modules/mail_history/orchestrator.py` - 히스토리 조회/관리
- [ ] `modules/mail_history/cleanup_service.py` - 자동 정리 기능

### 8.2 검색 기능
- [ ] 다양한 필터 조건 구현
- [ ] 페이징 처리

## Phase 9: API Gateway 및 통합 (2일)

### 9.1 API Gateway 구현
- [ ] `main/api_gateway.py` - 모듈 간 호출 총괄
- [ ] `main/request_handler.py` - 요청 처리 및 라우팅
- [ ] `main/response_formatter.py` - 응답 형식 통일

### 9.2 함수 주입 방식 구현
- [ ] MailProcessor에서 다른 모듈 기능 사용하는 함수 주입 로직

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

### Day 8-10: 메일 조회
1. Graph API 클라이언트 구현
2. Mail Query 모듈 완성
3. 페이징 및 필터링 테스트

### Day 11-12: 키워드 추출
1. OpenAI 연동
2. 키워드 추출 로직
3. 텍스트 처리 최적화

### Day 13-15: 메일 처리 및 이벤트
1. Mail Processor 구현
2. Kafka 이벤트 발행
3. 배치 처리 로직

### Day 16-17: 히스토리 및 통합
1. Mail History 모듈
2. API Gateway 구현
3. 모듈 간 통합

### Day 18-19: 스케줄러 및 테스트
1. 스케줄러 구현
2. 전체 플로우 테스트
3. 성능 최적화

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
