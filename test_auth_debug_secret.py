#!/usr/bin/env python3
"""
Auth 모듈 OAuth 인증 테스트 - 시크릿 디버깅 버전
"""

import asyncio
import sys
import webbrowser
from datetime import datetime

sys.path.insert(0, '/home/kimghw/IACSGRAPH')

from modules.auth import (
    get_auth_orchestrator,
    AuthStartRequest,
    AuthState
)

async def test_auth_with_debug():
    """디버깅이 포함된 인증 테스트"""
    print("=== Auth 모듈 시크릿 디버깅 테스트 ===")
    
    orchestrator = get_auth_orchestrator()
    
    try:
        # 1. 인증 시작
        user_id = "kimghw"
        print(f"\n1. 인증 시작: user_id={user_id}")
        
        # 데이터베이스에서 직접 시크릿 확인
        from infra.core.database import get_database_manager
        from infra.core.config import get_config
        from cryptography.fernet import Fernet
        
        db = get_database_manager()
        config = get_config()
        
        account = db.fetch_one(
            """
            SELECT oauth_client_id, oauth_client_secret, oauth_tenant_id
            FROM accounts 
            WHERE user_id = ? AND is_active = 1
            """,
            (user_id,)
        )
        
        if account:
            print(f"\n데이터베이스 정보:")
            print(f"Client ID: {account['oauth_client_id']}")
            print(f"Tenant ID: {account['oauth_tenant_id']}")
            print(f"암호화된 시크릿: {account['oauth_client_secret'][:30]}...")
            
            # 복호화 테스트
            try:
                fernet = Fernet(config.encryption_key.encode())
                decrypted_secret = fernet.decrypt(account['oauth_client_secret'].encode()).decode()
                print(f"\n복호화 성공!")
                print(f"복호화된 시크릿: {decrypted_secret}")
                print(f"예상 시크릿: Y2JM8Q~BoztVdgiyqiI85xydNp2.ZWS5G3lQaYaPf")
                print(f"일치 여부: {decrypted_secret == 'Y2JM8Q~BoztVdgiyqiI85xydNp2.ZWS5G3lQaYaPf'}")
            except Exception as e:
                print(f"\n복호화 실패: {str(e)}")
        
        # 인증 시작
        request = AuthStartRequest(user_id=user_id)
        response = await orchestrator.auth_orchestrator_start_authentication(request)
        
        print(f"\n인증 URL 생성됨:")
        print(f"세션 ID: {response.session_id}")
        print(f"State: {response.state}")
        print(f"만료 시간: {response.expires_at}")
        
        print(f"\n인증 URL:\n{response.auth_url}")
        
        # 브라우저 열기
        print("\n브라우저에서 위 URL로 접속하여 인증을 진행하세요.")
        print("인증이 완료되면 콜백이 처리됩니다.")
        webbrowser.open(response.auth_url)
        
        # 2. 세션 상태 확인 (최대 60초 대기)
        print("\n세션 상태 확인 중...")
        max_wait = 60
        check_interval = 2
        elapsed = 0
        
        while elapsed < max_wait:
            await asyncio.sleep(check_interval)
            elapsed += check_interval
            
            status = await orchestrator.auth_orchestrator_get_session_status(
                response.session_id
            )
            
            print(".", end="", flush=True)
            
            if status.status == AuthState.COMPLETED:
                print(f"\n\n✓ 인증 성공!")
                print(f"사용자: {status.user_id}")
                print(f"세션: {status.session_id}")
                break
            elif status.status == AuthState.FAILED:
                print(f"\n\n✗ 인증 실패: {status.error_message}")
                break
            elif status.status == AuthState.EXPIRED:
                print(f"\n\n✗ 세션 만료")
                break
        else:
            print(f"\n\n✗ 타임아웃 ({max_wait}초)")
        
        # 3. 전체 계정 상태 확인
        print("\n\n3. 전체 계정 상태 확인:")
        accounts = await orchestrator.auth_orchestrator_get_all_accounts_status()
        
        for account in accounts:
            print(f"\n계정: {account['user_id']}")
            print(f"  상태: {account['status']}")
            print(f"  토큰 만료: {account['token_expired']}")
            print(f"  활성: {account['is_active']}")
            if account.get('has_pending_session'):
                print(f"  진행 중인 세션: {account['pending_session_id']}")
        
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n\n테스트 완료")
        await orchestrator.auth_orchestrator_shutdown()
        print("\n오케스트레이터 종료됨")

if __name__ == "__main__":
    print(f"=== Auth 모듈 시크릿 디버깅 테스트 시작 ===")
    print(f"시간: {datetime.now()}")
    
    asyncio.run(test_auth_with_debug())
