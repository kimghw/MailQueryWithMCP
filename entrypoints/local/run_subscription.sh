#!/bin/bash
# Local Development - Subscription Tracker HTTP MCP Server
# HTTP-based server for local testing (NOT for Claude Desktop - use run_subscription_stdio.sh instead)

set -e

echo "🚀 Local Development - Subscription Tracker MCP Server"
echo "======================================================"
echo "Mode: HTTP"
echo "Port: 8003"
echo "Host: 127.0.0.1"
echo ""

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Set Python path
export PYTHONPATH="$PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [ -d ".venv" ]; then
    PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python3"
    echo "Using Python: $PYTHON_BIN"
else
    PYTHON_BIN="python3"
    echo "Using Python: $(which python3)"
fi

echo "Project Root: $PROJECT_ROOT"
echo ""
echo "Starting subscription tracker server..."

# Run the server
exec $PYTHON_BIN -c "
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path('$PROJECT_ROOT')
sys.path.insert(0, str(PROJECT_ROOT))

# Import and run server
from modules.subscription_tracker.mcp_server.http_server import HTTPStreamingSubscriptionServer
from modules.subscription_tracker.config import get_subscription_config

# Get configuration
config = get_subscription_config()

# Create and run server
server = HTTPStreamingSubscriptionServer(
    host=config.server_host,
    port=config.server_port
)
server.run()
"
