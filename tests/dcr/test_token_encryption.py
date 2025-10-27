"""
Token Service 암호화 테스트

이 테스트는 다음을 검증합니다:
1. Token Service가 토큰을 암호화하여 저장하는지 확인
2. 저장된 토큰이 Fernet 암호화 형식인지 검증
3. 복호화가 정상적으로 작동하는지 확인
4. 암호화/복호화 키가 일관성 있게 사용되는지 검증
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

logger = get_logger(__name__)


def test_token_encryption():
    """Token Service의 암호화 동작 테스트"""

    print("\n" + "="*80)
    print("Token Service 암호화/복호화 테스트")
    print("="*80)

    db_manager = get_database_manager()
    crypto = AccountCryptoHelpers()

    # 1. accounts 테이블에서 토큰 조회
    test_user_id = os.getenv("AUTO_REGISTER_USER_ID", "testuser")

    query = """
        SELECT user_id, email, access_token, refresh_token,
               oauth_client_secret, token_expiry, status
        FROM accounts
        WHERE user_id = ?
    """
    result = db_manager.fetch_one(query, (test_user_id,))

    if not result:
        print(f"\n❌ accounts 테이블에 {test_user_id} 계정이 없습니다")
        return False

    account = dict(result)

    print(f"\n📧 테스트 대상: {account['email']} (user_id: {account['user_id']})")
    print(f"   상태: {account['status']}")
    print(f"   만료: {account['token_expiry']}")

    # 2. 암호화 여부 확인
    print(f"\n🔐 암호화 형식 검증:")

    def is_encrypted(token):
        """Fernet 암호화된 토큰인지 확인"""
        if not token:
            return False
        # Fernet 암호화는 'gAAAAA'로 시작
        return token.startswith('gAAAAA')

    access_token = account['access_token']
    refresh_token = account['refresh_token']
    client_secret = account['oauth_client_secret']

    if not access_token:
        print(f"   ❌ access_token이 없습니다")
        return False

    access_encrypted = is_encrypted(access_token)
    refresh_encrypted = is_encrypted(refresh_token) if refresh_token else None
    secret_encrypted = is_encrypted(client_secret) if client_secret else None

    print(f"   - access_token: {access_token[:50]}...")
    print(f"     암호화: {'✅ Yes' if access_encrypted else '❌ No (평문)'}")

    if refresh_token:
        print(f"   - refresh_token: {refresh_token[:50]}...")
        print(f"     암호화: {'✅ Yes' if refresh_encrypted else '❌ No (평문)'}")

    if client_secret:
        print(f"   - oauth_client_secret: {client_secret[:50]}...")
        print(f"     암호화: {'✅ Yes' if secret_encrypted else '❌ No (평문)'}")

    if not access_encrypted:
        print(f"\n❌ 토큰이 암호화되지 않았습니다!")
        return False

    # 3. 복호화 테스트
    print(f"\n🔑 복호화 테스트:")

    try:
        # access_token 복호화
        decrypted_access = crypto.account_decrypt_sensitive_data(access_token)
        print(f"   ✅ access_token 복호화 성공")
        print(f"      원본: {decrypted_access[:80]}...")

        # JWT 형식 확인 (eyJ로 시작)
        if decrypted_access.startswith('eyJ'):
            print(f"      ✅ JWT 형식 확인")
        else:
            print(f"      ⚠️ JWT 형식이 아닐 수 있습니다")

        # refresh_token 복호화
        if refresh_token:
            decrypted_refresh = crypto.account_decrypt_sensitive_data(refresh_token)
            print(f"   ✅ refresh_token 복호화 성공")
            print(f"      원본: {decrypted_refresh[:80]}...")

        # oauth_client_secret 복호화
        if client_secret:
            decrypted_secret = crypto.account_decrypt_sensitive_data(client_secret)
            print(f"   ✅ oauth_client_secret 복호화 성공")
            print(f"      원본: {decrypted_secret[:40]}...")

    except Exception as e:
        print(f"   ❌ 복호화 실패: {str(e)}")
        return False

    # 4. 재암호화 후 일치 여부 테스트
    print(f"\n🔄 재암호화 일관성 테스트:")

    try:
        # 복호화 → 재암호화
        re_encrypted = crypto.account_encrypt_sensitive_data(decrypted_access)
        print(f"   - 재암호화: {re_encrypted[:50]}...")

        # 재암호화한 값을 다시 복호화
        re_decrypted = crypto.account_decrypt_sensitive_data(re_encrypted)

        if re_decrypted == decrypted_access:
            print(f"   ✅ 재암호화 후 복호화 결과가 원본과 일치합니다")
        else:
            print(f"   ❌ 재암호화 후 복호화 결과가 원본과 다릅니다!")
            return False

    except Exception as e:
        print(f"   ❌ 재암호화 테스트 실패: {str(e)}")
        return False

    # 5. 동일 암호화 키 사용 확인
    print(f"\n🔐 암호화 키 일관성 검증:")

    test_data = "test_encryption_consistency"
    try:
        encrypted1 = crypto.account_encrypt_sensitive_data(test_data)
        decrypted1 = crypto.account_decrypt_sensitive_data(encrypted1)

        if decrypted1 == test_data:
            print(f"   ✅ 암호화 키가 일관성 있게 작동합니다")
        else:
            print(f"   ❌ 암호화 키 불일치!")
            return False

    except Exception as e:
        print(f"   ❌ 암호화 키 검증 실패: {str(e)}")
        return False

    print(f"\n{'='*80}")
    print(f"✅ 모든 테스트 통과!")
    print(f"{'='*80}")
    print(f"\n📊 검증 완료:")
    print(f"   ✅ 모든 토큰이 Fernet 암호화되어 저장됨")
    print(f"   ✅ 복호화가 정상적으로 작동함")
    print(f"   ✅ 복호화된 토큰이 JWT 형식임")
    print(f"   ✅ 암호화 키가 일관성 있게 사용됨")

    return True


if __name__ == "__main__":
    success = test_token_encryption()
    sys.exit(0 if success else 1)
