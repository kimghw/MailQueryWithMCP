#!/bin/bash

# MCP HTTP Server 실행 스크립트

# Default values
PORT=${1:-8002}
HOST=${2:-"0.0.0.0"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🚀 MCP Mail Attachment Server"
echo "================================"
echo "Port: $PORT"
echo "Host: $HOST"
echo ""

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Set Python path and working directory
export PYTHONPATH="$PROJECT_ROOT"
export MCP_SETTINGS_PATH="${MCP_SETTINGS_PATH:-"$SCRIPT_DIR/config.json"}"

cd "$PROJECT_ROOT"

# Use virtual environment python if exists, otherwise use system python
if [ -f "$PROJECT_ROOT/.venv/bin/python3" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python3"
else
    PYTHON="python3"
fi

# Check if Python is available
if ! command -v $PYTHON &> /dev/null; then
    echo -e "${RED}❌ Python not found${NC}"
    exit 1
fi

echo "Using Python: $PYTHON"
echo "Project Root: $PROJECT_ROOT"
echo "Config Path: $MCP_SETTINGS_PATH"
echo ""

# Run the server
echo "Starting server..."
$PYTHON -m modules.mail_query_without_db.mcp_server.server --port $PORT --host $HOST
