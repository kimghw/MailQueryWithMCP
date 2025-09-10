#!/bin/bash
# 간단한 터널 상태 확인

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔍 Cloudflare Tunnel Status"
echo "=========================="

# Check running tunnels
TUNNELS=$(ps aux | grep -E "cloudflared.*tunnel.*--url" | grep -v grep)

if [ -z "$TUNNELS" ]; then
    echo -e "${RED}No active tunnels${NC}"
    exit 1
fi

# Parse each tunnel
echo "$TUNNELS" | while read -r line; do
    PID=$(echo "$line" | awk '{print $2}')
    PORT=$(echo "$line" | grep -oP 'localhost:\K[0-9]+')
    
    # Find URL from logs
    URL=""
    for log in tunnel_output_${PORT}.log tunnel_output.log ../*/tunnel*.log ../../tunnel*.log; do
        if [ -f "$log" ]; then
            found_url=$(grep -o "https://[a-z0-9-]*\.trycloudflare\.com" "$log" 2>/dev/null | tail -1)
            if [ ! -z "$found_url" ]; then
                URL=$found_url
                break
            fi
        fi
    done
    
    echo -e "${GREEN}✓${NC} Port $PORT (PID: $PID)"
    if [ ! -z "$URL" ]; then
        echo "  URL: $URL"
    fi
done