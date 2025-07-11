# OpenAI Embeddings Setup Guide

## 🚀 최신 임베딩 모델 정보 (2024)

### 사용 가능한 모델:

1. **text-embedding-3-small** (기본)
   - 차원: 1536
   - 가격: $0.00002/1K 토큰 (ada-002 대비 5배 저렴)
   - 특징: 빠르고 효율적

2. **text-embedding-3-large** (최고 성능)
   - 차원: 3072 (256, 512, 1024, 1536으로 축소 가능)
   - 가격: $0.00013/1K 토큰
   - 특징: 최고 성능, 다국어 지원 강화

## 설정 방법

### 1. OpenAI API 키 발급

1. [OpenAI Platform](https://platform.openai.com/api-keys) 접속
2. 계정 로그인 또는 회원가입
3. API Keys 섹션에서 "Create new secret key" 클릭
4. 키 복사 (한 번만 표시되므로 안전하게 보관)

### 2. 환경변수 설정

`.env` 파일에 OpenAI API 키 추가:

```bash
# .env 파일 편집
OPENAI_API_KEY=sk-proj-your-actual-api-key-here
```

### 3. 시스템 구성

현재 OpenAI 임베딩을 사용하도록 다음과 같이 변경되었습니다:

- **임베딩 모델**: `text-embedding-ada-002` (OpenAI)
- **벡터 차원**: 1536 (기존 384에서 변경)
- **컬렉션 이름**: `iacsgraph_queries_openai` (새로운 컬렉션)

### 4. 실행 방법

```bash
# 1. 마이그레이션 상태 확인
python scripts/migrate_to_openai.py

# 2. Query Assistant 실행
python -m modules.query_assistant.web_api

# 3. OpenAI 임베딩 테스트
python scripts/test_openai_embeddings.py
```

### 5. 주의사항

- OpenAI API는 사용량에 따라 과금됩니다
- `text-embedding-ada-002` 모델은 1,000 토큰당 $0.0001 비용
- 환경변수는 `.env` 파일에서 자동으로 로드됩니다
- API 키는 절대 코드에 직접 하드코딩하지 마세요

### 6. 문제 해결

**API 키가 인식되지 않는 경우:**
```bash
# .env 파일이 프로젝트 루트에 있는지 확인
ls -la .env

# 환경변수 확인
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('OPENAI_API_KEY'))"
```

**Qdrant 연결 오류:**
```bash
# Qdrant가 실행 중인지 확인
docker ps | grep qdrant
```