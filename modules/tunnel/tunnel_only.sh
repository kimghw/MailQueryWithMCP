#!/bin/bash
# Cloudflare Tunnel만 실행하는 스크립트

PORT=8002

echo "🌐 Cloudflare Tunnel 실행 (포트: $PORT)"
echo "URL이 생성되면 tunnel_output.log에 저장됩니다."
echo ""

# Run tunnel and save output
cloudflared tunnel --url http://localhost:${PORT} 2>&1 | tee tunnel_output.log