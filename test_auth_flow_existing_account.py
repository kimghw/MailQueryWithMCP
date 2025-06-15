#!/usr/bin/env python3
"""
Auth 모듈 기존 계정으로 인증 플로우 테스트

데이터베이스에 등록된 기존 계정을 사용하여
포트 5000번으로 OAuth 콜백을 처리하고 전체 플로우를 테스트합니다.
"""

import asyncio
import webbrowser
import time
from modules.auth import get_auth_orchestrator, AuthStartRequest
from infra.core.logger import get_logger
from infra.core.database import get_database_manager

logger = get_logger(__name__)


async def test_existing_account_auth():
    """기존 계정으로 인증 플로우 테스트"""
    print("=" * 60)
    print("🚀 Auth 모듈 기존 계정 인증 플로우 테스트 시작")
    print("=" * 60)
    
    try:
        # 1. 데이터베이스에서 기존 계정 조회
        print("\n📋 1. 데이터베이스에서 기존 계정 조회")
        db = get_database_manager()
        accounts = db.fetch_all(
            "SELECT user_id, user_name, status, oauth_client_id FROM accounts WHERE is_active = 1"
        )
        
        if not accounts:
            print("❌ 활성 계정이 없습니다")
            return False
        
        print("✅ 활성 계정 목록:")
        for account in accounts:
            print(f"   - {account['user_id']} ({account['user_name']}) - {account['status']}")
            print(f"     OAuth Client ID: {'있음' if account['oauth_client_id'] else '없음'}")
        
        # 첫 번째 계정 선택
        test_account = accounts[0]
        test_user_id = test_account['user_id']
        
        print(f"\n📋 선택된 테스트 계정: {test_user_id}")
        
        # 2. Auth 오케스트레이터 초기화
        print("\n📋 2. Auth 오케스트레이터 초기화")
        auth_orchestrator = get_auth_orchestrator()
        print("✅ Auth 오케스트레이터 초기화 완료")
        
        # 3. 인증 시작
        print(f"\n📋 3. OAuth 인증 시작: {test_user_id}")
        auth_request = AuthStartRequest(user_id=test_user_id)
        auth_response = await auth_orchestrator.auth_orchestrator_start_authentication(auth_request)
        
        print(f"✅ 인증 URL 생성 완료:")
        print(f"   - 세션 ID: {auth_response.session_id}")
        print(f"   - 만료 시간: {auth_response.expires_at}")
        print(f"   - 인증 URL: {auth_response.auth_url[:100]}...")
        
        # 4. 브라우저에서 인증 URL 열기
        print(f"\n📋 4. 브라우저에서 인증 진행")
        print(f"🌐 브라우저에서 인증 URL을 열고 있습니다...")
        print(f"📝 인증 완료 후 콜백이 포트 5000으로 전송됩니다")
        
        # 브라우저 열기
        webbrowser.open(auth_response.auth_url)
        
        # 5. 인증 완료 대기
        print(f"\n📋 5. 인증 완료 대기 (최대 300초)")
        print("⏳ 브라우저에서 인증을 완료해 주세요...")
        
        max_wait_time = 300  # 5분
        check_interval = 3   # 3초마다 확인
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            # 세션 상태 확인
            status_response = await auth_orchestrator.auth_orchestrator_get_session_status(
                auth_response.session_id
            )
            
            print(f"   [{elapsed_time:3d}s] 상태: {status_response.status.value} - {status_response.message}")
            
            if status_response.is_completed:
                print("✅ 인증이 성공적으로 완료되었습니다!")
                break
            elif status_response.status.value in ["FAILED", "EXPIRED"]:
                print(f"❌ 인증 실패: {status_response.message}")
                return False
            
            await asyncio.sleep(check_interval)
            elapsed_time += check_interval
        
        if elapsed_time >= max_wait_time:
            print("⏰ 인증 대기 시간이 초과되었습니다")
            return False
        
        # 6. 최종 계정 상태 확인
        print(f"\n📋 6. 최종 계정 상태 확인")
        final_account = db.fetch_one(
            """
            SELECT user_id, status, access_token, refresh_token, token_expiry, updated_at
            FROM accounts WHERE user_id = ?
            """,
            (test_user_id,)
        )
        
        if final_account:
            print(f"✅ 계정 정보 업데이트 완료:")
            print(f"   - 상태: {final_account['status']}")
            print(f"   - access_token: {'있음' if final_account['access_token'] else '없음'}")
            print(f"   - refresh_token: {'있음' if final_account['refresh_token'] else '없음'}")
            print(f"   - 토큰 만료: {final_account['token_expiry']}")
            print(f"   - 업데이트 시간: {final_account['updated_at']}")
            
            # refresh_token 유무에 따른 메시지
            if final_account['refresh_token']:
                print("🎉 refresh_token을 성공적으로 받았습니다! offline_access 권한이 정상적으로 위임되었습니다.")
            else:
                print("⚠️ refresh_token을 받지 못했습니다. offline_access 권한 위임이 필요할 수 있습니다.")
        else:
            print("❌ 계정 정보를 찾을 수 없습니다")
            return False
        
        # 7. 토큰 서비스를 통한 상태 확인
        print(f"\n📋 7. 토큰 서비스를 통한 인증 상태 확인")
        from infra.core.token_service import get_token_service
        token_service = get_token_service()
        
        auth_status = await token_service.check_authentication_status(test_user_id)
        print(f"✅ 인증 상태 확인 결과:")
        print(f"   - 상태: {auth_status['status']}")
        print(f"   - 재인증 필요: {auth_status['requires_reauth']}")
        print(f"   - 메시지: {auth_status['message']}")
        
        # 8. 세션 정리
        print(f"\n📋 8. 세션 정리")
        from modules.auth import AuthCleanupRequest
        cleanup_request = AuthCleanupRequest(force_cleanup=True)
        cleanup_response = await auth_orchestrator.auth_orchestrator_cleanup_sessions(cleanup_request)
        print(f"✅ 세션 정리 완료: {cleanup_response.cleaned_sessions}개 세션 정리됨")
        
        print("\n" + "=" * 60)
        print("🎉 Auth 모듈 기존 계정 인증 플로우 테스트 성공!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        logger.error(f"Auth 플로우 테스트 실패: {str(e)}", exc_info=True)
        return False
    
    finally:
        # 오케스트레이터 종료
        try:
            await auth_orchestrator.auth_orchestrator_shutdown()
            print("🔧 Auth 오케스트레이터 종료 완료")
        except Exception as e:
            print(f"⚠️ 오케스트레이터 종료 중 오류: {str(e)}")


async def main():
    """메인 함수"""
    print("Auth 모듈 기존 계정 인증 플로우 테스트")
    print("포트 5000번을 사용하여 OAuth 콜백을 처리합니다")
    print("브라우저에서 인증을 완료해 주세요")
    
    success = await test_existing_account_auth()
    
    if success:
        print("\n✅ 모든 테스트가 성공적으로 완료되었습니다!")
    else:
        print("\n❌ 테스트가 실패했습니다.")
    
    return success


if __name__ == "__main__":
    asyncio.run(main())
