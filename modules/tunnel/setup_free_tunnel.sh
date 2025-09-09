#!/bin/bash
# 무료 도메인으로 Cloudflare Tunnel 설정

echo "🌐 무료 도메인으로 Cloudflare Tunnel 설정"
echo "========================================"
echo ""
echo "옵션을 선택하세요:"
echo "1) Freenom 도메인 사용 (.tk, .ml, .ga, .cf)"
echo "2) DuckDNS 서브도메인 사용" 
echo "3) 이미 Cloudflare에 등록된 도메인 사용"
echo ""
read -p "선택 (1-3): " choice

case $choice in
    1)
        echo ""
        echo "📌 Freenom 설정 가이드:"
        echo "1. https://freenom.com 에서 무료 도메인 등록"
        echo "2. Cloudflare.com에 로그인 후 'Add Site' 클릭"
        echo "3. 등록한 도메인 입력 (예: yourname.tk)"
        echo "4. Free 플랜 선택"
        echo "5. Cloudflare가 제공하는 네임서버를 Freenom에 설정"
        echo ""
        read -p "위 단계를 완료하셨나요? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            read -p "등록한 도메인을 입력하세요: " DOMAIN
        else
            echo "도메인 등록 후 다시 실행해주세요."
            exit 1
        fi
        ;;
    2)
        echo ""
        echo "📌 DuckDNS 설정:"
        echo "1. https://duckdns.org 방문"
        echo "2. GitHub/Reddit 계정으로 로그인"
        echo "3. 서브도메인 생성 (예: mcp-server)"
        echo ""
        read -p "DuckDNS 서브도메인 (xxxxx.duckdns.org에서 xxxxx 부분): " SUBDOMAIN
        DOMAIN="${SUBDOMAIN}.duckdns.org"
        echo ""
        echo "⚠️  DuckDNS는 Cloudflare DNS를 직접 사용할 수 없습니다."
        echo "대신 DuckDNS의 동적 DNS 기능을 사용하거나,"
        echo "다른 터널링 서비스 (ngrok, localtunnel)를 고려해보세요."
        exit 0
        ;;
    3)
        read -p "도메인을 입력하세요: " DOMAIN
        ;;
    *)
        echo "잘못된 선택입니다."
        exit 1
        ;;
esac

# Cloudflare Tunnel 설정
echo ""
echo "🚀 Cloudflare Tunnel 설정 시작..."

# 로그인
if [ ! -f "$HOME/.cloudflared/cert.pem" ]; then
    cloudflared tunnel login
fi

# 터널 생성
TUNNEL_NAME="mcp-free-tunnel"
cloudflared tunnel create $TUNNEL_NAME

# DNS 라우트 설정
echo "🔗 DNS 라우트 설정..."
cloudflared tunnel route dns $TUNNEL_NAME $DOMAIN

# 설정 파일 생성
TUNNEL_ID=$(cloudflared tunnel list | grep $TUNNEL_NAME | awk '{print $1}')
cat > ~/.cloudflared/config.yml << EOF
tunnel: $TUNNEL_ID
credentials-file: $HOME/.cloudflared/$TUNNEL_ID.json

ingress:
  - hostname: $DOMAIN
    service: http://localhost:8002
  - service: http_status:404
EOF

echo ""
echo "✅ 설정 완료!"
echo "🌐 고정 URL: https://$DOMAIN"
echo ""
echo "실행 명령:"
echo "cloudflared tunnel run $TUNNEL_NAME"
echo ""
echo "백그라운드 실행:"
echo "nohup cloudflared tunnel run $TUNNEL_NAME &"