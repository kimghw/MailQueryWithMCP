# Render 배포 가이드

## 📋 준비사항

### 1. Azure AD 앱 등록
- [Azure Portal](https://portal.azure.com) → App registrations
- 새 앱 등록 또는 기존 앱 사용
- 다음 정보 확인:
  - `Tenant ID` (Directory ID)
  - `Client ID` (Application ID)
  - `Client Secret` (새로 생성 필요)

### 2. Azure AD Redirect URI 설정
**Authentication** → **Platform configurations** → **Add a platform** → **Web**

다음 **두 개** 모두 등록:
```
http://localhost:5000/auth/callback
https://your-app-name.onrender.com/auth/callback
```

> ⚠️ `your-app-name`은 Render 배포 후 제공되는 실제 URL로 변경

---

## 🚀 Render 배포 단계

### 1단계: Render 서비스 생성

1. [Render Dashboard](https://dashboard.render.com) 접속
2. **New +** → **Web Service** 클릭
3. GitHub 저장소 연결: `kimghw/MailQueryWithMCP`
4. 설정 자동 감지됨 (`render.yaml` 사용)

### 2단계: 환경변수 설정

**Environment** 탭에서 다음 변수들을 추가:

#### 필수 환경변수

```bash
# 보안
ENCRYPTION_KEY=랜덤문자열32자이상생성해주세요

# 계정 1 - 사용자 정보
ACCOUNT_1_USER_ID=kimghw
ACCOUNT_1_USER_NAME=김길현
ACCOUNT_1_EMAIL=kimghw@company.com

# 계정 1 - Azure AD 정보
ACCOUNT_1_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
ACCOUNT_1_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
ACCOUNT_1_CLIENT_SECRET=your-azure-client-secret

# 계정 1 - OAuth Redirect URI
ACCOUNT_1_REDIRECT_URI=https://your-app-name.onrender.com/auth/callback
```

#### 선택 환경변수 (필요시)

```bash
# AI 키워드 추출 (선택)
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...

# Kafka 이벤트 스트리밍 (선택)
KAFKA_BOOTSTRAP_SERVERS=your-kafka-server:9092
```

### 3단계: 배포

1. **Create Web Service** 클릭
2. 자동 빌드 및 배포 시작
3. 배포 완료 후 URL 확인: `https://your-app-name.onrender.com`

### 4단계: Azure AD Redirect URI 업데이트

배포된 URL로 Azure AD 설정 업데이트:
```
https://your-app-name.onrender.com/auth/callback
```

---

## 🔍 배포 확인

### Health Check
```bash
curl https://your-app-name.onrender.com/health
```

**응답:**
```json
{
  "status": "healthy",
  "server": "mail-attachment-server",
  "version": "2.0.0",
  "transport": "http-streaming"
}
```

### Server Info
```bash
curl https://your-app-name.onrender.com/info
```

---

## 🔗 Claude Desktop 연결

### 설정 파일 위치

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### 설정 내용

```json
{
  "mcpServers": {
    "mail-query": {
      "url": "https://your-app-name.onrender.com",
      "transport": {
        "type": "http"
      }
    }
  }
}
```

### Claude Desktop 재시작

설정 저장 후 Claude Desktop을 재시작하면 MCP 서버가 연결됩니다.

---

## 📊 계정 추가 (다중 계정)

여러 이메일 계정을 추가하려면 `ACCOUNT_2_*`, `ACCOUNT_3_*` 형식으로 환경변수를 추가:

```bash
ACCOUNT_2_USER_ID=user2
ACCOUNT_2_USER_NAME=사용자2
ACCOUNT_2_EMAIL=user2@company.com
ACCOUNT_2_TENANT_ID=...
ACCOUNT_2_CLIENT_ID=...
ACCOUNT_2_CLIENT_SECRET=...
ACCOUNT_2_REDIRECT_URI=https://your-app-name.onrender.com/auth/callback
```

---

## ⚠️ 주의사항

### 무료 플랜 제한
- **Sleep 모드**: 15분 동안 요청이 없으면 서버가 sleep 상태로 전환
- **Cold Start**: 첫 요청 시 30초 정도 소요
- **데이터 지속성**: SQLite 데이터베이스가 재시작 시 삭제됨

### 프로덕션 사용
프로덕션 환경에서는:
- **유료 플랜** 사용 권장
- **Persistent Disk** 추가 (데이터베이스 보존)
- **Custom Domain** 설정 (선택)

---

## 🆘 문제 해결

### 서버가 시작되지 않음
- **Logs** 탭에서 에러 확인
- 환경변수 설정 확인 (특히 `ENCRYPTION_KEY`)

### 계정 0개 경고
```
⚠️ No accounts found in environment variables
```
→ `ACCOUNT_1_*` 환경변수가 누락됨. 모든 필수 항목 확인

### OAuth 인증 실패
- Azure AD Redirect URI가 정확한지 확인
- `ACCOUNT_1_REDIRECT_URI`가 배포된 URL과 일치하는지 확인
- Azure AD에 두 URL 모두 등록되어 있는지 확인

---

## 📚 추가 문서

- [MCP 프로토콜 문서](https://modelcontextprotocol.io)
- [Render 문서](https://render.com/docs)
- [Microsoft Graph API](https://learn.microsoft.com/graph)
