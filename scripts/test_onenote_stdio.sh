#!/bin/bash

# OneNote MCP stdio 서버 테스트 스크립트 (with gRPC wrapper)

set -e

# 색상 코드
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 프로젝트 루트 경로
PROJECT_ROOT="/home/kimghw/MailQueryWithMCP"
PYTHONPATH="$PROJECT_ROOT"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}OneNote MCP stdio 서버 테스트 (gRPC)${NC}"
echo -e "${GREEN}========================================${NC}"

# 1. stdio 서버 백그라운드 실행
echo -e "\n${YELLOW}[1] stdio 서버 실행 중...${NC}"
PYTHONPATH=$PYTHONPATH timeout 60 python $PROJECT_ROOT/modules/onenote_mcp/entrypoints/stdio_server.py &
SERVER_PID=$!

echo -e "${GREEN}✅ stdio 서버 시작 (PID: $SERVER_PID)${NC}"

# 2. stdio 서버 준비 대기
sleep 2

# 3. gRPC를 통한 테스트 요청 전송
echo -e "\n${YELLOW}[2] gRPC 테스트 요청 전송${NC}"

# 3.1 list_tools 요청
echo -e "\n${YELLOW}[3.1] list_tools 요청...${NC}"
cat <<'EOF' | grpcurl -plaintext -d @ localhost:50051 mcp.MCPService/CallTool
{
  "method": "tools/list",
  "params": {}
}
EOF

# 3.2 list_notebooks 요청
echo -e "\n${YELLOW}[3.2] list_notebooks 요청...${NC}"
cat <<'EOF' | grpcurl -plaintext -d @ localhost:50051 mcp.MCPService/CallTool
{
  "method": "tools/call",
  "params": {
    "name": "list_notebooks",
    "arguments": {
      "user_id": "kimghw"
    }
  }
}
EOF

# 4. 서버 종료
echo -e "\n${YELLOW}[4] 서버 종료 중...${NC}"
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 테스트 완료${NC}"
echo -e "${GREEN}========================================${NC}"
