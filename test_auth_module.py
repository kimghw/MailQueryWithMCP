"""
Auth 모듈 테스트 스크립트

Auth 모듈의 주요 기능들이 올바르게 구현되었는지 확인하는 테스트입니다.
"""

import asyncio
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.auth import (
    get_auth_orchestrator, 
    AuthStartRequest, 
    AuthBulkRequest,
    AuthCleanupRequest,
    auth_module_info
)


async def test_auth_module():
    """Auth 모듈 기본 기능 테스트"""
    print("=== Auth 모듈 테스트 시작 ===")
    
    # 1. 모듈 정보 확인
    print("\n1. 모듈 정보:")
    info = auth_module_info()
    for key, value in info.items():
        print(f"   {key}: {value}")
    
    # 2. 오케스트레이터 초기화
    print("\n2. 오케스트레이터 초기화:")
    try:
        auth_orchestrator = get_auth_orchestrator()
        print("   ✓ Auth 오케스트레이터 초기화 성공")
    except Exception as e:
        print(f"   ✗ 오케스트레이터 초기화 실패: {str(e)}")
        return
    
    # 3. 단일 사용자 인증 요청 (실제 인증은 하지 않고 세션 생성만)
    print("\n3. 단일 사용자 인증 요청:")
    try:
        request = AuthStartRequest(user_id="kimghw")
        response = await auth_orchestrator.auth_orchestrator_start_authentication(request)
        
        print(f"   ✓ 세션 생성 성공:")
        print(f"     - 세션 ID: {response.session_id}")
        print(f"     - State: {response.state[:20]}...")
        print(f"     - 인증 URL: {response.auth_url[:50]}...")
        print(f"     - 만료 시간: {response.expires_at}")
        
        session_id = response.session_id
        
    except Exception as e:
        print(f"   ✗ 인증 요청 실패: {str(e)}")
        return
    
    # 4. 세션 상태 확인
    print("\n4. 세션 상태 확인:")
    try:
        status = await auth_orchestrator.auth_orchestrator_get_session_status(session_id)
        print(f"   ✓ 세션 상태 조회 성공:")
        print(f"     - 상태: {status.status}")
        print(f"     - 메시지: {status.message}")
        print(f"     - 완료 여부: {status.is_completed}")
        
    except Exception as e:
        print(f"   ✗ 세션 상태 확인 실패: {str(e)}")
    
    # 5. 일괄 인증 요청 (토큰 상태 확인만)
    print("\n5. 일괄 인증 요청:")
    try:
        bulk_request = AuthBulkRequest(
            user_ids=["user1@example.com", "user2@example.com"],
            max_concurrent=2,
            timeout_minutes=10
        )
        bulk_response = await auth_orchestrator.auth_orchestrator_bulk_authentication(bulk_request)
        
        print(f"   ✓ 일괄 인증 요청 성공:")
        print(f"     - 총 사용자: {bulk_response.total_users}")
        print(f"     - 대기 중: {bulk_response.pending_count}")
        print(f"     - 완료: {bulk_response.completed_count}")
        print(f"     - 실패: {bulk_response.failed_count}")
        
    except Exception as e:
        print(f"   ✗ 일괄 인증 요청 실패: {str(e)}")
    
    # 6. 전체 계정 상태 조회
    print("\n6. 전체 계정 상태 조회:")
    try:
        accounts = await auth_orchestrator.auth_orchestrator_get_all_accounts_status()
        print(f"   ✓ 계정 상태 조회 성공: {len(accounts)}개 계정")
        
        for account in accounts[:3]:  # 최대 3개만 표시
            print(f"     - {account['user_id']}: {account.get('status', 'N/A')}")
            
    except Exception as e:
        print(f"   ✗ 계정 상태 조회 실패: {str(e)}")
    
    # 7. 세션 정리
    print("\n7. 세션 정리:")
    try:
        cleanup_request = AuthCleanupRequest(
            expire_threshold_minutes=0,  # 모든 세션 정리
            force_cleanup=True
        )
        cleanup_response = await auth_orchestrator.auth_orchestrator_cleanup_sessions(cleanup_request)
        
        print(f"   ✓ 세션 정리 성공:")
        print(f"     - 정리된 세션: {cleanup_response.cleaned_sessions}")
        print(f"     - 활성 세션: {cleanup_response.active_sessions}")
        
    except Exception as e:
        print(f"   ✗ 세션 정리 실패: {str(e)}")
    
    # 8. 오케스트레이터 종료
    print("\n8. 오케스트레이터 종료:")
    try:
        await auth_orchestrator.auth_orchestrator_shutdown()
        print("   ✓ 오케스트레이터 종료 성공")
        
    except Exception as e:
        print(f"   ✗ 오케스트레이터 종료 실패: {str(e)}")
    
    print("\n=== Auth 모듈 테스트 완료 ===")


if __name__ == "__main__":
    try:
        asyncio.run(test_auth_module())
    except KeyboardInterrupt:
        print("\n테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n테스트 중 오류 발생: {str(e)}")
