#!/bin/bash
# Quick Start Script for MailQueryWithMCP
# Cloudflare Tunnel을 빠르게 시작하는 스크립트

set -e

PROJECT_DIR="/home/kimghw/MailQueryWithMCP"
cd "$PROJECT_DIR"

echo "🚀 MailQueryWithMCP Quick Start"
echo "=================================="
echo ""

# Unified Server 시작
echo "1️⃣ Unified Server 시작 중..."
if pgrep -f "unified_http_server.py" > /dev/null; then
    echo "   ✅ Unified Server가 이미 실행 중입니다"
else
    nohup bash "$PROJECT_DIR/entrypoints/production/run_unified_http.sh" > "$PROJECT_DIR/logs/unified_server.log" 2>&1 &
    echo $! > /tmp/unified_server.pid
    sleep 3

    if pgrep -f "unified_http_server.py" > /dev/null; then
        echo "   ✅ Unified Server 시작 성공"
    else
        echo "   ❌ Unified Server 시작 실패"
        echo "   로그 확인: cat $PROJECT_DIR/logs/unified_server.log"
        exit 1
    fi
fi

echo ""

# Quick Tunnel 시작
echo "2️⃣ Cloudflare Quick Tunnel 시작 중..."

# cloudflared 경로 확인
if command -v cloudflared &> /dev/null; then
    CLOUDFLARED="cloudflared"
elif [ -x "$HOME/.local/bin/cloudflared" ]; then
    CLOUDFLARED="$HOME/.local/bin/cloudflared"
else
    echo "   ❌ cloudflared가 설치되지 않았습니다"
    echo "   설치: ./cloudflare-manager.sh install"
    exit 1
fi

# Quick Tunnel이 이미 실행 중인지 확인
if pgrep -f "cloudflared.*tunnel.*--url" > /dev/null; then
    echo "   ✅ Quick Tunnel이 이미 실행 중입니다"

    # URL 추출
    TUNNEL_URL=$(grep -o "https://.*\.trycloudflare\.com" "$PROJECT_DIR/logs/quick_tunnel.log" 2>/dev/null | tail -1)
    if [ -n "$TUNNEL_URL" ]; then
        echo ""
        echo "=================================="
        echo "🌐 접속 URL: $TUNNEL_URL"
        echo "=================================="
    fi
else
    # Quick Tunnel 시작
    mkdir -p "$PROJECT_DIR/logs"
    nohup $CLOUDFLARED tunnel --url http://localhost:8000 > "$PROJECT_DIR/logs/quick_tunnel.log" 2>&1 &
    echo $! > /tmp/quick_tunnel.pid

    echo "   ⏳ Tunnel URL 생성 대기 중..."

    # URL이 생성될 때까지 대기 (최대 20초)
    for i in {1..10}; do
        sleep 2
        TUNNEL_URL=$(grep -o "https://.*\.trycloudflare\.com" "$PROJECT_DIR/logs/quick_tunnel.log" 2>/dev/null | tail -1)
        if [ -n "$TUNNEL_URL" ]; then
            echo "   ✅ Quick Tunnel 시작 성공"
            break
        fi
    done

    if [ -z "$TUNNEL_URL" ]; then
        echo "   ⚠️  Tunnel URL을 아직 가져올 수 없습니다"
        echo "   로그 확인: tail -f $PROJECT_DIR/logs/quick_tunnel.log"
    else
        echo ""
        echo "=================================="
        echo "🌐 접속 URL: $TUNNEL_URL"
        echo "=================================="
    fi
fi

echo ""
echo "✅ 모든 서비스가 시작되었습니다!"
echo ""
echo "📍 로컬 엔드포인트:"
echo "   http://localhost:8000/health"
echo ""
echo "📍 MCP 서버:"
echo "   • Mail Query:  /mail-query/"
echo "   • Enrollment:  /enrollment/"
echo "   • OneNote:     /onenote/"
echo "   • OneDrive:    /onedrive/"
echo "   • Teams:       /teams/"
echo ""
echo "📋 유용한 명령어:"
echo "   • 상태 확인:     ./cloudflare-manager.sh status"
echo "   • 로그 보기:     tail -f logs/quick_tunnel.log"
echo "   • 서버 중지:     pkill -f unified_http_server.py && pkill -f cloudflared"
echo ""
