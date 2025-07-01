#!/bin/bash
# IACSGRAPH UV Cron 설정 스크립트

# 프로젝트 경로
PROJECT_DIR="/home/kimghw/IACSGRAPH"
UV_PATH="$PROJECT_DIR/.venv/bin/uv"

# UV 존재 확인
if [ ! -f "$UV_PATH" ]; then
    echo "❌ UV를 찾을 수 없습니다: $UV_PATH"
    exit 1
fi

echo "📁 프로젝트 경로: $PROJECT_DIR"
echo "🔧 UV 경로: $UV_PATH"

# logs 디렉토리 생성
mkdir -p "$PROJECT_DIR/logs"

# Cron 작업 문자열
CRON_JOB="*/30 * * * * cd $PROJECT_DIR && $UV_PATH run python scripts/sync_mails.py >> $PROJECT_DIR/logs/mail_sync.log 2>&1"

# 기존 crontab 백업
crontab -l > /tmp/current_cron 2>/dev/null || touch /tmp/current_cron

# 중복 확인 및 처리
if grep -q "sync_mails.py" /tmp/current_cron; then
    echo -e "\n⚠️  기존 sync_mails.py cron 작업을 발견했습니다:"
    grep "sync_mails.py" /tmp/current_cron
    echo -e "\n기존 설정을 제거하고 새로 추가하시겠습니까? (y/n)"
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

echo -e "\n✅ Cron 작업이 추가되었습니다:"
echo "$CRON_JOB"

# 임시 파일 삭제
rm /tmp/current_cron

# 현재 설정 확인
echo -e "\n📋 현재 crontab 설정:"
crontab -l | grep sync_mails || echo "설정된 sync_mails 작업이 없습니다."

# 테스트 실행 옵션
echo -e "\n지금 테스트 실행하시겠습니까? (y/n)"
read -r test_response
if [ "$test_response" = "y" ]; then
    echo "테스트 실행 중..."
    cd "$PROJECT_DIR"
    $UV_PATH run python scripts/sync_mails.py
fi
