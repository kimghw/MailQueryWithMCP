#!/usr/bin/env python3
"""
인증 URL 생성 과정 디버깅
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from modules.auth import get_auth_orchestrator, AuthStartRequest
from infra.core.database import get_database_manager
from infra.core.oauth_client import get_oauth_client
import urllib.parse

def test_url_generation():
    """URL 생성 과정 디버깅"""
    
    print("=" * 60)
    print("인증 URL 생성 과정 디버깅")
    print("=" * 60)
    
    # 1. 데이터베이스에서 kimghw 계정 정보 확인
    print("\n1. 데이터베이스 계정 정보:")
    db = get_database_manager()
    account = db.fetch_one(
        """
        SELECT user_id, oauth_client_id, oauth_tenant_id, oauth_redirect_uri, delegated_permissions
        FROM accounts 
        WHERE user_id = ? AND is_active = 1
        """,
        ('kimghw',)
    )
    
    if account:
        account_dict = dict(account)
        print(f"  - user_id: {account_dict['user_id']}")
        print(f"  - oauth_client_id: {account_dict['oauth_client_id']}")
        print(f"  - oauth_tenant_id: {account_dict['oauth_tenant_id']}")
        print(f"  - oauth_redirect_uri: {account_dict['oauth_redirect_uri']}")
        print(f"  - delegated_permissions: {repr(account_dict['delegated_permissions'])}")
    else:
        print("  계정을 찾을 수 없습니다!")
        return
    
    # 2. OAuth 클라이언트로 URL 생성 (계정별 설정)
    print("\n2. 계정별 OAuth 설정으로 URL 생성:")
    oauth_client = get_oauth_client()
    
    # 권한 파싱 테스트
    delegated_permissions = account_dict.get('delegated_permissions')
    print(f"  - 원본 delegated_permissions: {repr(delegated_permissions)}")
    
    # auth_web_server의 파싱 로직과 동일하게 처리
    if not delegated_permissions:
        scopes = ["Mail.ReadWrite", "Mail.Send", "offline_access"]
    else:
        permissions = []
        for perm in delegated_permissions.replace(',', ' ').split():
            perm = perm.strip()
            if perm:
                if perm in ["Mail.ReadWrite", "Mail.Send", "offline_access", "User.Read"]:
                    permissions.append(perm)
                elif perm.startswith('https://graph.microsoft.com/'):
                    permissions.append(perm)
                else:
                    permissions.append(perm)
        
        if "offline_access" not in permissions:
            permissions.append("offline_access")
        
        scopes = permissions
    
    print(f"  - 파싱된 scopes: {scopes}")
    
    # URL 생성
    state = "test_state_12345"
    auth_url = oauth_client.generate_auth_url_with_account_config(
        client_id=account_dict['oauth_client_id'],
        tenant_id=account_dict['oauth_tenant_id'],
        redirect_uri=account_dict['oauth_redirect_uri'] or "http://localhost:5000/auth/callback",
        state=state,
        scopes=scopes
    )
    
    print(f"\n3. 생성된 인증 URL:")
    print(f"  - 원본 URL: {auth_url}")
    
    # URL 파싱해서 각 파라미터 확인
    parsed_url = urllib.parse.urlparse(auth_url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    
    print(f"\n4. URL 파라미터 분석:")
    print(f"  - 기본 URL: {parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}")
    for key, values in query_params.items():
        value = values[0] if values else ""
        if key == 'scope':
            print(f"  - {key}: {urllib.parse.unquote_plus(value)}")
        else:
            print(f"  - {key}: {value}")
    
    # 5. Auth 오케스트레이터로 URL 생성 테스트
    print(f"\n5. Auth 오케스트레이터로 URL 생성:")
    try:
        import asyncio
        
        async def test_orchestrator():
            auth_orchestrator = get_auth_orchestrator()
            request = AuthStartRequest(user_id="kimghw")
            response = await auth_orchestrator.auth_orchestrator_start_authentication(request)
            
            print(f"  - 오케스트레이터 생성 URL: {response.auth_url}")
            
            # URL 디코딩
            decoded_url = urllib.parse.unquote(response.auth_url)
            print(f"  - 디코딩된 URL: {decoded_url}")
            
            # 파라미터 분석
            parsed_url = urllib.parse.urlparse(response.auth_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            print(f"\n6. 오케스트레이터 URL 파라미터:")
            for key, values in query_params.items():
                value = values[0] if values else ""
                if key == 'scope':
                    print(f"  - {key}: {urllib.parse.unquote_plus(value)}")
                else:
                    print(f"  - {key}: {value}")
            
            # 정리
            await auth_orchestrator.auth_orchestrator_shutdown()
        
        asyncio.run(test_orchestrator())
        
    except Exception as e:
        print(f"  오케스트레이터 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_url_generation()
