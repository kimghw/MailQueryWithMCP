"""
Auth 모듈 인증 플로우 테스트 (포트 5000, 계정별 스코프 포함)

OAuth 2.0 인증 플로우를 포트 5000에서 테스트하고 URL 빌드 및 콜백 처리를 확인합니다.
"""

import asyncio
import webbrowser
import time
from modules.auth import get_auth_orchestrator, AuthStartRequest
from infra.core.logger import get_logger

logger = get_logger(__name__)


async def test_auth_flow_port5000():
    """포트 5000에서 인증 플로우 테스트"""
    
    print("=" * 60)
    print("Auth 모듈 인증 플로우 테스트 (포트 5000)")
    print("=" * 60)
    
    # 테스트할 사용자 ID
    test_user_id = "kimghw"
    
    try:
        # Auth 오케스트레이터 가져오기
        auth_orchestrator = get_auth_orchestrator()
        
        print(f"\n1. 인증 시작: {test_user_id}")
        print("-" * 40)
        
        # 인증 시작 요청
        auth_request = AuthStartRequest(user_id=test_user_id)
        auth_response = await auth_orchestrator.auth_orchestrator_start_authentication(auth_request)
        
        print(f"✓ 세션 ID: {auth_response.session_id}")
        print(f"✓ State: {auth_response.state[:16]}...")
        print(f"✓ 만료 시간: {auth_response.expires_at}")
        print(f"✓ 인증 URL 생성됨")
        
        # URL 분석
        auth_url = auth_response.auth_url
        print(f"\n2. 생성된 인증 URL 분석")
        print("-" * 40)
        print(f"URL: {auth_url}")
        
        # URL에서 주요 파라미터 확인
        if "redirect_uri" in auth_url:
            redirect_start = auth_url.find("redirect_uri=") + 13
            redirect_end = auth_url.find("&", redirect_start)
            if redirect_end == -1:
                redirect_uri = auth_url[redirect_start:]
            else:
                redirect_uri = auth_url[redirect_start:redirect_end]
            print(f"✓ Redirect URI: {redirect_uri}")
            
            # 포트 5000 확인
            if ":5000" in redirect_uri:
                print("✓ 포트 5000 사용 확인됨")
            else:
                print("⚠ 포트 5000이 아닌 다른 포트 사용 중")
        
        if "scope" in auth_url:
            scope_start = auth_url.find("scope=") + 6
            scope_end = auth_url.find("&", scope_start)
            if scope_end == -1:
                scope = auth_url[scope_start:]
            else:
                scope = auth_url[scope_start:scope_end]
            print(f"✓ 스코프: {scope}")
        
        print(f"\n3. 웹서버 상태 확인")
        print("-" * 40)
        
        # 웹서버 상태 확인
        web_server_manager = auth_orchestrator.web_server_manager
        if web_server_manager.is_running:
            print(f"✓ 웹서버 실행 중: {web_server_manager.server_url}")
        else:
            print("✗ 웹서버가 실행되지 않음")
        
        print(f"\n4. 브라우저에서 인증 진행")
        print("-" * 40)
        print("브라우저가 열립니다. 인증을 완료해주세요...")
        
        # 브라우저에서 인증 URL 열기
        webbrowser.open(auth_url)
        
        print("\n인증 진행 상황을 모니터링합니다...")
        print("(인증 완료까지 최대 5분 대기)")
        
        # 인증 완료 대기 (최대 5분)
        max_wait_time = 300  # 5분
        check_interval = 5   # 5초마다 확인
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            # 세션 상태 확인
            status_response = await auth_orchestrator.auth_orchestrator_get_session_status(
                auth_response.session_id
            )
            
            print(f"[{elapsed_time:3d}s] 상태: {status_response.status.value} - {status_response.message}")
            
            if status_response.is_completed:
                print(f"\n✓ 인증 완료!")
                print(f"  - 사용자: {status_response.user_id}")
                print(f"  - 세션: {status_response.session_id}")
                print(f"  - 완료 시간: {status_response.created_at}")
                break
            elif status_response.status.value == "FAILED":
                print(f"\n✗ 인증 실패!")
                if status_response.error_message:
                    print(f"  - 오류: {status_response.error_message}")
                break
            elif status_response.status.value == "EXPIRED":
                print(f"\n⚠ 세션 만료!")
                break
            
            # 대기
            await asyncio.sleep(check_interval)
            elapsed_time += check_interval
        
        if elapsed_time >= max_wait_time:
            print(f"\n⚠ 타임아웃: {max_wait_time}초 경과")
        
        print(f"\n5. 최종 계정 상태 확인")
        print("-" * 40)
        
        # 전체 계정 상태 확인
        accounts_status = await auth_orchestrator.auth_orchestrator_get_all_accounts_status()
        
        for account in accounts_status:
            if account['user_id'] == test_user_id:
                print(f"계정: {account['user_id']}")
                print(f"  - 상태: {account['status']}")
                print(f"  - 토큰 만료: {account.get('token_expired', 'Unknown')}")
                print(f"  - 마지막 동기화: {account.get('last_sync_time', 'None')}")
                print(f"  - 활성 상태: {account.get('is_active', False)}")
                break
        else:
            print(f"계정 {test_user_id}를 찾을 수 없습니다.")
        
    except Exception as e:
        logger.error(f"인증 플로우 테스트 실패: {str(e)}")
        print(f"\n✗ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 정리
        try:
            await auth_orchestrator.auth_orchestrator_shutdown()
            print(f"\n✓ Auth 오케스트레이터 종료됨")
        except Exception as e:
            print(f"⚠ 정리 중 오류: {str(e)}")
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_auth_flow_port5000())
