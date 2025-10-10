#!/bin/bash

# MCP Mail Attachment Server 실행 스크립트

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
PORT=${MCP_PORT:-8002}  # Use environment variable or default
RUN_TUNNEL=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--tunnel)
            RUN_TUNNEL=true
            shift
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -t, --tunnel    Run with Cloudflare tunnel"
            echo "  -p, --port      Specify port (default: ${MCP_PORT:-8002})"
            echo "  -h, --help      Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}🚀 Starting MCP Mail Attachment Server...${NC}"
echo -e "${BLUE}Server will run on port ${PORT}${NC}"

# Set Python path and settings path
export PYTHONPATH=/home/kimghw/IACSGRAPH
export MCP_SETTINGS_PATH=${MCP_SETTINGS_PATH:-"/home/kimghw/IACSGRAPH/modules/mail_query_without_db/settings.json"}

# Change to project directory
cd /home/kimghw/IACSGRAPH

if [ "$RUN_TUNNEL" = true ]; then
    echo -e "${YELLOW}📡 Running with Cloudflare tunnel enabled${NC}"
    echo "================================================================="
    
    # Check if cloudflared is installed
    if ! command -v cloudflared &> /dev/null; then
        echo -e "${RED}❌ Error: cloudflared is not installed${NC}"
        echo "Please install cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation"
        exit 1
    fi
    
    # Start MCP server in background
    echo -e "${GREEN}Starting MCP server on port ${PORT}...${NC}"
    python -m modules.mail_query_without_db.mcp_server_mail_attachment &
    SERVER_PID=$!
    
    # Wait for server to start
    echo -e "${BLUE}Waiting for server to start...${NC}"
    sleep 3
    
    # Check if server is running
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        echo -e "${RED}❌ Failed to start MCP server${NC}"
        exit 1
    fi
    
    # Start cloudflare tunnel
    echo -e "${GREEN}Starting Cloudflare tunnel...${NC}"
    echo "================================================================="
    cloudflared tunnel --url http://localhost:${PORT} &
    TUNNEL_PID=$!
    
    # Function to cleanup on exit
    cleanup() {
        echo -e "\n${YELLOW}Shutting down...${NC}"
        if [ ! -z "$TUNNEL_PID" ]; then
            kill $TUNNEL_PID 2>/dev/null
            echo -e "${BLUE}✓ Cloudflare tunnel stopped${NC}"
        fi
        if [ ! -z "$SERVER_PID" ]; then
            kill $SERVER_PID 2>/dev/null
            echo -e "${BLUE}✓ MCP server stopped${NC}"
        fi
        exit 0
    }
    
    # Set trap for cleanup
    trap cleanup SIGINT SIGTERM
    
    # Wait for tunnel to start and show URL
    echo -e "${YELLOW}Waiting for tunnel URL...${NC}"
    sleep 5
    
    echo "================================================================="
    echo -e "${GREEN}✅ MCP Server is running with Cloudflare tunnel${NC}"
    echo -e "${BLUE}Local URL: http://localhost:${PORT}${NC}"
    echo -e "${YELLOW}Check the Cloudflare tunnel output above for your public URL${NC}"
    echo "================================================================="
    echo -e "${RED}Press Ctrl+C to stop both server and tunnel${NC}"
    
    # Wait for both processes
    wait $SERVER_PID $TUNNEL_PID
    
else
    # Run without tunnel
    echo "================================================================="
    echo -e "${GREEN}✅ Starting MCP server locally on port ${PORT}${NC}"
    echo -e "${BLUE}URL: http://localhost:${PORT}${NC}"
    echo -e "${YELLOW}To run with Cloudflare tunnel, use: $0 --tunnel${NC}"
    echo "================================================================="
    echo -e "${RED}Press Ctrl+C to stop${NC}"
    
    # Run the server
    python -m modules.mail_query_without_db.mcp_server_mail_attachment
fi