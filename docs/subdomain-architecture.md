# Unified 서버 → 서브도메인 방식 분리 아키텍처

## 📋 현재 구조 (Path-based Routing)

```
https://api.example.com/
├── /oauth/authorize
├── /oauth/token
├── /mail-query/messages
├── /onenote/messages
├── /onedrive/messages
└── /teams/messages
```

**문제점:**
- 모든 서비스가 하나의 도메인에 집중
- 서비스별 독립적인 배포/스케일링 어려움
- URL 길이가 길어짐
- 서비스별 로드밸런싱 불가

---

## 🎯 목표 구조 (Subdomain-based Routing)

```
https://oauth.example.com/
├── /authorize
├── /token
└── /register

https://mail.example.com/
├── /messages
├── /.well-known/mcp.json
└── /health

https://onenote.example.com/
├── /messages
└── /.well-known/mcp.json

https://onedrive.example.com/
├── /messages
└── /.well-known/mcp.json

https://teams.example.com/
├── /messages
└── /.well-known/mcp.json
```

**장점:**
- 서비스별 독립적인 URL 네임스페이스
- 서비스별 독립 배포 및 스케일링 가능
- 깔끔한 URL 구조
- 서비스별 로드밸런싱 및 트래픽 관리 용이
- SSL 인증서 서브도메인별 관리 가능

---

## 🏗️ 구현 방안

### 방안 1: 리버스 프록시 (Nginx/Caddy) - **추천**

#### 아키텍처

```
Internet
   ↓
┌──────────────────────────────────────────┐
│         리버스 프록시 (Nginx/Caddy)       │
│                                          │
│  oauth.example.com    → :8001           │
│  mail.example.com     → :8002           │
│  onenote.example.com  → :8003           │
│  onedrive.example.com → :8004           │
│  teams.example.com    → :8005           │
└──────────────────────────────────────────┘
              ↓
┌─────────────┬─────────────┬─────────────┐
│   OAuth     │ Mail Query  │  OneNote    │
│   Server    │   Server    │   Server    │
│   :8001     │   :8002     │   :8003     │
└─────────────┴─────────────┴─────────────┘
```

#### Nginx 설정 예시

```nginx
# /etc/nginx/sites-available/mcp-services

# OAuth Server
server {
    listen 80;
    server_name oauth.example.com;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Mail Query Server
server {
    listen 80;
    server_name mail.example.com;

    location / {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# OneNote Server
server {
    listen 80;
    server_name onenote.example.com;

    location / {
        proxy_pass http://127.0.0.1:8003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# OneDrive Server
server {
    listen 80;
    server_name onedrive.example.com;

    location / {
        proxy_pass http://127.0.0.1:8004;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Teams Server
server {
    listen 80;
    server_name teams.example.com;

    location / {
        proxy_pass http://127.0.0.1:8005;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Caddy 설정 예시 (더 간단)

```caddy
# Caddyfile

oauth.example.com {
    reverse_proxy localhost:8001
}

mail.example.com {
    reverse_proxy localhost:8002
}

onenote.example.com {
    reverse_proxy localhost:8003
}

onedrive.example.com {
    reverse_proxy localhost:8004
}

teams.example.com {
    reverse_proxy localhost:8005
}
```

**장점:**
- 기존 코드 최소 수정
- 리버스 프록시가 SSL/TLS 자동 처리
- 로드밸런싱, 캐싱, 압축 등 추가 기능 활용 가능
- 서비스별 독립 배포 가능

---

### 방안 2: Starlette Host-based Routing (코드 수정)

#### 구현 코드

```python
# entrypoints/production/subdomain_http_server.py

from starlette.applications import Starlette
from starlette.routing import Host, Mount, Route
from starlette.responses import JSONResponse

class SubdomainMCPServer:
    def __init__(self):
        # 각 서비스 서버 초기화
        self.oauth_server = self._create_oauth_server()
        self.mail_server = HTTPStreamingMailAttachmentServer()
        self.onenote_server = HTTPStreamingOneNoteServer()
        self.onedrive_server = HTTPStreamingOneDriveServer()
        self.teams_server = HTTPStreamingTeamsServer()

        # Starlette Host-based routing
        self.app = self._create_subdomain_app()

    def _create_subdomain_app(self):
        routes = [
            # OAuth 서브도메인
            Host("oauth.{domain:.*}", app=self.oauth_server),

            # Mail Query 서브도메인
            Host("mail.{domain:.*}", app=self.mail_server.app),

            # OneNote 서브도메인
            Host("onenote.{domain:.*}", app=self.onenote_server.app),

            # OneDrive 서브도메인
            Host("onedrive.{domain:.*}", app=self.onedrive_server.app),

            # Teams 서브도메인
            Host("teams.{domain:.*}", app=self.teams_server.app),

            # 기본 도메인 (health check 등)
            Route("/health", endpoint=self._health_check),
        ]

        return Starlette(routes=routes)

    def _create_oauth_server(self):
        """OAuth 전용 서버 생성"""
        routes = [
            Route("/authorize", endpoint=oauth_authorize_handler, methods=["GET"]),
            Route("/token", endpoint=oauth_token_handler, methods=["POST"]),
            Route("/register", endpoint=dcr_register_handler, methods=["POST"]),
            Route("/azure_callback", endpoint=oauth_azure_callback_handler, methods=["GET"]),
            Route("/.well-known/oauth-authorization-server", endpoint=oauth_metadata_handler),
        ]
        return Starlette(routes=routes)

    async def _health_check(self, request):
        return JSONResponse({"status": "healthy"})
```

**장점:**
- 리버스 프록시 불필요
- Python 코드로 모든 라우팅 제어
- 개발 환경에서도 서브도메인 테스트 가능 (hosts 파일 설정)

**단점:**
- 코드 수정 필요
- SSL/TLS 처리를 직접 구현해야 함
- 로드밸런싱 등 추가 기능 구현 필요

---

### 방안 3: Cloudflare Tunnel + Workers (클라우드 기반)

#### 아키텍처

```
Internet
   ↓
┌────────────────────────────┐
│   Cloudflare Workers       │
│   - oauth.example.com      │
│   - mail.example.com       │
│   - onenote.example.com    │
└────────────┬───────────────┘
             │ Cloudflare Tunnel
             ↓
┌────────────────────────────┐
│   로컬 서버                 │
│   - :8001 (OAuth)          │
│   - :8002 (Mail)           │
│   - :8003 (OneNote)        │
└────────────────────────────┘
```

#### Cloudflare Workers 설정

```javascript
// cloudflare-worker.js

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url)
  const subdomain = url.hostname.split('.')[0]

  // 서브도메인별 백엔드 매핑
  const backends = {
    'oauth': 'https://tunnel-oauth.your-tunnel.com',
    'mail': 'https://tunnel-mail.your-tunnel.com',
    'onenote': 'https://tunnel-onenote.your-tunnel.com',
    'onedrive': 'https://tunnel-onedrive.your-tunnel.com',
    'teams': 'https://tunnel-teams.your-tunnel.com',
  }

  const backend = backends[subdomain]
  if (!backend) {
    return new Response('Unknown service', { status: 404 })
  }

  // 백엔드로 프록시
  const backendUrl = new URL(url.pathname + url.search, backend)
  return fetch(backendUrl, {
    method: request.method,
    headers: request.headers,
    body: request.body,
  })
}
```

#### Cloudflare Tunnel 설정

```yaml
# config.yml

tunnel: your-tunnel-id
credentials-file: /path/to/credentials.json

ingress:
  - hostname: oauth.example.com
    service: http://localhost:8001

  - hostname: mail.example.com
    service: http://localhost:8002

  - hostname: onenote.example.com
    service: http://localhost:8003

  - hostname: onedrive.example.com
    service: http://localhost:8004

  - hostname: teams.example.com
    service: http://localhost:8005

  - service: http_status:404
```

**장점:**
- 무료 SSL/TLS
- DDoS 보호
- 글로벌 CDN
- 로컬 서버를 외부에 노출하지 않음

**단점:**
- Cloudflare 의존성
- 네트워크 레이턴시 증가 가능

---

## 🔧 마이그레이션 계획

### 1단계: 개별 서버 분리

#### 1.1 OAuth 서버 분리

```python
# entrypoints/production/oauth_server.py

from starlette.applications import Starlette
from starlette.routing import Route
from modules.dcr_oauth import DCRService

class OAuthServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8001):
        self.host = host
        self.port = port
        self.dcr_service = DCRService()
        self.app = self._create_app()

    def _create_app(self):
        routes = [
            Route("/authorize", endpoint=self._authorize, methods=["GET"]),
            Route("/token", endpoint=self._token, methods=["POST"]),
            Route("/register", endpoint=self._register, methods=["POST"]),
            Route("/azure_callback", endpoint=self._azure_callback, methods=["GET"]),
            Route("/.well-known/oauth-authorization-server", endpoint=self._metadata),
            Route("/health", endpoint=self._health),
        ]
        return Starlette(routes=routes)

    # ... 핸들러 메서드들 ...

    def run(self):
        import uvicorn
        uvicorn.run(self.app, host=self.host, port=self.port)

if __name__ == "__main__":
    server = OAuthServer()
    server.run()
```

#### 1.2 Mail Query 서버 분리

```python
# entrypoints/production/mail_server.py

from modules.mail_query_MCP.mcp_server.http_server import HTTPStreamingMailAttachmentServer

class MailQueryServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8002):
        self.server = HTTPStreamingMailAttachmentServer(host=host, port=port)

    def run(self):
        self.server.run()

if __name__ == "__main__":
    server = MailQueryServer()
    server.run()
```

#### 1.3 기타 서버들도 동일하게 분리

### 2단계: 리버스 프록시 설정

#### Nginx 설치 및 설정

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx

# 설정 파일 작성
sudo nano /etc/nginx/sites-available/mcp-services

# 심볼릭 링크 생성
sudo ln -s /etc/nginx/sites-available/mcp-services /etc/nginx/sites-enabled/

# 설정 테스트
sudo nginx -t

# Nginx 재시작
sudo systemctl restart nginx
```

#### SSL/TLS 설정 (Let's Encrypt)

```bash
# Certbot 설치
sudo apt install certbot python3-certbot-nginx

# 인증서 발급 (각 서브도메인별)
sudo certbot --nginx -d oauth.example.com
sudo certbot --nginx -d mail.example.com
sudo certbot --nginx -d onenote.example.com
sudo certbot --nginx -d onedrive.example.com
sudo certbot --nginx -d teams.example.com
```

### 3단계: DNS 설정

#### Cloudflare DNS 설정 예시

```
A     oauth      123.45.67.89
A     mail       123.45.67.89
A     onenote    123.45.67.89
A     onedrive   123.45.67.89
A     teams      123.45.67.89
```

또는 와일드카드:

```
A     *          123.45.67.89
```

### 4단계: 프로세스 관리

#### systemd 서비스 파일

```ini
# /etc/systemd/system/mcp-oauth.service

[Unit]
Description=MCP OAuth Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/MailQueryWithMCP
ExecStart=/path/to/venv/bin/python entrypoints/production/oauth_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/mcp-mail.service

[Unit]
Description=MCP Mail Query Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/MailQueryWithMCP
ExecStart=/path/to/venv/bin/python entrypoints/production/mail_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 서비스 관리

```bash
# 서비스 활성화
sudo systemctl enable mcp-oauth
sudo systemctl enable mcp-mail
sudo systemctl enable mcp-onenote
sudo systemctl enable mcp-onedrive
sudo systemctl enable mcp-teams

# 서비스 시작
sudo systemctl start mcp-oauth
sudo systemctl start mcp-mail
sudo systemctl start mcp-onenote
sudo systemctl start mcp-onedrive
sudo systemctl start mcp-teams

# 상태 확인
sudo systemctl status mcp-*
```

---

## 🔄 코드 변경 사항

### Discovery 엔드포인트 URL 변경

**변경 전:**
```json
{
  "oauth": {
    "authorization_endpoint": "https://api.example.com/oauth/authorize",
    "token_endpoint": "https://api.example.com/oauth/token"
  }
}
```

**변경 후:**
```json
{
  "oauth": {
    "authorization_endpoint": "https://oauth.example.com/authorize",
    "token_endpoint": "https://oauth.example.com/token"
  }
}
```

### 각 MCP 서버의 Discovery 핸들러 수정

```python
# modules/mail_query_MCP/mcp_server/http_server.py

async def mcp_discovery_handler(request):
    # 서브도메인 방식에서는 경로에 서비스명 불필요
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    oauth_base_url = base_url.replace("mail.", "oauth.")  # 서브도메인 변경

    return JSONResponse({
        "mcp_version": "1.0",
        "name": "Mail Query MCP Server",
        "oauth": {
            "authorization_endpoint": f"{oauth_base_url}/authorize",
            "token_endpoint": f"{oauth_base_url}/token",
            "registration_endpoint": f"{oauth_base_url}/register"
        },
        "capabilities": {
            "tools": True
        }
    })
```

### 환경변수 설정

```bash
# .env

# OAuth Server
OAUTH_HOST=0.0.0.0
OAUTH_PORT=8001
OAUTH_BASE_URL=https://oauth.example.com

# Mail Query Server
MAIL_HOST=0.0.0.0
MAIL_PORT=8002
MAIL_BASE_URL=https://mail.example.com

# OneNote Server
ONENOTE_HOST=0.0.0.0
ONENOTE_PORT=8003
ONENOTE_BASE_URL=https://onenote.example.com

# OneDrive Server
ONEDRIVE_HOST=0.0.0.0
ONEDRIVE_PORT=8004
ONEDRIVE_BASE_URL=https://onedrive.example.com

# Teams Server
TEAMS_HOST=0.0.0.0
TEAMS_PORT=8005
TEAMS_BASE_URL=https://teams.example.com

# DCR 설정 (모든 서버가 공유)
DCR_DATABASE_PATH=/path/to/claudedcr.db
DCR_AZURE_CLIENT_ID=your-azure-app-id
DCR_AZURE_CLIENT_SECRET=your-azure-secret
DCR_AZURE_TENANT_ID=your-tenant-id
DCR_OAUTH_REDIRECT_URI=https://oauth.example.com/azure_callback
```

---

## 🧪 로컬 개발 환경 설정

### /etc/hosts 설정

```bash
# /etc/hosts

127.0.0.1  oauth.localhost
127.0.0.1  mail.localhost
127.0.0.1  onenote.localhost
127.0.0.1  onedrive.localhost
127.0.0.1  teams.localhost
```

### 개발용 리버스 프록시 (Caddy)

```caddy
# Caddyfile.dev

oauth.localhost {
    reverse_proxy localhost:8001
}

mail.localhost {
    reverse_proxy localhost:8002
}

onenote.localhost {
    reverse_proxy localhost:8003
}

onedrive.localhost {
    reverse_proxy localhost:8004
}

teams.localhost {
    reverse_proxy localhost:8005
}
```

```bash
# Caddy 실행
caddy run --config Caddyfile.dev
```

### 개발용 스크립트

```bash
#!/bin/bash
# scripts/start-all-servers.sh

# 각 서버를 백그라운드로 실행
python entrypoints/production/oauth_server.py &
python entrypoints/production/mail_server.py &
python entrypoints/production/onenote_server.py &
python entrypoints/production/onedrive_server.py &
python entrypoints/production/teams_server.py &

echo "All servers started"
echo "OAuth:    http://oauth.localhost"
echo "Mail:     http://mail.localhost"
echo "OneNote:  http://onenote.localhost"
echo "OneDrive: http://onedrive.localhost"
echo "Teams:    http://teams.localhost"
```

---

## 📊 비교표

| 항목 | Path-based (현재) | Subdomain-based (목표) |
|------|------------------|----------------------|
| **URL** | api.example.com/mail-query/messages | mail.example.com/messages |
| **URL 길이** | 길음 | 짧음 |
| **독립 배포** | 불가능 (단일 서버) | 가능 (서비스별 서버) |
| **로드밸런싱** | 전체만 가능 | 서비스별 가능 |
| **SSL 인증서** | 1개 (*.example.com) | 서비스별 또는 와일드카드 |
| **CORS 설정** | 단순 | 서브도메인 간 고려 필요 |
| **DNS 설정** | 단순 (A 레코드 1개) | 복잡 (A 레코드 5개 또는 와일드카드) |
| **코드 복잡도** | 낮음 | 중간 (분리 필요) |
| **운영 복잡도** | 낮음 | 중간 (여러 프로세스 관리) |

---

## ✅ 추천 방안

**프로덕션:** **방안 1 (Nginx 리버스 프록시)**

**이유:**
1. 기존 코드 최소 수정 (각 서버만 포트별로 분리)
2. SSL/TLS 자동 처리
3. 로드밸런싱, 캐싱 등 추가 기능 활용
4. 안정적이고 검증된 솔루션
5. 무중단 배포 가능 (Nginx reload)

**개발 환경:** **Caddy + hosts 파일**

**이유:**
1. 설정이 간단
2. 자동 HTTPS (로컬 개발 인증서)
3. 리로드 빠름

---

## 🚀 단계별 마이그레이션 전략

### Phase 1: 코드 분리 (1주)
- [ ] OAuth 서버 독립 실행 파일 작성
- [ ] Mail Query 서버 독립 실행 파일 작성
- [ ] OneNote 서버 독립 실행 파일 작성
- [ ] OneDrive 서버 독립 실행 파일 작성
- [ ] Teams 서버 독립 실행 파일 작성
- [ ] Discovery 엔드포인트 URL 동적 생성 로직 추가

### Phase 2: 로컬 테스트 (3일)
- [ ] Caddy 설정 및 테스트
- [ ] /etc/hosts 설정
- [ ] 모든 서버 동시 실행 스크립트 작성
- [ ] 서브도메인 간 통신 테스트

### Phase 3: 프로덕션 인프라 구축 (1주)
- [ ] Nginx 설치 및 설정
- [ ] DNS 레코드 생성
- [ ] SSL/TLS 인증서 발급 (Let's Encrypt)
- [ ] systemd 서비스 파일 작성

### Phase 4: 배포 및 모니터링 (3일)
- [ ] 서비스 배포
- [ ] 헬스 체크 설정
- [ ] 로그 모니터링 설정
- [ ] 에러 알림 설정

### Phase 5: 롤백 계획 (1일)
- [ ] 기존 unified 서버 백업
- [ ] 롤백 스크립트 작성
- [ ] DNS TTL 확인 (빠른 롤백 위해 낮게 설정)

---

## 📝 체크리스트

### 코드 변경
- [ ] 각 서버의 독립 실행 파일 작성
- [ ] Discovery 엔드포인트 URL 업데이트
- [ ] OAuth redirect URI 업데이트
- [ ] CORS 설정 업데이트 (서브도메인 간 통신)
- [ ] 로깅 설정 (서버별 로그 파일)

### 인프라 설정
- [ ] 리버스 프록시 설정 (Nginx/Caddy)
- [ ] DNS 레코드 생성
- [ ] SSL/TLS 인증서 발급
- [ ] 방화벽 규칙 설정

### 프로세스 관리
- [ ] systemd 서비스 파일 작성
- [ ] 자동 재시작 설정
- [ ] 로그 로테이션 설정

### 모니터링
- [ ] 헬스 체크 엔드포인트
- [ ] 프로세스 모니터링 (systemd status)
- [ ] 리소스 모니터링 (CPU, 메모리)
- [ ] 에러 알림 설정

### 문서화
- [ ] 배포 가이드 작성
- [ ] 운영 가이드 작성
- [ ] 트러블슈팅 가이드 작성
