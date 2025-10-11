#!/bin/bash

# MCP Server with Cloudflare Tunnel
# 로컬 MCP 서버를 Cloudflare Tunnel을 통해 외부에 노출

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 기본값
PORT=${1:-8002}
HOST="localhost"

echo -e "${BLUE}🚀 MCP Server with Cloudflare Tunnel${NC}"
echo "================================"

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Set environment
export PYTHONPATH="$PROJECT_ROOT"
export MCP_SETTINGS_PATH="${MCP_SETTINGS_PATH:-"$SCRIPT_DIR/config.json"}"
cd "$PROJECT_ROOT"

# Python 확인
if [ -f "$PROJECT_ROOT/.venv/bin/python3" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python3"
else
    PYTHON="python3"
fi

echo -e "${GREEN}✓${NC} Project Root: $PROJECT_ROOT"
echo -e "${GREEN}✓${NC} Python: $PYTHON"
echo -e "${GREEN}✓${NC} Port: $PORT"

# Cloudflare Tunnel 설치 확인
if ! command -v cloudflared &> /dev/null; then
    echo -e "${YELLOW}⚠${NC} cloudflared not found. Installing..."
    
    if command -v wget &> /dev/null; then
        wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
        sudo dpkg -i cloudflared-linux-amd64.deb
        rm cloudflared-linux-amd64.deb
    else
        echo -e "${RED}✗${NC} wget not found. Please install cloudflared manually."
        exit 1
    fi
fi

# MCP 서버 시작
echo ""
echo -e "${BLUE}Starting MCP Server...${NC}"
$PYTHON -m modules.mail_query_without_db.mcp_server.server --port $PORT --host $HOST &
SERVER_PID=$!

# 서버 시작 대기
sleep 3

# 서버 확인
if ! ps -p $SERVER_PID > /dev/null; then
    echo -e "${RED}✗${NC} Server failed to start"
    exit 1
fi

echo -e "${GREEN}✓${NC} Server started (PID: $SERVER_PID)"

# Cloudflare Tunnel 시작
echo ""
echo -e "${BLUE}Starting Cloudflare Tunnel...${NC}"
TUNNEL_LOG="$PROJECT_ROOT/tunnel_output_${PORT}.log"
cloudflared tunnel --url http://$HOST:$PORT > "$TUNNEL_LOG" 2>&1 &
TUNNEL_PID=$!

# Tunnel URL 대기
echo "Waiting for tunnel URL..."
sleep 5

# Tunnel URL 추출
TUNNEL_URL=""
for i in {1..10}; do
    if [ -f "$TUNNEL_LOG" ]; then
        TUNNEL_URL=$(grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com' "$TUNNEL_LOG" | tail -1)
        if [ -n "$TUNNEL_URL" ]; then
            break
        fi
    fi
    sleep 1
done

if [ -z "$TUNNEL_URL" ]; then
    echo -e "${RED}✗${NC} Failed to get tunnel URL"
    kill $SERVER_PID $TUNNEL_PID 2>/dev/null
    exit 1
fi

# 결과 출력
echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}✓ MCP Server is running!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "Local:     ${BLUE}http://$HOST:$PORT${NC}"
echo -e "Tunnel:    ${BLUE}$TUNNEL_URL${NC}"
echo ""
echo -e "Server PID:  $SERVER_PID"
echo -e "Tunnel PID:  $TUNNEL_PID"
echo -e "Tunnel Log:  $TUNNEL_LOG"
echo ""
echo -e "Press ${YELLOW}Ctrl+C${NC} to stop both server and tunnel"

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping server and tunnel...${NC}"
    kill $SERVER_PID $TUNNEL_PID 2>/dev/null
    echo -e "${GREEN}✓${NC} Stopped"
    exit 0
}

trap cleanup INT TERM

# Wait
wait $SERVER_PID
