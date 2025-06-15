#!/usr/bin/env python3
"""
Auth 모듈 인증 플로우 테스트 (포트 5000)
kimghw 계정의 새로운 시크릿으로 인증 플로우 테스트
"""

import asyncio
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath('.'))

from modules.auth import get_auth_orchestrator, AuthStartRequest
from infra.core.logger import get_logger

logger = get_logger(__name__)

async def test_auth_flow_port5000():
    """포트 5000번으로 인증 플로우 테스트"""
    
    print("=" * 60)
    print("Auth 모듈 인증 플로우 테스트 (포트 5000)")
    print("=" * 60)
    
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
        print(f"  - 만료 시간: {response.expires_at}")
        print(f"  - 인증 URL: {response.auth_url}")
        
        # 2. URL 분석
        print("\n2. 생성된 인증 URL 분석:")
        if "localhost:5000" in response.auth_url:
            print("✓ 리다이렉트 URI가 포트 5000으로 올바르게 설정됨")
        else:
            print("✗ 리다이렉트 URI 포트가 올바르지 않음")
        
        if "client_id=" in response.auth_url:
            # URL에서 client_id 추출
            import urllib.parse as urlparse
            parsed = urlparse.urlparse(response.auth_url)
            params = urlparse.parse_qs(parsed.query)
            client_id = params.get('client_id', [''])[0]
            print(f"✓ 클라이언트 ID: {client_id}")
        
        if "state=" in response.auth_url:
            print("✓ CSRF 방지용 state 파라미터 포함됨")
        
        # 3. 세션 상태 확인
        print("\n3. 세션 상태 확인...")
        status_response = await auth_orchestrator.auth_orchestrator_get_session_status(
            response.session_id
        )
        
        print(f"✓ 세션 상태:")
        print(f"  - 사용자: {status_response.user_id}")
        print(f"  - 상태: {status_response.status}")
        print(f"  - 메시지: {status_response.message}")
        print(f"  - 완료 여부: {status_response.is_completed}")
        
        # 4. 웹서버 상태 확인
        print("\n4. 웹서버 상태 확인...")
        web_server_manager = auth_orchestrator.web_server_manager
        if web_server_manager.is_running:
            print("✓ OAuth 콜백 웹서버가 실행 중입니다")
            print(f"  - 서버 URL: {web_server_manager.server_url}")
        else:
            print("✗ OAuth 콜백 웹서버가 실행되지 않음")
        
        # 5. 계정 정보 확인
        print("\n5. 계정 정보 확인...")
        accounts = await auth_orchestrator.auth_orchestrator_get_all_accounts_status()
        
        for account in accounts:
            if account['user_id'] == 'kimghw':
                print(f"✓ kimghw 계정 정보:")
                print(f"  - 이름: {account.get('user_name', 'N/A')}")
                print(f"  - 상태: {account.get('status', 'N/A')}")
                print(f"  - 토큰 만료: {account.get('token_expired', 'N/A')}")
                print(f"  - 진행 중인 세션: {account.get('has_pending_session', False)}")
                break
        
        print("\n" + "=" * 60)
        print("인증 플로우 테스트 완료!")
        print("=" * 60)
        print("\n다음 단계:")
        print("1. 위의 인증 URL을 브라우저에서 열어주세요")
        print("2. Microsoft 계정으로 로그인하세요")
        print("3. 권한 승인 후 콜백이 처리되는지 확인하세요")
        print("4. 웹서버가 포트 5000에서 콜백을 받는지 확인하세요")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 정리 작업
        try:
            await auth_orchestrator.auth_orchestrator_shutdown()
            print("\n✓ Auth 오케스트레이터 정리 완료")
        except Exception as e:
            print(f"\n⚠ 정리 중 오류: {str(e)}")

if __name__ == "__main__":
    # 비동기 실행
    success = asyncio.run(test_auth_flow_port5000())
    
    if success:
        print("\n🎉 테스트가 성공적으로 완료되었습니다!")
        sys.exit(0)
    else:
        print("\n❌ 테스트가 실패했습니다.")
        sys.exit(1)
