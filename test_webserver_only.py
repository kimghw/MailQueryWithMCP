#!/usr/bin/env python3
"""
웹서버 단독 테스트

OAuth 콜백 웹서버가 제대로 동작하는지 확인하는 테스트입니다.
"""

import asyncio
import sys
import os
import time
import urllib.request
import urllib.error
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.auth.auth_web_server import AuthWebServer
from infra.core.logger import get_logger

logger = get_logger(__name__)

async def test_webserver_only():
    """웹서버 단독 테스트"""
    print("=" * 60)
    print("OAuth 콜백 웹서버 단독 테스트")
    print("=" * 60)
    
    server = None
    try:
        # 1. 웹서버 생성 및 시작
        print("\n1. 웹서버 시작")
        print("-" * 40)
        
        server = AuthWebServer()
        server_url = await server.auth_web_server_start(port=5000)
        
        print(f"✓ 웹서버 시작됨: {server_url}")
        print(f"✓ 실행 상태: {server.is_running}")
        
        # 2. Health check 테스트
        print("\n2. Health Check 테스트")
        print("-" * 40)
        
        # 잠시 대기 (서버 완전 시작 대기)
        await asyncio.sleep(1)
        
        try:
            with urllib.request.urlopen(f"{server_url}/health", timeout=5) as response:
                if response.status == 200:
                    health_data = json.loads(response.read().decode())
                    print(f"✓ Health check 성공: {health_data}")
                else:
                    print(f"✗ Health check 실패: HTTP {response.status}")
        except Exception as e:
            print(f"✗ Health check 요청 실패: {str(e)}")
        
        # 3. 콜백 엔드포인트 테스트 (GET 요청)
        print("\n3. 콜백 엔드포인트 테스트")
        print("-" * 40)
        
        try:
            # 빈 콜백 요청 (에러 응답 예상)
            callback_url = f"{server_url}/auth/callback"
            try:
                with urllib.request.urlopen(callback_url, timeout=5) as response:
                    print(f"✓ 콜백 엔드포인트 응답: HTTP {response.status}")
                    content = response.read().decode()[:200]
                    print(f"응답 내용: {content}...")
            except urllib.error.HTTPError as http_err:
                print(f"✓ 콜백 엔드포인트 응답: HTTP {http_err.code}")
                if http_err.code == 400:
                    print("✓ 예상된 400 에러 (빈 매개변수)")
        except Exception as e:
            print(f"✗ 콜백 엔드포인트 요청 실패: {str(e)}")
        
        # 4. 포트 확인
        print("\n4. 포트 상태 확인")
        print("-" * 40)
        
        import subprocess
        try:
            result = subprocess.run(
                ["netstat", "-tlnp"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            lines = result.stdout.split('\n')
            port_5000_lines = [line for line in lines if ':5000' in line]
            
            if port_5000_lines:
                print("✓ 포트 5000 사용 중:")
                for line in port_5000_lines:
                    print(f"  {line.strip()}")
            else:
                print("✗ 포트 5000이 사용되지 않음")
                
        except Exception as e:
            print(f"포트 확인 실패: {str(e)}")
        
        # 5. 수동 테스트 안내
        print("\n5. 수동 테스트")
        print("-" * 40)
        print(f"브라우저에서 다음 URL들을 테스트해보세요:")
        print(f"  Health Check: {server_url}/health")
        print(f"  콜백 테스트: {server_url}/auth/callback")
        print("\n10초 동안 대기합니다...")
        
        # 10초 대기
        for i in range(10, 0, -1):
            print(f"\r남은 시간: {i}초", end="", flush=True)
            await asyncio.sleep(1)
        print("\n")
        
    except Exception as e:
        print(f"✗ 웹서버 테스트 실패: {str(e)}")
        logger.error(f"웹서버 테스트 실패: {str(e)}", exc_info=True)
        
    finally:
        # 6. 웹서버 정리
        print("\n6. 웹서버 정리")
        print("-" * 40)
        
        if server and server.is_running:
            await server.auth_web_server_stop()
            print("✓ 웹서버 중지됨")
        else:
            print("웹서버가 실행되지 않았음")

if __name__ == "__main__":
    asyncio.run(test_webserver_only())
