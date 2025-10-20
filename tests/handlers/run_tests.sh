#!/bin/bash
# 핸들러 직접 테스트 실행 스크립트
#
# 사용법:
#   ./tests/handlers/run_tests.sh [모듈명]
#
# 예시:
#   ./tests/handlers/run_tests.sh enrollment  # Enrollment만
#   ./tests/handlers/run_tests.sh mail-query  # Mail Query만
#   ./tests/handlers/run_tests.sh onenote     # OneNote만
#   ./tests/handlers/run_tests.sh             # 전체

set -e

# 프로젝트 루트로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# PYTHONPATH 설정
export PYTHONPATH="$PROJECT_ROOT"

# 색상 코드
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}🧪 핸들러 직접 테스트${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# 테스트 모듈 선택
TEST_MODULE="${1:-all}"

case "$TEST_MODULE" in
    enrollment)
        echo -e "${YELLOW}🔐 Enrollment 핸들러 테스트${NC}"
        python tests/handlers/test_enrollment_handlers.py
        ;;
    mail-query)
        echo -e "${YELLOW}📧 Mail Query 핸들러 테스트${NC}"
        python tests/handlers/test_mail_query_handlers.py
        ;;
    onenote)
        echo -e "${YELLOW}📝 OneNote 핸들러 테스트${NC}"
        python tests/handlers/test_onenote_handlers.py
        ;;
    all)
        echo -e "${YELLOW}🌐 전체 핸들러 테스트${NC}"
        echo ""

        python tests/handlers/test_enrollment_handlers.py
        EXIT_CODE_1=$?
        echo ""

        python tests/handlers/test_mail_query_handlers.py
        EXIT_CODE_2=$?
        echo ""

        python tests/handlers/test_onenote_handlers.py
        EXIT_CODE_3=$?

        # 하나라도 실패하면 에러 코드 반환
        if [ $EXIT_CODE_1 -ne 0 ] || [ $EXIT_CODE_2 -ne 0 ] || [ $EXIT_CODE_3 -ne 0 ]; then
            exit 1
        fi
        ;;
    *)
        echo "사용법: $0 [enrollment|mail-query|onenote|all]"
        exit 1
        ;;
esac
