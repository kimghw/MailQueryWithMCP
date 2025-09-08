#!/bin/bash

# MCP Mail Attachment Server with Cloudflare Tunnel
# 서버와 터널을 함께 실행하고 URL을 보기 좋게 표시

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

PORT=8002

echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${GREEN}   📧 MCP Mail Attachment Server - Cloudflare Tunnel${NC}"
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

# Check cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo -e "${RED}❌ cloudflared가 설치되지 않았습니다.${NC}"
    echo -e "${YELLOW}설치 방법: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation${NC}"
    exit 1
fi

# Set environment
export PYTHONPATH=/home/kimghw/IACSGRAPH
cd /home/kimghw/IACSGRAPH

# Start MCP server
echo -e "${BLUE}1️⃣  MCP 서버 시작 중... (포트: ${PORT})${NC}"
python -m modules.mail_attachment.mcp_server_mail_attachment > mcp_server.log 2>&1 &
SERVER_PID=$!

# Wait for server
sleep 3

# Check if server is running
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo -e "${RED}❌ MCP 서버 시작 실패${NC}"
    cat mcp_server.log
    exit 1
fi

echo -e "${GREEN}✅ MCP 서버 실행 중 (PID: $SERVER_PID)${NC}"
echo

# Start Cloudflare tunnel and capture output
echo -e "${BLUE}2️⃣  Cloudflare 터널 생성 중...${NC}"
TUNNEL_LOG="tunnel_output.log"
# Use stdbuf to disable buffering
stdbuf -oL -eL cloudflared tunnel --url http://localhost:${PORT} 2>&1 | tee $TUNNEL_LOG &
TUNNEL_PID=$!

# Wait for tunnel URL
echo -e "${YELLOW}   터널 URL 대기 중...${NC}"
COUNTER=0
TUNNEL_URL=""

while [ $COUNTER -lt 30 ]; do
    if [ -f $TUNNEL_LOG ]; then
        URL=$(grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com' $TUNNEL_LOG | head -1)
        if [ ! -z "$URL" ]; then
            TUNNEL_URL=$URL
            break
        fi
    fi
    sleep 1
    COUNTER=$((COUNTER + 1))
    echo -n "."
done

echo
echo

if [ -z "$TUNNEL_URL" ]; then
    echo -e "${RED}❌ 터널 URL을 찾을 수 없습니다${NC}"
    cat $TUNNEL_LOG
    kill $SERVER_PID 2>/dev/null
    kill $TUNNEL_PID 2>/dev/null
    exit 1
fi

# Display success info
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${GREEN}✨ 서버가 성공적으로 시작되었습니다!${NC}"
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo
echo -e "${CYAN}📍 접속 정보:${NC}"
echo -e "${BOLD}   🌐 Public URL: ${YELLOW}$TUNNEL_URL${NC}"
echo -e "${BOLD}   🏠 Local URL:  ${BLUE}http://localhost:${PORT}${NC}"
echo
echo -e "${CYAN}🔍 테스트 URL:${NC}"
echo -e "   Health: ${YELLOW}${TUNNEL_URL}/health${NC}"
echo -e "   Info:   ${YELLOW}${TUNNEL_URL}/info${NC}"
echo
echo -e "${CYAN}🤖 Claude.ai 설정:${NC}"
echo -e "   1. Claude.ai에서 MCP 서버 추가"
echo -e "   2. URL에 ${YELLOW}$TUNNEL_URL${NC} 입력"
echo -e "   3. 연결 확인 후 사용"
echo
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}종료하려면 Ctrl+C를 누르세요${NC}"
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Cleanup function
cleanup() {
    echo
    echo -e "${YELLOW}🛑 종료 중...${NC}"
    kill $TUNNEL_PID 2>/dev/null && echo -e "${BLUE}   ✓ 터널 종료${NC}"
    kill $SERVER_PID 2>/dev/null && echo -e "${BLUE}   ✓ 서버 종료${NC}"
    rm -f $TUNNEL_LOG mcp_server.log 2>/dev/null
    echo -e "${GREEN}✅ 정상 종료되었습니다${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Keep running
while kill -0 $SERVER_PID 2>/dev/null && kill -0 $TUNNEL_PID 2>/dev/null; do
    sleep 1
done