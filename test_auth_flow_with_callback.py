#!/usr/bin/env python3
"""
Auth 모듈 인증 흐름 테스트 (콜백 URL 빌드 및 처리 테스트)

포트 5000번으로 웹서버를 시작하고 실제 OAuth 인증 흐름을 테스트합니다.
"""

import asyncio
import webbrowser
from modules.auth import get_auth_orchestrator, AuthStartRequest
from infra.core.logger import get_logger

logger = get_logger(__name__)


async def test_auth_flow_with_callback():
    """인증 흐름 테스트 (콜백 URL 빌드 및 처리)"""
    
    orchestrator = get_auth_orchestrator()
    
    try:
        print("=" * 60)
        print("Auth 모듈 인증 흐름 테스트 (포트 5000)")
        print("=" * 60)
        
        # 테스트할 사용자 ID
        test_user_id = "kimghw"
        
        print(f"\n1. 인증 시작: {test_user_id}")
        print("-" * 40)
        
        # 인증 시작
        auth_request = AuthStartRequest(user_id=test_user_id)
        auth_response = await orchestrator.auth_orchestrator_start_authentication(auth_request)
        
        print(f"✓ 세션 ID: {auth_response.session_id}")
        print(f"✓ State: {auth_response.state}")
        print(f"✓ 만료 시간: {auth_response.expires_at}")
        print(f"✓ 인증 URL 생성됨")
        
        # URL 분석
        auth_url = auth_response.auth_url
        print(f"\n2. 생성된 인증 URL 분석")
        print("-" * 40)
        print(f"URL: {auth_url}")
        
        # URL 파라미터 확인
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(auth_url)
        query_params = parse_qs(parsed_url.query)
        
        print(f"✓ 호스트: {parsed_url.netloc}")
        print(f"✓ 경로: {parsed_url.path}")
        print(f"✓ client_id: {query_params.get('client_id', ['없음'])[0]}")
        print(f"✓ redirect_uri: {query_params.get('redirect_uri', ['없음'])[0]}")
        print(f"✓ state: {query_params.get('state', ['없음'])[0]}")
        print(f"✓ scope: {query_params.get('scope', ['없음'])[0]}")
        
        # redirect_uri가 포트 5000인지 확인
        redirect_uri = query_params.get('redirect_uri', [''])[0]
        if ':5000' in redirect_uri:
            print("✓ redirect_uri가 포트 5000으로 올바르게 설정됨")
        else:
            print(f"⚠ redirect_uri 포트 확인 필요: {redirect_uri}")
        
        print(f"\n3. 웹서버 상태 확인")
        print("-" * 40)
        
        # 웹서버 상태 확인
        web_server_manager = orchestrator.web_server_manager
        if web_server_manager.is_running:
            print("✓ OAuth 콜백 웹서버가 실행 중입니다")
            print(f"✓ 서버 URL: {web_server_manager.server_url}")
        else:
            print("✗ 웹서버가 실행되지 않았습니다")
        
        print(f"\n4. 세션 상태 확인")
        print("-" * 40)
        
        # 세션 상태 확인
        status_response = await orchestrator.auth_orchestrator_get_session_status(
            auth_response.session_id
        )
        
        print(f"✓ 세션 상태: {status_response.status}")
        print(f"✓ 메시지: {status_response.message}")
        print(f"✓ 완료 여부: {status_response.is_completed}")
        
        print(f"\n5. 브라우저에서 인증 진행")
        print("-" * 40)
        print("브라우저가 열립니다. Microsoft 계정으로 로그인해주세요.")
        print("인증 완료 후 이 스크립트로 돌아와서 Enter를 눌러주세요.")
        
        # 브라우저에서 인증 URL 열기
        webbrowser.open(auth_url)
        
        # 사용자 입력 대기
        input("\n인증 완료 후 Enter를 눌러주세요...")
        
        print(f"\n6. 인증 완료 후 세션 상태 재확인")
        print("-" * 40)
        
        # 세션 상태 재확인
        final_status = await orchestrator.auth_orchestrator_get_session_status(
            auth_response.session_id
        )
        
        print(f"✓ 최종 세션 상태: {final_status.status}")
        print(f"✓ 메시지: {final_status.message}")
        print(f"✓ 완료 여부: {final_status.is_completed}")
        
        if final_status.is_completed:
            print("🎉 인증이 성공적으로 완료되었습니다!")
            
            # 토큰 상태 확인
            from infra.core.token_service import get_token_service
            token_service = get_token_service()
            
            access_token = await token_service.get_valid_access_token(test_user_id)
            if access_token:
                print(f"✓ 유효한 액세스 토큰 확인됨: {access_token[:20]}...")
            else:
                print("✗ 액세스 토큰을 가져올 수 없습니다")
        else:
            print(f"❌ 인증이 완료되지 않았습니다: {final_status.status}")
            if final_status.error_message:
                print(f"오류: {final_status.error_message}")
        
        print(f"\n7. 전체 계정 상태 확인")
        print("-" * 40)
        
        # 전체 계정 상태 확인
        all_accounts = await orchestrator.auth_orchestrator_get_all_accounts_status()
        
        for account in all_accounts:
            user_id = account.get('user_id', 'Unknown')
            status = account.get('status', 'Unknown')
            token_expired = account.get('token_expired', True)
            has_pending = account.get('has_pending_session', False)
            
            print(f"계정: {user_id}")
            print(f"  - 상태: {status}")
            print(f"  - 토큰 만료: {token_expired}")
            print(f"  - 진행 중인 세션: {has_pending}")
            print()
        
    except Exception as e:
        logger.error(f"테스트 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 정리
        print(f"\n8. 리소스 정리")
        print("-" * 40)
        
        try:
            await orchestrator.auth_orchestrator_shutdown()
            print("✓ Auth 오케스트레이터 종료됨")
        except Exception as e:
            print(f"✗ 정리 중 오류: {str(e)}")


async def test_url_building():
    """URL 빌드 테스트만 수행"""
    
    print("=" * 60)
    print("URL 빌드 테스트")
    print("=" * 60)
    
    orchestrator = get_auth_orchestrator()
    
    try:
        # 인증 URL 생성만 테스트
        test_user_id = "kimghw"
        
        auth_request = AuthStartRequest(user_id=test_user_id)
        auth_response = await orchestrator.auth_orchestrator_start_authentication(auth_request)
        
        print(f"생성된 인증 URL:")
        print(auth_response.auth_url)
        print()
        
        # URL 파라미터 분석
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(auth_response.auth_url)
        query_params = parse_qs(parsed_url.query)
        
        print("URL 파라미터 분석:")
        for key, value in query_params.items():
            print(f"  {key}: {value[0] if value else 'None'}")
        
        # redirect_uri 확인
        redirect_uri = query_params.get('redirect_uri', [''])[0]
        print(f"\nredirect_uri 확인: {redirect_uri}")
        
        if ':5000' in redirect_uri and '/auth/callback' in redirect_uri:
            print("✅ redirect_uri가 올바르게 설정됨 (포트 5000, 경로 /auth/callback)")
        else:
            print("❌ redirect_uri 설정 확인 필요")
            
    except Exception as e:
        logger.error(f"URL 빌드 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await orchestrator.auth_orchestrator_shutdown()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "url-only":
        # URL 빌드만 테스트
        asyncio.run(test_url_building())
    else:
        # 전체 인증 흐름 테스트
        asyncio.run(test_auth_flow_with_callback())
