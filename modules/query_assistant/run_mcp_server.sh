#!/bin/bash
# Query Assistant MCP Server (without tunnel)

# Color output
GREEN='\033[0;32m'
NC='\033[0m'

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/../.."

# Log file
LOG_FILE="query_assistant_mcp_server.log"

echo -e "${GREEN}Starting Query Assistant MCP Server...${NC}"
echo -e "${GREEN}Port: 8001${NC}"
echo -e "${GREEN}Log file: $LOG_FILE${NC}"

# Start the MCP HTTP Streaming server
python -m modules.query_assistant.mcp_server_http_streaming 2>&1 | tee "$LOG_FILE"