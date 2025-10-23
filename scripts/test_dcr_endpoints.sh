#!/bin/bash
# DCR OAuth 엔드포인트 대화형 테스트 스크립트

set -e

SERVER_URL="${SERVER_URL:-http://localhost:8000}"
STATE_FILE="/tmp/dcr_test_state.json"

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# 상태 저장 함수
save_state() {
    local key=$1
    local value=$2

    if [ ! -f "$STATE_FILE" ]; then
        echo "{}" > "$STATE_FILE"
    fi

    python3 -c "
import json
with open('$STATE_FILE', 'r') as f:
    data = json.load(f)
data['$key'] = '$value'
with open('$STATE_FILE', 'w') as f:
    json.dump(data, f, indent=2)
"
}

# 상태 로드 함수
load_state() {
    local key=$1

    if [ ! -f "$STATE_FILE" ]; then
        echo ""
        return
    fi

    python3 -c "
import json
try:
    with open('$STATE_FILE', 'r') as f:
        data = json.load(f)
    print(data.get('$key', ''))
except:
    print('')
"
}

# 상태 초기화
reset_state() {
    rm -f "$STATE_FILE"
    echo -e "${GREEN}✅ 상태 초기화 완료${NC}"
}

# 헤더 출력
print_header() {
    clear
    echo "=========================================="
    echo -e "${CYAN}DCR OAuth Endpoints Interactive Test${NC}"
    echo "Server: $SERVER_URL"
    echo "=========================================="
    echo ""
}

# 저장된 상태 출력
print_saved_state() {
    echo -e "${BLUE}=== 저장된 상태 ===${NC}"

    local client_id=$(load_state "client_id")
    local client_secret=$(load_state "client_secret")
    local auth_code=$(load_state "auth_code")
    local access_token=$(load_state "access_token")
    local refresh_token=$(load_state "refresh_token")

    if [ -n "$client_id" ]; then
        echo -e "Client ID: ${GREEN}${client_id}${NC}"
    fi
    if [ -n "$client_secret" ]; then
        echo -e "Client Secret: ${GREEN}${client_secret:0:20}...${NC}"
    fi
    if [ -n "$auth_code" ]; then
        echo -e "Auth Code: ${GREEN}${auth_code:0:20}...${NC}"
    fi
    if [ -n "$access_token" ]; then
        echo -e "Access Token: ${GREEN}${access_token:0:20}...${NC}"
    fi
    if [ -n "$refresh_token" ]; then
        echo -e "Refresh Token: ${GREEN}${refresh_token:0:20}...${NC}"
    fi

    if [ -z "$client_id" ]; then
        echo -e "${YELLOW}(상태 없음 - 1번부터 시작하세요)${NC}"
    fi
    echo ""
}

# 1. 클라이언트 등록
test_register() {
    echo -e "${MAGENTA}[2] POST /oauth/register - Dynamic Client Registration${NC}"
    echo ""

    local request_data='{
  "client_name": "DCR Test Client",
  "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"],
  "grant_types": ["authorization_code", "refresh_token"],
  "scope": "Mail.Read User.Read"
}'

    echo -e "${YELLOW}요청:${NC}"
    echo "POST $SERVER_URL/oauth/register"
    echo "Headers:"
    echo "  Content-Type: application/json"
    echo ""
    echo "Body:"
    echo "$request_data" | python3 -m json.tool
    echo ""

    echo -e "${CYAN}요청 중...${NC}"
    response=$(curl -s -X POST "$SERVER_URL/oauth/register" \
      -H "Content-Type: application/json" \
      -d "$request_data")

    echo ""
    echo -e "${GREEN}응답:${NC}"
    echo "$response" | python3 -m json.tool
    echo ""

    # 상태 저장
    client_id=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('client_id', ''))" 2>/dev/null || echo "")
    client_secret=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('client_secret', ''))" 2>/dev/null || echo "")

    if [ -n "$client_id" ] && [ -n "$client_secret" ]; then
        save_state "client_id" "$client_id"
        save_state "client_secret" "$client_secret"
        echo -e "${GREEN}✅ Client ID와 Secret 저장됨${NC}"
    else
        echo -e "${RED}❌ 등록 실패${NC}"
    fi

    read -p "Press Enter to continue..."
}

# 2. Authorization 시작
test_authorize() {
    echo -e "${MAGENTA}[3] GET /oauth/authorize - Authorization (Azure AD 리다이렉트)${NC}"
    echo ""

    local client_id=$(load_state "client_id")

    if [ -z "$client_id" ]; then
        echo -e "${RED}❌ Client ID가 없습니다. 먼저 2번(클라이언트 등록)을 실행하세요.${NC}"
        read -p "Press Enter to continue..."
        return
    fi

    local redirect_uri="https://claude.ai/api/mcp/auth_callback"
    local scope="Mail.Read User.Read"
    local state="test_state_$(date +%s)"
    local response_type="code"

    # PKCE 생성 (선택적)
    local code_verifier=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    local code_challenge=$(python3 -c "
import hashlib, base64
verifier = '$code_verifier'
digest = hashlib.sha256(verifier.encode()).digest()
challenge = base64.urlsafe_b64encode(digest).decode().rstrip('=')
print(challenge)
")

    save_state "code_verifier" "$code_verifier"
    save_state "state" "$state"

    local auth_url="$SERVER_URL/oauth/authorize?client_id=$client_id&redirect_uri=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$redirect_uri'))")&scope=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$scope'))")&response_type=$response_type&state=$state&code_challenge=$code_challenge&code_challenge_method=S256"

    echo -e "${YELLOW}요청:${NC}"
    echo "GET $auth_url"
    echo ""
    echo "Query Parameters:"
    echo "  client_id: $client_id"
    echo "  redirect_uri: $redirect_uri"
    echo "  scope: $scope"
    echo "  state: $state"
    echo "  response_type: $response_type"
    echo "  code_challenge: ${code_challenge:0:20}..."
    echo "  code_challenge_method: S256"
    echo ""

    echo -e "${GREEN}전체 요청 URL:${NC}"
    echo "$auth_url"
    echo ""

    echo -e "${CYAN}서버에 요청 중...${NC}"
    # 서버로부터 Azure AD redirect URL 받기
    azure_redirect_url=$(curl -s -I "$auth_url" 2>/dev/null | grep -i "^location:" | sed 's/location: //i' | tr -d '\r')

    if [ -n "$azure_redirect_url" ]; then
        echo ""
        echo -e "${GREEN}✅ Azure AD 로그인 URL:${NC}"
        echo "$azure_redirect_url"
        echo ""
        echo -e "${YELLOW}⚠️  위 URL을 브라우저에서 열어 Azure AD 로그인을 진행하세요.${NC}"
        echo -e "${YELLOW}로그인 후 리다이렉트된 URL에서 'code' 파라미터 값을 복사하세요.${NC}"
        echo ""
        echo -e "${CYAN}예시:${NC}"
        echo "https://claude.ai/api/mcp/auth_callback?code=XXXXX&state=..."
        echo "                                            ^^^^^^"
    else
        echo -e "${RED}❌ Azure AD URL을 받지 못했습니다. 서버 응답을 확인하세요.${NC}"
    fi
    echo ""

    read -p "Authorization code를 입력하세요 (Enter로 건너뛰기): " auth_code

    if [ -n "$auth_code" ]; then
        save_state "auth_code" "$auth_code"
        echo -e "${GREEN}✅ Authorization code 저장됨${NC}"
    fi

    read -p "Press Enter to continue..."
}

# 3. 토큰 발급 (authorization_code)
test_token_exchange() {
    echo -e "${MAGENTA}[4] POST /oauth/token - Token Exchange (authorization_code)${NC}"
    echo ""

    local client_id=$(load_state "client_id")
    local client_secret=$(load_state "client_secret")
    local auth_code=$(load_state "auth_code")
    local code_verifier=$(load_state "code_verifier")

    if [ -z "$client_id" ] || [ -z "$client_secret" ]; then
        echo -e "${RED}❌ Client 정보가 없습니다. 먼저 2번을 실행하세요.${NC}"
        read -p "Press Enter to continue..."
        return
    fi

    if [ -z "$auth_code" ]; then
        echo -e "${RED}❌ Authorization code가 없습니다. 먼저 3번을 실행하세요.${NC}"
        read -p "Press Enter to continue..."
        return
    fi

    echo -e "${YELLOW}요청:${NC}"
    echo "POST $SERVER_URL/oauth/token"
    echo "Headers:"
    echo "  Content-Type: application/x-www-form-urlencoded"
    echo ""
    echo "Form Data:"
    echo "  grant_type: authorization_code"
    echo "  code: ${auth_code:0:20}..."
    echo "  client_id: $client_id"
    echo "  client_secret: ${client_secret:0:20}..."
    echo "  redirect_uri: https://claude.ai/api/mcp/auth_callback"
    echo "  code_verifier: ${code_verifier:0:20}..."
    echo ""

    echo -e "${CYAN}요청 중...${NC}"
    response=$(curl -s -X POST "$SERVER_URL/oauth/token" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "grant_type=authorization_code" \
      -d "code=$auth_code" \
      -d "client_id=$client_id" \
      -d "client_secret=$client_secret" \
      -d "redirect_uri=https://claude.ai/api/mcp/auth_callback" \
      -d "code_verifier=$code_verifier")

    echo ""
    echo -e "${GREEN}응답:${NC}"
    echo "$response" | python3 -m json.tool
    echo ""

    # 상태 저장
    access_token=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null || echo "")
    refresh_token=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('refresh_token', ''))" 2>/dev/null || echo "")

    if [ -n "$access_token" ] && [ -n "$refresh_token" ]; then
        save_state "access_token" "$access_token"
        save_state "refresh_token" "$refresh_token"
        echo -e "${GREEN}✅ Access Token과 Refresh Token 저장됨${NC}"
    else
        echo -e "${RED}❌ 토큰 발급 실패${NC}"
    fi

    read -p "Press Enter to continue..."
}

# 4. 토큰 갱신 (refresh_token)
test_token_refresh() {
    echo -e "${MAGENTA}[6] POST /oauth/token - Token Refresh (refresh_token)${NC}"
    echo ""

    local client_id=$(load_state "client_id")
    local client_secret=$(load_state "client_secret")
    local refresh_token=$(load_state "refresh_token")

    if [ -z "$client_id" ] || [ -z "$client_secret" ]; then
        echo -e "${RED}❌ Client 정보가 없습니다. 먼저 2번을 실행하세요.${NC}"
        read -p "Press Enter to continue..."
        return
    fi

    if [ -z "$refresh_token" ]; then
        echo -e "${RED}❌ Refresh Token이 없습니다. 먼저 4번을 실행하세요.${NC}"
        read -p "Press Enter to continue..."
        return
    fi

    echo -e "${YELLOW}요청:${NC}"
    echo "POST $SERVER_URL/oauth/token"
    echo "Headers:"
    echo "  Content-Type: application/x-www-form-urlencoded"
    echo ""
    echo "Form Data:"
    echo "  grant_type: refresh_token"
    echo "  refresh_token: ${refresh_token:0:20}..."
    echo "  client_id: $client_id"
    echo "  client_secret: ${client_secret:0:20}..."
    echo ""

    echo -e "${CYAN}요청 중...${NC}"
    response=$(curl -s -X POST "$SERVER_URL/oauth/token" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "grant_type=refresh_token" \
      -d "refresh_token=$refresh_token" \
      -d "client_id=$client_id" \
      -d "client_secret=$client_secret")

    echo ""
    echo -e "${GREEN}응답:${NC}"
    echo "$response" | python3 -m json.tool
    echo ""

    # 상태 업데이트 (rotation)
    new_access_token=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null || echo "")
    new_refresh_token=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('refresh_token', ''))" 2>/dev/null || echo "")

    if [ -n "$new_access_token" ] && [ -n "$new_refresh_token" ]; then
        save_state "access_token" "$new_access_token"
        save_state "refresh_token" "$new_refresh_token"
        echo -e "${GREEN}✅ 새로운 Access Token과 Refresh Token 저장됨 (Rotation)${NC}"
    else
        echo -e "${RED}❌ 토큰 갱신 실패${NC}"
    fi

    read -p "Press Enter to continue..."
}

# 5. MCP 서버 테스트
test_mcp_server() {
    echo -e "${MAGENTA}[5] POST /mail-query/message - MCP API 호출 (Bearer token)${NC}"
    echo ""

    local access_token=$(load_state "access_token")

    if [ -z "$access_token" ]; then
        echo -e "${RED}❌ Access Token이 없습니다. 먼저 4번을 실행하세요.${NC}"
        read -p "Press Enter to continue..."
        return
    fi

    echo -e "${YELLOW}요청:${NC}"
    echo "POST $SERVER_URL/mail-query/message"
    echo "Headers:"
    echo "  Content-Type: application/json"
    echo "  Authorization: Bearer ${access_token:0:20}..."
    echo ""
    echo "Body:"
    echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python3 -m json.tool
    echo ""

    echo -e "${CYAN}요청 중...${NC}"
    response=$(curl -s -X POST "$SERVER_URL/mail-query/message" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $access_token" \
      -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}')

    echo ""
    echo -e "${GREEN}응답 (처음 20줄):${NC}"
    echo "$response" | python3 -m json.tool | head -20
    echo "..."
    echo ""

    if echo "$response" | grep -q "result"; then
        echo -e "${GREEN}✅ MCP 서버 정상 작동${NC}"
    else
        echo -e "${RED}❌ MCP 서버 오류${NC}"
    fi

    read -p "Press Enter to continue..."
}

# 6. 메타데이터 조회
test_metadata() {
    echo -e "${MAGENTA}[1] GET /.well-known/oauth-authorization-server - Server Metadata Discovery${NC}"
    echo ""

    echo -e "${YELLOW}요청:${NC}"
    echo "GET $SERVER_URL/.well-known/oauth-authorization-server"
    echo "Headers:"
    echo "  Accept: application/json"
    echo ""

    echo -e "${CYAN}요청 중...${NC}"
    response=$(curl -s -X GET "$SERVER_URL/.well-known/oauth-authorization-server")

    echo ""
    echo -e "${GREEN}응답:${NC}"
    echo "$response" | python3 -m json.tool
    echo ""

    read -p "Press Enter to continue..."
}

# 7. 전체 플로우 자동 실행
test_full_flow() {
    echo -e "${MAGENTA}[7] 전체 플로우 자동 실행 (Claude.ai 호출 순서)${NC}"
    echo ""
    echo -e "${YELLOW}다음 순서로 테스트합니다 (Claude.ai와 동일):${NC}"
    echo "1. Server Metadata Discovery"
    echo "2. Dynamic Client Registration"
    echo "3. Authorization (Azure AD 리다이렉트)"
    echo "4. (수동) 브라우저에서 Azure 로그인 후 코드 입력"
    echo "5. Token Exchange"
    echo "6. MCP API 호출"
    echo "7. Token Refresh"
    echo ""

    # 상태 초기화
    reset_state

    # 1. Server Metadata Discovery
    echo ""
    echo -e "${BLUE}Step 1: Server Metadata Discovery${NC}"
    metadata_response=$(curl -s -X GET "$SERVER_URL/.well-known/oauth-authorization-server")
    echo "$metadata_response" | python3 -m json.tool
    echo -e "${GREEN}✅ Metadata 조회 완료${NC}"

    # 2. Dynamic Client Registration
    echo ""
    echo -e "${BLUE}Step 2: Dynamic Client Registration${NC}"
    response=$(curl -s -X POST "$SERVER_URL/oauth/register" \
      -H "Content-Type: application/json" \
      -d '{
        "client_name": "Auto Test Client",
        "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"],
        "grant_types": ["authorization_code", "refresh_token"],
        "scope": "Mail.Read User.Read"
      }')

    echo "$response" | python3 -m json.tool

    client_id=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('client_id', ''))" 2>/dev/null || echo "")
    client_secret=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('client_secret', ''))" 2>/dev/null || echo "")

    if [ -z "$client_id" ]; then
        echo -e "${RED}❌ 클라이언트 등록 실패${NC}"
        return
    fi

    save_state "client_id" "$client_id"
    save_state "client_secret" "$client_secret"
    echo -e "${GREEN}✅ 등록 완료${NC}"

    # 3. Authorization
    echo ""
    echo -e "${BLUE}Step 3: Authorization (Azure AD 리다이렉트)${NC}"

    code_verifier=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    code_challenge=$(python3 -c "
import hashlib, base64
verifier = '$code_verifier'
digest = hashlib.sha256(verifier.encode()).digest()
challenge = base64.urlsafe_b64encode(digest).decode().rstrip('=')
print(challenge)
")
    state="auto_test_$(date +%s)"

    save_state "code_verifier" "$code_verifier"
    save_state "state" "$state"

    auth_url="$SERVER_URL/oauth/authorize?client_id=$client_id&redirect_uri=https%3A%2F%2Fclaude.ai%2Fapi%2Fmcp%2Fauth_callback&scope=Mail.Read%20User.Read&response_type=code&state=$state&code_challenge=$code_challenge&code_challenge_method=S256"

    echo -e "${YELLOW}⚠️  다음 URL을 브라우저에서 열어주세요:${NC}"
    echo "$auth_url"
    echo ""

    read -p "로그인 후 받은 Authorization code를 입력하세요: " auth_code
    save_state "auth_code" "$auth_code"

    # 4. Token Exchange
    echo ""
    echo -e "${BLUE}Step 4: Token Exchange (authorization_code)${NC}"

    response=$(curl -s -X POST "$SERVER_URL/oauth/token" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "grant_type=authorization_code" \
      -d "code=$auth_code" \
      -d "client_id=$client_id" \
      -d "client_secret=$client_secret" \
      -d "redirect_uri=https://claude.ai/api/mcp/auth_callback" \
      -d "code_verifier=$code_verifier")

    echo "$response" | python3 -m json.tool

    access_token=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null || echo "")
    refresh_token=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('refresh_token', ''))" 2>/dev/null || echo "")

    if [ -z "$access_token" ]; then
        echo -e "${RED}❌ 토큰 발급 실패${NC}"
        return
    fi

    save_state "access_token" "$access_token"
    save_state "refresh_token" "$refresh_token"
    echo -e "${GREEN}✅ 토큰 발급 완료${NC}"

    # 5. MCP API 호출
    echo ""
    echo -e "${BLUE}Step 5: MCP API 호출 (Bearer token)${NC}"

    response=$(curl -s -X POST "$SERVER_URL/mail-query/message" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $access_token" \
      -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}')

    echo "$response" | python3 -m json.tool | head -20
    echo -e "${GREEN}✅ MCP API 호출 완료${NC}"

    # 6. Token Refresh
    echo ""
    echo -e "${BLUE}Step 6: Token Refresh (refresh_token)${NC}"

    response=$(curl -s -X POST "$SERVER_URL/oauth/token" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "grant_type=refresh_token" \
      -d "refresh_token=$refresh_token" \
      -d "client_id=$client_id" \
      -d "client_secret=$client_secret")

    echo "$response" | python3 -m json.tool

    new_access_token=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null || echo "")

    if [ -n "$new_access_token" ]; then
        echo -e "${GREEN}✅ 토큰 갱신 완료${NC}"
    fi

    echo ""
    echo -e "${GREEN}=========================================="
    echo "✅ 전체 플로우 테스트 완료!"
    echo "==========================================${NC}"

    read -p "Press Enter to continue..."
}

# 메인 메뉴
while true; do
    print_header
    print_saved_state

    echo -e "${CYAN}=== 테스트 메뉴 (Claude.ai 호출 순서) ===${NC}"
    echo "1. GET  /.well-known/oauth-authorization-server - Server Metadata Discovery"
    echo "2. POST /oauth/register - Dynamic Client Registration"
    echo "3. GET  /oauth/authorize - Authorization (Azure AD 리다이렉트)"
    echo "4. POST /oauth/token - Token Exchange (authorization_code)"
    echo "5. POST /mail-query/message - MCP API 호출 (Bearer token)"
    echo "6. POST /oauth/token - Token Refresh (refresh_token)"
    echo "7. 전체 플로우 자동 실행 (1→2→3→4→5→6)"
    echo ""
    echo "8. 상태 초기화"
    echo "9. 종료"
    echo ""

    read -p "선택 (1-9): " choice

    case $choice in
        1)
            test_metadata
            ;;
        2)
            test_register
            ;;
        3)
            test_authorize
            ;;
        4)
            test_token_exchange
            ;;
        5)
            test_mcp_server
            ;;
        6)
            test_token_refresh
            ;;
        7)
            test_full_flow
            ;;
        8)
            reset_state
            read -p "Press Enter to continue..."
            ;;
        9)
            echo -e "${GREEN}종료합니다.${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}잘못된 선택입니다.${NC}"
            sleep 1
            ;;
    esac
done
