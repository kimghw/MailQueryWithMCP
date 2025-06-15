#!/usr/bin/env python3
"""
브라우저를 통한 실제 OAuth 인증 플로우 테스트
"""

import asyncio
import sys
import os
import webbrowser
import time

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath('.'))

from modules.auth import get_auth_orchestrator, AuthStartRequest
from infra.core.logger import get_logger

logger = get_logger(__name__)

async def test_browser_auth_flow():
    """브라우저를 통한 실제 인증 플로우 테스트"""
    
    print("=" * 60)
    print("브라우저 OAuth 인증 플로우 테스트")
    print("=" * 60)
    
    auth_orchestrator = None
    
    try:
        # Auth 오케스트레이터 가져오기
        auth_orchestrator = get_auth_orchestrator()
        print("✓ Auth 오케스트레이터 초기화 완료")
        
        # 1. 인증 시작
        print("\n1. kimghw 계정 인증 시작...")
        request = AuthStartRequest(user_id="kimghw")
        response = await auth_orchestrator.auth_orchestrator_start_authentication(request)
        
        print(f"✓ 인증 세션 생성됨:")
        print(f"  - 세션 ID: {response.session_id}")
        print(f"  - 상태값: {response.state}")
        
        # URL 디코딩해서 보여주기
        import urllib.parse
        decoded_url = urllib.parse.unquote(response.auth_url)
        print(f"  - 인증 URL (디코딩됨): {decoded_url}")
        
        # 2. 브라우저에서 인증 URL 열기
        print(f"\n2. 브라우저에서 인증 URL 열기...")
        print(f"인증 URL: {response.auth_url}")
        
        # 사용자에게 브라우저 열기 확인
        user_input = input("\n브라우저에서 인증 URL을 열까요? (y/n): ")
        if user_input.lower() == 'y':
            webbrowser.open(response.auth_url)
            print("✓ 브라우저에서 인증 URL이 열렸습니다")
        else:
            print("수동으로 위의 URL을 브라우저에 복사해서 열어주세요")
        
        # 3. 콜백 대기
        print(f"\n3. OAuth 콜백 대기 중...")
        print(f"웹서버가 http://localhost:5000 에서 콜백을 기다리고 있습니다")
        print(f"Microsoft 로그인 후 권한을 승인해주세요...")
        
        # 주기적으로 세션 상태 확인
        max_wait_time = 300  # 5분
        check_interval = 5   # 5초마다 확인
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            await asyncio.sleep(check_interval)
            elapsed_time += check_interval
            
            # 세션 상태 확인
            status_response = await auth_orchestrator.auth_orchestrator_get_session_status(
                response.session_id
            )
            
            print(f"[{elapsed_time:3d}초] 세션 상태: {status_response.status} - {status_response.message}")
            
            if status_response.is_completed:
                print(f"\n🎉 인증이 성공적으로 완료되었습니다!")
                print(f"  - 사용자: {status_response.user_id}")
                print(f"  - 완료 시간: {status_response.created_at}")
                
                # 계정 상태 재확인
                accounts = await auth_orchestrator.auth_orchestrator_get_all_accounts_status()
                for account in accounts:
                    if account['user_id'] == 'kimghw':
                        print(f"\n✓ 업데이트된 계정 정보:")
                        print(f"  - 상태: {account.get('status', 'N/A')}")
                        print(f"  - 토큰 만료: {account.get('token_expired', 'N/A')}")
                        break
                
                return True
            
            elif status_response.status.value == 'FAILED':
                print(f"\n❌ 인증이 실패했습니다:")
                print(f"  - 오류: {status_response.error_message}")
                return False
            
            elif status_response.status.value == 'EXPIRED':
                print(f"\n⏰ 세션이 만료되었습니다")
                return False
        
        print(f"\n⏰ 시간 초과: {max_wait_time}초 동안 인증이 완료되지 않았습니다")
        return False
        
    except Exception as e:
        print(f"\n✗ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 정리 작업
        if auth_orchestrator:
            try:
                await auth_orchestrator.auth_orchestrator_shutdown()
                print("\n✓ Auth 오케스트레이터 정리 완료")
            except Exception as e:
                print(f"\n⚠ 정리 중 오류: {str(e)}")

if __name__ == "__main__":
    print("이 테스트는 실제 브라우저에서 Microsoft OAuth 인증을 수행합니다.")
    print("테스트를 계속하려면 Enter를 누르세요...")
    input()
    
    # 비동기 실행
    success = asyncio.run(test_browser_auth_flow())
    
    if success:
        print("\n🎉 브라우저 인증 테스트가 성공적으로 완료되었습니다!")
        sys.exit(0)
    else:
        print("\n❌ 브라우저 인증 테스트가 실패했습니다.")
        sys.exit(1)
