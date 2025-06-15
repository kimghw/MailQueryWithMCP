#!/usr/bin/env python3
"""
데이터베이스 accounts와 enrollment 파일 비교
"""

import sys
import yaml
from pathlib import Path
sys.path.insert(0, '/home/kimghw/IACSGRAPH')

from infra.core.config import get_config
from infra.core.database import get_database_manager
from cryptography.fernet import Fernet

def compare_accounts_enrollment():
    """데이터베이스와 enrollment 파일을 비교합니다."""
    config = get_config()
    db = get_database_manager()
    
    print("=== 데이터베이스 accounts 테이블 ===")
    accounts = db.fetch_all(
        """
        SELECT user_id, oauth_client_id, oauth_client_secret, oauth_tenant_id, oauth_redirect_uri
        FROM accounts 
        WHERE is_active = 1
        ORDER BY user_id
        """
    )
    
    fernet = Fernet(config.encryption_key.encode())
    
    for account in accounts:
        print(f"\n사용자: {account['user_id']}")
        print(f"  Client ID: {account['oauth_client_id']}")
        print(f"  Tenant ID: {account['oauth_tenant_id']}")
        print(f"  Redirect URI: {account['oauth_redirect_uri']}")
        
        # 시크릿 복호화
        try:
            if account['oauth_client_secret']:
                decrypted_secret = fernet.decrypt(account['oauth_client_secret'].encode()).decode()
                print(f"  Client Secret: {decrypted_secret}")
            else:
                print(f"  Client Secret: (없음)")
        except Exception as e:
            print(f"  Client Secret: (복호화 실패: {str(e)})")
    
    print(f"\n=== Enrollment 파일들 ===")
    enrollment_dir = Path(config.enrollment_directory)
    
    for yaml_file in enrollment_dir.glob("*.yaml"):
        print(f"\n파일: {yaml_file.name}")
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            print(f"  User ID: {data.get('user_id', '(없음)')}")
            print(f"  Client ID: {data.get('oauth_client_id', '(없음)')}")
            print(f"  Client Secret: {data.get('oauth_client_secret', '(없음)')}")
            print(f"  Tenant ID: {data.get('oauth_tenant_id', '(없음)')}")
            print(f"  Redirect URI: {data.get('oauth_redirect_uri', '(없음)')}")
            
        except Exception as e:
            print(f"  오류: {str(e)}")
    
    print(f"\n=== 비교 분석 ===")
    # 각 사용자별로 DB와 enrollment 파일 비교
    for account in accounts:
        user_id = account['user_id']
        yaml_file = enrollment_dir / f"{user_id}.yaml"
        
        print(f"\n사용자: {user_id}")
        
        if yaml_file.exists():
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    enrollment_data = yaml.safe_load(f)
                
                # Client ID 비교
                db_client_id = account['oauth_client_id']
                enrollment_client_id = enrollment_data.get('oauth_client_id')
                print(f"  Client ID 일치: {db_client_id == enrollment_client_id}")
                if db_client_id != enrollment_client_id:
                    print(f"    DB: {db_client_id}")
                    print(f"    Enrollment: {enrollment_client_id}")
                
                # Tenant ID 비교
                db_tenant_id = account['oauth_tenant_id']
                enrollment_tenant_id = enrollment_data.get('oauth_tenant_id')
                print(f"  Tenant ID 일치: {db_tenant_id == enrollment_tenant_id}")
                if db_tenant_id != enrollment_tenant_id:
                    print(f"    DB: {db_tenant_id}")
                    print(f"    Enrollment: {enrollment_tenant_id}")
                
                # Client Secret 비교
                try:
                    db_secret = fernet.decrypt(account['oauth_client_secret'].encode()).decode()
                    enrollment_secret = enrollment_data.get('oauth_client_secret')
                    print(f"  Client Secret 일치: {db_secret == enrollment_secret}")
                    if db_secret != enrollment_secret:
                        print(f"    DB: {db_secret}")
                        print(f"    Enrollment: {enrollment_secret}")
                except Exception as e:
                    print(f"  Client Secret 비교 실패: {str(e)}")
                
            except Exception as e:
                print(f"  Enrollment 파일 읽기 실패: {str(e)}")
        else:
            print(f"  Enrollment 파일 없음: {yaml_file}")

if __name__ == "__main__":
    compare_accounts_enrollment()
