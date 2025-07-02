#!/bin/bash
# IACSGRAPH Mail Sync 모니터링 스크립트

LOG_FILE="/home/kimghw/IACSGRAPH/logs/mail_sync.log"

echo "📊 IACSGRAPH Mail Sync 모니터링"
echo "================================"

# 마지막 실행 시간
if [ -f "$LOG_FILE" ]; then
    echo -e "\n📅 마지막 실행:"
    grep "메일 동기화 시작" "$LOG_FILE" | tail -1
    
    echo -e "\n✅ 최근 성공:"
    grep "동기화 완료" "$LOG_FILE" | tail -5
    
    echo -e "\n❌ 최근 오류:"
    grep -E "ERROR|CRITICAL|실패" "$LOG_FILE" | tail -5
    
    echo -e "\n📈 오늘의 통계:"
    TODAY=$(date +%Y-%m-%d)
    grep "$TODAY" "$LOG_FILE" | grep "동기화 완료" | wc -l | xargs echo "  - 실행 횟수:"
    grep "$TODAY" "$LOG_FILE" | grep -oE "메일=[0-9]+" | awk -F= '{sum+=$2} END {print "  - 총 메일 수: " sum}'
fi

echo -e "\n⏰ 다음 실행 예정:"
crontab -l | grep sync_mails.py | awk '{print "  - " $1, $2, $3, $4, $5}'
