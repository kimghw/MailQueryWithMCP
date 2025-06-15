#!/usr/bin/env python3
"""
Auth 모듈의 OAuth 인증 플로우 테스트

계정별 OAuth 설정을 사용하여 인증 URL 생성 및 콜백 처리를 테스트합니다.
"""

import asyncio
import webbrowser
from modules.auth import (
    get_auth_orchestrator, 
    get_auth_web_server_manager,
    AuthStartRequest
)
from infra.core.logger import get_logger
from infra.core.database import get_database_manager
from infra.core.config import get_config

logger = get_logger(__name__)


async def test_auth_flow():
    """인증 플로우 전체 테스트"""
    
    print("\n" + "="*60)
    print("Auth 모듈 인증 플로우 테스트")
    print("="*60 + "\n")
    
    # 1. 데이터베이스에서 테스트할 사용자 확인
    db = get_database_manager()
    accounts = db.fetch_all(
        """
        SELECT user_id, user_name, oauth_client_id, oauth_tenant_id, oauth_redirect_uri
        FROM accounts 
        WHERE is_active = 1
        ORDER BY user_id
        """
    )
    
    if not accounts:
        print("❌ 활성화된 계정이 없습니다.")
        return
    
    print("📋 등록된 계정 목록:")
    for i, account in enumerate(accounts):
        oauth_info = "계정별 OAuth 설정 있음" if account['oauth_client_id'] else "전역 OAuth 사용"
        print(f"{i+1}. {account['user_id']} ({account['user_name']}) - {oauth_info}")
    
    # 사용자 선택
    try:
        choice = int(input("\n인증할 계정 번호를 선택하세요: ")) - 1
        if choice < 0 or choice >= len(accounts):
            print("❌ 잘못된 선택입니다.")
            return
    except ValueError:
        print("❌ 숫자를 입력해주세요.")
        return
    
    selected_account = accounts[choice]
    user_id = selected_account['user_id']
    
    print(f"\n✅ 선택된 계정: {user_id}")
    
    # 2. OAuth 설정 확인
    if selected_account['oauth_client_id']:
        print(f"   - Client ID: {selected_account['oauth_client_id'][:20]}...")
        print(f"   - Tenant ID: {selected_account['oauth_tenant_id']}")
        print(f"   - Redirect URI: {selected_account['oauth_redirect_uri'] or 'http://localhost:5000/auth/callback'}")
    else:
        print("   - 전역 OAuth 설정을 사용합니다.")
    
    # 3. Auth 오케스트레이터 초기화
    auth_orchestrator = get_auth_orchestrator()
    
    # 4. 인증 시작
    print(f"\n🔐 {user_id}의 인증을 시작합니다...")
    
    try:
        # 인증 시작 요청
        auth_request = AuthStartRequest(user_id=user_id)
        auth_response = await auth_orchestrator.auth_orchestrator_start_authentication(auth_request)
        
        print(f"\n✅ 인증 세션 생성됨:")
        print(f"   - 세션 ID: {auth_response.session_id}")
        print(f"   - State: {auth_response.state[:20]}...")
        print(f"   - 만료 시간: {auth_response.expires_at}")
        
        # 5. 인증 URL 확인
        print(f"\n🔗 인증 URL:")
        print(f"   {auth_response.auth_url[:100]}...")
        
        # URL 파싱하여 파라미터 확인
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(auth_response.auth_url)
        query_params = parse_qs(parsed_url.query)
        
        print(f"\n📝 URL 파라미터:")
        print(f"   - client_id: {query_params.get('client_id', ['N/A'])[0][:20]}...")
        print(f"   - redirect_uri: {query_params.get('redirect_uri', ['N/A'])[0]}")
        print(f"   - state: {query_params.get('state', ['N/A'])[0][:20]}...")
        print(f"   - scope: {query_params.get('scope', ['N/A'])[0]}")
        
        # 6. 브라우저 열기 확인
        open_browser = input("\n브라우저에서 인증 페이지를 열까요? (y/n): ")
        if open_browser.lower() == 'y':
            print("\n🌐 브라우저에서 인증 페이지를 엽니다...")
            webbrowser.open(auth_response.auth_url)
            
            # 7. 콜백 대기
            print("\n⏳ 인증 완료를 기다립니다... (최대 5분)")
            print("   브라우저에서 Microsoft 계정으로 로그인하고 권한을 부여해주세요.")
            
            # 세션 상태 주기적으로 확인
            max_wait = 300  # 5분
            check_interval = 5  # 5초마다 확인
            elapsed = 0
            
            while elapsed < max_wait:
                await asyncio.sleep(check_interval)
                elapsed += check_interval
                
                # 세션 상태 확인
                status = await auth_orchestrator.auth_orchestrator_get_session_status(
                    auth_response.session_id
                )
                
                if status.is_completed:
                    print(f"\n✅ 인증 완료!")
                    print(f"   - 상태: {status.status}")
                    print(f"   - 메시지: {status.message}")
                    break
                elif status.status == "FAILED":
                    print(f"\n❌ 인증 실패!")
                    print(f"   - 오류: {status.error_message}")
                    break
                elif status.status == "EXPIRED":
                    print(f"\n⏰ 세션 만료!")
                    break
                else:
                    print(f"   ... {elapsed}초 경과 (상태: {status.status})")
            
            if elapsed >= max_wait:
                print("\n⏰ 인증 시간 초과")
        
        # 8. 최종 계정 상태 확인
        print("\n📊 최종 계정 상태 확인:")
        final_account = db.fetch_one(
            """
            SELECT user_id, status, access_token, refresh_token, token_expiry
            FROM accounts 
            WHERE user_id = ?
            """,
            (user_id,)
        )
        
        if final_account:
            print(f"   - 사용자: {final_account['user_id']}")
            print(f"   - 상태: {final_account['status']}")
            print(f"   - 액세스 토큰: {'있음' if final_account['access_token'] else '없음'}")
            print(f"   - 리프레시 토큰: {'있음' if final_account['refresh_token'] else '없음'}")
            print(f"   - 토큰 만료: {final_account['token_expiry']}")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        logger.error(f"인증 플로우 테스트 실패: {str(e)}", exc_info=True)
    
    finally:
        # 웹서버 상태 확인
        web_server_manager = get_auth_web_server_manager()
        if web_server_manager.is_running:
            print("\n🛑 웹서버를 중지합니다...")
            await web_server_manager.auth_web_server_manager_stop()


async def test_bulk_auth():
    """일괄 인증 테스트"""
    
    print("\n" + "="*60)
    print("일괄 인증 테스트")
    print("="*60 + "\n")
    
    auth_orchestrator = get_auth_orchestrator()
    
    # 모든 계정 상태 확인
    accounts_status = await auth_orchestrator.auth_orchestrator_get_all_accounts_status()
    
    if not accounts_status:
        print("❌ 등록된 계정이 없습니다.")
        return
    
    print(f"📋 총 {len(accounts_status)}개 계정 발견:")
    for account in accounts_status:
        token_status = "만료됨" if account['token_expired'] else "유효함"
        print(f"   - {account['user_id']}: {account['status']} (토큰: {token_status})")
    
    # 일괄 인증 실행 확인
    proceed = input("\n모든 계정에 대해 일괄 인증을 시작할까요? (y/n): ")
    if proceed.lower() != 'y':
        return
    
    # 일괄 인증 요청
    from modules.auth import AuthBulkRequest
    
    user_ids = [acc['user_id'] for acc in accounts_status]
    bulk_request = AuthBulkRequest(
        user_ids=user_ids,
        max_concurrent=1,  # 순차 처리
        timeout_minutes=10
    )
    
    bulk_response = await auth_orchestrator.auth_orchestrator_bulk_authentication(bulk_request)
    
    print(f"\n📊 일괄 인증 결과:")
    print(f"   - 총 사용자: {bulk_response.total_users}")
    print(f"   - 인증 대기: {bulk_response.pending_count}")
    print(f"   - 이미 완료: {bulk_response.completed_count}")
    print(f"   - 실패: {bulk_response.failed_count}")
    
    if bulk_response.pending_count > 0:
        print(f"\n🔗 인증이 필요한 계정:")
        for status in bulk_response.user_statuses:
            if status.status == "PENDING" and status.auth_url:
                print(f"\n   {status.user_id}:")
                print(f"   {status.auth_url[:100]}...")


async def main():
    """메인 테스트 함수"""
    
    config = get_config()
    
    print("\n" + "="*60)
    print("OAuth 인증 플로우 테스트 프로그램")
    print("="*60)
    print(f"\n환경 설정:")
    print(f"   - Redirect URI: http://localhost:5000/auth/callback")
    print(f"   - 웹서버 포트: 5000")
    
    while True:
        print("\n메뉴:")
        print("1. 단일 사용자 인증 테스트")
        print("2. 일괄 인증 테스트")
        print("3. 모든 계정 상태 확인")
        print("0. 종료")
        
        choice = input("\n선택: ")
        
        if choice == '1':
            await test_auth_flow()
        elif choice == '2':
            await test_bulk_auth()
        elif choice == '3':
            auth_orchestrator = get_auth_orchestrator()
            accounts = await auth_orchestrator.auth_orchestrator_get_all_accounts_status()
            
            print(f"\n📊 총 {len(accounts)}개 계정:")
            for acc in accounts:
                token_status = "만료됨" if acc['token_expired'] else "유효함"
                session_info = f", 세션: {acc['pending_session_id'][:10]}..." if acc['has_pending_session'] else ""
                print(f"   - {acc['user_id']}: {acc['status']} (토큰: {token_status}{session_info})")
        elif choice == '0':
            print("\n프로그램을 종료합니다.")
            
            # 웹서버 정리
            web_server_manager = get_auth_web_server_manager()
            if web_server_manager.is_running:
                await web_server_manager.auth_web_server_manager_stop()
            
            # 오케스트레이터 정리
            auth_orchestrator = get_auth_orchestrator()
            await auth_orchestrator.auth_orchestrator_shutdown()
            
            break
        else:
            print("❌ 잘못된 선택입니다.")


if __name__ == "__main__":
    asyncio.run(main())
