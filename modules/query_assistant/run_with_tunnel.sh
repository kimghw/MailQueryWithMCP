#!/bin/bash
# Query Assistant MCP Server with Cloudflare Tunnel

# Color output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/../.."

# Try to read port from settings.json
DEFAULT_PORT=8001
if [ -f "$SCRIPT_DIR/settings.json" ]; then
    PORT=$(python3 -c "import json; print(json.load(open('$SCRIPT_DIR/settings.json'))['mcp_server']['port'])" 2>/dev/null || echo $DEFAULT_PORT)
else
    PORT=$DEFAULT_PORT
fi

echo -e "${GREEN}Using MCP Server port from settings.json: $PORT${NC}"

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo -e "${RED}cloudflared is not installed. Please install it first:${NC}"
    echo "wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"
    echo "sudo dpkg -i cloudflared-linux-amd64.deb"
    exit 1
fi

# Start MCP server in background
echo -e "${GREEN}Starting Query Assistant MCP Server on port $PORT...${NC}"
python -m modules.query_assistant.mcp_server_http_streaming &
MCP_PID=$!

# Wait for server to start
sleep 3

# Check if server is running
if ! ps -p $MCP_PID > /dev/null; then
    echo -e "${RED}Failed to start MCP server${NC}"
    exit 1
fi

echo -e "${GREEN}MCP Server started with PID: $MCP_PID${NC}"

# Start Cloudflare tunnel
echo -e "${GREEN}Starting Cloudflare Tunnel...${NC}"
echo -e "${GREEN}Creating tunnel for http://localhost:$PORT${NC}"

# Create tunnel with output redirection
cloudflared tunnel --url http://localhost:$PORT 2>&1 | tee query_assistant_tunnel.log &
TUNNEL_PID=$!

# Function to cleanup on exit
cleanup() {
    echo -e "\n${GREEN}Shutting down...${NC}"
    kill $MCP_PID 2>/dev/null
    kill $TUNNEL_PID 2>/dev/null
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM

# Wait for tunnel URL to appear in log
echo -e "${GREEN}Waiting for tunnel URL...${NC}"
URL_FOUND=false
for i in {1..60}; do
    if grep -q "trycloudflare.com" query_assistant_tunnel.log 2>/dev/null; then
        URL=$(grep -o "https://[a-z0-9-]*\.trycloudflare\.com" query_assistant_tunnel.log | tail -1)
        if [ ! -z "$URL" ]; then
            echo -e "\n${GREEN}✅ Tunnel URL: $URL${NC}"
            echo -e "${GREEN}📋 Add this URL to your Claude MCP configuration:${NC}"
            echo -e "${GREEN}   Location: ~/.config/claude/claude_desktop_config.json${NC}"
            echo -e "${GREEN}   URL: $URL${NC}"
            URL_FOUND=true
            break
        fi
    fi
    # Show progress
    if [ $((i % 3)) -eq 0 ]; then
        echo -n "."
    fi
    sleep 1
done

if [ "$URL_FOUND" = false ]; then
    echo -e "\n${YELLOW}⚠️ Tunnel URL not found in 60 seconds. Check the log:${NC}"
    echo -e "${YELLOW}   cat query_assistant_tunnel.log | grep trycloudflare${NC}"
fi

# Keep running
echo -e "${GREEN}Server and tunnel are running. Press Ctrl+C to stop.${NC}"
wait