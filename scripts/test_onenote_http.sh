#!/bin/bash

# OneNote MCP HTTP 서버 테스트 스크립트 (curl)

set -e

# 색상 코드
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 서버 주소
SERVER_URL="http://localhost:8003"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}OneNote MCP HTTP 서버 테스트${NC}"
echo -e "${GREEN}========================================${NC}"

# 1. Health Check
echo -e "\n${YELLOW}[1] Health Check${NC}"
curl -s "$SERVER_URL/health" | jq '.'

# 2. List Tools
echo -e "\n${YELLOW}[2] List Tools${NC}"
curl -s "$SERVER_URL/api/tools" | jq '.tools[] | {name: .name, description: .description}'

# 3. List Notebooks
echo -e "\n${YELLOW}[3] List Notebooks (user_id: kimghw)${NC}"
curl -s -X POST "$SERVER_URL/api/list_notebooks" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "kimghw"}' | jq '.'

# 4. Register Account (인증 도구 테스트)
echo -e "\n${YELLOW}[4] Register Account (Auth Tool)${NC}"
curl -s -X POST "$SERVER_URL/api/tool/register_account" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "email": "test@example.com",
    "oauth_client_id": "test_client_id",
    "oauth_client_secret": "test_secret",
    "oauth_tenant_id": "test_tenant_id"
  }' | jq '.'

# 5. Get Account Status
echo -e "\n${YELLOW}[5] Get Account Status${NC}"
curl -s -X POST "$SERVER_URL/api/tool/get_account_status" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "kimghw"}' | jq '.'

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 테스트 완료${NC}"
echo -e "${GREEN}========================================${NC}"
