# IACSGRAPH Mail Sync - 메일 동기화 가이드

## 📋 개요

IACSGRAPH Mail Sync는 Microsoft Graph API를 통해 여러 계정의 이메일을 자동으로 수집하고 처리하는 시스템입니다. 증분 동기화를 지원하여 효율적으로 새로운 메일만 처리합니다.

## 🚀 주요 기능

- **다중 계정 지원**: 여러 Microsoft 365 계정의 메일을 동시에 처리
- **증분 동기화**: 마지막 동기화 이후의 메일만 조회하여 효율성 극대화
- **자동 토큰 관리**: 만료된 토큰 자동 갱신
- **배치 처리**: 대량의 메일을 효율적으로 처리
- **중복 방지**: 이미 처리된 메일 자동 필터링
- **필터링 기능**: 스팸, 광고 메일 등 자동 필터링

## 📁 관련 파일

```
scripts/
├── sync_mails.py              # 메인 동기화 스크립트
├── setup_project_uv_cron.sh   # Cron 자동 설정 스크립트
├── monitor_mail_sync.sh       # 모니터링 스크립트
├── mail_sync_dashboard.sh     # 대시보드 스크립트
├── mail_query.py              # 메일 조회 테스트
└── mail_query_process.py      # 메일 처리 테스트
```

## 🔧 설치 및 설정

### 1. 환경 설정

`.env` 파일에서 다음 설정을 확인하세요:

```bash
# 메일 동기화 설정
MAIL_SYNC_INITIAL_MONTHS=3     # 초기 동기화 시 가져올 개월 수
MAIL_SYNC_BATCH_SIZE=10        # 동시 처리할 계정 수

# 메일 필터링 설정
ENABLE_MAIL_FILTERING=true      # 필터링 활성화 여부
BLOCKED_DOMAINS=spam.com,ad.com # 차단할 도메인
BLOCKED_KEYWORDS=광고,스팸      # 차단할 키워드

# 중복 체크 설정
ENABLE_MAIL_DUPLICATE_CHECK=true # 중복 체크 활성화
```

### 2. 수동 실행

```bash
# 프로젝트 디렉토리로 이동
cd ~/IACSGRAPH

# UV를 사용한 실행
uv run python scripts/sync_mails.py

# 또는 가상환경 활성화 후 실행
source .venv/bin/activate
python scripts/sync_mails.py
```

### 3. 자동 실행 설정 (Cron)

#### 자동 설정 스크립트 사용 (권장)

```bash
# 설정 스크립트 실행
./scripts/setup_project_uv_cron.sh

# 대화형 메뉴에서 실행 주기 선택:
# 1) 30분마다 (기본값)
# 2) 1시간마다
# 3) 2시간마다
# 4) 4시간마다
# 5) 매일 자정
# 6) 매일 오전 6시
# 7) 사용자 정의
```

#### 수동 Cron 설정

```bash
# Crontab 편집
crontab -e

# 30분마다 실행 예제
*/30 * * * * cd /home/kimghw/IACSGRAPH && source .venv/bin/activate && echo "[$(date '+\%Y-\%m-\%d \%H:\%M:\%S')] 메일 동기화 시작" >> logs/mail_sync.log && /home/kimghw/IACSGRAPH/.venv/bin/uv run python scripts/sync_mails.py >> logs/mail_sync.log 2>&1
```

## 📊 모니터링

### 1. 실시간 로그 확인

```bash
# 로그 실시간 모니터링
tail -f ~/IACSGRAPH/logs/mail_sync.log

# 최근 100줄 확인
tail -100 ~/IACSGRAPH/logs/mail_sync.log
```

### 2. 모니터링 스크립트

```bash
# 간단한 상태 확인
./scripts/monitor_mail_sync.sh

# 대시보드 (더 자세한 정보)
./scripts/mail_sync_dashboard.sh
```

### 3. 대시보드 출력 예시

```
╔══════════════════════════════════════════════════════╗
║        IACSGRAPH Mail Sync Monitor Dashboard         ║
╚══════════════════════════════════════════════════════╝

📊 시스템 상태
─────────────────────────────────────
Cron 서비스: ● 실행중
Cron 스케줄: */30 * * * *

📈 오늘의 통계
─────────────────────────────────────
실행 횟수: 24 회
처리된 메일: 1,234 개
저장된 메일: 987 개
필터링된 메일: 247 개
저장률: 80%
```

## 🔍 동작 원리

### 1. 증분 동기화

- **초기 동기화**: 계정의 첫 동기화 시 최근 3개월 메일 조회
- **증분 동기화**: 이후 실행 시 `last_sync_time` 이후 메일만 조회
- **시간대 처리**: 모든 시간은 UTC 기준으로 처리

### 2. 처리 흐름

```
1. 활성 계정 조회 (is_active=1, status='ACTIVE')
2. 각 계정별 날짜 범위 계산
3. Microsoft Graph API로 메일 조회
4. 메일 필터링 (스팸, 중복 등)
5. 데이터베이스 저장
6. 이벤트 발행 (추가 처리용)
7. last_sync_time 업데이트
```

### 3. 배치 처리

- 기본적으로 10개 계정씩 동시 처리
- 각 계정당 최대 5,000개 메일 조회 (100개씩 50페이지)
- 배치 간 0.5초 대기로 API 부하 분산

## ⚠️ 주의사항

### 1. API 제한

- Microsoft Graph API는 사용량 제한이 있습니다
- 너무 짧은 주기로 실행하면 제한에 걸릴 수 있습니다
- 권장 실행 주기: 30분 ~ 1시간

### 2. 토큰 관리

- 토큰이 만료되면 자동으로 갱신을 시도합니다
- 갱신 실패 시 해당 계정은 건너뜁니다
- 재인증이 필요한 경우 `auth_flow.py` 실행

### 3. 로그 관리

```bash
# 로그 로테이션 설정 (선택사항)
sudo tee /etc/logrotate.d/iacsgraph << EOF
/home/kimghw/IACSGRAPH/logs/mail_sync.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 kimghw kimghw
}
EOF
```

## 🛠️ 문제 해결

### 1. Cron이 실행되지 않을 때

```bash
# Cron 로그 확인
sudo grep CRON /var/log/syslog | tail -20

# Cron 서비스 상태 확인
systemctl status cron

# 현재 Crontab 확인
crontab -l
```

### 2. 토큰 오류

```bash
# 토큰 상태 확인 및 갱신
uv run python scripts/ignore/token_validation_and_refresh.py

# 재인증 필요 시
uv run python scripts/ignore/auth_flow.py --mode check-all
```

### 3. 특정 계정 테스트

```bash
# 단일 계정 메일 조회 테스트
uv run python scripts/mail_query.py

# 중복 체크 동작 테스트
uv run python scripts/mail_query_process.py --test-duplicate kimghw
```

## 📈 성능 최적화

### 1. 실행 주기 조정

- **메일량이 많은 경우**: 15-30분 주기
- **메일량이 적은 경우**: 1-2시간 주기
- **야간/주말**: 실행 빈도 감소 고려

### 2. 배치 크기 조정

```bash
# .env 파일에서 조정
MAIL_SYNC_BATCH_SIZE=5  # API 제한 시 감소
MAIL_SYNC_BATCH_SIZE=20 # 성능이 좋을 때 증가
```

### 3. 필터링 최적화

```bash
# 불필요한 메일 필터링으로 처리량 감소
BLOCKED_DOMAINS=noreply.github.com,notifications.linkedin.com
BLOCKED_KEYWORDS=Unsubscribe,구독해지
```

## 📝 로그 형식

### 정상 실행 로그
```
[2025-07-02 14:30:00] 메일 동기화 시작
INFO - 동기화 시작: 5개 계정
INFO - 메일 동기화 시작: kimghw (2025-07-01 14:30 UTC ~ 2025-07-02 14:30 UTC)
INFO - 메일 동기화 완료: kimghw (123개, 2500ms)
INFO - 동기화 완료: 성공=5/5, 메일=543개, 시간=15.2초
```

### 오류 로그
```
ERROR - 동기화 실패: testuser - Token expired and refresh failed
WARNING - 토큰 만료됨: testuser
```

## 🔄 업데이트 및 유지보수

### 1. 코드 업데이트 후

```bash
# Git pull 후 의존성 업데이트
uv sync

# 테스트 실행
uv run python scripts/sync_mails.py
```

### 2. 정기 점검 사항

- [ ] 로그 파일 크기 확인
- [ ] 실패한 계정 확인 및 재인증
- [ ] API 사용량 모니터링
- [ ] 데이터베이스 크기 확인

## 💡 추가 팁

1. **초기 설정 시**: 소수 계정으로 테스트 후 전체 적용
2. **대량 계정**: 계정을 그룹으로 나누어 시간대별 실행
3. **모니터링**: Grafana, Prometheus 등과 연동하여 시각화
4. **알림 설정**: 실패 시 Slack, Email 등으로 알림

## 📞 지원

문제가 발생하거나 추가 기능이 필요한 경우:
- 로그 파일 확인: `~/IACSGRAPH/logs/`
- 설정 파일 검토: `.env`
- 테스트 스크립트 실행: `scripts/mail_query_process.py`