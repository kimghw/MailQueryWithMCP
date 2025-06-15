#!/usr/bin/env python3
"""
클라이언트 시크릿 복호화 테스트
"""

import sys
sys.path.insert(0, '/home/kimghw/IACSGRAPH')

from infra.core.config import get_config
from infra.core.database import get_database_manager
from cryptography.fernet import Fernet

def test_decrypt():
    config = get_config()
    db = get_database_manager()
    
    # kimghw 계정의 OAuth 설정 가져오기
    account = db.fetch_one(
        """
        SELECT user_id, oauth_client_id, oauth_client_secret, oauth_tenant_id
        FROM accounts 
        WHERE user_id = ? AND is_active = 1
        """,
        ("kimghw",)
    )
    
    if account:
        print(f"User ID: {account['user_id']}")
        print(f"Client ID: {account['oauth_client_id']}")
        print(f"Tenant ID: {account['oauth_tenant_id']}")
        print(f"Encrypted Secret: {account['oauth_client_secret'][:20]}...")
        
        # 복호화 시도
        try:
            encrypted_secret = account['oauth_client_secret']
            if encrypted_secret and encrypted_secret.startswith('gAAAAA'):
                fernet = Fernet(config.encryption_key.encode())
                decrypted_secret = fernet.decrypt(encrypted_secret.encode()).decode()
                print(f"\n복호화 성공!")
                print(f"Decrypted Secret: {decrypted_secret}")
                
                # enrollment 파일의 값과 비교
                print(f"\nEnrollment 파일의 시크릿: Y2JM8Q~BoztVdgiyqiI85xydNp2.ZWS5G3lQaYaPf")
                print(f"일치 여부: {decrypted_secret == 'Y2JM8Q~BoztVdgiyqiI85xydNp2.ZWS5G3lQaYaPf'}")
            else:
                print("암호화되지 않은 시크릿")
        except Exception as e:
            print(f"\n복호화 실패: {str(e)}")
            print(f"Encryption Key: {config.encryption_key}")

if __name__ == "__main__":
    test_decrypt()
