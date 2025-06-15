#!/usr/bin/env python3
"""
토큰 교환 과정 디버깅
"""

import sys
import requests
from urllib.parse import urlencode
from datetime import datetime, timedelta
sys.path.insert(0, '/home/kimghw/IACSGRAPH')

from infra.core.config import get_config
from infra.core.database import get_database_manager
from cryptography.fernet import Fernet

def debug_token_exchange():
    """토큰 교환 과정을 디버깅합니다."""
    config = get_config()
    db = get_database_manager()
    
    # kimghw 계정 정보 가져오기
    account = db.fetch_one(
        """
        SELECT oauth_client_id, oauth_client_secret, oauth_tenant_id, oauth_redirect_uri
        FROM accounts 
        WHERE user_id = ? AND is_active = 1
        """,
        ("kimghw",)
    )
    
    if not account:
        print("kimghw 계정을 찾을 수 없습니다")
        return
    
    # 클라이언트 시크릿 복호화
    try:
        fernet = Fernet(config.encryption_key.encode())
        decrypted_secret = fernet.decrypt(account['oauth_client_secret'].encode()).decode()
        print(f"복호화된 시크릿: {decrypted_secret}")
    except Exception as e:
        print(f"복호화 실패: {str(e)}")
        return
    
    # 토큰 엔드포인트 URL
    token_url = f"https://login.microsoftonline.com/{account['oauth_tenant_id']}/oauth2/v2.0/token"
    
    print(f"\n=== 토큰 교환 요청 정보 ===")
    print(f"Token URL: {token_url}")
    print(f"Client ID: {account['oauth_client_id']}")
    print(f"Client Secret: {decrypted_secret}")
    print(f"Tenant ID: {account['oauth_tenant_id']}")
    print(f"Redirect URI: {account['oauth_redirect_uri'] or config.oauth_redirect_uri}")
    
    # 테스트용 더미 코드로 토큰 교환 시도 (실패할 것이지만 오류 메시지 확인용)
    dummy_code = "dummy_authorization_code_for_testing"
    
    data = {
        "client_id": account['oauth_client_id'],
        "client_secret": decrypted_secret,
        "code": dummy_code,
        "redirect_uri": account['oauth_redirect_uri'] or config.oauth_redirect_uri,
        "grant_type": "authorization_code",
        "scope": "https://graph.microsoft.com/.default offline_access"
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    print(f"\n=== 토큰 교환 요청 데이터 ===")
    for key, value in data.items():
        if key == "client_secret":
            print(f"{key}: {value[:10]}...")
        else:
            print(f"{key}: {value}")
    
    print(f"\n=== 토큰 교환 시도 ===")
    try:
        response = requests.post(
            token_url,
            data=urlencode(data),
            headers=headers
        )
        
        print(f"응답 상태 코드: {response.status_code}")
        print(f"응답 헤더: {dict(response.headers)}")
        
        response_data = response.json()
        print(f"\n응답 데이터:")
        for key, value in response_data.items():
            print(f"  {key}: {value}")
        
        if response.status_code != 200:
            error = response_data.get("error", "unknown_error")
            error_description = response_data.get("error_description", "")
            print(f"\n❌ 토큰 교환 실패: {error}")
            print(f"오류 설명: {error_description}")
            
            # 특정 오류 분석
            if "AADSTS7000215" in error_description:
                print(f"\n🔍 분석: Client Secret이 잘못되었습니다.")
                print(f"   - Azure Portal에서 새로운 Client Secret을 생성해야 할 수 있습니다")
                print(f"   - 기존 Secret이 만료되었을 수 있습니다")
            elif "AADSTS70002" in error_description:
                print(f"\n🔍 분석: Authorization Code가 잘못되었습니다 (예상된 오류)")
            
    except Exception as e:
        print(f"요청 실패: {str(e)}")

if __name__ == "__main__":
    debug_token_exchange()
