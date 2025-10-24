#!/bin/bash
# JSON-RPC 테스트 러너 - 완전 인터랙티브 모드

set -e

# 스크립트 위치 기준으로 프로젝트 루트 찾기
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# venv 확인
check_venv() {
    if [ ! -d "$VENV_PATH" ]; then
        echo -e "${RED}❌ Virtual environment를 찾을 수 없습니다: $VENV_PATH${NC}" >&2
        echo -e "${YELLOW}💡 다음 명령으로 venv를 생성하세요:${NC}" >&2
        echo "   cd $PROJECT_ROOT" >&2
        echo "   python3 -m venv .venv" >&2
        echo "   source .venv/bin/activate" >&2
        echo "   pip install -r requirements.txt" >&2
        exit 1
    fi
}

# 헤더 출력
print_header() {
    local title="$1"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" >&2
    echo -e "${BOLD}${GREEN}  $title${NC}" >&2
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" >&2
    echo "" >&2
}

# 모듈 선택 메뉴
select_module() {
    print_header "📦 모듈 선택"

    echo -e "${YELLOW}  [1]${NC} enrollment  - Enrollment MCP 테스트" >&2
    echo -e "${YELLOW}  [2]${NC} mail-query  - Mail Query MCP 테스트" >&2
    echo -e "${YELLOW}  [3]${NC} onenote     - OneNote MCP 테스트" >&2
    echo -e "${YELLOW}  [4]${NC} all         - 모든 모듈 테스트" >&2
    echo "" >&2

    while true; do
        echo -ne "${MAGENTA}모듈 선택 (1-4) > ${NC}" >&2
        read -r module_choice

        case "$module_choice" in
            1) echo "enrollment"; return 0 ;;
            2) echo "mail-query"; return 0 ;;
            3) echo "onenote"; return 0 ;;
            4) echo "all"; return 0 ;;
            *) echo -e "${RED}❌ 잘못된 입력입니다. 1-4 중 선택하세요.${NC}" >&2 ;;
        esac
    done
}

# 테스트 목록 보여주기
show_test_list() {
    local module="$1"
    local json_file="$SCRIPT_DIR/jsonrpc_cases/${module}.json"

    if [ ! -f "$json_file" ]; then
        echo -e "${RED}❌ 테스트 케이스 파일을 찾을 수 없습니다: $json_file${NC}" >&2
        exit 1
    fi

    print_header "🧪 ${module^^} 테스트 목록"

    # Python으로 JSON 파싱해서 테스트 목록 출력
    source "$VENV_PATH/bin/activate"
    python3 - <<EOF
import json
import sys

with open("$json_file", "r", encoding="utf-8") as f:
    data = json.load(f)

test_cases = data.get("test_cases", [])

for i, tc in enumerate(test_cases, 1):
    name = tc.get("name", "Unnamed")
    enabled = tc.get("enabled", True)
    tool = tc.get("tool", "")

    status = "✓" if enabled else "✗"
    status_color = "\033[0;32m" if enabled else "\033[0;31m"

    print(f"  {status_color}{status}\033[0m \033[1;33m[{i}]\033[0m {name}", file=sys.stderr)
    print(f"      Tool: {tool}", file=sys.stderr)
    print("", file=sys.stderr)
EOF

    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" >&2
}

# 테스트 선택 메뉴
select_tests() {
    echo "" >&2
    echo -e "${YELLOW}실행할 테스트를 선택하세요:${NC}" >&2
    echo -e "${BLUE}  • 단일: 1${NC}" >&2
    echo -e "${BLUE}  • 복수: 1,3,5${NC}" >&2
    echo -e "${BLUE}  • 범위: 2-4${NC}" >&2
    echo -e "${BLUE}  • 전체: all${NC}" >&2
    echo -e "${CYAN}  • 모듈 선택으로: 0${NC}" >&2
    echo -e "${CYAN}  • 종료: q${NC}" >&2
    echo "" >&2

    while true; do
        echo -ne "${MAGENTA}선택 > ${NC}" >&2
        read -r test_selection

        if [ -z "$test_selection" ]; then
            echo -e "${RED}❌ 입력이 없습니다.${NC}" >&2
            continue
        fi

        # 특수 명령어 처리
        case "$test_selection" in
            0)
                echo "BACK_TO_MODULE"
                return 0
                ;;
            q|Q|quit|exit)
                echo "QUIT"
                return 0
                ;;
            all|a)
                echo ""
                return 0
                ;;
            *)
                # 번호 입력인 경우
                echo "$test_selection"
                return 0
                ;;
        esac
    done
}

# 테스트 실행 함수
run_test() {
    local module="$1"
    local test_numbers="$2"

    # venv 활성화
    source "$VENV_PATH/bin/activate"

    # Python 스크립트 실행
    echo "" >&2
    echo -e "${BLUE}🚀 테스트 실행 중...${NC}" >&2
    echo "" >&2

    if [ -n "$test_numbers" ]; then
        python3 "$SCRIPT_DIR/run_jsonrpc_tests.py" "$module" "$test_numbers"
    else
        python3 "$SCRIPT_DIR/run_jsonrpc_tests.py" "$module"
    fi

    local exit_code=$?

    # 결과 메시지
    echo "" >&2
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ 테스트 완료!${NC}" >&2
    else
        echo -e "${RED}❌ 테스트 실패 (exit code: $exit_code)${NC}" >&2
    fi

    return $exit_code
}

# 인터랙티브 모드 루프
interactive_mode() {
    clear

    while true; do
        # 1. 모듈 선택
        MODULE=$(select_module)

        # 'all' 모듈인 경우 바로 실행
        if [ "$MODULE" = "all" ]; then
            run_test "$MODULE" ""

            echo "" >&2
            echo -e "${YELLOW}계속하려면 Enter를 누르세요...${NC}" >&2
            read -r
            clear
            continue
        fi

        # 테스트 선택 루프
        while true; do
            # 2. 테스트 목록 표시
            show_test_list "$MODULE"

            # 3. 테스트 선택
            TEST_NUMBERS=$(select_tests)

            # 특수 명령어 처리
            if [ "$TEST_NUMBERS" = "QUIT" ]; then
                echo -e "${GREEN}👋 종료합니다.${NC}" >&2
                exit 0
            elif [ "$TEST_NUMBERS" = "BACK_TO_MODULE" ]; then
                clear
                break  # 모듈 선택으로 돌아감
            fi

            # 테스트 실행
            run_test "$MODULE" "$TEST_NUMBERS"

            # 다시 테스트 선택으로
            echo "" >&2
            echo -e "${YELLOW}계속하려면 Enter를 누르세요...${NC}" >&2
            read -r
            clear
        done
    done
}

# 메인 실행
main() {
    # venv 확인
    check_venv

    # 명령줄 인자가 있으면 직접 실행 모드
    if [ $# -ge 1 ]; then
        MODULE="$1"
        TEST_NUMBERS="${2:-}"

        run_test "$MODULE" "$TEST_NUMBERS"
        exit $?
    else
        # 인터랙티브 모드
        interactive_mode
    fi
}

# 실행
main "$@"
