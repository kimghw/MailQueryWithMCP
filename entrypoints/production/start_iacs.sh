#!/bin/bash
# Production Deployment Startup Script - IACS MCP Server
# For Render.com and other cloud platforms

set -e

echo "🚀 Starting Production IACS MCP HTTP Server..."

# Load uv environment
export PATH="$HOME/.cargo/bin:$PATH"

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Set Python path
export PYTHONPATH="$PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Export environment
export PORT="${PORT:-8002}"
export IACS_SERVER_PORT="$PORT"
export IACS_SERVER_HOST="0.0.0.0"

echo "📁 Project root: $PROJECT_ROOT"
echo "📍 Port: $PORT"
echo "📍 Host: 0.0.0.0"
echo ""

# Run with uv if available, otherwise use system python
if command -v uv &> /dev/null; then
    echo "Using uv to run IACS production server..."
    exec uv run python "$PROJECT_ROOT/entrypoints/production/start_iacs.py"
else
    echo "Using system python to run IACS production server..."
    exec python3 "$PROJECT_ROOT/entrypoints/production/start_iacs.py"
fi
