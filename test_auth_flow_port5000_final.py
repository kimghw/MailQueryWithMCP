#!/usr/bin/env python3
"""
Auth 모듈 인증 플로우 테스트 (포트 5000)

계정별 OAuth 설정을 사용하여 인증 플로우를 테스트합니다.
"""

import asyncio
import webbrowser
import time
from modules.auth import get_auth_orchestrator, AuthStartRequest
from infra.core.logger import get_logger

logger = get_logger(__name__)


async def test_auth_flow():
    """인증 플로우 테스트"""
    
    # 테스트할 사용자 ID
    user_id = "krsdpt@krsdpt.onmicrosoft.com"
    
    print(f"\n🚀 Auth 모듈 인증 플로우 테스트 시작")
    print(f"📧 사용자: {user_id}")
    print(f"🌐 웹서버 포트: 5000")
    print("=" * 60)
    
    try:
        # Auth 오케스트레이터 가져오기
        auth_orchestrator = get_auth_orchestrator()
        
        # 1. 인증 시작
        print("\n1️⃣ 인증 시작...")
        auth_request = AuthStartRequest(user_id=user_id)
        auth_response = await auth_orchestrator.auth_orchestrator_start_authentication(auth_request)
        
        print(f"✅ 세션 생성됨: {auth_response.session_id}")
        print(f"🔗 인증 URL: {auth_response.auth_url}")
        print(f"🔑 State: {auth_response.state[:16]}...")
        print(f"⏰ 만료 시간: {auth_response.expires_at}")
        
        # 2. 브라우저에서 인증 URL 열기
        print("\n2️⃣ 브라우저에서 인증 URL 열기...")
        webbrowser.open(auth_response.auth_url)
        print("🌐 브라우저가 열렸습니다. Azure AD에서 인증을 진행해주세요.")
        
        # 3. 인증 완료 대기
        print("\n3️⃣ 인증 완료 대기 중...")
        max_wait_time = 300  # 5분
        check_interval = 3   # 3초마다 확인
        
        for i in range(0, max_wait_time, check_interval):
            # 세션 상태 확인
            status_response = await auth_orchestrator.auth_orchestrator_get_session_status(
                auth_response.session_id
            )
            
            print(f"⏳ [{i:3d}s] 상태: {status_response.status.value} - {status_response.message}")
            
            if status_response.is_completed:
                print(f"\n🎉 인증 완료!")
                print(f"✅ 사용자: {status_response.user_id}")
                print(f"✅ 세션: {status_response.session_id}")
                print(f"✅ 상태: {status_response.status.value}")
                break
            elif status_response.status.value in ["FAILED", "EXPIRED"]:
                print(f"\n❌ 인증 실패!")
                print(f"💥 오류: {status_response.error_message}")
                return False
            
            await asyncio.sleep(check_interval)
        else:
            print(f"\n⏰ 타임아웃! {max_wait_time}초 내에 인증이 완료되지 않았습니다.")
            return False
        
        # 4. 최종 계정 상태 확인
        print("\n4️⃣ 최종 계정 상태 확인...")
        accounts_status = await auth_orchestrator.auth_orchestrator_get_all_accounts_status()
        
        target_account = None
        for account in accounts_status:
            if account['user_id'] == user_id:
                target_account = account
                break
        
        if target_account:
            print(f"✅ 계정 상태: {target_account['status']}")
            print(f"✅ 활성 상태: {target_account['is_active']}")
            print(f"✅ 토큰 만료: {target_account['token_expired']}")
            print(f"✅ 마지막 업데이트: {target_account['updated_at']}")
        else:
            print(f"❌ 계정을 찾을 수 없습니다: {user_id}")
            return False
        
        print("\n🎊 인증 플로우 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"\n💥 테스트 실패: {str(e)}")
        logger.error(f"인증 플로우 테스트 실패: {str(e)}", exc_info=True)
        return False
    
    finally:
        # 5. 정리
        print("\n5️⃣ 리소스 정리...")
        try:
            await auth_orchestrator.auth_orchestrator_shutdown()
            print("✅ Auth 오케스트레이터 종료됨")
        except Exception as e:
            print(f"⚠️ 정리 중 오류: {str(e)}")


async def main():
    """메인 함수"""
    print("🔐 Auth 모듈 인증 플로우 테스트 (포트 5000)")
    print("=" * 60)
    
    success = await test_auth_flow()
    
    if success:
        print("\n✅ 모든 테스트가 성공적으로 완료되었습니다!")
    else:
        print("\n❌ 테스트가 실패했습니다.")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
