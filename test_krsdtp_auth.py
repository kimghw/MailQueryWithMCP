#!/usr/bin/env python3
"""
krsdtp@krs.co.kr 계정 OAuth 인증 테스트

포트 5000번으로 콜백을 받아 OAuth 인증을 완료합니다.
"""

import asyncio
import webbrowser
from modules.auth import get_auth_orchestrator, AuthStartRequest
from infra.core.logger import get_logger

logger = get_logger(__name__)

async def test_krsdtp_auth():
    """krsdtp@krs.co.kr 계정 OAuth 인증 테스트"""
    
    user_id = "krsdtp@krs.co.kr"
    
    try:
        # Auth 오케스트레이터 가져오기
        auth_orchestrator = get_auth_orchestrator()
        
        print(f"\n🚀 {user_id} OAuth 인증을 시작합니다...")
        print("=" * 60)
        
        # 인증 시작
        request = AuthStartRequest(user_id=user_id)
        response = await auth_orchestrator.auth_orchestrator_start_authentication(request)
        
        print(f"✅ 세션 ID: {response.session_id}")
        print(f"✅ 인증 URL 생성됨")
        print(f"✅ 만료 시간: {response.expires_at}")
        print(f"✅ 콜백 포트: 5000번")
        print()
        
        # 인증 URL 출력
        print("🔗 인증 URL:")
        print(response.auth_url)
        print()
        
        # 브라우저에서 인증 URL 열기
        print("🌐 브라우저에서 인증 URL을 열고 있습니다...")
        webbrowser.open(response.auth_url)
        print()
        
        # 인증 완료 대기
        print("⏳ 브라우저에서 인증을 완료해주세요...")
        print("   (Microsoft 계정으로 로그인 후 권한을 승인해주세요)")
        print()
        
        # 30초마다 상태 확인
        max_wait_time = 300  # 5분
        check_interval = 10   # 10초마다 확인
        
        for i in range(0, max_wait_time, check_interval):
            await asyncio.sleep(check_interval)
            
            # 세션 상태 확인
            status_response = await auth_orchestrator.auth_orchestrator_get_session_status(
                response.session_id
            )
            
            print(f"📊 상태 확인 ({i+check_interval}초): {status_response.status.value}")
            
            if status_response.status.value == "COMPLETED":
                print()
                print("🎉 인증이 완료되었습니다!")
                print(f"✅ 사용자: {status_response.user_id}")
                print(f"✅ 상태: {status_response.message}")
                print()
                
                # 계정 상태 확인
                accounts = await auth_orchestrator.auth_orchestrator_get_all_accounts_status()
                for account in accounts:
                    if account['user_id'] == user_id:
                        print("📋 계정 정보:")
                        print(f"   - 사용자 ID: {account['user_id']}")
                        print(f"   - 사용자 이름: {account.get('user_name', 'N/A')}")
                        print(f"   - 상태: {account['status']}")
                        print(f"   - 토큰 만료: {account['token_expired']}")
                        print(f"   - 활성 상태: {account['is_active']}")
                        break
                
                return True
                
            elif status_response.status.value == "FAILED":
                print()
                print("❌ 인증에 실패했습니다!")
                print(f"   오류: {status_response.error_message}")
                return False
                
            elif status_response.status.value == "EXPIRED":
                print()
                print("⏰ 세션이 만료되었습니다!")
                return False
        
        print()
        print("⏰ 시간 초과: 인증이 완료되지 않았습니다.")
        return False
        
    except Exception as e:
        print(f"\n❌ 인증 중 오류 발생: {str(e)}")
        logger.error(f"krsdtp 인증 실패: {str(e)}", exc_info=True)
        return False
    
    finally:
        # 오케스트레이터 정리
        try:
            await auth_orchestrator.auth_orchestrator_shutdown()
        except:
            pass

if __name__ == "__main__":
    print("🔐 krsdtp@krs.co.kr OAuth 인증 테스트")
    print("=" * 60)
    
    # 비동기 실행
    result = asyncio.run(test_krsdtp_auth())
    
    if result:
        print("\n🎯 인증 테스트 성공!")
    else:
        print("\n💥 인증 테스트 실패!")
