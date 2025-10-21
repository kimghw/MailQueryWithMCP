# Cloudflare Tunnel 배포 가이드

## 개요
이 문서는 MailQueryWithMCP unified HTTP 서버를 Cloudflare Tunnel을 통해 배포하는 방법을 설명합니다.

## 사전 요구사항
- Cloudflare 계정
- 도메인 (Cloudflare DNS 관리)
- Linux 서버 (Ubuntu/Debian 권장)

## 빠른 시작

### 1. 배포 스크립트 실행
```bash
./deploy-cloudflare-tunnel.sh deploy
```

이 명령은 다음 작업을 자동으로 수행합니다:
1. cloudflared 설치 확인
2. Cloudflare 로그인
3. 터널 생성
4. DNS 설정 안내
5. unified HTTP 서버 시작
6. systemd 서비스 설치 및 시작

### 2. DNS 설정
스크립트 실행 중 DNS 설정 안내가 표시됩니다:
- Cloudflare 대시보드에서 CNAME 레코드 추가
- 또는 CLI 명령 사용: `cloudflared tunnel route dns mailquery-mcp mailquery-mcp.yourdomain.com`

## 관리 명령어

### 서비스 관리
```bash
# 시작
./deploy-cloudflare-tunnel.sh start

# 중지
./deploy-cloudflare-tunnel.sh stop

# 재시작
./deploy-cloudflare-tunnel.sh restart

# 상태 확인
./deploy-cloudflare-tunnel.sh status

# 로그 보기
./deploy-cloudflare-tunnel.sh logs
```

### systemd 직접 관리
```bash
# 서비스 상태
sudo systemctl status cloudflared

# 서비스 재시작
sudo systemctl restart cloudflared

# 로그 확인
sudo journalctl -u cloudflared -f
```

## 설정 파일

### cloudflare-tunnel-config.yml
터널 설정 파일입니다. 필요시 수정 가능:
- `hostname`: 사용할 도메인
- `service`: 프록시할 로컬 서비스 주소
- `originRequest`: 추가 옵션 (타임아웃, HTTP/2 등)

### cloudflared.service
systemd 서비스 파일입니다. 자동 시작 및 재시작을 관리합니다.

## 문제 해결

### 터널이 시작되지 않음
```bash
# 로그 확인
sudo journalctl -u cloudflared -n 50

# 수동 실행 테스트
cloudflared tunnel --config cloudflare-tunnel-config.yml run
```

### DNS 해결 실패
- CNAME 레코드가 올바르게 설정되었는지 확인
- DNS 전파 대기 (최대 5분)
- `nslookup mailquery-mcp.yourdomain.com` 로 확인

### 502 Bad Gateway
- unified HTTP 서버가 실행 중인지 확인
- 포트 8000이 올바르게 리스닝하는지 확인
```bash
netstat -tlnp | grep 8000
curl http://localhost:8000/health
```

## 보안 고려사항

1. **터널 자격 증명 보호**
   - `~/.cloudflared/` 디렉토리 권한 확인
   - 자격 증명 파일 백업

2. **액세스 제어**
   - Cloudflare Access 사용 고려
   - IP 화이트리스트 설정

3. **모니터링**
   - Cloudflare 대시보드에서 트래픽 모니터링
   - 비정상 접근 패턴 감지

## 프로덕션 체크리스트

- [ ] DNS 레코드 설정 완료
- [ ] SSL/TLS 설정 확인
- [ ] 백업 및 복구 계획
- [ ] 모니터링 설정
- [ ] 로그 로테이션 설정
- [ ] 방화벽 규칙 검토
- [ ] Cloudflare Access 설정 (선택사항)
- [ ] 부하 테스트 수행

## 고급 설정

### 다중 서비스 프록시
```yaml
ingress:
  - hostname: api.example.com
    service: http://localhost:8000
  - hostname: admin.example.com
    service: http://localhost:8001
```

### 헬스체크 엔드포인트
```yaml
ingress:
  - hostname: health.example.com
    service: http://localhost:8000
    path: /health
```

### Zero Trust 액세스
Cloudflare Access를 통한 추가 보안:
1. Cloudflare 대시보드 > Access
2. 애플리케이션 생성
3. 액세스 정책 설정 (이메일, IP, 국가 등)