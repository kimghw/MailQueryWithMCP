#!/usr/bin/env python3
"""
Auth 오케스트레이터 디버깅 전용 테스트
"""

import asyncio
from infra.core.database import get_database_manager
from modules.auth import get_auth_orchestrator

async def debug_auth_config():
    """Auth 설정 조회 디버깅"""
    print("=== Auth 설정 조회 디버깅 ===\n")
    
    # 1. 데이터베이스 직접 쿼리
    print("1. 데이터베이스 직접 쿼리:")
    db = get_database_manager()
    
    # 모든 계정 조회
    all_accounts = db.fetch_all("SELECT user_id, oauth_client_id, oauth_tenant_id, is_active FROM accounts")
    print(f"   전체 계정 수: {len(all_accounts)}")
    for account in all_accounts:
        account_dict = dict(account)
        print(f"   - {account_dict['user_id']}: oauth_client_id={account_dict['oauth_client_id']}, is_active={account_dict['is_active']}")
    
    # 테스트 계정 직접 조회
    test_user_id = "kimghw"
    print(f"\n2. 테스트 계정 '{test_user_id}' 직접 조회:")
    
    account = db.fetch_one("""
        SELECT oauth_client_id, oauth_client_secret, oauth_tenant_id, oauth_redirect_uri
        FROM accounts 
        WHERE user_id = ? AND is_active = 1
    """, (test_user_id,))
    
    if account:
        account_dict = dict(account)
        print("   ✅ 계정 발견:")
        for key, value in account_dict.items():
            if 'secret' in key.lower() and value:
                print(f"      {key}: {value[:8]}...")
            else:
                print(f"      {key}: {value}")
    else:
        print("   ❌ 계정을 찾을 수 없음")
    
    # is_active = 1 조건 제거하고 다시 조회
    print(f"\n3. is_active 조건 없이 '{test_user_id}' 조회:")
    account_all = db.fetch_one("""
        SELECT oauth_client_id, oauth_client_secret, oauth_tenant_id, oauth_redirect_uri, is_active
        FROM accounts 
        WHERE user_id = ?
    """, (test_user_id,))
    
    if account_all:
        account_dict = dict(account_all)
        print("   ✅ 계정 발견:")
        for key, value in account_dict.items():
            if 'secret' in key.lower() and value:
                print(f"      {key}: {value[:8]}...")
            else:
                print(f"      {key}: {value}")
    else:
        print("   ❌ 계정을 찾을 수 없음")
    
    # 4. Auth 오케스트레이터 메서드 테스트
    print(f"\n4. Auth 오케스트레이터 _get_account_oauth_config 메서드 테스트:")
    auth_orchestrator = get_auth_orchestrator()
    
    try:
        oauth_config = await auth_orchestrator._get_account_oauth_config(test_user_id)
        if oauth_config:
            print("   ✅ OAuth 설정 조회 성공:")
            for key, value in oauth_config.items():
                if 'secret' in key.lower() and value:
                    print(f"      {key}: {value[:8]}...")
                else:
                    print(f"      {key}: {value}")
        else:
            print("   ❌ OAuth 설정 조회 실패")
    except Exception as e:
        print(f"   ❌ 예외 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_auth_config())
