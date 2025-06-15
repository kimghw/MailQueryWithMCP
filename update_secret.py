#!/usr/bin/env python3
"""
kimghw 계정의 클라이언트 시크릿 업데이트
"""

import sys
sys.path.insert(0, '/home/kimghw/IACSGRAPH')

from infra.core.config import get_config
from infra.core.database import get_database_manager
from cryptography.fernet import Fernet

def update_secret():
    config = get_config()
    db = get_database_manager()
    
    # 새로운 시크릿
    new_secret = "Y2JM8Q~BoztVdgiyqiI85xydNp2.ZWS5G3lQaYaPf"
    
    # 암호화
    fernet = Fernet(config.encryption_key.encode())
    encrypted_secret = fernet.encrypt(new_secret.encode()).decode()
    
    print(f"원본 시크릿: {new_secret}")
    print(f"암호화된 시크릿: {encrypted_secret[:20]}...")
    
    # 데이터베이스 업데이트
    try:
        db.execute_query(
            """
            UPDATE accounts 
            SET oauth_client_secret = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (encrypted_secret, "kimghw")
        )
        print("\n✓ 데이터베이스 업데이트 완료")
        
        # 확인
        account = db.fetch_one(
            "SELECT user_id, oauth_client_secret FROM accounts WHERE user_id = ?",
            ("kimghw",)
        )
        if account:
            print(f"\n업데이트 확인:")
            print(f"User ID: {account['user_id']}")
            print(f"암호화된 시크릿: {account['oauth_client_secret'][:20]}...")
            
            # 복호화 테스트
            decrypted = fernet.decrypt(account['oauth_client_secret'].encode()).decode()
            print(f"복호화 테스트: {decrypted == new_secret}")
            
    except Exception as e:
        print(f"\n✗ 업데이트 실패: {str(e)}")

if __name__ == "__main__":
    update_secret()
