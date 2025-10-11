# 설정 가이드 - Mail Query Without DB

## 📁 경로 설정

### 기본 경로 구조

모든 데이터는 `${HOME}/mcp_data` 아래 체계적으로 저장됩니다:

```
${HOME}/mcp_data/
├── attachments/     # 첨부파일 저장
├── emails/          # 이메일 본문 저장
├── exports/         # CSV/JSON 내보내기
├── temp/            # 임시 파일
└── logs/            # 로그 파일
    └── mcp_mail_server.log
```

### 경로 커스터마이징

#### 방법 1: config.json 직접 수정

`config.json` 파일의 `paths` 섹션을 수정:

```json
{
  "paths": {
    "base_dir": "/custom/path/mcp_data",
    "attachments_dir": "/custom/path/attachments",
    "emails_dir": "/custom/path/emails",
    "exports_dir": "/custom/path/exports",
    "temp_dir": "/tmp/mcp_temp"
  }
}
```

#### 방법 2: 사용자 설정 파일 사용 (권장)

1. `config.user.json.example`을 `config.user.json`으로 복사
2. 원하는 경로 설정:

```json
{
  "paths": {
    "base_dir": "/home/user/Documents/MCP_Data",
    "attachments_dir": "/home/user/Documents/MCP_Data/attachments"
  }
}
```

사용자 설정은 기본 설정을 덮어씁니다.

#### 방법 3: 환경변수 사용

설정 파일 위치 지정:
```bash
export MCP_CONFIG_PATH=/path/to/my/config.json
python -m modules.mail_query_without_db.mcp_server
```

### 환경변수 지원

경로 설정에서 다음 환경변수를 사용할 수 있습니다:

- `${HOME}` - 사용자 홈 디렉토리
- `${USER}` - 현재 사용자명
- `${PWD}` - 현재 작업 디렉토리
- `~` - 홈 디렉토리 (축약형)

예시:
```json
{
  "paths": {
    "base_dir": "${HOME}/Documents/emails",
    "temp_dir": "${PWD}/temp",
    "log_file": "~/logs/mcp.log"
  }
}
```

## ⚙️ 기타 설정

### 이메일 설정

```json
{
  "email": {
    "blocked_senders": ["spam@example.com"],
    "default_days_back": 30,
    "default_max_mails": 300
  }
}
```

- `blocked_senders`: 차단할 발신자 목록
- `default_days_back`: 기본 조회 기간 (일)
- `default_max_mails`: 기본 최대 메일 수

### 파일 처리 설정

```json
{
  "file_handling": {
    "max_file_size_mb": 50,
    "max_filename_length": 200,
    "cleanup_after_query": true
  }
}
```

- `max_file_size_mb`: 최대 파일 크기 (MB)
- `max_filename_length`: 최대 파일명 길이
- `cleanup_after_query`: 쿼리 후 임시 파일 정리 여부

## 🔧 설정 우선순위

1. 사용자 설정 (`config.user.json`)
2. 기본 설정 (`config.json`)
3. 하드코딩된 기본값

## 📝 설정 확인

현재 설정을 확인하려면:

```python
from modules.mail_query_without_db.mcp_server.config import Config

config = Config()
config.print_config_info()
```

출력 예시:
```
============================================================
MCP Server Configuration
============================================================

Path Settings:
  base_dir            : /home/user/mcp_data
  attachments_dir     : /home/user/mcp_data/attachments
  emails_dir          : /home/user/mcp_data/emails
  exports_dir         : /home/user/mcp_data/exports
  temp_dir            : /home/user/mcp_data/temp
  log_file            : /home/user/mcp_data/logs/mcp_mail_server.log

Email Settings:
  Default days back   : 30
  Default max mails   : 300
  Blocked senders     : 2 configured

File Handling:
  Max file size (MB)  : 50
  Max filename length : 200
  Cleanup after query : True

Server Settings:
  Default host        : 0.0.0.0
  Default port        : 8002
============================================================
```

## 🚀 실행

설정 후 서버 실행:

```bash
# HTTP 모드
python -m modules.mail_query_without_db.mcp_server --mode http

# STDIO 모드
python -m modules.mail_query_without_db.mcp_server --mode stdio
```

## 📂 디렉토리 자동 생성

`create_if_not_exists: true` 설정 시 필요한 디렉토리가 자동으로 생성됩니다.

## 🔐 권한 설정

생성되는 디렉토리에 적절한 권한이 있는지 확인하세요:

```bash
# 권한 확인
ls -la ~/mcp_data

# 필요시 권한 변경
chmod 755 ~/mcp_data
chmod -R 644 ~/mcp_data/emails
```

## 💡 팁

1. **프로덕션 환경**: 안정적인 경로 사용 (`/var/lib/mcp_data` 등)
2. **개발 환경**: 홈 디렉토리 사용 (`~/mcp_data`)
3. **백업**: 정기적으로 emails와 exports 디렉토리 백업
4. **로그 관리**: 로그 파일 크기 모니터링 및 로테이션 설정

## 문제 해결

### 디렉토리 생성 실패
- 권한 확인
- 상위 디렉토리 존재 여부 확인
- `create_if_not_exists: true` 설정 확인

### 환경변수 인식 안 됨
- `echo $HOME` 등으로 환경변수 확인
- 설정 파일 JSON 문법 확인
- `${VAR}` 형식 사용 (중괄호 포함)

### 설정 변경 적용 안 됨
- 서버 재시작
- `config.user.json` 우선순위 확인
- 캐시된 설정 확인