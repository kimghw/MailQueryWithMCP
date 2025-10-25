# Cloudflare 무료 Tunnel의 서브도메인 제약사항

## ❌ 무료 Tunnel (trycloudflare.com)의 한계

### 질문: `random-name.trycloudflare.com` 내에서 서브도메인 구성 가능한가?

**답변: 불가능합니다.**

무료 Cloudflare Tunnel (`cloudflared tunnel --url http://localhost:8000`)이 제공하는 URL은:

```
https://random-abc123.trycloudflare.com
```

이 도메인에서 **서브도메인을 추가로 만들 수 없습니다.**

### 시도해봤자 안 되는 것들:

❌ `oauth.random-abc123.trycloudflare.com` → **불가능**
❌ `mail.random-abc123.trycloudflare.com` → **불가능**
❌ 와일드카드 DNS → **불가능** (DNS 제어 권한 없음)

**이유:**
- `trycloudflare.com`의 DNS는 Cloudflare가 완전히 제어
- 사용자는 DNS 레코드를 추가/수정할 수 없음
- 무료 터널은 단일 랜덤 서브도메인만 제공

---

## ✅ 해결책: 유료 도메인 필요 (연 $12)

### 방법 1: 자신의 도메인 구매 후 Cloudflare Tunnel 연결

```
1. 도메인 구매 (예: yourdomain.com - $12/년)
   ↓
2. Cloudflare에 도메인 추가 (무료)
   ↓
3. Named Tunnel 생성 (무료)
   ↓
4. 서브도메인 무제한 사용 가능!
   - oauth.yourdomain.com
   - mail.yourdomain.com
   - onenote.yourdomain.com
   - 등등 무제한
```

#### 구체적인 흐름:

```
도메인: example.com (Namecheap에서 구매)
   ↓
Cloudflare에 등록 (무료)
   ↓
Cloudflare Tunnel 생성 (무료)
   ↓
DNS 설정 (Cloudflare 대시보드)
   CNAME  oauth      tunnel-id.cfargotunnel.com
   CNAME  mail       tunnel-id.cfargotunnel.com
   CNAME  onenote    tunnel-id.cfargotunnel.com
   ↓
config.yml에 서브도메인별 라우팅 설정
   oauth.example.com → localhost:8001
   mail.example.com  → localhost:8002
   ↓
완료! 모든 서브도메인이 HTTPS로 작동
```

---

## 📊 비교표

| 항목 | 무료 Tunnel (trycloudflare) | 유료 도메인 + 무료 Tunnel |
|------|----------------------------|--------------------------|
| **비용** | 완전 무료 | 도메인 비용만 (~$12/년) |
| **URL** | random-abc.trycloudflare.com | yourdomain.com |
| **서브도메인** | ❌ 불가능 | ✅ 무제한 |
| **URL 지속성** | ❌ 재시작 시 변경 | ✅ 영구적 |
| **DNS 제어** | ❌ 불가능 | ✅ 완전 제어 |
| **HTTPS** | ✅ 자동 | ✅ 자동 |
| **DDoS 보호** | ✅ 기본 | ✅ 강력 |
| **프로덕션 사용** | ❌ 비추천 | ✅ 추천 |

---

## 💡 현재 상황에서 가능한 대안

### 대안 1: Path-based Routing (현재 방식 유지)

무료 터널에서는 **서브도메인 대신 경로로 구분**해야 합니다.

```
https://random-abc.trycloudflare.com/oauth/authorize
https://random-abc.trycloudflare.com/mail-query/messages
https://random-abc.trycloudflare.com/onenote/messages
https://random-abc.trycloudflare.com/onedrive/messages
https://random-abc.trycloudflare.com/teams/messages
```

**이미 이렇게 구현되어 있습니다!** (unified_http_server.py)

#### cloudflare-tunnel-config.yml (무료 터널용)

```yaml
# 무료 터널에서는 서브도메인 설정 안 함
ingress:
  # Unified 서버로 모든 트래픽 전달
  - service: http://localhost:8000
```

```bash
# 무료 터널 실행 (URL 자동 생성)
cloudflared tunnel --url http://localhost:8000

# 출력 예시:
# https://random-abc-def.trycloudflare.com
```

---

### 대안 2: 로컬 도메인 + Reverse Proxy (개발용)

로컬 개발 환경에서는 `/etc/hosts` + Nginx/Caddy로 서브도메인 흉내 가능:

#### /etc/hosts

```
127.0.0.1  oauth.localhost
127.0.0.1  mail.localhost
127.0.0.1  onenote.localhost
127.0.0.1  onedrive.localhost
127.0.0.1  teams.localhost
```

#### Caddyfile

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
```

**하지만:** 이건 로컬에서만 작동하고, 외부에서 접근 불가능합니다.

---

### 대안 3: ngrok (유료지만 서브도메인 지원)

ngrok은 유료 플랜($8/월)에서 서브도메인을 제공합니다.

```bash
# ngrok 유료 플랜
ngrok http 8001 --subdomain=oauth
ngrok http 8002 --subdomain=mail
ngrok http 8003 --subdomain=onenote
```

**결과:**
```
https://oauth.ngrok.io
https://mail.ngrok.io
https://onenote.ngrok.io
```

**비용:** $96/년 (Cloudflare 도메인보다 8배 비쌈)

---

## ✅ 추천 방안

### 개발/테스트: 무료 Tunnel + Path-based (현재 방식)

```
https://random.trycloudflare.com/mail-query/messages
https://random.trycloudflare.com/onenote/messages
```

**장점:**
- ✅ 완전 무료
- ✅ 빠른 설정
- ✅ HTTPS 자동

**단점:**
- ❌ URL 재시작 시 변경
- ❌ 서브도메인 불가
- ❌ 프로덕션 부적합

---

### 프로덕션: 도메인 구매 ($12/년) + Named Tunnel

```
https://oauth.yourdomain.com
https://mail.yourdomain.com
https://onenote.yourdomain.com
```

**장점:**
- ✅ 서브도메인 무제한
- ✅ 영구적인 URL
- ✅ 전문적인 이미지
- ✅ DNS 완전 제어

**단점:**
- ❌ 도메인 비용 ($12/년)

---

## 🚀 Named Tunnel 설정 방법 (도메인 있을 때)

### 1. Named Tunnel 생성

```bash
# 터널 생성
cloudflared tunnel create mailquery-mcp

# 출력:
# Tunnel credentials written to: /home/kimghw/.cloudflared/TUNNEL_ID.json
# Tunnel mailquery-mcp created with ID: TUNNEL_ID
```

### 2. DNS 레코드 추가 (Cloudflare 대시보드 또는 CLI)

```bash
# CLI로 DNS 자동 설정
cloudflared tunnel route dns mailquery-mcp oauth.yourdomain.com
cloudflared tunnel route dns mailquery-mcp mail.yourdomain.com
cloudflared tunnel route dns mailquery-mcp onenote.yourdomain.com
cloudflared tunnel route dns mailquery-mcp onedrive.yourdomain.com
cloudflared tunnel route dns mailquery-mcp teams.yourdomain.com

# 또는 와일드카드
cloudflared tunnel route dns mailquery-mcp "*.yourdomain.com"
```

### 3. config.yml 작성

```yaml
tunnel: TUNNEL_ID
credentials-file: /home/kimghw/.cloudflared/TUNNEL_ID.json

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

### 4. 터널 실행

```bash
# config 파일로 실행
cloudflared tunnel --config config.yml run mailquery-mcp

# 또는 systemd 서비스로 등록
sudo cloudflared service install
sudo systemctl start cloudflared
```

---

## 💰 도메인 구매 가이드

### 추천 도메인 레지스트라

1. **Namecheap** (가장 인기)
   - .com: $13.98/년 (첫 해 할인 가능)
   - 무료 WhoisGuard (개인정보 보호)
   - URL: https://www.namecheap.com

2. **Porkbun** (저렴)
   - .com: $10.39/년
   - 무료 WHOIS 프라이버시
   - URL: https://porkbun.com

3. **Cloudflare Registrar** (가장 저렴)
   - .com: $9.77/년 (도매가)
   - 추가 수수료 없음
   - URL: https://www.cloudflare.com/products/registrar/

### 도메인 선택 팁

- `.com` 추천 (가장 범용적)
- 짧고 기억하기 쉬운 이름
- 하이픈 피하기
- 숫자 최소화

### 구매 후 Cloudflare 연결

1. Cloudflare 계정 생성 (무료)
2. "Add a Site" 클릭
3. 도메인 입력
4. 무료 플랜 선택
5. Nameserver 변경 (레지스트라에서)
   ```
   NS1: ava.ns.cloudflare.com
   NS2: reza.ns.cloudflare.com
   ```
6. 24-48시간 대기 (보통 몇 분이면 완료)
7. Cloudflare Tunnel 설정

---

## 🔍 무료 vs 유료 결정 가이드

### 무료 Tunnel 사용 (trycloudflare.com)

**이런 경우 추천:**
- ✅ 개발/테스트만 사용
- ✅ 단기 프로젝트
- ✅ URL이 자주 바뀌어도 괜찮음
- ✅ 예산이 전혀 없음

### 도메인 구매 ($12/년)

**이런 경우 추천:**
- ✅ 프로덕션 사용
- ✅ 영구적인 URL 필요
- ✅ 서브도메인 필요
- ✅ 전문적인 이미지 중요
- ✅ Claude.ai와 장기 연동

---

## 📝 정리

### 질문: 무료 Cloudflare Tunnel에서 서브도메인 가능?

**답변:**

❌ **불가능** - `random.trycloudflare.com` 내에서는 서브도메인 추가 불가

✅ **가능** - 자신의 도메인 구매 후 Cloudflare Tunnel 연결하면 서브도메인 무제한

### 현재 선택지:

1. **무료로 계속 사용** → Path-based routing 유지
   ```
   random.trycloudflare.com/mail-query/messages
   random.trycloudflare.com/onenote/messages
   ```

2. **도메인 구매 ($12/년)** → 서브도메인 방식으로 전환
   ```
   mail.yourdomain.com/messages
   onenote.yourdomain.com/messages
   ```

### 추천:

- **개발/테스트**: 무료 Tunnel (현재 방식)
- **프로덕션**: 도메인 구매 (연 $12 투자 가치 충분)

도메인을 구매하면 **추가 비용 없이** Cloudflare Tunnel의 모든 기능(서브도메인, 영구 URL, HTTPS 등)을 사용할 수 있습니다!
