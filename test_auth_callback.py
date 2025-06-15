"""
Auth 모듈 콜백 처리 테스트 스크립트

OAuth 콜백 처리 웹서버의 기능을 직접 테스트합니다.
실제 HTTP 요청을 통해 콜백 처리 로직을 검증합니다.
"""

import asyncio
import sys
import os
import aiohttp
from urllib.parse import urlencode
from datetime import datetime, timedelta

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.auth.auth_web_server import AuthWebServer, get_auth_web_server_manager
from modules.auth.auth_schema import AuthSession, AuthState, AuthCallback
from modules.auth._auth_helpers import (
    auth_generate_session_id,
    auth_generate_state_token,
    auth_create_session_expiry
)
from infra.core.logger import get_logger

logger = get_logger(__name__)


class MockTokenService:
    """테스트용 Mock 토큰 서비스"""
    
    async def store_tokens(self, user_id: str, token_info: dict) -> str:
        """Mock 토큰 저장"""
        logger.info(f"Mock: 토큰 저장됨 - user_id={user_id}")
        return f"account_{user_id}_123"


class MockOAuthClient:
    """테스트용 Mock OAuth 클라이언트"""
    
    async def exchange_code_for_tokens(self, code: str) -> dict:
        """Mock 토큰 교환"""
        if code == "invalid_code":
            raise Exception("Invalid authorization code")
        
        return {
            "access_token": f"mock_access_token_{code[:8]}",
            "refresh_token": f"mock_refresh_token_{code[:8]}",
            "expires_in": 3600,
            "scope": "https://graph.microsoft.com/Mail.Read",
            "token_type": "Bearer"
        }


async def test_callback_processing():
    """콜백 처리 기능 종합 테스트"""
    print("=== Auth 콜백 처리 테스트 시작 ===")
    
    # 1. 테스트용 세션 저장소 및 웹서버 설정
    print("\n1. 웹서버 초기화:")
    session_store = {}
    web_server = AuthWebServer()
    
    # Mock 서비스 주입
    web_server.token_service = MockTokenService()
    web_server.oauth_client = MockOAuthClient()
    web_server.set_session_store(session_store)
    
    try:
        # 웹서버 시작 (동적 포트)
        server_url = await web_server.auth_web_server_start(port=0)  # 0 = 동적 포트
        port = int(server_url.split(":")[-1])
        print(f"   ✓ 웹서버 시작됨: {server_url}")
        
        # 2. 테스트용 세션 생성
        print("\n2. 테스트 세션 생성:")
        user_id = "test_user@example.com"
        session_id = auth_generate_session_id(user_id)
        state = auth_generate_state_token()
        
        session = AuthSession(
            session_id=session_id,
            user_id=user_id,
            state=state,
            auth_url=f"https://example.com/auth?state={state}",
            expires_at=auth_create_session_expiry(10)
        )
        
        session_store[state] = session
        print(f"   ✓ 테스트 세션 생성:")
        print(f"     - 세션 ID: {session_id}")
        print(f"     - State: {state[:20]}...")
        print(f"     - 사용자: {user_id}")
        
        # 3. 성공 콜백 테스트
        print("\n3. 성공 콜백 처리 테스트:")
        await test_successful_callback(port, state, session_store)
        
        # 4. 새로운 세션으로 오류 콜백 테스트
        print("\n4. 오류 콜백 처리 테스트:")
        error_state = auth_generate_state_token()
        error_session = AuthSession(
            session_id=auth_generate_session_id("error_user"),
            user_id="error_user@example.com", 
            state=error_state,
            auth_url=f"https://example.com/auth?state={error_state}",
            expires_at=auth_create_session_expiry(10)
        )
        session_store[error_state] = error_session
        
        await test_error_callback(port, error_state, session_store)
        
        # 5. 무효한 state 테스트
        print("\n5. 무효한 state 처리 테스트:")
        await test_invalid_state_callback(port)
        
        # 6. 헬스 체크 테스트
        print("\n6. 헬스 체크 테스트:")
        await test_health_check(port)
        
        print("\n=== 모든 콜백 테스트 완료 ===")
        
    except Exception as e:
        print(f"\n✗ 테스트 실행 실패: {str(e)}")
        logger.error(f"콜백 테스트 실패: {str(e)}")
        
    finally:
        # 웹서버 정리
        try:
            await web_server.auth_web_server_stop()
            print("\n웹서버 정리 완료")
        except Exception as e:
            print(f"웹서버 정리 실패: {str(e)}")


async def test_successful_callback(port: int, state: str, session_store: dict):
    """성공적인 콜백 처리 테스트"""
    callback_params = {
        "code": "mock_authorization_code_12345",
        "state": state,
        "session_state": "mock_session_state"
    }
    
    callback_url = f"http://localhost:{port}/auth/callback?" + urlencode(callback_params)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(callback_url) as response:
                content = await response.text()
                
                print(f"   응답 상태: {response.status}")
                print(f"   응답 크기: {len(content)} bytes")
                
                if response.status == 200:
                    print("   ✓ 성공 콜백 처리 완료")
                    
                    # 세션 상태 확인
                    session_obj = session_store.get(state)
                    if session_obj:
                        print(f"   ✓ 세션 상태: {session_obj.status}")
                        if session_obj.status == AuthState.COMPLETED:
                            print("   ✓ 토큰 교환 완료")
                            if session_obj.token_info:
                                print(f"   ✓ 토큰 정보 저장됨")
                        else:
                            print(f"   ⚠ 예상과 다른 세션 상태: {session_obj.status}")
                    else:
                        print("   ✗ 세션을 찾을 수 없음")
                else:
                    print(f"   ✗ 예상하지 못한 응답 상태: {response.status}")
                    print(f"   응답 내용: {content[:200]}...")
                    
        except Exception as e:
            print(f"   ✗ 성공 콜백 테스트 실패: {str(e)}")


async def test_error_callback(port: int, state: str, session_store: dict):
    """오류 콜백 처리 테스트"""
    error_params = {
        "error": "access_denied",
        "error_description": "사용자가 인증을 거부했습니다",
        "state": state
    }
    
    callback_url = f"http://localhost:{port}/auth/callback?" + urlencode(error_params)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(callback_url) as response:
                content = await response.text()
                
                print(f"   응답 상태: {response.status}")
                
                if response.status == 400:  # Bad Request for OAuth errors
                    print("   ✓ 오류 콜백 처리 완료")
                    
                    # 세션 상태 확인
                    session_obj = session_store.get(state)
                    if session_obj and session_obj.status == AuthState.FAILED:
                        print("   ✓ 세션 상태가 FAILED로 업데이트됨")
                        print(f"   ✓ 오류 메시지: {session_obj.error_message}")
                    else:
                        print("   ⚠ 세션 상태가 예상과 다름")
                        
                    if "access_denied" in content:
                        print("   ✓ 오류 페이지에 적절한 메시지 포함됨")
                else:
                    print(f"   ✗ 예상하지 못한 응답 상태: {response.status}")
                    
        except Exception as e:
            print(f"   ✗ 오류 콜백 테스트 실패: {str(e)}")


async def test_invalid_state_callback(port: int):
    """무효한 state로 콜백 테스트"""
    invalid_params = {
        "code": "some_code",
        "state": "invalid_state_token_12345"
    }
    
    callback_url = f"http://localhost:{port}/auth/callback?" + urlencode(invalid_params)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(callback_url) as response:
                content = await response.text()
                
                print(f"   응답 상태: {response.status}")
                
                if response.status == 400:
                    print("   ✓ 무효한 state 거부됨")
                    if "유효하지 않은" in content:
                        print("   ✓ 적절한 오류 메시지 표시됨")
                else:
                    print(f"   ✗ 예상하지 못한 응답 상태: {response.status}")
                    
        except Exception as e:
            print(f"   ✗ 무효한 state 테스트 실패: {str(e)}")


async def test_health_check(port: int):
    """헬스 체크 엔드포인트 테스트"""
    health_url = f"http://localhost:{port}/health"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(health_url) as response:
                data = await response.json()
                
                print(f"   응답 상태: {response.status}")
                
                if response.status == 200:
                    print("   ✓ 헬스 체크 성공")
                    print(f"   ✓ 서버 상태: {data.get('status')}")
                    print(f"   ✓ 서버 타입: {data.get('server')}")
                else:
                    print(f"   ✗ 헬스 체크 실패: {response.status}")
                    
        except Exception as e:
            print(f"   ✗ 헬스 체크 테스트 실패: {str(e)}")


async def test_concurrent_callbacks():
    """동시 다중 콜백 처리 테스트"""
    print("\n=== 동시 다중 콜백 테스트 시작 ===")
    
    session_store = {}
    web_server = AuthWebServer()
    web_server.token_service = MockTokenService()
    web_server.oauth_client = MockOAuthClient()
    web_server.set_session_store(session_store)
    
    try:
        server_url = await web_server.auth_web_server_start(port=0)
        port = int(server_url.split(":")[-1])
        print(f"웹서버 시작됨: {server_url}")
        
        # 여러 세션 생성
        sessions = []
        for i in range(5):
            user_id = f"user{i}@example.com"
            session_id = auth_generate_session_id(user_id)
            state = auth_generate_state_token()
            
            session = AuthSession(
                session_id=session_id,
                user_id=user_id,
                state=state,
                auth_url=f"https://example.com/auth?state={state}",
                expires_at=auth_create_session_expiry(10)
            )
            
            session_store[state] = session
            sessions.append((state, user_id))
        
        print(f"생성된 세션: {len(sessions)}개")
        
        # 동시 콜백 요청
        async def send_callback(state, user_id):
            callback_params = {
                "code": f"code_for_{user_id}",
                "state": state
            }
            callback_url = f"http://localhost:{port}/auth/callback?" + urlencode(callback_params)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(callback_url) as response:
                    return response.status, user_id
        
        # 모든 콜백 동시 실행
        tasks = [send_callback(state, user_id) for state, user_id in sessions]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = 0
        for result in results:
            if isinstance(result, tuple) and result[0] == 200:
                success_count += 1
                print(f"   ✓ {result[1]} 콜백 성공")
            else:
                print(f"   ✗ 콜백 실패: {result}")
        
        print(f"\n동시 콜백 결과: {success_count}/{len(sessions)} 성공")
        
        # 세션 상태 확인
        completed_count = 0
        for state, user_id in sessions:
            session_obj = session_store.get(state)
            if session_obj and session_obj.status == AuthState.COMPLETED:
                completed_count += 1
        
        print(f"완료된 세션: {completed_count}/{len(sessions)}")
        
    except Exception as e:
        print(f"동시 콜백 테스트 실패: {str(e)}")
        
    finally:
        await web_server.auth_web_server_stop()
        print("동시 콜백 테스트 정리 완료")


if __name__ == "__main__":
    try:
        # 기본 콜백 처리 테스트
        asyncio.run(test_callback_processing())
        
        print("\n" + "="*50)
        
        # 동시 다중 콜백 테스트
        asyncio.run(test_concurrent_callbacks())
        
    except KeyboardInterrupt:
        print("\n테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n테스트 실행 중 오류 발생: {str(e)}")
