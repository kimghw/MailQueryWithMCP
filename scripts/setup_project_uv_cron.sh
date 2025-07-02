#!/bin/bash
# IACSGRAPH UV Cron 설정 스크립트

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 프로젝트 경로
PROJECT_DIR="/home/kimghw/IACSGRAPH"
UV_PATH="$PROJECT_DIR/.venv/bin/uv"
PYTHON_PATH="$PROJECT_DIR/.venv/bin/python"
LOG_DIR="$PROJECT_DIR/logs"
CRON_LOG="$LOG_DIR/mail_sync.log"

# UV 및 Python 존재 확인
if [ ! -f "$UV_PATH" ]; then
    echo -e "${RED}❌ UV를 찾을 수 없습니다: $UV_PATH${NC}"
    exit 1
fi

if [ ! -f "$PYTHON_PATH" ]; then
    echo -e "${RED}❌ Python을 찾을 수 없습니다: $PYTHON_PATH${NC}"
    exit 1
fi

echo -e "${BLUE}📁 프로젝트 경로: $PROJECT_DIR${NC}"
echo -e "${BLUE}🔧 UV 경로: $UV_PATH${NC}"
echo -e "${BLUE}🐍 Python 경로: $PYTHON_PATH${NC}"

# logs 디렉토리 생성
mkdir -p "$LOG_DIR"
echo -e "${GREEN}✓ 로그 디렉토리 생성: $LOG_DIR${NC}"

# 로그 로테이션 설정 함수
setup_log_rotation() {
    echo -e "\n${YELLOW}로그 로테이션을 설정하시겠습니까? (y/n)${NC}"
    read -r rotate_response
    
    if [ "$rotate_response" = "y" ]; then
        LOGROTATE_CONF="/etc/logrotate.d/iacsgraph"
        LOGROTATE_CONTENT="$CRON_LOG {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 $USER $USER
}"
        
        echo "$LOGROTATE_CONTENT" | sudo tee $LOGROTATE_CONF > /dev/null
        echo -e "${GREEN}✓ 로그 로테이션 설정 완료${NC}"
    fi
}

# Cron 주기 선택
echo -e "\n${YELLOW}실행 주기를 선택하세요:${NC}"
echo "1) 30분마다 (기본값)"
echo "2) 1시간마다"
echo "3) 2시간마다"
echo "4) 4시간마다"
echo "5) 매일 자정"
echo "6) 매일 오전 6시"
echo "7) 사용자 정의"
read -r cron_choice

case $cron_choice in
    1|"")
        CRON_SCHEDULE="*/30 * * * *"
        SCHEDULE_DESC="30분마다"
        ;;
    2)
        CRON_SCHEDULE="0 * * * *"
        SCHEDULE_DESC="1시간마다"
        ;;
    3)
        CRON_SCHEDULE="0 */2 * * *"
        SCHEDULE_DESC="2시간마다"
        ;;
    4)
        CRON_SCHEDULE="0 */4 * * *"
        SCHEDULE_DESC="4시간마다"
        ;;
    5)
        CRON_SCHEDULE="0 0 * * *"
        SCHEDULE_DESC="매일 자정"
        ;;
    6)
        CRON_SCHEDULE="0 6 * * *"
        SCHEDULE_DESC="매일 오전 6시"
        ;;
    7)
        echo -e "${YELLOW}Cron 표현식을 입력하세요 (예: */30 * * * *):${NC}"
        read -r CRON_SCHEDULE
        SCHEDULE_DESC="사용자 정의"
        ;;
    *)
        CRON_SCHEDULE="*/30 * * * *"
        SCHEDULE_DESC="30분마다 (기본값)"
        ;;
esac

# Cron 작업 문자열 생성
# 환경 변수 로드 및 로그 타임스탬프 추가
CRON_JOB="$CRON_SCHEDULE cd $PROJECT_DIR && source .venv/bin/activate && echo \"[\$(date '+\%Y-\%m-\%d \%H:\%M:\%S')] 메일 동기화 시작\" >> $CRON_LOG && $UV_PATH run python scripts/sync_mails.py >> $CRON_LOG 2>&1"

# 기존 crontab 백업
BACKUP_FILE="/tmp/crontab_backup_$(date +%Y%m%d_%H%M%S)"
crontab -l > "$BACKUP_FILE" 2>/dev/null || touch "$BACKUP_FILE"
echo -e "${GREEN}✓ 기존 crontab 백업: $BACKUP_FILE${NC}"

# 현재 crontab 가져오기
crontab -l > /tmp/current_cron 2>/dev/null || touch /tmp/current_cron

# 중복 확인 및 처리
if grep -q "sync_mails.py" /tmp/current_cron; then
    echo -e "\n${YELLOW}⚠️  기존 sync_mails.py cron 작업을 발견했습니다:${NC}"
    grep "sync_mails.py" /tmp/current_cron
    echo -e "\n${YELLOW}기존 설정을 제거하고 새로 추가하시겠습니까? (y/n)${NC}"
    read -r response
    if [ "$response" = "y" ]; then
        grep -v "sync_mails.py" /tmp/current_cron > /tmp/new_cron
        mv /tmp/new_cron /tmp/current_cron
    else
        rm /tmp/current_cron
        exit 0
    fi
fi

# 새 작업 추가
echo "$CRON_JOB" >> /tmp/current_cron
crontab /tmp/current_cron

echo -e "\n${GREEN}✅ Cron 작업이 추가되었습니다:${NC}"
echo -e "${BLUE}스케줄: $SCHEDULE_DESC${NC}"
echo "$CRON_JOB"

# 임시 파일 삭제
rm /tmp/current_cron

# 현재 설정 확인
echo -e "\n${BLUE}📋 현재 crontab 설정:${NC}"
crontab -l | grep sync_mails || echo "설정된 sync_mails 작업이 없습니다."

# 로그 로테이션 설정
setup_log_rotation

# systemd 타이머 옵션 제안
echo -e "\n${YELLOW}💡 팁: systemd 타이머를 사용하면 더 강력한 스케줄링이 가능합니다.${NC}"
echo -e "${BLUE}systemd 타이머 설정 스크립트를 생성하시겠습니까? (y/n)${NC}"
read -r systemd_response

if [ "$systemd_response" = "y" ]; then
    # systemd 서비스 파일 생성
    SERVICE_FILE="/tmp/iacsgraph-mail-sync.service"
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=IACSGRAPH Mail Sync Service
After=network.target

[Service]
Type=oneshot
User=$USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$UV_PATH run python scripts/sync_mails.py
StandardOutput=append:$CRON_LOG
StandardError=append:$CRON_LOG

[Install]
WantedBy=multi-user.target
EOF

    # systemd 타이머 파일 생성
    TIMER_FILE="/tmp/iacsgraph-mail-sync.timer"
    
    # cron 스케줄을 systemd 타이머 형식으로 변환
    case $CRON_SCHEDULE in
        "*/30 * * * *")
            TIMER_SCHEDULE="OnCalendar=*:0/30"
            ;;
        "0 * * * *")
            TIMER_SCHEDULE="OnCalendar=hourly"
            ;;
        "0 0 * * *")
            TIMER_SCHEDULE="OnCalendar=daily"
            ;;
        *)
            TIMER_SCHEDULE="OnCalendar=*:0/30"
            ;;
    esac
    
    cat > "$TIMER_FILE" << EOF
[Unit]
Description=IACSGRAPH Mail Sync Timer
Requires=iacsgraph-mail-sync.service

[Timer]
$TIMER_SCHEDULE
Persistent=true

[Install]
WantedBy=timers.target
EOF

    echo -e "\n${GREEN}✓ systemd 파일이 생성되었습니다:${NC}"
    echo "  - 서비스: $SERVICE_FILE"
    echo "  - 타이머: $TIMER_FILE"
    echo -e "\n${YELLOW}설치하려면 다음 명령어를 실행하세요:${NC}"
    echo "sudo cp $SERVICE_FILE /etc/systemd/system/"
    echo "sudo cp $TIMER_FILE /etc/systemd/system/"
    echo "sudo systemctl daemon-reload"
    echo "sudo systemctl enable iacsgraph-mail-sync.timer"
    echo "sudo systemctl start iacsgraph-mail-sync.timer"
fi

# 모니터링 스크립트 생성
echo -e "\n${YELLOW}모니터링 스크립트를 생성하시겠습니까? (y/n)${NC}"
read -r monitor_response

if [ "$monitor_response" = "y" ]; then
    MONITOR_SCRIPT="$PROJECT_DIR/scripts/monitor_mail_sync.sh"
    cat > "$MONITOR_SCRIPT" << 'EOF'
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
EOF

    chmod +x "$MONITOR_SCRIPT"
    echo -e "${GREEN}✓ 모니터링 스크립트 생성: $MONITOR_SCRIPT${NC}"
fi

# 테스트 실행 옵션
echo -e "\n${YELLOW}지금 테스트 실행하시겠습니까? (y/n)${NC}"
read -r test_response
if [ "$test_response" = "y" ]; then
    echo -e "${GREEN}테스트 실행 중...${NC}"
    cd "$PROJECT_DIR"
    source .venv/bin/activate
    $UV_PATH run python scripts/sync_mails.py
    
    echo -e "\n${BLUE}📋 최근 로그:${NC}"
    tail -20 "$CRON_LOG"
fi

# 최종 안내
echo -e "\n${GREEN}✅ 설정이 완료되었습니다!${NC}"
echo -e "\n${BLUE}유용한 명령어:${NC}"
echo "  - 로그 확인: tail -f $CRON_LOG"
echo "  - cron 상태: crontab -l"
echo "  - cron 제거: crontab -l | grep -v sync_mails.py | crontab -"
if [ -f "$PROJECT_DIR/scripts/monitor_mail_sync.sh" ]; then
    echo "  - 모니터링: $PROJECT_DIR/scripts/monitor_mail_sync.sh"
fi

echo -e "\n${YELLOW}💡 문제 해결:${NC}"
echo "  - cron이 실행되지 않으면 /var/log/cron 또는 /var/log/syslog 확인"
echo "  - 환경 변수 문제시 cron에 PATH 추가 필요"
echo "  - 권한 문제시 스크립트와 로그 디렉토리 권한 확인"