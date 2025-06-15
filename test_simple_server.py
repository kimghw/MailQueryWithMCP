#!/usr/bin/env python3
"""
간단한 OAuth 콜백 테스트 서버
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
from datetime import datetime

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/health':
            # 헬스체크
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "message": "OAuth callback server is running"
            }
            self.wfile.write(json.dumps(response).encode())
            
        elif parsed_path.path == '/auth/callback':
            # OAuth 콜백 처리
            query_params = parse_qs(parsed_path.query)
            
            print("\n=== OAuth 콜백 수신됨 ===")
            print(f"시간: {datetime.now()}")
            print(f"쿼리 파라미터:")
            
            for key, values in query_params.items():
                value = values[0] if values else ""
                if key in ['code', 'state']:
                    # 민감한 정보는 일부만 표시
                    display_value = f"{value[:10]}..." if len(value) > 10 else value
                    print(f"  {key}: {display_value}")
                else:
                    print(f"  {key}: {value}")
            
            # 성공 응답 HTML
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
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
            self.wfile.write(html.encode('utf-8'))
            
        else:
            # 기본 응답
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OAuth Callback Server Running")
    
    def log_message(self, format, *args):
        # 기본 로그 메시지 억제 (필요시 주석 해제)
        pass

def run_server(port=5000):
    server_address = ('localhost', port)
    httpd = HTTPServer(server_address, CallbackHandler)
    
    print(f"\n=== OAuth 콜백 서버 시작됨 ===")
    print(f"URL: http://localhost:{port}")
    print(f"콜백 엔드포인트: http://localhost:{port}/auth/callback")
    print(f"헬스체크: http://localhost:{port}/health")
    print("\n대기 중... (Ctrl+C로 종료)")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n서버를 종료합니다...")
        httpd.shutdown()

if __name__ == "__main__":
    print("=== 간단한 OAuth 콜백 테스트 서버 ===")
    print("이 서버는 OAuth 콜백을 수신하고 로그를 출력합니다.")
    print("Azure AD에서 리다이렉트 URI가 http://localhost:5000/auth/callback로 설정되어 있는지 확인하세요.\n")
    
    run_server(5000)
