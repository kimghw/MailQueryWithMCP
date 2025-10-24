#!/bin/bash
# OneDrive MCP Tools 테스트 스크립트

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

BASE_URL="${1:-http://localhost:8000}"
USER_ID="${2:-test_user}"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}OneDrive MCP Tools 테스트${NC}"
echo -e "${BLUE}================================${NC}"
echo ""
echo "Base URL: $BASE_URL"
echo "User ID: $USER_ID"
echo ""

# 1. Initialize MCP Session
echo -e "${GREEN}1. MCP 세션 초기화${NC}"
INIT_RESPONSE=$(curl -s -X POST "$BASE_URL/onedrive/" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-06-18",
      "capabilities": {},
      "clientInfo": {
        "name": "test-client",
        "version": "1.0.0"
      }
    }
  }')

echo "$INIT_RESPONSE" | jq '.'
echo ""

# 2. List Tools
echo -e "${GREEN}2. 사용 가능한 툴 목록 조회${NC}"
TOOLS_RESPONSE=$(curl -s -X POST "$BASE_URL/onedrive/" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }')

echo "$TOOLS_RESPONSE" | jq '.result.tools[] | {name: .name, description: .description}'
echo ""

# 3. List Files (Root)
echo -e "${GREEN}3. 루트 폴더 파일 목록 조회${NC}"
LIST_ROOT_RESPONSE=$(curl -s -X POST "$BASE_URL/onedrive/" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "list_files",
      "arguments": {
        "user_id": "'$USER_ID'"
      }
    }
  }')

echo "$LIST_ROOT_RESPONSE" | jq '.'
echo ""

# 4. List Files (Documents folder)
echo -e "${GREEN}4. Documents 폴더 파일 목록 조회${NC}"
LIST_DOCS_RESPONSE=$(curl -s -X POST "$BASE_URL/onedrive/" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "list_files",
      "arguments": {
        "user_id": "'$USER_ID'",
        "folder_path": "Documents"
      }
    }
  }')

echo "$LIST_DOCS_RESPONSE" | jq '.'
echo ""

# 5. Search Files
echo -e "${GREEN}5. 파일 검색 (검색어: test)${NC}"
SEARCH_RESPONSE=$(curl -s -X POST "$BASE_URL/onedrive/" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 5,
    "method": "tools/call",
    "params": {
      "name": "list_files",
      "arguments": {
        "user_id": "'$USER_ID'",
        "search": "test"
      }
    }
  }')

echo "$SEARCH_RESPONSE" | jq '.'
echo ""

# 6. Create Folder
echo -e "${GREEN}6. 테스트 폴더 생성${NC}"
CREATE_FOLDER_RESPONSE=$(curl -s -X POST "$BASE_URL/onedrive/" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 6,
    "method": "tools/call",
    "params": {
      "name": "create_folder",
      "arguments": {
        "user_id": "'$USER_ID'",
        "folder_path": "TestFolder"
      }
    }
  }')

echo "$CREATE_FOLDER_RESPONSE" | jq '.'
echo ""

# 7. Write File
echo -e "${GREEN}7. 테스트 파일 생성${NC}"
WRITE_FILE_RESPONSE=$(curl -s -X POST "$BASE_URL/onedrive/" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 7,
    "method": "tools/call",
    "params": {
      "name": "write_file",
      "arguments": {
        "user_id": "'$USER_ID'",
        "file_path": "TestFolder/test.txt",
        "content": "Hello from OneDrive MCP!"
      }
    }
  }')

echo "$WRITE_FILE_RESPONSE" | jq '.'
echo ""

# 8. Read File
echo -e "${GREEN}8. 테스트 파일 읽기${NC}"
READ_FILE_RESPONSE=$(curl -s -X POST "$BASE_URL/onedrive/" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 8,
    "method": "tools/call",
    "params": {
      "name": "read_file",
      "arguments": {
        "user_id": "'$USER_ID'",
        "file_path": "TestFolder/test.txt"
      }
    }
  }')

echo "$READ_FILE_RESPONSE" | jq '.'
echo ""

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}테스트 완료${NC}"
echo -e "${BLUE}================================${NC}"
