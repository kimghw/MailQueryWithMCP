# Cloudflare Tunnel로 서브도메인 구성하기 (무료 플랜)

## ✅ 가능합니다!

Cloudflare Tunnel **무료 플랜**에서도 한 개의 도메인 내에서 **무제한 서브도메인** 사용 가능합니다!

### 현재 상황 예시
```
도메인: example.com (Cloudflare에 등록)

서브도메인 구성:
- oauth.example.com     → localhost:8001
- mail.example.com      → localhost:8002
- onenote.example.com   → localhost:8003
- onedrive.example.com  → localhost:8004
- teams.example.com     → localhost:8005
```

**무료로 제공:**
- ✅ 무제한 서브도메인
- ✅ 자동 SSL/TLS (HTTPS)
- ✅ DDoS 보호
- ✅ 글로벌 CDN
- ✅ 대역폭 무제한

---

## 🚀 설정 방법 (3단계)

### 1단계: Cloudflare Tunnel 설정 파일

#### cloudflare-tunnel-config.yml

```yaml
tunnel: YOUR_TUNNEL_ID
credentials-file: /home/kimghw/.cloudflared/YOUR_TUNNEL_ID.json

# 서브도메인별 라우팅
ingress:
  # OAuth Server
  - hostname: oauth.yourdomain.com
    service: http://localhost:8001
    originRequest:
      noTLSVerify: true

  # Mail Query Server
  - hostname: mail.yourdomain.com
    service: http://localhost:8002
    originRequest:
      noTLSVerify: true

  # OneNote Server
  - hostname: onenote.yourdomain.com
    service: http://localhost:8003
    originRequest:
      noTLSVerify: true

  # OneDrive Server
  - hostname: onedrive.yourdomain.com
    service: http://localhost:8004
    originRequest:
      noTLSVerify: true

  # Teams Server
  - hostname: teams.yourdomain.com
    service: http://localhost:8005
    originRequest:
      noTLSVerify: true

  # Catch-all (404)
  - service: http_status:404
```

---

### 2단계: Cloudflare 대시보드에서 DNS 설정

Cloudflare Dashboard → DNS → Records에서 CNAME 레코드 추가:

```
CNAME  oauth      YOUR_TUNNEL_ID.cfargotunnel.com  (Proxied ✅)
CNAME  mail       YOUR_TUNNEL_ID.cfargotunnel.com  (Proxied ✅)
CNAME  onenote    YOUR_TUNNEL_ID.cfargotunnel.com  (Proxied ✅)
CNAME  onedrive   YOUR_TUNNEL_ID.cfargotunnel.com  (Proxied ✅)
CNAME  teams      YOUR_TUNNEL_ID.cfargotunnel.com  (Proxied ✅)
```

**또는 와일드카드 (더 간단):**

```
CNAME  *          YOUR_TUNNEL_ID.cfargotunnel.com  (Proxied ✅)
```

와일드카드를 사용하면 **모든 서브도메인**이 자동으로 터널로 연결됩니다!

---

### 3단계: 서버 실행 및 터널 시작

#### 각 서버 실행 (터미널 5개 또는 systemd)

```bash
# 터미널 1
python entrypoints/production/run_oauth.py

# 터미널 2
python entrypoints/production/run_mail.py

# 터미널 3
python entrypoints/production/run_onenote.py

# 터미널 4
python entrypoints/production/run_onedrive.py

# 터미널 5
python entrypoints/production/run_teams.py
```

#### Cloudflare Tunnel 실행

```bash
# config 파일 사용
cloudflared tunnel --config cloudflare-tunnel-config.yml run

# 또는 터널 이름으로 실행
cloudflared tunnel run mailquery-mcp
```

---

## 🔧 완전 자동화 스크립트

### cloudflare-subdomain-setup.sh

```bash
#!/bin/bash

# Cloudflare Tunnel 서브도메인 설정 스크립트

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}Cloudflare Tunnel 서브도메인 설정${NC}"
echo "=========================================="

# 1. 터널 정보 입력
read -p "도메인 이름 (예: example.com): " DOMAIN
read -p "Cloudflare Tunnel ID: " TUNNEL_ID

# 2. config.yml 생성
cat > cloudflare-tunnel-config.yml <<EOF
tunnel: ${TUNNEL_ID}
credentials-file: /home/kimghw/.cloudflared/${TUNNEL_ID}.json

ingress:
  - hostname: oauth.${DOMAIN}
    service: http://localhost:8001
    originRequest:
      noTLSVerify: true

  - hostname: mail.${DOMAIN}
    service: http://localhost:8002
    originRequest:
      noTLSVerify: true

  - hostname: onenote.${DOMAIN}
    service: http://localhost:8003
    originRequest:
      noTLSVerify: true

  - hostname: onedrive.${DOMAIN}
    service: http://localhost:8004
    originRequest:
      noTLSVerify: true

  - hostname: teams.${DOMAIN}
    service: http://localhost:8005
    originRequest:
      noTLSVerify: true

  - service: http_status:404
EOF

echo -e "${GREEN}✓ cloudflare-tunnel-config.yml 생성 완료${NC}"

# 3. DNS 레코드 자동 생성
echo -e "\n${BLUE}DNS 레코드 생성 중...${NC}"

cloudflared tunnel route dns ${TUNNEL_ID} oauth.${DOMAIN}
cloudflared tunnel route dns ${TUNNEL_ID} mail.${DOMAIN}
cloudflared tunnel route dns ${TUNNEL_ID} onenote.${DOMAIN}
cloudflared tunnel route dns ${TUNNEL_ID} onedrive.${DOMAIN}
cloudflared tunnel route dns ${TUNNEL_ID} teams.${DOMAIN}

echo -e "${GREEN}✓ DNS 레코드 생성 완료${NC}"

# 4. systemd 서비스 생성
echo -e "\n${BLUE}systemd 서비스 파일 생성 중...${NC}"

# Cloudflare Tunnel 서비스
sudo tee /etc/systemd/system/cloudflared-tunnel.service > /dev/null <<EOF
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
Type=simple
User=kimghw
ExecStart=/usr/local/bin/cloudflared tunnel --config /home/kimghw/MailQueryWithMCP/cloudflare-tunnel-config.yml run
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# MCP 서버 서비스들
for service in oauth mail onenote onedrive teams; do
    port=$((8000 + ${service//[a-z]/}))

    if [ "$service" = "oauth" ]; then port=8001; fi
    if [ "$service" = "mail" ]; then port=8002; fi
    if [ "$service" = "onenote" ]; then port=8003; fi
    if [ "$service" = "onedrive" ]; then port=8004; fi
    if [ "$service" = "teams" ]; then port=8005; fi

    sudo tee /etc/systemd/system/mcp-${service}.service > /dev/null <<EOF
[Unit]
Description=MCP ${service^} Server
After=network.target

[Service]
Type=simple
User=kimghw
WorkingDirectory=/home/kimghw/MailQueryWithMCP
Environment="PATH=/home/kimghw/MailQueryWithMCP/venv/bin"
ExecStart=/home/kimghw/MailQueryWithMCP/venv/bin/python3 entrypoints/production/run_${service}.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
done

echo -e "${GREEN}✓ systemd 서비스 파일 생성 완료${NC}"

# 5. 서비스 활성화 및 시작
echo -e "\n${BLUE}서비스 활성화 및 시작 중...${NC}"

sudo systemctl daemon-reload
sudo systemctl enable cloudflared-tunnel mcp-oauth mcp-mail mcp-onenote mcp-onedrive mcp-teams
sudo systemctl start cloudflared-tunnel mcp-oauth mcp-mail mcp-onenote mcp-onedrive mcp-teams

echo -e "${GREEN}✓ 모든 서비스 시작 완료${NC}"

# 6. 상태 확인
echo -e "\n${BLUE}서비스 상태:${NC}"
sudo systemctl status cloudflared-tunnel --no-pager
sudo systemctl status mcp-* --no-pager

echo -e "\n${GREEN}=========================================="
echo "✓ 설정 완료!"
echo "=========================================="
echo ""
echo "서브도메인 URL:"
echo "  - https://oauth.${DOMAIN}"
echo "  - https://mail.${DOMAIN}"
echo "  - https://onenote.${DOMAIN}"
echo "  - https://onedrive.${DOMAIN}"
echo "  - https://teams.${DOMAIN}"
echo ""
echo "로그 확인:"
echo "  sudo journalctl -u cloudflared-tunnel -f"
echo "  sudo journalctl -u mcp-mail -f"
echo "${NC}"
```

#### 실행 권한 부여 및 실행

```bash
chmod +x cloudflare-subdomain-setup.sh
./cloudflare-subdomain-setup.sh
```

---

## 🎯 핵심 포인트

### 1. 무료로 가능한 것들

✅ **무제한 서브도메인**
- oauth.example.com
- mail.example.com
- api.example.com
- admin.example.com
- 등등 무제한!

✅ **자동 HTTPS (SSL/TLS)**
- Let's Encrypt 설정 불필요
- 인증서 자동 갱신
- 모든 서브도메인에 적용

✅ **DDoS 보호**
- Cloudflare의 강력한 DDoS 보호
- Rate limiting
- WAF (Web Application Firewall)

✅ **글로벌 CDN**
- 전 세계 200+ 데이터센터
- 자동 캐싱
- 낮은 레이턴시

---

### 2. 와일드카드 vs 개별 서브도메인

#### 와일드카드 (추천)

**장점:**
- 한 번 설정으로 모든 서브도메인 자동 연결
- 새 서브도메인 추가 시 DNS 설정 불필요
- 관리 간편

**설정:**
```
CNAME  *  YOUR_TUNNEL_ID.cfargotunnel.com
```

**config.yml:**
```yaml
ingress:
  - hostname: oauth.example.com
    service: http://localhost:8001
  - hostname: mail.example.com
    service: http://localhost:8002
  # ... 등등
  - service: http_status:404
```

#### 개별 서브도메인

**장점:**
- 세밀한 제어
- 보안 강화 (허용된 서브도메인만)

**설정:**
```
CNAME  oauth     YOUR_TUNNEL_ID.cfargotunnel.com
CNAME  mail      YOUR_TUNNEL_ID.cfargotunnel.com
CNAME  onenote   YOUR_TUNNEL_ID.cfargotunnel.com
```

---

## 🔄 기존 Unified 서버에서 마이그레이션

### 현재 (Path-based)
```
https://your-tunnel.trycloudflare.com/mail-query/messages
https://your-tunnel.trycloudflare.com/onenote/messages
```

### 변경 후 (Subdomain-based)
```
https://mail.yourdomain.com/messages
https://onenote.yourdomain.com/messages
```

### cloudflare-tunnel-config.yml 변경

**변경 전:**
```yaml
ingress:
  - service: http://localhost:8000  # Unified 서버
```

**변경 후:**
```yaml
ingress:
  - hostname: oauth.yourdomain.com
    service: http://localhost:8001
  - hostname: mail.yourdomain.com
    service: http://localhost:8002
  - hostname: onenote.yourdomain.com
    service: http://localhost:8003
  - hostname: onedrive.yourdomain.com
    service: http://localhost:8004
  - hostname: teams.yourdomain.com
    service: http://localhost:8005
  - service: http_status:404
```

---

## 📊 비교표

| 항목 | 무료 터널 (trycloudflare.com) | 유료 도메인 + 터널 |
|------|------------------------------|-------------------|
| **비용** | 무료 | 도메인 비용만 (~$12/년) |
| **URL** | random.trycloudflare.com | yourdomain.com |
| **서브도메인** | 불가능 | ✅ 무제한 |
| **SSL** | ✅ 자동 | ✅ 자동 |
| **지속성** | 재시작 시 URL 변경 | ✅ 영구적 |
| **커스터마이징** | 제한적 | ✅ 완전 제어 |
| **프로덕션** | 비추천 | ✅ 추천 |

---

## 🧪 테스트 방법

### 1. 로컬 hosts 파일로 테스트 (DNS 전)

```bash
# /etc/hosts에 추가
127.0.0.1  oauth.yourdomain.com
127.0.0.1  mail.yourdomain.com
127.0.0.1  onenote.yourdomain.com
127.0.0.1  onedrive.yourdomain.com
127.0.0.1  teams.yourdomain.com
```

```bash
# 각 서버 실행
python entrypoints/production/run_mail.py

# 테스트
curl http://mail.yourdomain.com:8002/health
```

### 2. Cloudflare Tunnel 로그 확인

```bash
# 실시간 로그
cloudflared tunnel --config cloudflare-tunnel-config.yml run --loglevel debug

# systemd 로그
sudo journalctl -u cloudflared-tunnel -f
```

### 3. 연결 테스트

```bash
# 각 서브도메인 헬스 체크
for subdomain in oauth mail onenote onedrive teams; do
    echo "Testing ${subdomain}.yourdomain.com"
    curl -s https://${subdomain}.yourdomain.com/health | jq .
done
```

---

## 💡 추가 팁

### 1. 개발/프로덕션 분리

```yaml
# 개발용
ingress:
  - hostname: dev-mail.yourdomain.com
    service: http://localhost:8002

# 프로덕션용
  - hostname: mail.yourdomain.com
    service: http://localhost:9002
```

### 2. 로드밸런싱 (무료!)

```yaml
ingress:
  - hostname: mail.yourdomain.com
    service: http://localhost:8002
    # Cloudflare가 자동으로 로드밸런싱
    originRequest:
      connectTimeout: 10s
      noHappyEyeballs: false
```

### 3. 커스텀 에러 페이지

```yaml
ingress:
  - service: http_status:404
    # 커스텀 404 페이지 제공 가능
```

---

## ✅ 체크리스트

### 설정 전
- [ ] Cloudflare 계정 생성 (무료)
- [ ] 도메인 구매 (예: Namecheap, $12/년)
- [ ] 도메인을 Cloudflare로 이전 (무료)
- [ ] cloudflared 설치
- [ ] Cloudflare Tunnel 생성

### 설정
- [ ] cloudflare-tunnel-config.yml 작성
- [ ] DNS 레코드 생성 (와일드카드 또는 개별)
- [ ] 각 MCP 서버 실행 스크립트 작성
- [ ] systemd 서비스 파일 작성 (선택)

### 테스트
- [ ] 로컬 hosts 파일로 테스트
- [ ] 각 서브도메인 헬스 체크
- [ ] MCP 연결 테스트
- [ ] SSL/TLS 확인

### 배포
- [ ] systemd 서비스 시작
- [ ] Cloudflare Tunnel 시작
- [ ] 로그 모니터링
- [ ] Claude.ai 연결 테스트

---

## 🎉 결론

**네, Cloudflare Tunnel 무료 플랜에서 서브도메인 완전히 가능합니다!**

필요한 것:
1. ✅ Cloudflare 계정 (무료)
2. ✅ 도메인 (연 $12 정도)
3. ✅ cloudflared (무료)

얻는 것:
- 🎁 무제한 서브도메인
- 🎁 자동 HTTPS
- 🎁 DDoS 보호
- 🎁 글로벌 CDN
- 🎁 대역폭 무제한

**총 비용: 연 $12 (도메인 비용만!)**

가장 빠른 시작:
```bash
# 1. 터널 생성
cloudflared tunnel create mailquery-mcp

# 2. config.yml 작성 (위 예시 참고)

# 3. DNS 자동 설정
cloudflared tunnel route dns mailquery-mcp mail.yourdomain.com

# 4. 터널 실행
cloudflared tunnel run mailquery-mcp

# 완료!
```
