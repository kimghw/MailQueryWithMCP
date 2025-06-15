#!/usr/bin/env python3
"""
수정된 Auth 모듈 테스트
"""

import asyncio
import sys
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, '/home/kimghw/IACSGRAPH')

from modules.auth import get_auth_orchestrator, AuthStartRequest


async def test_auth_flow():
    """Auth 모듈의 인증 플로우를 테스트합니다."""
    print("=== Auth 모듈 테스트 시작 ===")
    print(f"시간: {datetime.now()}")
    
    try:
        # Auth 오케스트레이터 가져오기
        auth_orchestrator = get_auth_orchestrator()
        
        # 테스트 사용자로 인증 시작
        user_id = "kimghw"
        print(f"\n1. 인증 시작: user_id={user_id}")
        
        request = AuthStartRequest(user_id=user_id)
        response = await auth_orchestrator.auth_orchestrator_start_authentication(request)
        
        print(f"\n인증 URL 생성됨:")
        print(f"세션 ID: {response.session_id}")
        print(f"State: {response.state}")
        print(f"만료 시간: {response.expires_at}")
        print(f"\n인증 URL:\n{response.auth_url}")
        
        print("\n브라우저에서 위 URL로 접속하여 인증을 진행하세요.")
        print("인증이 완료되면 콜백이 처리됩니다.")
        
        # 세션 상태 확인 (몇 번 시도)
        print("\n세션 상태 확인 중...")
        for i in range(30):  # 30초 동안 대기
            await asyncio.sleep(1)
            status = await auth_orchestrator.auth_orchestrator_get_session_status(response.session_id)
            
            if status.is_completed:
                print(f"\n✓ 인증 완료! user_id={status.user_id}")
                break
            elif status.status == "FAILED":
                print(f"\n✗ 인증 실패: {status.error_message}")
                break
            else:
                print(".", end="", flush=True)
        
        print("\n\n테스트 완료")
        
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 오케스트레이터 종료
        try:
            await auth_orchestrator.auth_orchestrator_shutdown()
            print("\n오케스트레이터 종료됨")
        except:
            pass


if __name__ == "__main__":
    print("=== 수정된 Auth 모듈 OAuth 인증 테스트 ===")
    print("이 테스트는 실제 OAuth 인증 플로우를 실행합니다.")
    print("웹서버가 포트 5000에서 자동으로 시작됩니다.\n")
    
    asyncio.run(test_auth_flow())
