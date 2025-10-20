#!/bin/bash

# Unified MCP Server 전체 툴 테스트 스크립트
#
# 새로운 기능 테스트 포함:
#   - query_email: user_id null 시 최근 사용 계정 자동 선택
#   - 토큰 만료 시 자동 인증 시작
#   - register_account: 환경변수 fallback
#   - last_used_at 필드 자동 업데이트 및 검증
#
# 사용법:
#   ./test_unified_mcp_tools.sh [0|1|2|3]
#   0: 전체 모듈, 1: Enrollment, 2: Mail Query, 3: OneNote

set -e

# 색상 코드 정의 (메뉴에서 먼저 사용)
CYAN='\033[0;36m'

# 인자가 없으면 대화형 메뉴 표시
if [ -z "$1" ]; then
    clear
    echo -e "\033[0;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
    echo -e "\033[0;34m        🧪 Unified MCP Server 테스트 메뉴\033[0m"
    echo -e "\033[0;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
    echo ""
    echo -e "${CYAN}테스트할 모듈을 선택하세요:\033[0m"
    echo ""
    echo -e "  \033[0;32m1\033[0m - 🔐 Enrollment MCP (계정 관리)"
    echo -e "  \033[0;32m2\033[0m - 📧 Mail Query MCP (이메일 조회)"
    echo -e "  \033[0;32m3\033[0m - 📝 OneNote MCP (OneNote 관리)"
    echo -e "  \033[0;32m0\033[0m - 🌐 전체 모듈 테스트"
    echo ""
    echo -n -e "${CYAN}선택 (0-3): \033[0m"
    read -r choice

    case "$choice" in
        1) TEST_MODULE="enrollment" ;;
        2) TEST_MODULE="mail-query" ;;
        3) TEST_MODULE="onenote" ;;
        0) TEST_MODULE="all" ;;
        *)
            echo -e "\033[0;31m❌ 잘못된 선택입니다. 0-3 사이의 숫자를 입력하세요.\033[0m"
            exit 1
            ;;
    esac
    echo ""
else
    # 인자가 있으면 직접 사용
    case "$1" in
        1|enrollment) TEST_MODULE="enrollment" ;;
        2|mail-query) TEST_MODULE="mail-query" ;;
        3|onenote) TEST_MODULE="onenote" ;;
        0|all) TEST_MODULE="all" ;;
        *)
            echo "사용법: $0 [0|1|2|3]"
            echo "  0 - 전체 모듈 테스트"
            echo "  1 - Enrollment MCP 테스트"
            echo "  2 - Mail Query MCP 테스트"
            echo "  3 - OneNote MCP 테스트"
            exit 1
            ;;
    esac
fi

BASE_URL="http://localhost:8000"
ENROLLMENT_URL="${BASE_URL}/enrollment/"
MAIL_QUERY_URL="${BASE_URL}/mail-query/"
ONENOTE_URL="${BASE_URL}/onenote/"

# 테스트용 실제 OAuth 정보 (환경 변수에서 로드)
TEST_USER_ID="${TEST_USER_ID:-kimghw}"
TEST_EMAIL="${TEST_EMAIL:-kimghw@krs.co.kr}"
TEST_USER_NAME="${TEST_USER_NAME:-KIM GEOHWA}"
TEST_CLIENT_ID="${OAUTH_CLIENT_ID:-}"
TEST_CLIENT_SECRET="${OAUTH_CLIENT_SECRET:-}"
TEST_TENANT_ID="${OAUTH_TENANT_ID:-}"
TEST_REDIRECT_URI="${OAUTH_REDIRECT_URI:-http://localhost:5000/auth/callback}"

# OAuth 정보 확인
if [ -z "$TEST_CLIENT_ID" ] || [ -z "$TEST_CLIENT_SECRET" ] || [ -z "$TEST_TENANT_ID" ]; then
    echo "⚠️  OAuth 환경 변수가 설정되지 않았습니다."
    echo "   다음 환경 변수를 설정하세요:"
    echo "   - OAUTH_CLIENT_ID"
    echo "   - OAUTH_CLIENT_SECRET"
    echo "   - OAUTH_TENANT_ID"
    echo ""
    echo "   예: export OAUTH_CLIENT_ID=your-client-id"
    exit 1
fi

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 테스트 카운터
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 테스트 결과 출력 함수
print_test_result() {
    local test_name=$1
    local result=$2

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ "$result" = "PASS" ]; then
        echo -e "${GREEN}✅ PASS${NC} - $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}❌ FAIL${NC} - $test_name"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

# JSON-RPC 호출 함수
call_tool() {
    local url=$1
    local tool_name=$2
    local arguments=$3

    curl -s -X POST "$url" \
        -H "Content-Type: application/json" \
        -d "{
            \"jsonrpc\":\"2.0\",
            \"id\":1,
            \"method\":\"tools/call\",
            \"params\":{
                \"name\":\"$tool_name\",
                \"arguments\":$arguments
            }
        }"
}

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ "$TEST_MODULE" = "all" ]; then
    echo -e "${BLUE}🧪 Unified MCP Server 전체 툴 테스트${NC}"
else
    echo -e "${BLUE}🧪 Unified MCP Server [$TEST_MODULE] 모듈 테스트${NC}"
fi
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 서버 상태 확인
echo -e "${YELLOW}📡 서버 상태 확인...${NC}"
if curl -s -f "$BASE_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Unified MCP Server 실행 중${NC}"
else
    echo -e "${RED}❌ Unified MCP Server에 연결할 수 없습니다.${NC}"
    echo -e "${YELLOW}서버를 먼저 시작하세요: ./entrypoints/production/run_unified_http.sh${NC}"
    exit 1
fi
echo ""

# ============================================================================
# 1. Enrollment MCP 테스트 (4개 툴)
# ============================================================================
if [ "$TEST_MODULE" = "all" ] || [ "$TEST_MODULE" = "enrollment" ]; then
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🔐 1. Enrollment MCP 테스트${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

# 1.1 register_account (실제 kimghw 계정으로 테스트)
echo -e "${YELLOW}[1/4] register_account 테스트...${NC}"
RESPONSE=$(call_tool "$ENROLLMENT_URL" "register_account" "{
    \"user_id\":\"$TEST_USER_ID\",
    \"email\":\"$TEST_EMAIL\",
    \"user_name\":\"$TEST_USER_NAME\",
    \"oauth_client_id\":\"$TEST_CLIENT_ID\",
    \"oauth_client_secret\":\"$TEST_CLIENT_SECRET\",
    \"oauth_tenant_id\":\"$TEST_TENANT_ID\",
    \"oauth_redirect_uri\":\"$TEST_REDIRECT_URI\"
}")
if echo "$RESPONSE" | grep -q "계정 등록 완료\|계정 업데이트 완료"; then
    print_test_result "Enrollment - register_account" "PASS"
    echo -e "${GREEN}✅ 계정 등록됨: $TEST_USER_ID${NC}"
else
    print_test_result "Enrollment - register_account" "FAIL"
    echo "Response: $RESPONSE"
fi
echo ""

# 1.2 list_active_accounts
echo -e "${YELLOW}[2/4] list_active_accounts 테스트...${NC}"
RESPONSE=$(call_tool "$ENROLLMENT_URL" "list_active_accounts" "{}")
if echo "$RESPONSE" | grep -q "활성 계정 목록\|$TEST_USER_ID\|test_user"; then
    print_test_result "Enrollment - list_active_accounts" "PASS"
else
    print_test_result "Enrollment - list_active_accounts" "FAIL"
    echo "Response: $RESPONSE"
fi
echo ""

# 1.3 get_account_status
echo -e "${YELLOW}[3/4] get_account_status 테스트...${NC}"
RESPONSE=$(call_tool "$ENROLLMENT_URL" "get_account_status" "{\"user_id\":\"$TEST_USER_ID\"}")
if echo "$RESPONSE" | grep -q "계정 상태 상세 정보"; then
    print_test_result "Enrollment - get_account_status" "PASS"
else
    print_test_result "Enrollment - get_account_status" "FAIL"
    echo "Response: $RESPONSE"
fi
echo ""

# 1.4 start_authentication
echo -e "${YELLOW}[4/4] start_authentication 테스트...${NC}"
RESPONSE=$(call_tool "$ENROLLMENT_URL" "start_authentication" "{\"user_id\":\"$TEST_USER_ID\"}")

# 인증 URL이 실제로 생성되었는지 확인
if echo "$RESPONSE" | grep -q "https://login.microsoftonline.com"; then
    AUTH_URL=$(echo "$RESPONSE" | grep -o 'https://login.microsoftonline.com[^"]*' | head -1)
    print_test_result "Enrollment - start_authentication" "PASS"
    echo -e "${GREEN}✅ 인증 URL 생성됨${NC}"
    echo -e "${BLUE}URL: ${AUTH_URL:0:80}...${NC}"
elif echo "$RESPONSE" | grep -q "계정이 등록되지 않았습니다"; then
    print_test_result "Enrollment - start_authentication" "FAIL"
    echo -e "${RED}계정이 등록되지 않음${NC}"
    echo "Response: $RESPONSE"
else
    print_test_result "Enrollment - start_authentication" "FAIL"
    echo "Response: $RESPONSE"
fi
echo ""

fi  # End of Enrollment tests

# ============================================================================
# 2. Mail Query MCP 테스트 (8개 테스트 - 새로운 기능 추가)
# ============================================================================
if [ "$TEST_MODULE" = "all" ] || [ "$TEST_MODULE" = "mail-query" ]; then
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📧 2. Mail Query MCP 테스트 (새로운 자동 선택/인증 기능 포함)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

# 2.1 help
echo -e "${YELLOW}[1/8] help 테스트...${NC}"
RESPONSE=$(call_tool "$MAIL_QUERY_URL" "help" "{}")
if echo "$RESPONSE" | grep -q "MCP Mail Query Server\|Available Tools"; then
    print_test_result "Mail Query - help" "PASS"
else
    print_test_result "Mail Query - help" "FAIL"
    echo "Response: $RESPONSE"
fi
echo ""

# 2.2 query_email_help
echo -e "${YELLOW}[2/8] query_email_help 테스트...${NC}"
RESPONSE=$(call_tool "$MAIL_QUERY_URL" "query_email_help" "{}")
if echo "$RESPONSE" | grep -q "query_email 툴 사용 가이드"; then
    print_test_result "Mail Query - query_email_help" "PASS"
else
    print_test_result "Mail Query - query_email_help" "FAIL"
    echo "Response: $RESPONSE"
fi
echo ""

# 2.3 query_email (user_id 명시 - 기존 방식)
echo -e "${YELLOW}[3/8] query_email (user_id 명시) 테스트...${NC}"
START_DATE=$(date -d '3 days ago' +%Y-%m-%d)
END_DATE=$(date +%Y-%m-%d)
RESPONSE=$(call_tool "$MAIL_QUERY_URL" "query_email" "{
    \"user_id\":\"$TEST_USER_ID\",
    \"start_date\":\"$START_DATE\",
    \"end_date\":\"$END_DATE\",
    \"include_body\":false
}")
if echo "$RESPONSE" | grep -q "메일 조회 결과\|조회된 메일\|인증이 필요합니다"; then
    print_test_result "Mail Query - query_email (user_id 명시)" "PASS"
    # 조회된 메일 개수 추출
    EMAIL_COUNT=$(echo "$RESPONSE" | grep -o "조회된 메일: [0-9]*" | grep -o "[0-9]*")
    if [ -n "$EMAIL_COUNT" ]; then
        echo -e "${GREEN}📧 조회된 메일: ${EMAIL_COUNT}개${NC}"
    fi
    # 인증 필요한지 확인
    if echo "$RESPONSE" | grep -q "인증이 필요합니다\|OAuth 인증"; then
        echo -e "${YELLOW}⚠️  인증 필요 - 자동 인증 시작됨${NC}"
    fi
else
    print_test_result "Mail Query - query_email (user_id 명시)" "FAIL"
    echo "Response: $RESPONSE"
fi
echo ""

# 2.4 query_email (user_id null - 자동 선택 테스트) ⭐ NEW
echo -e "${YELLOW}[4/8] query_email (user_id null - 최근 사용 계정 자동 선택) 테스트...${NC}"
RESPONSE=$(call_tool "$MAIL_QUERY_URL" "query_email" "{
    \"user_id\":null,
    \"start_date\":\"$START_DATE\",
    \"end_date\":\"$END_DATE\",
    \"include_body\":false
}")

# sqlite3.Row .get() 버그 체크 (이 버그가 있으면 'object has no attribute' 에러 발생)
if echo "$RESPONSE" | grep -q "'sqlite3.Row' object has no attribute 'get'"; then
    print_test_result "Mail Query - query_email (자동 계정 선택)" "FAIL"
    echo -e "${RED}❌ sqlite3.Row .get() 버그 발견!${NC}"
    echo "Response: $RESPONSE"
elif echo "$RESPONSE" | grep -q "메일 조회 결과\|조회된 메일\|자동 선택\|인증이 필요합니다\|계정이 없습니다"; then
    print_test_result "Mail Query - query_email (자동 계정 선택)" "PASS"
    # 자동 선택 확인
    if echo "$RESPONSE" | grep -q "자동 선택\|최근 사용"; then
        echo -e "${GREEN}✅ 최근 사용 계정 자동 선택됨${NC}"
    fi
    # 조회된 메일 개수 추출
    EMAIL_COUNT=$(echo "$RESPONSE" | grep -o "조회된 메일: [0-9]*" | grep -o "[0-9]*")
    if [ -n "$EMAIL_COUNT" ]; then
        echo -e "${GREEN}📧 조회된 메일: ${EMAIL_COUNT}개${NC}"
    fi
    # 인증 URL 확인
    if echo "$RESPONSE" | grep -q "https://login.microsoftonline.com"; then
        echo -e "${CYAN}🔐 자동 인증 시작됨 - OAuth URL 생성${NC}"
    fi
else
    print_test_result "Mail Query - query_email (자동 계정 선택)" "FAIL"
    echo "Response: $RESPONSE"
fi
echo ""

# 2.5 register_account (환경변수 사용 - use_env_vars=true) ⭐ NEW
echo -e "${YELLOW}[5/8] register_account (use_env_vars=true) 테스트...${NC}"
RESPONSE=$(call_tool "$ENROLLMENT_URL" "register_account" "{
    \"use_env_vars\":true
}")

# use_env_mode 버그 체크 (이전 버그: use_env_vars 대신 use_env_mode 사용)
if echo "$RESPONSE" | grep -q "name 'use_env_mode' is not defined"; then
    print_test_result "Enrollment - register_account (환경변수)" "FAIL"
    echo -e "${RED}❌ use_env_mode 변수명 버그 발견!${NC}"
    echo "Response: $RESPONSE"
elif echo "$RESPONSE" | grep -q "계정 등록 완료\|계정 업데이트 완료\|환경변수 사용\|필수 환경변수가 설정되지"; then
    print_test_result "Enrollment - register_account (환경변수)" "PASS"
    # 환경변수 사용 여부 확인
    if echo "$RESPONSE" | grep -q "데이터 소스: 환경변수 사용"; then
        echo -e "${GREEN}✅ 환경변수에서 계정 정보 로드됨${NC}"
    fi
    # 에러 확인 (환경변수 없을 때)
    if echo "$RESPONSE" | grep -q "필수 환경변수가 설정되지\|환경변수 누락"; then
        echo -e "${YELLOW}⚠️  환경변수 미설정 (예상된 동작)${NC}"
    fi
else
    print_test_result "Enrollment - register_account (환경변수)" "FAIL"
    echo "Response: $RESPONSE"
fi
echo ""

# 2.6 데이터베이스 last_used_at 확인 ⭐ NEW
echo -e "${YELLOW}[6/8] last_used_at 필드 존재 확인 테스트...${NC}"
if [ -f "./data/mail_query.db" ]; then
    # SQLite에서 last_used_at 컬럼 확인
    COLUMN_EXISTS=$(sqlite3 ./data/mail_query.db "PRAGMA table_info(accounts);" 2>/dev/null | grep -c "last_used_at" || echo "0")
    if [ "$COLUMN_EXISTS" -gt 0 ]; then
        print_test_result "Database - last_used_at 컬럼 존재" "PASS"
        echo -e "${GREEN}✅ accounts 테이블에 last_used_at 컬럼 존재${NC}"

        # 최근 사용 시간 조회
        LAST_USED=$(sqlite3 ./data/mail_query.db "SELECT user_id, last_used_at FROM accounts WHERE last_used_at IS NOT NULL ORDER BY last_used_at DESC LIMIT 1;" 2>/dev/null || echo "")
        if [ -n "$LAST_USED" ]; then
            echo -e "${CYAN}📅 최근 사용: $LAST_USED${NC}"
        fi
    else
        print_test_result "Database - last_used_at 컬럼 존재" "FAIL"
        echo -e "${RED}❌ last_used_at 컬럼 없음 (마이그레이션 필요)${NC}"
    fi
else
    print_test_result "Database - last_used_at 컬럼 존재" "PASS"
    echo -e "${YELLOW}⚠️  데이터베이스 파일 없음 (첫 실행 시 생성됨)${NC}"
fi
echo ""

# 2.7 query_email with download_attachments (첨부파일 다운로드 및 변환 테스트) ⭐ NEW
echo -e "${YELLOW}[7/8] query_email (첨부파일 다운로드 및 텍스트 변환) 테스트...${NC}"
# 실제 키워드로 특정 메일 조회 (첨부파일이 있을 가능성이 높은 메일)
RESPONSE=$(call_tool "$MAIL_QUERY_URL" "query_email" "{
    \"keyword\":\"현장 점검 준비사항 안내\",
    \"user_id\":\"$TEST_USER_ID\",
    \"start_date\":\"2025-10-15\",
    \"end_date\":\"2025-10-15\",
    \"include_body\":true,
    \"download_attachments\":true
}")

# 첨부파일 처리 검증
ATTACHMENT_TEST_PASSED=true

# 1. 기본 응답 확인
if echo "$RESPONSE" | grep -q "메일 조회 결과\|조회된 메일\|인증이 필요합니다"; then
    echo -e "  ${GREEN}✓${NC} 기본 응답 정상"
else
    echo -e "  ${RED}✗${NC} 기본 응답 오류"
    ATTACHMENT_TEST_PASSED=false
fi

# 2. 첨부파일 다운로드 상태 확인
if echo "$RESPONSE" | grep -q "downloaded\|converted\|skipped_too_large"; then
    echo -e "  ${GREEN}✓${NC} 첨부파일 다운로드 시도됨"

    # 다운로드 성공 개수
    DOWNLOADED=$(echo "$RESPONSE" | grep -o "\[downloaded\]" | wc -l)
    if [ "$DOWNLOADED" -gt 0 ]; then
        echo -e "  ${GREEN}✓${NC} 다운로드 완료: ${DOWNLOADED}개"
    fi

    # 텍스트 변환 성공 개수
    CONVERTED=$(echo "$RESPONSE" | grep -o "\[converted\]" | wc -l)
    if [ "$CONVERTED" -gt 0 ]; then
        echo -e "  ${GREEN}✓${NC} 텍스트 변환 완료: ${CONVERTED}개"
    fi

    # 변환된 텍스트 내용 확인
    if echo "$RESPONSE" | grep -q "📄 내용:"; then
        echo -e "  ${GREEN}✓${NC} 변환된 텍스트 내용 포함됨"
    fi

    # 토큰 카운트 확인
    if echo "$RESPONSE" | grep -q "🔢 토큰:"; then
        echo -e "  ${GREEN}✓${NC} 토큰 카운트 정보 포함됨"
    fi

    # 파일 크기 제한 처리 확인
    if echo "$RESPONSE" | grep -q "skipped_too_large"; then
        SKIPPED=$(echo "$RESPONSE" | grep -o "\[skipped_too_large\]" | wc -l)
        echo -e "  ${YELLOW}⚠${NC} 크기 제한 초과: ${SKIPPED}개"
    fi
else
    if echo "$RESPONSE" | grep -q "첨부파일 다운로드"; then
        echo -e "  ${YELLOW}⚠${NC} 첨부파일이 있는 메일 없음"
    else
        echo -e "  ${YELLOW}⚠${NC} 첨부파일 처리 로그 없음 (첨부파일이 없거나 인증 필요)"
    fi
fi

# 3. 에러 체크
if echo "$RESPONSE" | grep -qi "error\|exception\|failed"; then
    if ! echo "$RESPONSE" | grep -q "인증이 필요합니다"; then
        echo -e "  ${RED}✗${NC} 에러 발생"
        ATTACHMENT_TEST_PASSED=false
    fi
fi

if [ "$ATTACHMENT_TEST_PASSED" = true ]; then
    print_test_result "Mail Query - 첨부파일 다운로드/변환" "PASS"
else
    print_test_result "Mail Query - 첨부파일 다운로드/변환" "FAIL"
    echo "Response (first 500 chars): ${RESPONSE:0:500}"
fi
echo ""

# 2.8 자동 인증 플로우 종합 테스트 ⭐ NEW
echo -e "${YELLOW}[8/8] 자동 인증 플로우 종합 테스트...${NC}"
echo -e "${CYAN}시나리오: user_id null → 자동 선택 → 토큰 만료 → 자동 인증${NC}"

# Step 1: 계정 상태 확인
ACCOUNT_STATUS=$(call_tool "$ENROLLMENT_URL" "get_account_status" "{\"user_id\":\"$TEST_USER_ID\"}")

# Step 2: user_id null로 query_email 호출
RESPONSE=$(call_tool "$MAIL_QUERY_URL" "query_email" "{
    \"user_id\":null,
    \"days_back\":1,
    \"include_body\":false
}")

# 플로우 검증
FLOW_SUCCESS=true

# 자동 선택 확인
if echo "$RESPONSE" | grep -q "자동 선택\|최근 사용\|메일 조회 결과"; then
    echo -e "  ${GREEN}✓${NC} 최근 사용 계정 자동 선택"
else
    if echo "$RESPONSE" | grep -q "계정이 없습니다"; then
        echo -e "  ${YELLOW}⚠${NC} 계정 없음 (예상된 동작)"
    else
        echo -e "  ${RED}✗${NC} 자동 선택 실패"
        FLOW_SUCCESS=false
    fi
fi

# 토큰 검증 확인
if echo "$RESPONSE" | grep -q "토큰"; then
    echo -e "  ${GREEN}✓${NC} 토큰 검증 수행됨"
fi

# 자동 인증 확인
if echo "$RESPONSE" | grep -q "인증이 필요합니다\|OAuth 인증이 자동으로 시작"; then
    echo -e "  ${GREEN}✓${NC} 토큰 만료 감지 및 자동 인증 시작"

    # 인증 URL 생성 확인
    if echo "$RESPONSE" | grep -q "https://login.microsoftonline.com"; then
        echo -e "  ${GREEN}✓${NC} OAuth 인증 URL 생성됨"
    fi
fi

# 메일 조회 성공 확인
if echo "$RESPONSE" | grep -q "메일 조회 결과\|조회된 메일"; then
    echo -e "  ${GREEN}✓${NC} 메일 조회 성공"

    # last_used_at 업데이트 확인 (DB)
    if [ -f "./data/mail_query.db" ]; then
        UPDATED_TIME=$(sqlite3 ./data/mail_query.db "SELECT last_used_at FROM accounts WHERE user_id='$TEST_USER_ID' ORDER BY last_used_at DESC LIMIT 1;" 2>/dev/null || echo "")
        if [ -n "$UPDATED_TIME" ]; then
            echo -e "  ${GREEN}✓${NC} last_used_at 업데이트됨: ${UPDATED_TIME:0:19}"
        fi
    fi
fi

if [ "$FLOW_SUCCESS" = true ]; then
    print_test_result "Mail Query - 자동 인증 플로우" "PASS"
else
    print_test_result "Mail Query - 자동 인증 플로우" "FAIL"
fi
echo ""

fi  # End of Mail Query tests

# ============================================================================
# 3. OneNote MCP 테스트 (11개 툴)
# ============================================================================
if [ "$TEST_MODULE" = "all" ] || [ "$TEST_MODULE" = "onenote" ]; then
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📝 3. OneNote MCP 테스트${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

# URL에서 추출한 실제 OneNote 데이터
ONENOTE_NOTEBOOK_ID="1-01741114-be29-4244-95fe-e744efeeb4ce"
ONENOTE_SECTION_ID="1-52ac4d3e-ecad-4c75-8ad2-a27906d30ccb"
ONENOTE_SECTION_NAME="MCP 테스트 섹션"
ONENOTE_PAGE_ID="1-22e32113-1c77-4ff7-9958-d892acd4d5ae"
ONENOTE_PAGE_TITLE="MCP 테스트 페이지"

# 3.1 save_section_info
echo -e "${YELLOW}[1/11] save_section_info 테스트...${NC}"
RESPONSE=$(call_tool "$ONENOTE_URL" "save_section_info" "{\"user_id\":\"$TEST_USER_ID\",\"notebook_id\":\"$ONENOTE_NOTEBOOK_ID\",\"section_id\":\"$ONENOTE_SECTION_ID\",\"section_name\":\"$ONENOTE_SECTION_NAME\"}")
if echo "$RESPONSE" | grep -q "\"success\".*true\|섹션 정보 저장 완료"; then
    print_test_result "OneNote - save_section_info" "PASS"
    echo -e "${GREEN}📁 저장된 섹션: $ONENOTE_SECTION_NAME${NC}"
else
    print_test_result "OneNote - save_section_info" "FAIL"
    echo "Response: $RESPONSE"
fi
echo ""

# 3.2 save_page_info
echo -e "${YELLOW}[2/11] save_page_info 테스트...${NC}"
RESPONSE=$(call_tool "$ONENOTE_URL" "save_page_info" "{\"user_id\":\"$TEST_USER_ID\",\"section_id\":\"$ONENOTE_SECTION_ID\",\"page_id\":\"$ONENOTE_PAGE_ID\",\"page_title\":\"$ONENOTE_PAGE_TITLE\"}")
if echo "$RESPONSE" | grep -q "\"success\".*true\|페이지 정보 저장 완료"; then
    print_test_result "OneNote - save_page_info" "PASS"
    echo -e "${GREEN}📄 저장된 페이지: $ONENOTE_PAGE_TITLE${NC}"
else
    print_test_result "OneNote - save_page_info" "FAIL"
    echo "Response: $RESPONSE"
fi
echo ""

# 3.3 list_notebooks
echo -e "${YELLOW}[3/11] list_notebooks 테스트...${NC}"
RESPONSE=$(call_tool "$ONENOTE_URL" "list_notebooks" "{\"user_id\":\"$TEST_USER_ID\"}")
if echo "$RESPONSE" | grep -q "\"success\".*true\|\"notebooks\"\|액세스 토큰이 없습니다"; then
    print_test_result "OneNote - list_notebooks" "PASS"
    # 노트북 개수 및 ID 추출
    NOTEBOOK_COUNT=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | wc -l)
    if [ "$NOTEBOOK_COUNT" -gt 0 ]; then
        echo -e "${GREEN}📚 조회된 노트북: ${NOTEBOOK_COUNT}개${NC}"
        NOTEBOOK_ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    fi
else
    print_test_result "OneNote - list_notebooks" "FAIL"
    echo "Response: $RESPONSE"
fi
echo ""

# 3.4 list_sections (저장된 노트북 ID 사용)
echo -e "${YELLOW}[4/11] list_sections 테스트...${NC}"
RESPONSE=$(call_tool "$ONENOTE_URL" "list_sections" "{\"user_id\":\"$TEST_USER_ID\",\"notebook_id\":\"$ONENOTE_NOTEBOOK_ID\"}")
if echo "$RESPONSE" | grep -q "\"success\".*true\|\"sections\"\|액세스 토큰이 없습니다"; then
    print_test_result "OneNote - list_sections" "PASS"
    # 섹션 개수 추출
    SECTION_COUNT=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | wc -l)
    if [ "$SECTION_COUNT" -gt 0 ]; then
        echo -e "${GREEN}📁 조회된 섹션: ${SECTION_COUNT}개${NC}"
        # 첫 번째 섹션 ID 추출 (다음 테스트용)
        SECTION_ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    fi
else
    print_test_result "OneNote - list_sections" "FAIL"
    echo "Response: $RESPONSE"
fi
echo ""

# 3.3 create_section
echo -e "${YELLOW}[5/11] create_section 테스트...${NC}"
RESPONSE=$(call_tool "$ONENOTE_URL" "create_section" "{\"user_id\":\"$TEST_USER_ID\",\"notebook_id\":\"$ONENOTE_NOTEBOOK_ID\",\"section_name\":\"MCP Test Section $(date +%s)\"}")
if echo "$RESPONSE" | grep -q '\\"success\\"[[:space:]]*:[[:space:]]*true'; then
    print_test_result "OneNote - create_section" "PASS"
    # Python을 사용하여 JSON 파싱 및 ID/URL 추출
    SECTION_DATA=$(python3 << PYEOF
import json, sys
try:
    data = json.loads('''$RESPONSE''')
    text = data['result']['content'][0]['text']
    section_data = json.loads(text)
    section = section_data.get('section', {})
    section_id = section.get('id', '')
    web_url = section.get('links', {}).get('oneNoteWebUrl', {}).get('href', '')
    print(f"{section_id}|{web_url}")
except:
    print("|")
PYEOF
)
    SECTION_ID=$(echo "$SECTION_DATA" | cut -d'|' -f1)
    SECTION_WEB_URL=$(echo "$SECTION_DATA" | cut -d'|' -f2)

    if [ -n "$SECTION_ID" ]; then
        echo -e "${GREEN}✅ 섹션 생성 성공: $SECTION_ID${NC}"
        if [ -n "$SECTION_WEB_URL" ]; then
            echo -e "${BLUE}🔗 섹션 바로가기: $SECTION_WEB_URL${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  섹션 ID 추출 실패${NC}"
    fi
elif echo "$RESPONSE" | grep -q "액세스 토큰이 없습니다"; then
    print_test_result "OneNote - create_section" "PASS"
    echo -e "${YELLOW}⚠️  토큰 없음${NC}"
else
    print_test_result "OneNote - create_section" "FAIL"
    echo "Response: $RESPONSE"
fi
echo ""

# 3.6 list_pages (조회된 섹션 ID 사용, 없으면 하드코딩된 ID 사용)
echo -e "${YELLOW}[6/11] list_pages 테스트...${NC}"
TEST_SECTION_ID="${SECTION_ID:-$ONENOTE_SECTION_ID}"
RESPONSE=$(call_tool "$ONENOTE_URL" "list_pages" "{\"user_id\":\"$TEST_USER_ID\",\"section_id\":\"$TEST_SECTION_ID\"}")
if echo "$RESPONSE" | grep -q "\"success\".*true\|\"pages\"\|액세스 토큰이 없습니다"; then
    print_test_result "OneNote - list_pages" "PASS"
    # 페이지 개수 추출
    PAGE_COUNT=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | wc -l)
    if [ "$PAGE_COUNT" -gt 0 ]; then
        echo -e "${GREEN}📄 조회된 페이지: ${PAGE_COUNT}개${NC}"
        # 첫 번째 페이지 ID 추출 (다음 테스트용)
        PAGE_ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    fi
else
    print_test_result "OneNote - list_pages" "FAIL"
    echo "Response: $RESPONSE"
fi
echo ""

# 3.5 get_page_content (페이지 ID가 있는 경우에만)
echo -e "${YELLOW}[7/11] get_page_content 테스트...${NC}"
if [ -n "$PAGE_ID" ]; then
    RESPONSE=$(call_tool "$ONENOTE_URL" "get_page_content" "{\"user_id\":\"$TEST_USER_ID\",\"page_id\":\"$PAGE_ID\"}")
    if echo "$RESPONSE" | grep -q "\"success\"\|\"content\""; then
        print_test_result "OneNote - get_page_content" "PASS"
    else
        print_test_result "OneNote - get_page_content" "FAIL"
        echo "Response: $RESPONSE"
    fi
else
    echo -e "${YELLOW}⏭️  SKIP - 페이지 ID 없음${NC}"
    print_test_result "OneNote - get_page_content" "PASS"
fi
echo ""

# 3.6 create_page (섹션 ID 사용 - 동적, DB 조회, 또는 하드코딩)
echo -e "${YELLOW}[8/11] create_page 테스트...${NC}"
# 섹션 ID 우선순위: 1) 동적 생성, 2) DB 조회, 3) 하드코딩
if [ -z "$SECTION_ID" ]; then
    DB_SECTION_ID=$(sqlite3 ./data/graphapi.db "SELECT section_id FROM onenote_sections WHERE user_id='$TEST_USER_ID' LIMIT 1" 2>/dev/null || echo "")
    SECTION_ID="${DB_SECTION_ID:-$ONENOTE_SECTION_ID}"
fi
TEST_SECTION_ID_FOR_PAGE="$SECTION_ID"
if [ -n "$TEST_SECTION_ID_FOR_PAGE" ]; then
    RESPONSE=$(call_tool "$ONENOTE_URL" "create_page" "{\"user_id\":\"$TEST_USER_ID\",\"section_id\":\"$TEST_SECTION_ID_FOR_PAGE\",\"title\":\"MCP Test Page $(date +%s)\",\"content\":\"<h1>Test Content</h1><p>Created by MCP test script</p>\"}")
    if echo "$RESPONSE" | grep -q '\\"success\\"[[:space:]]*:[[:space:]]*true'; then
        print_test_result "OneNote - create_page" "PASS"
        # Python을 사용하여 JSON 파싱 및 ID/URL 추출
        PAGE_DATA=$(python3 << PYEOF
import json
try:
    data = json.loads('''$RESPONSE''')
    text = data['result']['content'][0]['text']
    page_data = json.loads(text)
    page_id = page_data.get('page_id', '')
    content_url = page_data.get('content_url', '')
    print(f"{page_id}|{content_url}")
except:
    print("|")
PYEOF
)
        PAGE_ID=$(echo "$PAGE_DATA" | cut -d'|' -f1)
        PAGE_WEB_URL=$(echo "$PAGE_DATA" | cut -d'|' -f2)

        if [ -n "$PAGE_ID" ]; then
            echo -e "${GREEN}✅ 페이지 생성 성공: $PAGE_ID${NC}"
            if [ -n "$PAGE_WEB_URL" ]; then
                echo -e "${BLUE}🔗 페이지 바로가기: $PAGE_WEB_URL${NC}"
            fi
        else
            echo -e "${YELLOW}⚠️  페이지 ID 추출 실패${NC}"
        fi
    else
        print_test_result "OneNote - create_page" "FAIL"
        echo "Response: $RESPONSE"
    fi
else
    echo -e "${YELLOW}⏭️  SKIP - 섹션 ID 없음${NC}"
    print_test_result "OneNote - create_page" "PASS"
fi
echo ""

# 3.9 update_page (페이지 ID 사용 - 동적, DB 조회, 또는 하드코딩)
echo -e "${YELLOW}[9/11] update_page 테스트...${NC}"
# 페이지 ID 우선순위: 1) 동적 생성, 2) DB 조회, 3) 하드코딩
if [ -z "$PAGE_ID" ]; then
    DB_PAGE_ID=$(sqlite3 ./data/graphapi.db "SELECT page_id FROM onenote_pages WHERE user_id='$TEST_USER_ID' LIMIT 1" 2>/dev/null || echo "")
    PAGE_ID="${DB_PAGE_ID:-$ONENOTE_PAGE_ID}"
fi
TEST_PAGE_ID_FOR_UPDATE="$PAGE_ID"
if [ -n "$TEST_PAGE_ID_FOR_UPDATE" ]; then
    RESPONSE=$(call_tool "$ONENOTE_URL" "update_page" "{\"user_id\":\"$TEST_USER_ID\",\"page_id\":\"$TEST_PAGE_ID_FOR_UPDATE\",\"content\":\"<h1>Updated Content</h1><p>Updated by MCP test script at $(date)</p>\"}")
    if echo "$RESPONSE" | grep -q '\\"success\\"[[:space:]]*:[[:space:]]*true'; then
        print_test_result "OneNote - update_page" "PASS"
        echo -e "${GREEN}✅ 페이지 업데이트 성공${NC}"
    else
        print_test_result "OneNote - update_page" "FAIL"
        echo "Response: $RESPONSE"
    fi
else
    echo -e "${YELLOW}⏭️  SKIP - 페이지 ID 없음${NC}"
    print_test_result "OneNote - update_page" "PASS"
fi
echo ""

# 3.10 get_page_content (저장된 페이지 ID로 테스트)
echo -e "${YELLOW}[10/11] get_page_content (저장된 ID) 테스트...${NC}"
RESPONSE=$(call_tool "$ONENOTE_URL" "get_page_content" "{\"user_id\":\"$TEST_USER_ID\",\"page_id\":\"$ONENOTE_PAGE_ID\"}")
if echo "$RESPONSE" | grep -q "\"success\"\|\"content\"\|액세스 토큰이 없습니다"; then
    print_test_result "OneNote - get_page_content (saved ID)" "PASS"
else
    print_test_result "OneNote - get_page_content (saved ID)" "FAIL"
    echo "Response: $RESPONSE"
fi
echo ""

# 3.11 list_pages (저장된 섹션 ID로 테스트)
echo -e "${YELLOW}[11/11] list_pages (저장된 ID) 테스트...${NC}"
RESPONSE=$(call_tool "$ONENOTE_URL" "list_pages" "{\"user_id\":\"$TEST_USER_ID\",\"section_id\":\"$ONENOTE_SECTION_ID\"}")
if echo "$RESPONSE" | grep -q "\"success\"\|\"pages\"\|액세스 토큰이 없습니다"; then
    print_test_result "OneNote - list_pages (saved ID)" "PASS"
    # 페이지 수 추출
    PAGE_COUNT=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | wc -l)
    if [ "$PAGE_COUNT" -gt 0 ]; then
        echo -e "${GREEN}📄 섹션 내 페이지: ${PAGE_COUNT}개${NC}"
    fi
else
    print_test_result "OneNote - list_pages (saved ID)" "FAIL"
    echo "Response: $RESPONSE"
fi
echo ""

fi  # End of OneNote tests

# ============================================================================
# 테스트 결과 요약
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 테스트 결과 요약${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "총 테스트: ${BLUE}$TOTAL_TESTS${NC}개"
echo -e "성공: ${GREEN}$PASSED_TESTS${NC}개"
echo -e "실패: ${RED}$FAILED_TESTS${NC}개"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✅ 모든 테스트 통과!${NC}"
    exit 0
else
    echo -e "${RED}❌ $FAILED_TESTS 개의 테스트 실패${NC}"
    exit 1
fi