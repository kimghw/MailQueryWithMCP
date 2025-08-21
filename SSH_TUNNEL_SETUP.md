# SSH 터널링을 통한 원격 MCP 서버 연결 가이드

## 개요
SSE 기반 MCP 서버를 SSH 터널링을 통해 원격에서 접속하는 방법을 설명합니다.

## 서버 측 설정

### 1. SSE MCP 서버 실행
```bash
# 서버에서 실행
cd /home/kimghw/IACSGRAPH
python -m modules.query_assistant.mcp_server_sse
```

서버는 기본적으로 `0.0.0.0:8765` 에서 실행됩니다.

### 2. 환경 변수 설정 (선택사항)
```bash
export MCP_HOST=0.0.0.0
export MCP_PORT=8765
export DB_PATH=/home/kimghw/IACSGRAPH/data/email_dashboard.db
export OPENAI_API_KEY=your-api-key
```

## 클라이언트 측 설정

### 1. SSH 터널 생성
```bash
# 로컬 포트 8765를 원격 서버의 8765 포트로 포워딩
ssh -L 8765:localhost:8765 kimghw@your-server-address
```

또는 백그라운드에서 실행:
```bash
ssh -fN -L 8765:localhost:8765 kimghw@your-server-address
```

### 2. Claude Desktop 설정
Claude Desktop의 설정 파일에 다음 내용을 추가합니다:

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Linux**: `~/.config/claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "iacsgraph-remote": {
      "url": "http://localhost:8765/sse",
      "transport": {
        "type": "sse"
      }
    }
  }
}
```

### 3. 연결 확인
브라우저에서 `http://localhost:8765/health` 접속하여 서버 상태 확인:
```json
{
  "status": "healthy",
  "server": "iacsgraph-query-assistant-sse",
  "version": "2.0.0"
}
```

## 고급 설정

### 1. SSH Config 파일 사용
`~/.ssh/config` 파일에 다음 내용 추가:
```
Host iacsgraph-tunnel
    HostName your-server-address
    User kimghw
    LocalForward 8765 localhost:8765
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

연결:
```bash
ssh iacsgraph-tunnel
```

### 2. 자동 재연결 스크립트
```bash
#!/bin/bash
# auto-tunnel.sh
while true; do
    ssh -N -L 8765:localhost:8765 kimghw@your-server-address
    echo "SSH tunnel disconnected. Reconnecting in 5 seconds..."
    sleep 5
done
```

### 3. systemd 서비스로 등록 (Linux)
`/etc/systemd/system/mcp-tunnel.service`:
```ini
[Unit]
Description=MCP SSH Tunnel
After=network.target

[Service]
Type=simple
User=your-username
ExecStart=/usr/bin/ssh -N -L 8765:localhost:8765 kimghw@your-server-address
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

서비스 시작:
```bash
sudo systemctl enable mcp-tunnel
sudo systemctl start mcp-tunnel
```

## 보안 고려사항

1. **SSH 키 인증 사용**: 비밀번호 대신 SSH 키를 사용하여 보안 강화
2. **방화벽 설정**: 서버의 8765 포트는 로컬에서만 접근 가능하도록 설정
3. **VPN 사용**: 추가적인 보안을 위해 VPN 위에서 SSH 터널 사용 고려

## 문제 해결

### 연결 실패 시
1. SSH 터널이 활성화되어 있는지 확인:
   ```bash
   ps aux | grep "ssh -L"
   ```

2. 서버의 MCP 서비스가 실행 중인지 확인:
   ```bash
   curl http://localhost:8765/health
   ```

3. 포트 충돌 확인:
   ```bash
   lsof -i :8765
   ```

### 로그 확인
서버 측에서 MCP 서버 로그 확인:
```bash
tail -f /path/to/mcp-server.log
```