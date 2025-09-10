#!/bin/bash
# Cloudflare Tunnel만 실행하는 스크립트
# 사용법: ./tunnel_only.sh [포트번호]

# 첫 번째 인자로 포트를 받거나 기본값 8002 사용
PORT=${1:-8002}

echo "🌐 Cloudflare Tunnel 실행 (포트: $PORT)"
echo "URL이 생성되면 tunnel_output_${PORT}.log에 저장됩니다."
echo ""

# Run tunnel and save output
cloudflared tunnel --url http://localhost:${PORT} 2>&1 | tee tunnel_output_${PORT}.log