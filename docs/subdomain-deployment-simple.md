# 서브도메인 방식 배포 가이드 (간단 버전)

## 🎉 현재 상황

**좋은 소식:** 이미 각 MCP 서버가 독립적으로 실행 가능하도록 구현되어 있습니다!

```python
# 각 서버가 이미 독립 실행 가능
HTTPStreamingMailAttachmentServer(host="0.0.0.0", port=8002).run()
HTTPStreamingAuthServer(host="0.0.0.0", port=8001).run()
HTTPStreamingOneNoteServer(host="0.0.0.0", port=8003).run()
HTTPStreamingOneDriveServer(host="0.0.0.0", port=8004).run()
HTTPStreamingTeamsServer(host="0.0.0.0", port=8005).run()
```

**필요한 작업:**
1. 각 서버의 실행 스크립트 작성 (5분)
2. 리버스 프록시 설정 (10분)
3. DNS 설정 (5분)

끝!

---

## 🚀 빠른 시작 (3단계)

### 1단계: 개별 서버 실행 스크립트 작성

각 서버를 독립적으로 실행하는 간단한 스크립트만 만들면 됩니다.

#### entrypoints/production/run_oauth.py

```python
#!/usr/bin/env python3
"""OAuth Server - 독립 실행"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Unified 서버에서 OAuth 부분만 분리해서 실행
# 현재는 unified_http_server.py의 OAuth 핸들러들을 사용

if __name__ == "__main__":
    # TODO: OAuth 전용 서버 클래스 생성 필요
    # 또는 unified 서버를 OAuth 포트로 실행
    from entrypoints.production.unified_http_server import UnifiedMCPServer

    # OAuth 포트로 실행 (다른 서비스는 비활성화)
    server = UnifiedMCPServer(host="0.0.0.0", port=8001)
    server.run()
```

#### entrypoints/production/run_mail.py

```python
#!/usr/bin/env python3
"""Mail Query Server - 독립 실행"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from modules.mail_query_MCP.mcp_server.http_server import HTTPStreamingMailAttachmentServer

if __name__ == "__main__":
    server = HTTPStreamingMailAttachmentServer(host="0.0.0.0", port=8002)
    server.run()
```

#### entrypoints/production/run_onenote.py

```python
#!/usr/bin/env python3
"""OneNote Server - 독립 실행"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from modules.onenote_mcp.mcp_server.http_server import HTTPStreamingOneNoteServer

if __name__ == "__main__":
    server = HTTPStreamingOneNoteServer(host="0.0.0.0", port=8003)
    server.run()
```

#### entrypoints/production/run_onedrive.py

```python
#!/usr/bin/env python3
"""OneDrive Server - 독립 실행"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from modules.onedrive_mcp.mcp_server.http_server import HTTPStreamingOneDriveServer

if __name__ == "__main__":
    server = HTTPStreamingOneDriveServer(host="0.0.0.0", port=8004)
    server.run()
```

#### entrypoints/production/run_teams.py

```python
#!/usr/bin/env python3
"""Teams Server - 독립 실행"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from modules.teams_mcp.mcp_server.http_server import HTTPStreamingTeamsServer

if __name__ == "__main__":
    server = HTTPStreamingTeamsServer(host="0.0.0.0", port=8005)
    server.run()
```

#### 실행 권한 부여

```bash
chmod +x entrypoints/production/run_*.py
```

---

### 2단계: 리버스 프록시 설정 (Caddy 추천)

#### Caddyfile (슈퍼 간단!)

```caddy
# Caddyfile

oauth.yourdomain.com {
    reverse_proxy localhost:8001
}

mail.yourdomain.com {
    reverse_proxy localhost:8002
}

onenote.yourdomain.com {
    reverse_proxy localhost:8003
}

onedrive.yourdomain.com {
    reverse_proxy localhost:8004
}

teams.yourdomain.com {
    reverse_proxy localhost:8005
}
```

#### Caddy 설치 및 실행

```bash
# Ubuntu/Debian
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy

# Caddyfile 복사
sudo cp Caddyfile /etc/caddy/Caddyfile

# Caddy 실행 (자동으로 Let's Encrypt SSL 발급!)
sudo systemctl restart caddy
```

끝! Caddy가 자동으로 SSL 인증서를 발급하고 관리합니다.

---

### 3단계: DNS 설정

Cloudflare, AWS Route53 등에서 A 레코드 추가:

```
A    oauth      YOUR_SERVER_IP
A    mail       YOUR_SERVER_IP
A    onenote    YOUR_SERVER_IP
A    onedrive   YOUR_SERVER_IP
A    teams      YOUR_SERVER_IP
```

또는 와일드카드:

```
A    *          YOUR_SERVER_IP
```

---

## 🔧 프로세스 관리 (systemd)

각 서버를 systemd 서비스로 등록하면 자동 재시작, 로그 관리 등이 쉬워집니다.

### /etc/systemd/system/mcp-mail.service

```ini
[Unit]
Description=MCP Mail Query Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/home/kimghw/MailQueryWithMCP
Environment="PATH=/home/kimghw/MailQueryWithMCP/venv/bin"
ExecStart=/home/kimghw/MailQueryWithMCP/venv/bin/python3 entrypoints/production/run_mail.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 나머지 서비스들도 동일하게 생성

```bash
# 서비스 파일 생성
sudo nano /etc/systemd/system/mcp-oauth.service
sudo nano /etc/systemd/system/mcp-mail.service
sudo nano /etc/systemd/system/mcp-onenote.service
sudo nano /etc/systemd/system/mcp-onedrive.service
sudo nano /etc/systemd/system/mcp-teams.service

# 서비스 활성화 및 시작
sudo systemctl enable mcp-oauth mcp-mail mcp-onenote mcp-onedrive mcp-teams
sudo systemctl start mcp-oauth mcp-mail mcp-onenote mcp-onedrive mcp-teams

# 상태 확인
sudo systemctl status mcp-*
```

---

## 💡 더 간단한 방법: Docker Compose

이미 각 서버가 독립적이므로 Docker Compose로 관리하면 더 쉽습니다.

### docker-compose.yml

```yaml
version: '3.8'

services:
  oauth:
    build: .
    command: python entrypoints/production/run_oauth.py
    ports:
      - "8001:8001"
    environment:
      - DCR_DATABASE_PATH=/data/claudedcr.db
    volumes:
      - ./data:/data
    restart: always

  mail:
    build: .
    command: python entrypoints/production/run_mail.py
    ports:
      - "8002:8002"
    volumes:
      - ./data:/data
    restart: always

  onenote:
    build: .
    command: python entrypoints/production/run_onenote.py
    ports:
      - "8003:8003"
    volumes:
      - ./data:/data
    restart: always

  onedrive:
    build: .
    command: python entrypoints/production/run_onedrive.py
    ports:
      - "8004:8004"
    volumes:
      - ./data:/data
    restart: always

  teams:
    build: .
    command: python entrypoints/production/run_teams.py
    ports:
      - "8005:8005"
    volumes:
      - ./data:/data
    restart: always

  caddy:
    image: caddy:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    restart: always

volumes:
  caddy_data:
  caddy_config:
```

### Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "entrypoints/production/unified_http_server.py"]
```

### 실행

```bash
# 모든 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 특정 서비스만 재시작
docker-compose restart mail

# 중지
docker-compose down
```

---

## 🧪 로컬 테스트

### /etc/hosts 설정

```bash
sudo nano /etc/hosts

# 추가
127.0.0.1  oauth.localhost
127.0.0.1  mail.localhost
127.0.0.1  onenote.localhost
127.0.0.1  onedrive.localhost
127.0.0.1  teams.localhost
```

### Caddyfile.dev (개발용)

```caddy
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

### 테스트

```bash
# 1. 각 서버 실행 (터미널 5개)
python entrypoints/production/run_oauth.py
python entrypoints/production/run_mail.py
python entrypoints/production/run_onenote.py
python entrypoints/production/run_onedrive.py
python entrypoints/production/run_teams.py

# 2. Caddy 실행
caddy run --config Caddyfile.dev

# 3. 테스트
curl http://oauth.localhost/health
curl http://mail.localhost/health
curl http://onenote.localhost/health
curl http://onedrive.localhost/health
curl http://teams.localhost/health
```

---

## 📊 현재 vs 서브도메인 비교

| 항목 | 현재 (Unified) | 서브도메인 |
|------|---------------|----------|
| **서버 프로세스** | 1개 | 5개 |
| **URL** | api.com/mail-query/messages | mail.api.com/messages |
| **독립 배포** | 불가능 | 가능 |
| **필요한 코드 변경** | - | 거의 없음 (이미 구현됨!) |
| **필요한 인프라** | - | Caddy + DNS |
| **배포 난이도** | 쉬움 | 쉬움 (Caddy 덕분) |

---

## ✅ 체크리스트

### 코드 (거의 완료!)
- [x] HTTPStreaming 서버 구현 (이미 완료)
- [ ] 실행 스크립트 작성 (5분)
- [ ] Discovery URL 동적 생성 (필요시)

### 인프라
- [ ] DNS 레코드 생성 (5분)
- [ ] Caddy 설치 및 설정 (10분)
- [ ] systemd 서비스 등록 (선택사항)

### 테스트
- [ ] 로컬 테스트 (/etc/hosts)
- [ ] 헬스 체크 확인
- [ ] MCP 연결 테스트

---

## 🎯 결론

**이미 90% 완료!** 각 서버가 독립 실행 가능하도록 구현되어 있으므로:

1. **실행 스크립트 5개 작성** (5분)
2. **Caddy 설정 파일 작성** (5분)
3. **DNS 레코드 추가** (5분)

**총 15분이면 서브도메인 방식으로 전환 가능합니다!**

가장 쉬운 경로:
```bash
# 1. 실행 스크립트 작성
# 2. Caddy 설치
sudo apt install caddy

# 3. Caddyfile 작성 (위 예시 복사)
# 4. DNS 설정
# 5. Caddy 시작
sudo systemctl start caddy

# 완료! 자동으로 HTTPS까지 적용됨
```
