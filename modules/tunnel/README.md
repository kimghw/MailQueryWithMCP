# Cloudflare Tunnel Management

## 문제점
- trycloudflare.com은 매번 실행할 때마다 새로운 URL을 생성합니다
- 기존 터널이 있어도 새 터널을 생성하면 URL이 바뀝니다
- Claude MCP 설정을 매번 업데이트해야 합니다

## 해결 방법

### 1. 터널 시작 (처음 한 번만)
```bash
modules/tunnel/tunnel_start.sh 8001
```
- 터널 URL과 PID를 `.tunnel_info_8001.json`에 저장합니다

### 2. 터널 상태 확인
```bash
modules/tunnel/tunnel_status.sh          # 모든 터널 확인
modules/tunnel/check_tunnel_status.sh 8001  # 특정 포트 확인
```

### 3. MCP 서버 실행 (터널 재사용)
```bash
modules/query_assistant/run_with_tunnel.sh
```
- 기존 터널이 있으면 재사용합니다
- 터널 정보를 `.tunnel_info_8001.json`에서 읽어옵니다

## 주의사항
- 터널 URL이 작동하지 않으면 터널을 재시작해야 합니다
- 터널을 재시작하면 URL이 바뀌므로 Claude 설정을 업데이트해야 합니다
- 가능하면 한 번 시작한 터널을 계속 사용하세요