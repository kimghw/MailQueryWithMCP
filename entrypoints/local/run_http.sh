#!/bin/bash
# Local Development - HTTP MCP Server Launch Script

set -e

# Default values
PORT=${1:-8002}
HOST=${2:-"127.0.0.1"}

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🚀 Local Development - MCP Mail Attachment Server"
echo "=================================================="
echo "Mode: HTTP"
echo "Port: $PORT"
echo "Host: $HOST"
echo ""

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Set Python path
export PYTHONPATH="$PROJECT_ROOT"
export MCP_PORT="$PORT"
export MCP_HOST="$HOST"

cd "$PROJECT_ROOT"

# Use virtual environment if exists, otherwise use system python3
if [ -f "$PROJECT_ROOT/.venv/bin/python3" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python3"
else
    PYTHON="python3"
fi

echo "Using Python: $PYTHON"
echo "Project Root: $PROJECT_ROOT"
echo ""

# Run the HTTP server
echo "Starting server..."
$PYTHON "$PROJECT_ROOT/entrypoints/local/run_http.py" --port $PORT --host $HOST
