#!/usr/bin/env python3
"""
Auth 모듈 최종 인증 플로우 테스트

포트 5000번으로 웹서버를 실행하고 실제 OAuth 인증을 테스트합니다.
"""

import asyncio
import webbrowser
import time
from modules.auth import get_auth_orchestrator, AuthStartRequest

async def test_auth_flow():
    """실제 OAuth 인증 플로우 테스트"""
    print("=" * 60)
    print("Auth 모듈 최종 인증 플로우 테스트")
    print("=" * 60)
    
    orchestrator = get_auth_orchestrator()
    
    try:
        # 1. 인증 시작
        print("\n1. 인증 시작...")
        request = AuthStartRequest(user_id="krsdtp")
        response = await orchestrator.auth_orchestrator_start_authentication(request)
        
        print(f"✅ 세션 ID: {response.session_id}")
        print(f"✅ 인증 URL: {response.auth_url}")
        print(f"✅ 만료 시간: {response.expires_at}")
        
        # 2. 브라우저에서 인증 URL 열기
        print("\n2. 브라우저에서 인증 URL을 엽니다...")
        print("🌐 브라우저가 자동으로 열립니다. 인증을 완료해주세요.")
        webbrowser.open(response.auth_url)
        
        # 3. 인증 완료 대기
        print("\n3. 인증 완료를 기다립니다...")
        max_wait_time = 300  # 5분
        check_interval = 2   # 2초마다 확인
        
        for i in range(0, max_wait_time, check_interval):
            await asyncio.sleep(check_interval)
            
            # 세션 상태 확인
            status = await orchestrator.auth_orchestrator_get_session_status(response.session_id)
            
            print(f"⏳ [{i+check_interval:3d}s] 상태: {status.status.value} - {status.message}")
            
            if status.status.value == "COMPLETED":
                print("\n🎉 인증이 성공적으로 완료되었습니다!")
                break
            elif status.status.value == "FAILED":
                print(f"\n❌ 인증에 실패했습니다: {status.error_message}")
                break
            elif status.status.value == "EXPIRED":
                print("\n⏰ 세션이 만료되었습니다.")
                break
        else:
            print(f"\n⏰ {max_wait_time}초 대기 시간이 초과되었습니다.")
        
        # 4. 최종 상태 확인
        print("\n4. 최종 상태 확인...")
        final_status = await orchestrator.auth_orchestrator_get_session_status(response.session_id)
        print(f"최종 상태: {final_status.status.value}")
        print(f"메시지: {final_status.message}")
        
        if final_status.error_message:
            print(f"오류: {final_status.error_message}")
        
        # 5. 계정 상태 확인
        print("\n5. 계정 상태 확인...")
        accounts = await orchestrator.auth_orchestrator_get_all_accounts_status()
        for account in accounts:
            if account['user_id'] == 'kimghw':
                print(f"계정: {account['user_id']}")
                print(f"상태: {account['status']}")
                print(f"토큰 만료: {account['token_expired']}")
                print(f"마지막 동기화: {account['last_sync_time']}")
                break
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 6. 정리
        print("\n6. 리소스 정리...")
        await orchestrator.auth_orchestrator_shutdown()
        print("✅ 테스트 완료")

if __name__ == "__main__":
    asyncio.run(test_auth_flow())
