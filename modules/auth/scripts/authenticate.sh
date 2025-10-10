#!/bin/bash

# 계정 인증 스크립트
# OAuth 2.0 인증을 통해 계정의 토큰을 갱신합니다.
#
# 사용법:
#   ./authenticate.sh single kimghw          # 단일 계정 인증
#   ./authenticate.sh bulk kimghw krsdtp     # 여러 계정 일괄 인증
#   ./authenticate.sh check-all              # 모든 계정 상태 확인 후 자동 인증

# 스크립트 디렉토리 기준으로 프로젝트 루트 찾기
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Python 스크립트 경로
PYTHON_SCRIPT="$SCRIPT_DIR/authenticate.py"

# 모드에 따라 인자 구성
if [ "$1" == "single" ]; then
    if [ -z "$2" ]; then
        echo "사용법: $0 single <user_id>"
        exit 1
    fi
    cd "$PROJECT_ROOT"
    python3 "$PYTHON_SCRIPT" --mode single --user-id "$2"
elif [ "$1" == "bulk" ]; then
    if [ -z "$2" ]; then
        echo "사용법: $0 bulk <user_id1> [user_id2 ...]"
        exit 1
    fi
    shift  # 'bulk' 제거
    cd "$PROJECT_ROOT"
    python3 "$PYTHON_SCRIPT" --mode bulk --user-ids "$@"
elif [ "$1" == "check-all" ]; then
    cd "$PROJECT_ROOT"
    python3 "$PYTHON_SCRIPT" --mode check-all
else
    echo "사용법:"
    echo "  $0 single <user_id>              # 단일 계정 인증"
    echo "  $0 bulk <user_id1> [user_id2 ...]  # 여러 계정 일괄 인증"
    echo "  $0 check-all                     # 모든 계정 확인 후 인증"
    exit 1
fi
