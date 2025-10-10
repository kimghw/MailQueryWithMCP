#!/bin/bash
# MCP Server Log Monitor Script

echo "🔍 MCP Server Log Monitor"
echo "========================="

# 로그 디렉토리 확인
LOG_DIR="logs"
if [ ! -d "$LOG_DIR" ]; then
    echo "❌ Log directory not found: $LOG_DIR"
    echo "   Please run the MCP server first to generate logs."
    exit 1
fi

# 최근 에러 확인
echo -e "\n📛 Recent Errors:"
if [ -f "$LOG_DIR/mcp_stdio.log" ]; then
    grep "ERROR" "$LOG_DIR/mcp_stdio.log" 2>/dev/null | tail -5 || echo "  No errors found"
else
    echo "  Log file not found: $LOG_DIR/mcp_stdio.log"
fi

# 활성 계정 상태
echo -e "\n👤 Account Status:"
if [ -f "$LOG_DIR/mcp_stdio.log" ]; then
    grep "Active accounts" "$LOG_DIR/mcp_stdio.log" 2>/dev/null | tail -1 || echo "  No account status found"
else
    echo "  Log file not found"
fi

# 최근 도구 호출
echo -e "\n🔧 Recent Tool Calls:"
HANDLER_LOG=$(ls $LOG_DIR/*handlers.log 2>/dev/null | head -1)
if [ -n "$HANDLER_LOG" ]; then
    grep "call_tool" "$HANDLER_LOG" 2>/dev/null | tail -5 || echo "  No tool calls found"
else
    echo "  Handler log not found"
fi

# 로그 통계
echo -e "\n📊 Log Level Statistics:"
if [ -f "$LOG_DIR/mcp_stdio.log" ]; then
    for level in DEBUG INFO WARNING ERROR CRITICAL; do
        count=$(grep -c "$level" "$LOG_DIR/mcp_stdio.log" 2>/dev/null || echo "0")
        printf "  %-10s: %s\n" "$level" "$count"
    done
else
    echo "  Log file not found"
fi

# 실시간 모니터링 옵션
echo -e "\n"
read -p "Start live monitoring? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📊 Live Monitoring (Ctrl+C to stop):"
    echo "===================================="
    tail -f $LOG_DIR/*.log 2>/dev/null | grep -E "(ERROR|WARNING|✅|❌|call_tool|Active accounts)"
fi