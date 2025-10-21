#!/bin/bash

# ngrok을 사용하여 로컬 서버를 공개 URL로 노출시키는 스크립트

echo "🚀 Setting up public access for Claude AI integration"
echo "=================================================="

# 서버가 실행 중인지 확인
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ Server is not running on port 8000"
    echo "Please start the server first:"
    echo "  python entrypoints/production/unified_http_server.py --port 8000"
    exit 1
fi

echo "✅ Server is running on port 8000"

# ngrok 설치 확인
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed"
    echo ""
    echo "Please install ngrok:"
    echo "1. Visit: https://ngrok.com/download"
    echo "2. Download and install ngrok for your OS"
    echo "3. Sign up for a free account: https://dashboard.ngrok.com/signup"
    echo "4. Add your authtoken: ngrok config add-authtoken YOUR_TOKEN"
    exit 1
fi

echo "✅ ngrok is installed"
echo ""
echo "Starting ngrok tunnel..."
echo "========================"

# ngrok을 백그라운드에서 시작
ngrok http 8000 &
NGROK_PID=$!

# ngrok이 시작될 때까지 대기
sleep 3

# ngrok URL 가져오기
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python -c "
import sys, json
data = json.load(sys.stdin)
if data['tunnels']:
    print(data['tunnels'][0]['public_url'])
")

if [ -z "$NGROK_URL" ]; then
    echo "❌ Failed to get ngrok URL"
    kill $NGROK_PID
    exit 1
fi

echo ""
echo "🎉 Success! Your server is now publicly accessible"
echo "=================================================="
echo ""
echo "📌 Public URLs:"
echo "   Base URL: $NGROK_URL"
echo "   OAuth Metadata: $NGROK_URL/.well-known/oauth-authorization-server"
echo "   DCR Endpoint: $NGROK_URL/oauth/register"
echo ""
echo "📝 Next Steps:"
echo "1. Update your .env file:"
echo "   DCR_BASE_URL=$NGROK_URL"
echo ""
echo "2. In Claude AI, add MCP server with:"
echo "   OAuth Metadata URL: $NGROK_URL/.well-known/oauth-authorization-server"
echo ""
echo "3. Update Azure AD redirect URI to:"
echo "   $NGROK_URL/enrollment/callback"
echo ""
echo "⚠️  Note: ngrok URL changes each time. For production, use a permanent domain."
echo ""
echo "Press Ctrl+C to stop the tunnel..."

# 종료 시그널 처리
trap "kill $NGROK_PID; echo 'Tunnel stopped.'; exit" INT TERM

# 대기
wait $NGROK_PID