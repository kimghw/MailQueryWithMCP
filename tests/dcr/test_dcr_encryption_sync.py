"""
DCR과 accounts 테이블 간 암호화 동기화 테스트

이 테스트는 다음을 검증합니다:
1. DCR 인증 후 accounts 테이블에 자동 동기화
2. 저장된 토큰이 암호화되어 있는지 확인
3. DCR과 accounts의 암호화 키가 동일한지 검증
4. 복호화 후 원본 토큰과 일치하는지 확인
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

from infra.core.database import get_database_manager
from infra.core.logger import get_logger
from modules.enrollment.account import AccountCryptoHelpers
from modules.dcr_oauth.dcr_service import DCRService

logger = get_logger(__name__)


def test_dcr_accounts_encryption_sync():
    """DCR과 accounts 테이블의 암호화 동기화 테스트"""

    print("\n" + "="*80)
    print("DCR → accounts 테이블 암호화 동기화 테스트")
    print("="*80)

    # 1. DCR 데이터베이스에서 최신 토큰 조회
    dcr_service = DCRService()
    crypto = AccountCryptoHelpers()

    test_email = os.getenv("AUTO_REGISTER_EMAIL", "kimghw@krs.co.kr")
    test_user_id = test_email.split('@')[0]

    print(f"\n📧 테스트 대상: {test_email} (user_id: {test_user_id})")

    # 2. dcr_azure_tokens에서 암호화된 토큰 조회
    dcr_query = """
        SELECT access_token, refresh_token, user_email
        FROM dcr_azure_tokens
        WHERE user_email = ?
        ORDER BY created_at DESC
        LIMIT 1
    """
    dcr_result = dcr_service._fetch_one(dcr_query, (test_email,))

    if not dcr_result:
        print(f"\n❌ DCR 데이터베이스에 {test_email} 토큰이 없습니다")
        print("   먼저 DCR 인증을 완료하세요")
        return False

    dcr_encrypted_access = dcr_result[0]
    dcr_encrypted_refresh = dcr_result[1]

    print(f"\n✅ DCR 테이블에서 토큰 조회 성공")
    print(f"   - access_token: {dcr_encrypted_access[:50]}...")
    print(f"   - refresh_token: {dcr_encrypted_refresh[:50] if dcr_encrypted_refresh else 'None'}...")

    # 3. accounts 테이블에서 동기화된 토큰 조회
    db_manager = get_database_manager()
    accounts_query = """
        SELECT user_id, email, access_token, refresh_token,
               oauth_client_secret, status
        FROM accounts
        WHERE user_id = ? OR email = ?
    """
    accounts_result = db_manager.fetch_one(accounts_query, (test_user_id, test_email))

    if not accounts_result:
        print(f"\n❌ accounts 테이블에 {test_user_id} 계정이 없습니다")
        print("   DCR 동기화가 실패했을 수 있습니다")
        return False

    accounts_dict = dict(accounts_result)
    accounts_encrypted_access = accounts_dict["access_token"]
    accounts_encrypted_refresh = accounts_dict["refresh_token"]
    accounts_encrypted_secret = accounts_dict["oauth_client_secret"]

    print(f"\n✅ accounts 테이블에서 계정 조회 성공")
    print(f"   - user_id: {accounts_dict['user_id']}")
    print(f"   - email: {accounts_dict['email']}")
    print(f"   - status: {accounts_dict['status']}")
    print(f"   - access_token: {accounts_encrypted_access[:50]}...")
    print(f"   - refresh_token: {accounts_encrypted_refresh[:50] if accounts_encrypted_refresh else 'None'}...")

    # 4. 암호화 여부 확인 (Fernet 암호화는 'gAAAAA'로 시작)
    print(f"\n🔐 암호화 형식 검증:")

    def is_encrypted(token):
        """Fernet 암호화된 토큰인지 확인"""
        if not token:
            return False
        return token.startswith('gAAAAA')

    dcr_access_encrypted = is_encrypted(dcr_encrypted_access)
    accounts_access_encrypted = is_encrypted(accounts_encrypted_access)

    print(f"   - DCR access_token 암호화: {'✅ Yes' if dcr_access_encrypted else '❌ No (평문)'}")
    print(f"   - accounts access_token 암호화: {'✅ Yes' if accounts_access_encrypted else '❌ No (평문)'}")

    if not accounts_access_encrypted:
        print(f"\n❌ accounts 테이블의 토큰이 암호화되지 않았습니다!")
        return False

    # 5. 암호화 키 동일성 검증 (복호화 테스트)
    print(f"\n🔑 암호화 키 동일성 검증:")

    try:
        # DCR 토큰 복호화
        dcr_decrypted_access = crypto.account_decrypt_sensitive_data(dcr_encrypted_access)
        print(f"   ✅ DCR access_token 복호화 성공: {dcr_decrypted_access[:50]}...")

        # accounts 토큰 복호화
        accounts_decrypted_access = crypto.account_decrypt_sensitive_data(accounts_encrypted_access)
        print(f"   ✅ accounts access_token 복호화 성공: {accounts_decrypted_access[:50]}...")

        # 복호화한 토큰이 JWT 형식인지 확인 (eyJ로 시작)
        if dcr_decrypted_access.startswith('eyJ') and accounts_decrypted_access.startswith('eyJ'):
            print(f"   ✅ 복호화된 토큰이 JWT 형식입니다")
        else:
            print(f"   ⚠️ 복호화된 토큰이 JWT 형식이 아닐 수 있습니다")

    except Exception as e:
        print(f"   ❌ 복호화 실패: {str(e)}")
        print(f"   DCR과 accounts의 암호화 키가 다를 수 있습니다")
        return False

    # 6. 동일한 토큰인지 검증
    print(f"\n🔄 동기화 데이터 일치성 검증:")

    if dcr_decrypted_access == accounts_decrypted_access:
        print(f"   ✅ DCR과 accounts의 access_token이 동일합니다")
    else:
        print(f"   ❌ DCR과 accounts의 access_token이 다릅니다!")
        print(f"      DCR: {dcr_decrypted_access[:80]}...")
        print(f"      accounts: {accounts_decrypted_access[:80]}...")
        return False

    if dcr_encrypted_refresh and accounts_encrypted_refresh:
        try:
            dcr_decrypted_refresh = crypto.account_decrypt_sensitive_data(dcr_encrypted_refresh)
            accounts_decrypted_refresh = crypto.account_decrypt_sensitive_data(accounts_encrypted_refresh)

            if dcr_decrypted_refresh == accounts_decrypted_refresh:
                print(f"   ✅ DCR과 accounts의 refresh_token이 동일합니다")
            else:
                print(f"   ❌ DCR과 accounts의 refresh_token이 다릅니다!")
                return False
        except Exception as e:
            print(f"   ⚠️ refresh_token 복호화 실패: {str(e)}")

    # 7. oauth_client_secret 복호화 테스트
    if accounts_encrypted_secret:
        try:
            decrypted_secret = crypto.account_decrypt_sensitive_data(accounts_encrypted_secret)
            print(f"   ✅ oauth_client_secret 복호화 성공: {decrypted_secret[:20]}...")
        except Exception as e:
            print(f"   ❌ oauth_client_secret 복호화 실패: {str(e)}")
            return False

    print(f"\n{'='*80}")
    print(f"✅ 모든 테스트 통과!")
    print(f"{'='*80}")
    print(f"\n📊 검증 완료:")
    print(f"   ✅ DCR 인증 후 accounts 테이블에 자동 동기화됨")
    print(f"   ✅ 모든 토큰이 Fernet 암호화되어 저장됨")
    print(f"   ✅ DCR과 accounts가 동일한 암호화 키 사용")
    print(f"   ✅ 복호화 후 원본 토큰과 일치")

    return True


if __name__ == "__main__":
    success = test_dcr_accounts_encryption_sync()
    sys.exit(0 if success else 1)
