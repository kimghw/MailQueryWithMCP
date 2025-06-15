#!/usr/bin/env python3
"""
수동 콜백 테스트 스크립트
웹서버를 실행하고 콜백 URL을 직접 테스트합니다.
"""

import asyncio
import sys
from aiohttp import web
from datetime import datetime

class SimpleCallbackServer:
    def __init__(self):
        self.app = None
        self.runner = None
        self.site = None
        
    async def handle_callback(self, request):
        """OAuth 콜백 처리"""
        print("\n=== OAuth 콜백 수신됨 ===")
        print(f"시간: {datetime.now()}")
        print(f"경로: {request.path}")
        print(f"쿼리 파라미터:")
        
        for key, value in request.query.items():
            if key in ['code', 'state']:
                # 민감한 정보는 일부만 표시
                display_value = f"{value[:10]}..." if len(value) > 10 else value
                print(f"  {key}: {display_value}")
            else:
                print(f"  {key}: {value}")
        
        # 성공 응답 HTML
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>인증 콜백 수신됨</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    text-align: center; 
                    padding: 50px;
                    background-color: #f0f0f0;
                }
                .container {
                    background-color: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    max-width: 600px;
                    margin: 0 auto;
                }
                .success { color: #4CAF50; }
                .info { color: #2196F3; margin: 20px 0; }
                pre {
                    background-color: #f5f5f5;
                    padding: 10px;
                    border-radius: 5px;
                    text-align: left;
                    overflow-x: auto;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="success">✓ OAuth 콜백이 성공적으로 수신되었습니다!</h1>
                <div class="info">
                    <p>서버가 콜백을 정상적으로 받았습니다.</p>
                    <p>터미널에서 상세 정보를 확인하세요.</p>
                </div>
                <p>이 창은 닫으셔도 됩니다.</p>
            </div>
        </body>
        </html>
        """
        
        return web.Response(text=html, content_type='text/html')
    
    async def handle_health(self, request):
        """헬스체크 엔드포인트"""
        return web.json_response({
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "message": "OAuth callback server is running"
        })
    
    async def start_server(self, port=5000):
        """서버 시작"""
        self.app = web.Application()
        
        # 라우트 설정
        self.app.router.add_get('/auth/callback', self.handle_callback)
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/', lambda r: web.Response(text="OAuth Callback Server Running"))
        
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, 'localhost', port)
        await self.site.start()
        
        print(f"\n=== OAuth 콜백 서버 시작됨 ===")
        print(f"URL: http://localhost:{port}")
        print(f"콜백 엔드포인트: http://localhost:{port}/auth/callback")
        print(f"헬스체크: http://localhost:{port}/health")
        print("\n대기 중... (Ctrl+C로 종료)")
        
        return f"http://localhost:{port}"

async def main():
    server = SimpleCallbackServer()
    
    try:
        # 서버 시작
        await server.start_server(5000)
        
        # 무한 대기
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n서버를 종료합니다...")
    finally:
        if server.site:
            await server.site.stop()
        if server.runner:
            await server.runner.cleanup()

if __name__ == "__main__":
    print("=== OAuth 콜백 테스트 서버 ===")
    print("이 서버는 OAuth 콜백을 수신하고 로그를 출력합니다.")
    print("Azure AD에서 리다이렉트 URI가 http://localhost:5000/auth/callback로 설정되어 있는지 확인하세요.\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n종료됨")
        sys.exit(0)
