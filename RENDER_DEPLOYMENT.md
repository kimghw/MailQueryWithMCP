# Render.com 배포 가이드

## 개요

이 문서는 MailQueryWithMCP 프로젝트를 Render.com에 배포하는 방법을 설명합니다.

## 사전 준비

1. **Render.com 계정**: https://render.com 에서 무료 계정 생성
2. **GitHub 연동**: Render.com과 GitHub 저장소 연결
3. **환경 변수 준비**: 아래 환경 변수 값 준비

## 필수 환경 변수

Render.com 대시보드에서 다음 환경 변수를 설정해야 합니다:

```bash
# 필수 환경 변수
PYTHON_VERSION=3.11.9              # Python 버전 (자동 설정됨)
UV_VERSION=0.7.12                  # uv 버전 (자동 설정됨)
ENCRYPTION_KEY=<32바이트 암호화 키>  # 자동 생성됨
OAUTH_CLIENT_ID=<Azure AD 클라이언트 ID>
OAUTH_CLIENT_SECRET=<Azure AD 클라이언트 시크릿>
OAUTH_TENANT_ID=<Azure AD 테넌트 ID>
OAUTH_REDIRECT_URI=https://your-app.onrender.com/auth/callback

# 선택 환경 변수 (권장)
OPENAI_API_KEY=<OpenAI API 키>  # AI 기능 사용 시
OPENROUTER_API_KEY=<OpenRouter API 키>  # AI 기능 사용 시
```

## 배포 방법

### 방법 1: render.yaml 자동 배포 (권장)

1. **GitHub에 코드 푸시**
   ```bash
   git add .
   git commit -m "Add Render.com deployment config"
   git push origin main
   ```

2. **Render.com에서 배포**
   - Render.com 대시보드 접속
   - "New +" → "Blueprint" 선택
   - GitHub 저장소 선택
   - `render.yaml` 자동 인식
   - "Apply" 클릭

3. **환경 변수 설정**
   - Dashboard → 생성된 서비스 선택
   - "Environment" 탭 선택
   - 위의 필수 환경 변수 입력
   - "Save Changes" 클릭

### 방법 2: 수동 배포

1. **Render.com 대시보드에서 New Web Service 생성**

2. **저장소 선택**
   - GitHub 저장소 연결
   - `kimghw/MailQueryWithMCP` 선택

3. **서비스 설정**
   ```
   Name: mailquery-mcp-server
   Runtime: Python 3
   Branch: main
   Build Command: uv sync
   Start Command: bash entrypoints/production/run_unified_http.sh --host 0.0.0.0 --port $PORT
   ```

   **✅ uv를 사용하는 이유**:
   - 프로젝트에 `uv.lock` 파일이 있으면 Render.com이 자동으로 `uv`를 인식
   - `uv sync`는 `uv.lock` 파일 기반으로 정확한 의존성 설치
   - 빠른 설치 속도 및 일관된 환경 보장

4. **환경 변수 설정**
   - "Advanced" → "Add Environment Variable" 클릭
   - 위의 필수 환경 변수 모두 입력
   - **중요**: `UV_VERSION=0.7.12` 반드시 설정

5. **배포**
   - "Create Web Service" 클릭
   - 자동으로 빌드 및 배포 시작

## 배포 후 확인

### 1. 헬스 체크

```bash
curl https://your-app.onrender.com/health
```

예상 응답:
```json
{
  "status": "healthy",
  "modules": {
    "mail_query": "ok",
    "enrollment": "ok",
    "onenote": "ok"
  }
}
```

### 2. 서버 정보 확인

```bash
curl https://your-app.onrender.com/info
```

### 3. MCP 엔드포인트 테스트

**Enrollment MCP (계정 관리)**
```bash
curl -X POST https://your-app.onrender.com/enrollment/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "id":1,
    "method":"tools/list",
    "params":{}
  }'
```

**Mail Query MCP (이메일 조회)**
```bash
curl -X POST https://your-app.onrender.com/mail-query/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "id":1,
    "method":"tools/list",
    "params":{}
  }'
```

**OneNote MCP (OneNote 관리)**
```bash
curl -X POST https://your-app.onrender.com/onenote/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "id":1,
    "method":"tools/list",
    "params":{}
  }'
```

## 파일 구조

```
entrypoints/production/
├── start_server.sh           # Render.com 시작 스크립트
├── unified_http_server.py    # 통합 HTTP 서버
└── run_unified_http.sh       # 로컬 실행 스크립트

render.yaml                    # Render.com 배포 설정
RENDER_DEPLOYMENT.md          # 이 문서
```

## 주요 특징

### 1. Unified HTTP Server
- 단일 서버에서 3개의 MCP 서버 제공:
  - `/mail-query/*` - 이메일 조회
  - `/enrollment/*` - 계정 관리
  - `/onenote/*` - OneNote 관리

### 2. uv 패키지 관리자 사용
- **uv.lock 기반 의존성 관리**: 프로젝트에 `uv.lock` 파일이 있으면 Render.com이 자동으로 `uv` 인식
- **빠른 설치 속도**: `uv sync`는 전통적인 pip보다 훨씬 빠름
- **일관된 환경**: lockfile 기반으로 동일한 버전 보장
- **필수 설정**: `UV_VERSION=0.7.12` 환경 변수 설정 필요

### 3. 자동 복구 기능
- 헬스 체크 엔드포인트 제공
- Render.com 자동 재시작 지원

## uv 사용 가이드

### uv.lock 파일의 중요성

Render.com은 프로젝트 루트에 `uv.lock` 파일이 있으면 자동으로 `uv`를 Python 런타임에 추가합니다.

**필수 파일 구조**:
```
프로젝트_루트/
├── pyproject.toml
├── uv.lock           # 필수! 이 파일이 있어야 uv 자동 인식
├── .python-version   # 선택 (PYTHON_VERSION 환경변수로 대체 가능)
└── render.yaml
```

### 빌드 로그 확인 방법

1. Render.com Dashboard → 서비스 선택
2. **"Events"** 탭 클릭
3. 타임라인에서 최근 배포의 **"Deploy"** 텍스트 클릭
4. 빌드 로그 전체 확인

**정상 빌드 로그 예시**:
```
==> Using uv version 0.7.12 (default)
==> Installing uv version 0.7.12...
==> Running build command 'uv sync && echo "Build completed"'
Using Python 3.11.9 environment at: /opt/render/project/src/.venv
Resolved 80 packages in 0.5s
Installed 80 packages in 1.2s
 + uvicorn==0.38.0
 + fastapi==0.119.0
 ...
Build completed
==> Build successful 🎉
```

### 의존성 업데이트 방법

```bash
# 로컬에서 pyproject.toml 수정 후
uv lock                    # uv.lock 업데이트
git add pyproject.toml uv.lock
git commit -m "Update dependencies"
git push                   # Render.com 자동 재배포
```

## 트러블슈팅

### 1. 빌드 실패

**문제**: `uv: command not found`

**원인**: `UV_VERSION` 환경 변수가 설정되지 않았거나 `uv.lock` 파일이 없음

**해결방법**:
```bash
# 1. 환경 변수 설정 확인
UV_VERSION=0.7.12  # Render.com 대시보드에서 설정

# 2. uv.lock 파일 존재 확인
ls -la uv.lock  # 프로젝트 루트에 있어야 함

# 3. uv.lock 파일 생성 (없는 경우)
uv lock
```

**문제**: Python 버전 불일치
```bash
# 해결방법: render.yaml에서 PYTHON_VERSION 확인
# Python 3.11 권장
PYTHON_VERSION=3.11.9
```

**문제**: `ModuleNotFoundError: No module named 'uvicorn'` (해결됨!)

**원인과 해결 과정**:

1. **초기 문제**: `uv pip install --system` 사용 시
   - Render.com이 자동으로 `.venv` 가상환경 생성
   - `--system` 플래그로 시스템에 설치
   - 런타임에 `.venv`를 사용하여 패키지를 찾지 못함

2. **1차 시도**: `uv pip install -e .` (--system 제거)
   - 여전히 문제 발생 (버전 충돌 가능성)

3. **최종 해결**: `uv sync` 사용 ✅
   - `uv.lock` 파일 기반으로 정확한 의존성 설치
   - Render.com이 자동으로 `.venv`에 설치
   - `UV_VERSION` 환경 변수 필수

**올바른 설정**:
```yaml
# render.yaml
buildCommand: uv sync && echo "Build completed"  # ✅ 올바름

# 환경 변수
UV_VERSION=0.7.12
PYTHON_VERSION=3.11.9
```

**디버깅 방법**:
```bash
# Events 탭에서 "Deploy" 클릭하여 빌드 로그 확인
# 다음 내용이 보여야 함:
==> Using uv version 0.7.12 (default)
==> Running build command 'uv sync && echo "Build completed"'
Resolved XX packages in X.XXs
Installed XX packages in X.XXs
```

### 2. 실행 실패

**문제**: 환경 변수 누락
```bash
# 해결방법: Render.com 대시보드에서 모든 필수 환경 변수 확인
# ENCRYPTION_KEY는 자동 생성되므로 서버 로그 확인
```

**문제**: 포트 바인딩 실패
```bash
# 해결방법: Render.com이 자동으로 PORT 환경 변수 설정
# start_server.sh가 자동으로 사용
```

### 3. 데이터베이스 초기화 실패

**문제**: SQLite DB 생성 불가
```bash
# 해결방법: Render.com의 ephemeral filesystem 사용
# 재시작 시 데이터 초기화됨 (Free tier 특성)
# 영구 저장이 필요한 경우 Render PostgreSQL 사용 권장
```

## 로그 확인

### Render.com 대시보드에서 로그 확인

1. Dashboard → 서비스 선택
2. "Logs" 탭 클릭
3. 실시간 로그 스트림 확인

### 주요 로그 메시지

```
🚀 Starting Unified MCP Server on Render.com
📍 Server will bind to 0.0.0.0:10000
📦 Installing dependencies with uv...
✅ Environment check:
🔥 Starting Unified MCP HTTP Server...
🚀 Starting Unified MCP Server on http://0.0.0.0:10000
📧 Mail Query MCP: http://0.0.0.0:10000/mail-query/
🔐 Enrollment MCP: http://0.0.0.0:10000/enrollment/
📝 OneNote MCP: http://0.0.0.0:10000/onenote/
```

## 성능 및 제한사항

### Render.com Free Tier 제한

- **메모리**: 512MB RAM
- **CPU**: Shared CPU
- **디스크**: Ephemeral (재시작 시 초기화)
- **슬립 모드**: 15분 비활성 시 자동 슬립
- **부팅 시간**: 슬립 해제 시 30-60초 소요

### 권장사항

- **Paid Plan 업그레이드**: 프로덕션 환경에서는 Starter Plan 이상 권장
- **데이터베이스**: 영구 저장이 필요한 경우 Render PostgreSQL 사용
- **백업**: 중요한 데이터는 외부 백업 권장

## 업데이트 배포

### 자동 배포 (권장)

```bash
git add .
git commit -m "Update: feature description"
git push origin main
```

Render.com이 자동으로 새 버전 배포

### 수동 재배포

1. Render.com Dashboard 접속
2. 서비스 선택
3. "Manual Deploy" → "Deploy latest commit" 클릭

## 보안 권장사항

1. **환경 변수 보호**: 절대 코드에 하드코딩하지 말 것
2. **HTTPS 사용**: Render.com 자동 SSL 인증서 제공
3. **API 키 로테이션**: 정기적으로 API 키 갱신
4. **접근 제어**: 필요 시 IP 화이트리스트 설정

## 지원 및 문의

- **Render.com 문서**: https://render.com/docs
- **GitHub Issues**: https://github.com/kimghw/MailQueryWithMCP/issues
- **프로젝트 문서**: README.md, MCP_DEVELOPMENT_GUIDE.md

---

**작성일**: 2025-10-19
**버전**: 1.0.0
