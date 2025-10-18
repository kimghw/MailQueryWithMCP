#!/bin/bash
# Unified MCP HTTP Server - Production script for Render.com
# Serves multiple MCP servers on different paths:
# - /mail-query/* - Mail Query MCP Server
# - /enrollment/* - Enrollment MCP Server
# - /onenote/* - OneNote MCP Server

set -e

# Get the project root directory (2 levels up from this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Set environment variables
export PYTHONPATH="$PROJECT_ROOT"
export PYTHONDONTWRITEBYTECODE=1

# Default port (can be overridden by environment variable or command line argument)
# Render.com sets PORT automatically
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--port PORT] [--host HOST]"
            exit 1
            ;;
    esac
done

echo "=================================="
echo "🚀 Starting Unified MCP Server"
echo "=================================="
echo "📍 Server URL: http://$HOST:$PORT"
echo "📧 Mail Query: http://$HOST:$PORT/mail-query/"
echo "🔐 Enrollment: http://$HOST:$PORT/enrollment/"
echo "📝 OneNote:    http://$HOST:$PORT/onenote/"
echo "💚 Health:     http://$HOST:$PORT/health"
echo "ℹ️  Info:       http://$HOST:$PORT/info"
echo "=================================="
echo ""

# Create data directory if it doesn't exist (for SQLite databases)
mkdir -p "$PROJECT_ROOT/data"
echo "✅ Data directory: $PROJECT_ROOT/data"

# Verify environment
echo "✅ Python path: $PYTHONPATH"
echo "✅ Working directory: $(pwd)"
echo ""

# Check if required environment variables are set
if [ -z "$ENCRYPTION_KEY" ]; then
    echo "⚠️  WARNING: ENCRYPTION_KEY not set (will be auto-generated)"
fi

# Run the unified server
echo "🔥 Starting HTTP server..."
exec python3 "$PROJECT_ROOT/entrypoints/production/unified_http_server.py" \
    --host "$HOST" \
    --port "$PORT"
