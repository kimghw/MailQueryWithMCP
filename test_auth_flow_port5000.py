#!/usr/bin/env python3
"""
Auth 모듈 인증 플로우 테스트 (포트 5000)
"""

import sys
import asyncio
sys.path.insert(0, '/home/kimghw/IACSGRAPH')

from modules.auth import get_auth_orchestrator, AuthStartRequest

async def test_auth_flow():
    """인증 플로우 테스트"""
    print("=== Auth 모듈 인증 플로우 테스트 (포트 5000) ===")
    
    # Auth 오케스트레이터 가져오기
    auth_orchestrator = get_auth_orchestrator()
    
    # 테스트할 사용자 ID
    user_id = "kimghw"  # 활성 계정으로 테스트
    
    try:
        print(f"\n1. 인증 시작: {user_id}")
        
        # 인증 시작 요청
        request = AuthStartRequest(user_id=user_id)
        response = await auth_orchestrator.auth_orchestrator_start_authentication(request)
        
        print(f"세션 ID: {response.session_id}")
        print(f"인증 URL: {response.auth_url}")
        print(f"State: {response.state}")
        print(f"만료 시간: {response.expires_at}")
        
        # 웹서버가 포트 5000에서 실행되는지 확인
        web_server_manager = auth_orchestrator.web_server_manager
        if web_server_manager.is_running:
            print(f"\n✓ 웹서버가 실행 중입니다: {web_server_manager.server_url}")
        else:
            print("\n✗ 웹서버가 실행되지 않았습니다")
        
        print(f"\n2. 브라우저에서 다음 URL로 인증을 진행하세요:")
        print(f"{response.auth_url}")
        print(f"\n3. 인증 완료 후 콜백이 http://localhost:5000/auth/callback 으로 전달됩니다")
        
        # 세션 상태 모니터링
        print(f"\n4. 세션 상태 모니터링 시작...")
        for i in range(30):  # 30초 동안 모니터링
            await asyncio.sleep(1)
            
            status_response = await auth_orchestrator.auth_orchestrator_get_session_status(
                response.session_id
            )
            
            print(f"[{i+1:2d}초] 상태: {status_response.status.value} - {status_response.message}")
            
            if status_response.is_completed:
                print(f"\n✓ 인증이 완료되었습니다!")
                break
            elif status_response.status.value in ["FAILED", "EXPIRED"]:
                print(f"\n✗ 인증이 실패했습니다: {status_response.error_message}")
                break
        else:
            print(f"\n⏰ 30초 타임아웃 - 인증이 완료되지 않았습니다")
        
        # 최종 상태 확인
        final_status = await auth_orchestrator.auth_orchestrator_get_session_status(
            response.session_id
        )
        print(f"\n최종 상태: {final_status.status.value}")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 정리
        try:
            await auth_orchestrator.auth_orchestrator_shutdown()
            print(f"\n🧹 Auth 오케스트레이터 정리 완료")
        except Exception as e:
            print(f"\n⚠️ 정리 중 오류: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_auth_flow())
