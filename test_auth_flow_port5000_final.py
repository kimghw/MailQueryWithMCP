#!/usr/bin/env python3
"""
Auth 모듈 인증 플로우 테스트 (포트 5000번)

OAuth 인증 플로우를 테스트하고 콜백 URL 빌드를 확인합니다.
웹서버는 포트 5000번에서 실행됩니다.
"""

import asyncio
import sys
import os
import webbrowser
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath('.'))

from modules.auth import get_auth_orchestrator, AuthStartRequest
from infra.core.logger import get_logger
from infra.core.config import get_config

logger = get_logger(__name__)


async def test_auth_flow_port5000():
    """포트 5000번으로 인증 플로우 테스트"""
    
    print("=" * 60)
    print("🔐 Auth 모듈 인증 플로우 테스트 (포트 5000번)")
    print("=" * 60)
    
    # 설정 확인
    config = get_config()
    print(f"📋 OAuth 설정 상태: {config.is_oauth_configured()}")
    print(f"📋 리다이렉트 URI: {config.oauth_redirect_uri}")
    
    # 오케스트레이터 가져오기
    auth_orchestrator = get_auth_orchestrator()
    
    # 테스트할 사용자 ID
    test_user_id = "kimghw@krsdpt.onmicrosoft.com"
    
    try:
        print(f"\n🚀 인증 시작: {test_user_id}")
        
        # 인증 시작 요청
        auth_request = AuthStartRequest(user_id=test_user_id)
        auth_response = await auth_orchestrator.auth_orchestrator_start_authentication(auth_request)
        
        print(f"✅ 세션 생성됨:")
        print(f"   - 세션 ID: {auth_response.session_id}")
        print(f"   - State: {auth_response.state[:16]}...")
        print(f"   - 만료 시간: {auth_response.expires_at}")
        
        print(f"\n🌐 인증 URL:")
        print(f"   {auth_response.auth_url}")
        
        # URL 구성 요소 분석
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(auth_response.auth_url)
        query_params = parse_qs(parsed_url.query)
        
        print(f"\n📊 URL 분석:")
        print(f"   - 호스트: {parsed_url.netloc}")
        print(f"   - 경로: {parsed_url.path}")
        print(f"   - 클라이언트 ID: {query_params.get('client_id', ['N/A'])[0][:16]}...")
        print(f"   - 리다이렉트 URI: {query_params.get('redirect_uri', ['N/A'])[0]}")
        print(f"   - 스코프: {query_params.get('scope', ['N/A'])[0]}")
        print(f"   - State: {query_params.get('state', ['N/A'])[0][:16]}...")
        
        # 리다이렉트 URI 포트 확인
        redirect_uri = query_params.get('redirect_uri', [''])[0]
        if redirect_uri:
            redirect_parsed = urlparse(redirect_uri)
            print(f"   - 리다이렉트 포트: {redirect_parsed.port}")
            
            if redirect_parsed.port == 5000:
                print("   ✅ 포트 5000번 확인됨")
            else:
                print(f"   ⚠️ 예상 포트(5000)와 다름: {redirect_parsed.port}")
        
        # 웹서버 상태 확인
        web_server_manager = auth_orchestrator.web_server_manager
        print(f"\n🖥️ 웹서버 상태:")
        print(f"   - 실행 중: {web_server_manager.is_running}")
        if web_server_manager.server_url:
            print(f"   - 서버 URL: {web_server_manager.server_url}")
        
        # 브라우저에서 인증 URL 열기
        print(f"\n🌐 브라우저에서 인증 URL을 여는 중...")
        webbrowser.open(auth_response.auth_url)
        
        # 인증 완료 대기
        print(f"\n⏳ 인증 완료를 기다리는 중... (최대 5분)")
        print(f"   브라우저에서 인증을 완료해주세요.")
        
        # 주기적으로 세션 상태 확인
        max_wait_time = 300  # 5분
        check_interval = 5   # 5초마다 확인
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            await asyncio.sleep(check_interval)
            elapsed_time += check_interval
            
            # 세션 상태 확인
            status_response = await auth_orchestrator.auth_orchestrator_get_session_status(
                auth_response.session_id
            )
            
            print(f"   [{elapsed_time:3d}s] 상태: {status_response.status.value} - {status_response.message}")
            
            if status_response.is_completed:
                print(f"\n🎉 인증 완료!")
                print(f"   - 최종 상태: {status_response.status.value}")
                print(f"   - 완료 시간: {datetime.utcnow().isoformat()}")
                break
            elif status_response.status.value in ["FAILED", "EXPIRED"]:
                print(f"\n❌ 인증 실패:")
                print(f"   - 상태: {status_response.status.value}")
                print(f"   - 오류: {status_response.error_message}")
                break
        else:
            print(f"\n⏰ 타임아웃: {max_wait_time}초 내에 인증이 완료되지 않았습니다.")
        
        # 최종 계정 상태 확인
        print(f"\n📊 최종 계정 상태 확인:")
        accounts_status = await auth_orchestrator.auth_orchestrator_get_all_accounts_status()
        
        for account in accounts_status:
            if account['user_id'] == test_user_id:
                print(f"   - 사용자: {account['user_id']}")
                print(f"   - 상태: {account['status']}")
                print(f"   - 토큰 만료: {account['token_expired']}")
                print(f"   - 활성: {account['is_active']}")
                if account.get('has_pending_session'):
                    print(f"   - 진행 중인 세션: {account.get('pending_session_id', 'N/A')}")
                break
        else:
            print(f"   ⚠️ 계정을 찾을 수 없음: {test_user_id}")
        
    except Exception as e:
        logger.error(f"인증 플로우 테스트 실패: {str(e)}")
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 정리
        try:
            await auth_orchestrator.auth_orchestrator_shutdown()
            print(f"\n🧹 리소스 정리 완료")
        except Exception as e:
            print(f"⚠️ 정리 중 오류: {str(e)}")


async def main():
    """메인 함수"""
    try:
        await test_auth_flow_port5000()
    except KeyboardInterrupt:
        print(f"\n\n⏹️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
