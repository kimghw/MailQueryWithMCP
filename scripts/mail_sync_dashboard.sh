#!/bin/bash
# IACSGRAPH Mail Sync 대시보드

clear
echo "╔══════════════════════════════════════════════════════╗"
echo "║        IACSGRAPH Mail Sync Monitor Dashboard         ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

LOG_FILE="$HOME/IACSGRAPH/logs/mail_sync.log"
ENV_FILE="$HOME/IACSGRAPH/.env"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 1. 시스템 상태
echo -e "${BLUE}📊 시스템 상태${NC}"
echo "─────────────────────────────────────"
echo -n "Cron 서비스: "
if systemctl is-active --quiet cron; then
    echo -e "${GREEN}● 실행중${NC}"
else
    echo -e "${RED}● 중지됨${NC}"
fi

# Cron 표현식 확인
CRON_EXPR=$(crontab -l 2>/dev/null | grep sync_mails.py | awk '{print $1" "$2" "$3" "$4" "$5}')
echo -n "Cron 스케줄: "
if [[ "$CRON_EXPR" == *"**"* ]]; then
    echo -e "${RED}$CRON_EXPR (오류 - 수정 필요)${NC}"
else
    echo -e "${GREEN}$CRON_EXPR${NC}"
fi
echo ""

# 2. 최근 실행 이력
echo -e "${BLUE}📅 최근 실행 이력${NC}"
echo "─────────────────────────────────────"
if [ -f "$LOG_FILE" ]; then
    # 최근 5번의 동기화 시작 시간
    echo "최근 실행 시간:"
    grep "메일 동기화 시작" "$LOG_FILE" | tail -5 | while read line; do
        echo "  $line"
    done
    echo ""
    
    # 마지막 실행 결과
    LAST_SYNC=$(grep "동기화 완료" "$LOG_FILE" | tail -1)
    if [ ! -z "$LAST_SYNC" ]; then
        echo "마지막 실행 결과:"
        echo "  $LAST_SYNC"
    fi
fi
echo ""

# 3. 오늘의 통계
echo -e "${BLUE}📈 오늘의 통계${NC}"
echo "─────────────────────────────────────"
TODAY=$(date +%Y-%m-%d)
if [ -f "$LOG_FILE" ]; then
    RUNS=$(grep "$TODAY" "$LOG_FILE" | grep "동기화 완료" | wc -l)
    TOTAL_MAILS=$(grep "$TODAY" "$LOG_FILE" | grep -oE "메일=[0-9]+" | awk -F= '{sum+=$2} END {print sum}')
    SAVED_MAILS=$(grep "$TODAY" "$LOG_FILE" | grep -oE "저장=[0-9]+" | awk -F= '{sum+=$2} END {print sum}')
    FILTERED=$(grep "$TODAY" "$LOG_FILE" | grep -oE "필터링: [0-9]+" | awk -F': ' '{sum+=$2} END {print sum}')
    
    echo "실행 횟수: $RUNS 회"
    echo "처리된 메일: ${TOTAL_MAILS:-0} 개"
    echo "저장된 메일: ${SAVED_MAILS:-0} 개"
    echo "필터링된 메일: ${FILTERED:-0} 개"
    
    if [ "${TOTAL_MAILS:-0}" -gt 0 ]; then
        SAVE_RATE=$((${SAVED_MAILS:-0} * 100 / ${TOTAL_MAILS:-0}))
        echo -n "저장률: "
        if [ $SAVE_RATE -lt 20 ]; then
            echo -e "${RED}${SAVE_RATE}%${NC}"
        elif [ $SAVE_RATE -lt 50 ]; then
            echo -e "${YELLOW}${SAVE_RATE}%${NC}"
        else
            echo -e "${GREEN}${SAVE_RATE}%${NC}"
        fi
    fi
fi
echo ""

# 4. 필터 설정
echo -e "${BLUE}🔍 필터 설정${NC}"
echo "─────────────────────────────────────"
if [ -f "$ENV_FILE" ]; then
    FILTER_ENABLED=$(grep "ENABLE_MAIL_FILTERING" "$ENV_FILE" | cut -d= -f2)
    echo -n "필터링 상태: "
    if [ "$FILTER_ENABLED" = "true" ]; then
        echo -e "${YELLOW}활성화${NC}"
        
        # 차단 설정 표시
        BLOCKED_DOMAINS=$(grep "BLOCKED_DOMAINS" "$ENV_FILE" | cut -d= -f2)
        if [ ! -z "$BLOCKED_DOMAINS" ]; then
            echo "차단 도메인:"
            echo "$BLOCKED_DOMAINS" | tr ',' '\n' | while read domain; do
                echo "  • $domain"
            done
        fi
        
        BLOCKED_KEYWORDS=$(grep "BLOCKED_KEYWORDS" "$ENV_FILE" | cut -d= -f2)
        if [ ! -z "$BLOCKED_KEYWORDS" ]; then
            echo "차단 키워드:"
            echo "$BLOCKED_KEYWORDS" | tr ',' '\n' | while read keyword; do
                echo "  • $keyword"
            done
        fi
    else
        echo -e "${GREEN}비활성화${NC}"
    fi
fi
echo ""

# 5. 다음 실행 예정
echo -e "${BLUE}⏰ 다음 실행 예정${NC}"
echo "─────────────────────────────────────"
CURRENT_MIN=$(date +%M)
CURRENT_HOUR=$(date +%H)
if [ $CURRENT_MIN -lt 30 ]; then
    NEXT_TIME="${CURRENT_HOUR}:30"
else
    NEXT_HOUR=$(date -d "+1 hour" +%H)
    NEXT_TIME="${NEXT_HOUR}:00"
fi
echo "예정 시간: $(date +%Y-%m-%d) $NEXT_TIME"
echo ""

# 6. 최근 오류
echo -e "${BLUE}❌ 최근 오류${NC}"
echo "─────────────────────────────────────"
ERROR_COUNT=$(grep -E "ERROR|실패|CRITICAL" "$LOG_FILE" 2>/dev/null | grep "$TODAY" | wc -l)
if [ $ERROR_COUNT -gt 0 ]; then
    echo -e "${RED}오늘 $ERROR_COUNT 건의 오류 발생${NC}"
    grep -E "ERROR|실패|CRITICAL" "$LOG_FILE" | grep "$TODAY" | tail -3
else
    echo -e "${GREEN}오늘 오류 없음${NC}"
fi
echo ""

# 7. 권장사항
echo -e "${BLUE}💡 권장사항${NC}"
echo "─────────────────────────────────────"
if [[ "$CRON_EXPR" == *"**"* ]]; then
    echo -e "${RED}• Cron 표현식을 수정하세요 (*/30 * * * *)${NC}"
fi

if [ "${SAVED_MAILS:-0}" -eq 0 ] && [ "${TOTAL_MAILS:-0}" -gt 0 ]; then
    echo -e "${YELLOW}• 모든 메일이 필터링되고 있습니다. 필터 설정을 검토하세요.${NC}"
fi

if [ $ERROR_COUNT -gt 5 ]; then
    echo -e "${RED}• 오류가 많이 발생하고 있습니다. 로그를 확인하세요.${NC}"
fi
echo ""

# 8. 유용한 명령어
echo -e "${BLUE}🛠️  유용한 명령어${NC}"
echo "─────────────────────────────────────"
echo "실시간 로그: tail -f $LOG_FILE"
echo "수동 실행: cd ~/IACSGRAPH && uv run python scripts/sync_mails.py"
echo "Cron 편집: crontab -e"
echo "필터 설정: nano ~/IACSGRAPH/.env"