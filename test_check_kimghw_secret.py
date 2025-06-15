#!/usr/bin/env python3
"""
kimghw 계정의 OAuth 설정 확인
"""

import sys
sys.path.insert(0, '/home/kimghw/IACSGRAPH')

from infra.core.config import get_config
from infra.core.database import get_database_manager
from cryptography.fernet import Fernet
import yaml

def check_kimghw():
    config = get_config()
    db = get_database_manager()
    
    # 1. 데이터베이스에서 kimghw 계정 정보 가져오기
    account = db.fetch_one(
        """
        SELECT user_id, oauth_client_id, oauth_client_secret, oauth_tenant_id, is_active
        FROM accounts 
        WHERE user_id = ?
        """,
        ("kimghw",)
    )
    
    if account:
        print("=== 데이터베이스 정보 ===")
        print(f"User ID: {account['user_id']}")
        print(f"Client ID: {account['oauth_client_id']}")
        print(f"Tenant ID: {account['oauth_tenant_id']}")
        print(f"활성 상태: {account['is_active']}")
        
        if account['oauth_client_secret']:
            print(f"암호화된 시크릿: {account['oauth_client_secret'][:30]}...")
            
            # 복호화 시도
            try:
                fernet = Fernet(config.encryption_key.encode())
                decrypted_secret = fernet.decrypt(account['oauth_client_secret'].encode()).decode()
                print(f"\n복호화 성공!")
                print(f"복호화된 시크릿: {decrypted_secret}")
            except Exception as e:
                print(f"\n복호화 실패: {str(e)}")
        else:
            print("시크릿이 없습니다")
    else:
        print("kimghw 계정을 찾을 수 없습니다")
    
    # 2. enrollment 파일 확인
    print("\n\n=== Enrollment 파일 정보 ===")
    try:
        with open('enrollment/kimghw.yaml', 'r') as f:
            enrollment_data = yaml.safe_load(f)
        
        ms_graph = enrollment_data.get('microsoft_graph', {})
        print(f"Client ID: {ms_graph.get('client_id')}")
        print(f"Client Secret: {ms_graph.get('client_secret')}")
        print(f"Tenant ID: {ms_graph.get('tenant_id')}")
        
        # 비교
        if account and ms_graph.get('client_secret'):
            print(f"\n=== 비교 결과 ===")
            print(f"Enrollment 파일의 시크릿: {ms_graph.get('client_secret')}")
            if account['oauth_client_secret']:
                try:
                    fernet = Fernet(config.encryption_key.encode())
                    decrypted_secret = fernet.decrypt(account['oauth_client_secret'].encode()).decode()
                    print(f"DB의 복호화된 시크릿: {decrypted_secret}")
                    print(f"일치 여부: {decrypted_secret == ms_graph.get('client_secret')}")
                except:
                    print("복호화 실패로 비교 불가")
            
    except FileNotFoundError:
        print("enrollment/kimghw.yaml 파일을 찾을 수 없습니다")
    except Exception as e:
        print(f"파일 읽기 오류: {str(e)}")

if __name__ == "__main__":
    check_kimghw()
