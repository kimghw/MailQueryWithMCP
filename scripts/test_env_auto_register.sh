#!/bin/bash
# 환경변수 기반 계정 자동 등록 테스트 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=================================="
echo "🧪 환경변수 기반 계정 자동 등록 테스트"
echo "=================================="
echo ""

# 테스트용 환경변수 설정
export AUTO_REGISTER_USER_ID="test_env_user"
export AUTO_REGISTER_USER_NAME="Test Environment User"
export AUTO_REGISTER_EMAIL="test_env@example.com"
export AUTO_REGISTER_OAUTH_CLIENT_ID="88f1daa2-a6cc-4c7b-b575-b76bf0a6435b"
export AUTO_REGISTER_OAUTH_CLIENT_SECRET="test-secret-value"
export AUTO_REGISTER_OAUTH_TENANT_ID="2da6fff9-9e75-4088-b510-a5d769de35f8"
export AUTO_REGISTER_OAUTH_REDIRECT_URI="http://localhost:5000/auth/callback"
export AUTO_REGISTER_DELEGATED_PERMISSIONS="Mail.ReadWrite,Mail.Send,offline_access"

echo "✅ 환경변수 설정 완료:"
echo "   - USER_ID: $AUTO_REGISTER_USER_ID"
echo "   - EMAIL: $AUTO_REGISTER_EMAIL"
echo "   - CLIENT_ID: ${AUTO_REGISTER_OAUTH_CLIENT_ID:0:8}..."
echo ""

# 1. 환경변수 로드 테스트
echo "=================================="
echo "1️⃣  환경변수 로드 테스트"
echo "=================================="

cat > /tmp/test_env_loader.py << 'EOF'
import sys
sys.path.insert(0, '/home/kimghw/MailQueryWithMCP')

from modules.enrollment.account._env_account_loader import env_load_account_from_env

# 환경변수에서 계정 정보 로드
account_data = env_load_account_from_env()

if account_data:
    print(f"✅ 계정 정보 로드 성공")
    print(f"   - user_id: {account_data.user_id}")
    print(f"   - user_name: {account_data.user_name}")
    print(f"   - email: {account_data.email}")
    print(f"   - oauth_client_id: {account_data.oauth_client_id[:8]}...")
    print(f"   - oauth_tenant_id: {account_data.oauth_tenant_id[:8]}...")
    print(f"   - redirect_uri: {account_data.oauth_redirect_uri}")
    print(f"   - permissions: {', '.join(account_data.delegated_permissions)}")
else:
    print("❌ 계정 정보 로드 실패")
    sys.exit(1)
EOF

python3 /tmp/test_env_loader.py
echo ""

# 2. AccountOrchestrator 등록 테스트
echo "=================================="
echo "2️⃣  AccountOrchestrator 등록 테스트"
echo "=================================="

cat > /tmp/test_account_register.py << 'EOF'
import sys
sys.path.insert(0, '/home/kimghw/MailQueryWithMCP')

from modules.enrollment.account import AccountOrchestrator

# AccountOrchestrator 인스턴스 생성
orchestrator = AccountOrchestrator()

# 환경변수 기반 계정 등록
account = orchestrator.account_register_from_env()

if account:
    print(f"✅ 계정 등록 성공")
    print(f"   - account_id: {account.id}")
    print(f"   - user_id: {account.user_id}")
    print(f"   - email: {account.email}")
    print(f"   - status: {account.status}")
    print(f"   - is_active: {account.is_active}")
else:
    print("❌ 계정 등록 실패 (환경변수 없거나 이미 등록됨)")
EOF

python3 /tmp/test_account_register.py
echo ""

# 3. 등록된 계정 조회
echo "=================================="
echo "3️⃣  등록된 계정 조회 테스트"
echo "=================================="

cat > /tmp/test_account_query.py << 'EOF'
import sys
sys.path.insert(0, '/home/kimghw/MailQueryWithMCP')

from modules.enrollment.account import AccountOrchestrator

orchestrator = AccountOrchestrator()

# user_id로 계정 조회
account = orchestrator.account_get_by_user_id("test_env_user")

if account:
    print(f"✅ 계정 조회 성공")
    print(f"   - account_id: {account.id}")
    print(f"   - user_id: {account.user_id}")
    print(f"   - user_name: {account.user_name}")
    print(f"   - email: {account.email}")
    print(f"   - status: {account.status.value}")
    print(f"   - enrollment_file_path: {account.enrollment_file_path}")
    print(f"   - has_valid_token: {account.has_valid_token}")
else:
    print("❌ 계정을 찾을 수 없음")
    sys.exit(1)
EOF

python3 /tmp/test_account_query.py
echo ""

echo "=================================="
echo "✅ 모든 테스트 완료"
echo "=================================="
echo ""
echo "💡 참고사항:"
echo "   - 환경변수를 설정하고 MCP 서버를 실행하면 자동으로 계정이 등록됩니다"
echo "   - 인증 시작 시 계정이 없으면 환경변수에서 자동으로 등록됩니다"
echo ""
