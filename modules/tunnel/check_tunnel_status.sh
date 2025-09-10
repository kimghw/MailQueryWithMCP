#!/bin/bash
# Cloudflare Tunnel 상태 확인 스크립트

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${BLUE}   🔍 Cloudflare Tunnel Status Check${NC}"
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

# Check if cloudflared process is running
TUNNEL_PROCESSES=$(pgrep -f "cloudflared.*tunnel" | wc -l)

if [ $TUNNEL_PROCESSES -eq 0 ]; then
    echo -e "${RED}❌ No active Cloudflare tunnels found${NC}"
    echo
    exit 1
fi

echo -e "${GREEN}✅ Found $TUNNEL_PROCESSES active tunnel(s)${NC}"
echo

# Get detailed information about each tunnel
echo -e "${BOLD}${YELLOW}Active Tunnels:${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Process each tunnel
ps aux | grep -E "cloudflared.*tunnel.*--url" | grep -v grep | while read -r line; do
    # Extract PID
    PID=$(echo "$line" | awk '{print $2}')
    
    # Extract port from command line
    PORT=$(echo "$line" | grep -oP 'localhost:\K[0-9]+')
    
    # Extract start time
    START_TIME=$(ps -o lstart= -p $PID 2>/dev/null | xargs)
    
    # Get CPU and Memory usage
    CPU=$(echo "$line" | awk '{print $3}')
    MEM=$(echo "$line" | awk '{print $4}')
    
    echo -e "${BOLD}📡 Tunnel PID: ${GREEN}$PID${NC}"
    echo -e "   • Port: ${YELLOW}$PORT${NC}"
    echo -e "   • Started: ${BLUE}$START_TIME${NC}"
    echo -e "   • CPU: ${CYAN}$CPU%${NC} | Memory: ${CYAN}$MEM%${NC}"
    
    # Try to find tunnel URL from log files
    TUNNEL_URL=""
    
    # Check various log file locations
    LOG_FILES=(
        "tunnel_output_${PORT}.log"
        "tunnel_output.log"
        "../mail_attachment/tunnel.log"
        "../query_assistant/query_assistant_tunnel.log"
        "../../tunnel_output.log"
    )
    
    for log_file in "${LOG_FILES[@]}"; do
        if [ -f "$log_file" ]; then
            URL=$(grep -o "https://[a-z0-9-]*\.trycloudflare\.com" "$log_file" 2>/dev/null | tail -1)
            if [ ! -z "$URL" ]; then
                TUNNEL_URL=$URL
                break
            fi
        fi
    done
    
    # Also check process output
    if [ -z "$TUNNEL_URL" ]; then
        # Try to get from /proc if available
        if [ -d "/proc/$PID/fd" ]; then
            TUNNEL_URL=$(strings /proc/$PID/fd/* 2>/dev/null | grep -o "https://[a-z0-9-]*\.trycloudflare\.com" | head -1)
        fi
    fi
    
    if [ ! -z "$TUNNEL_URL" ]; then
        echo -e "   • URL: ${GREEN}$TUNNEL_URL${NC}"
        
        # Check if URL is accessible
        if command -v curl &> /dev/null; then
            HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$TUNNEL_URL" 2>/dev/null)
            if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "404" ]; then
                echo -e "   • Status: ${GREEN}✓ Accessible${NC} (HTTP $HTTP_STATUS)"
            else
                echo -e "   • Status: ${YELLOW}⚠ Not accessible${NC} (HTTP $HTTP_STATUS)"
            fi
        fi
    else
        echo -e "   • URL: ${YELLOW}Not found in logs${NC}"
    fi
    
    echo -e "${CYAN}────────────────────────────────────────────────────────────────${NC}"
done

echo

# Check for MCP servers
echo -e "${BOLD}${YELLOW}Related MCP Servers:${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check mail_attachment server (port 8002)
if lsof -ti:8002 > /dev/null 2>&1; then
    PID=$(lsof -ti:8002 | head -1)
    echo -e "${GREEN}✅ Mail Attachment Server${NC} - Port 8002 (PID: $PID)"
else
    echo -e "${RED}❌ Mail Attachment Server${NC} - Port 8002 not active"
fi

# Check query_assistant server (port 8001)
if lsof -ti:8001 > /dev/null 2>&1; then
    PID=$(lsof -ti:8001 | head -1)
    echo -e "${GREEN}✅ Query Assistant Server${NC} - Port 8001 (PID: $PID)"
else
    echo -e "${RED}❌ Query Assistant Server${NC} - Port 8001 not active"
fi

echo
echo -e "${BOLD}${YELLOW}Quick Commands:${NC}"
echo -e "  • Start tunnel only:     ${CYAN}./tunnel_only.sh [port]${NC}"
echo -e "  • Kill all tunnels:      ${CYAN}pkill -f cloudflared${NC}"
echo -e "  • Kill specific tunnel:  ${CYAN}kill [PID]${NC}"
echo -e "  • View tunnel logs:      ${CYAN}tail -f tunnel_output_[port].log${NC}"
echo