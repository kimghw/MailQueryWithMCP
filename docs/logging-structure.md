# 로그 파일 디렉터리 구조

## 개요

로그 파일이 모듈별로 **하나의 파일로 통합**되도록 개선되었습니다. 이를 통해 로그 파일 관리가 훨씬 쉬워졌습니다.

## 새로운 디렉터리 구조

```
logs/
├── __main__.log              # 메인 엔트리포인트 로그
├── app.log                   # 루트 로거 로그
│
├── infra/                    # 인프라 레이어 로그
│   └── core.log              # 모든 infra.core.* 로거가 여기에 기록
│
└── modules/                  # 모듈 레이어 로그
    ├── account.log           # 모든 modules.account.* 로거가 여기에 기록
    ├── auth.log              # 모든 modules.auth.* 로거가 여기에 기록
    ├── mail_query.log        # 모든 modules.mail_query.* 로거가 여기에 기록
    └── mcp_server.log        # 모든 modules.*.mcp_server.* 로거가 여기에 기록
```

**총 7개의 로그 파일**로 모든 로그를 관리합니다!

## 로거 이름 → 파일 경로 매핑

| 로거 이름 | 파일 경로 | 비고 |
|-----------|-----------|------|
| `infra.core.database` | `logs/infra/core.log` | |
| `infra.core.config` | `logs/infra/core.log` | ⭐ 같은 파일 |
| `infra.core.oauth_client` | `logs/infra/core.log` | ⭐ 같은 파일 |
| `modules.account.account_repository` | `logs/modules/account.log` | |
| `modules.account.account_orchestrator` | `logs/modules/account.log` | ⭐ 같은 파일 |
| `modules.auth.auth_orchestrator` | `logs/modules/auth.log` | |
| `modules.auth.auth_web_server` | `logs/modules/auth.log` | ⭐ 같은 파일 |
| `modules.mail_query.graph_api_client` | `logs/modules/mail_query.log` | |
| `modules.mail_query_without_db.mcp_server.http_server` | `logs/modules/mcp_server.log` | |
| `modules.mail_query_without_db.mcp_server.tools.account` | `logs/modules/mcp_server.log` | ⭐ 같은 파일 |
| `modules.mail_query_without_db.mcp_server.tools.email_query` | `logs/modules/mcp_server.log` | ⭐ 같은 파일 |

## 구현 세부사항

### 로거 이름 변환 규칙

[logging_config.py:126-180](infra/core/logging_config.py#L126-L180)의 `_get_log_file_path` 메서드에서 처리:

1. **특수 케이스**: `__main__`, `app` → 루트에 바로 생성
2. **infra 모듈**: `infra.core.*` → `logs/infra/core.log` (모두 하나의 파일)
3. **modules 모듈**:
   - MCP Server: `modules.*.mcp_server.*` → `logs/modules/mcp_server.log` (모두 하나의 파일)
   - 일반 모듈: `modules.<module_name>.*` → `logs/modules/<module_name>.log` (모두 하나의 파일)

### 로그 파일 내용 예시

각 로그 파일에는 해당 모듈의 **모든 하위 컴포넌트 로그**가 함께 기록됩니다:

```
# logs/infra/core.log
2025-10-13 12:57:04,325 - infra.core.database - INFO - [database.py:56] - 데이터베이스 연결 성공
2025-10-13 12:57:04,325 - infra.core.config - INFO - [config.py:63] - ✅ 환경변수 검증 성공
2025-10-13 12:57:04,325 - infra.core.oauth_client - INFO - [oauth_client.py:42] - OAuth 클라이언트 초기화

# logs/modules/account.log
2025-10-13 12:57:04,325 - modules.account.account_repository - INFO - [account_repository.py:23] - 계정 조회
2025-10-13 12:57:04,326 - modules.account.account_orchestrator - INFO - [account_orchestrator.py:45] - 계정 동기화 시작
```

### 기존 평면 구조 로그

기존에 생성된 평면 구조의 로그 파일들 (예: `modules_account_account_repository.log`)은 자동으로 삭제되지 않습니다.

정리 스크립트 사용:
```bash
# 기존 평면 구조 로그 파일을 백업 후 제거
./scripts/cleanup_old_logs.sh
```

## 장점

1. **파일 수 대폭 감소**: 20+ 개 파일 → 7개 파일로 간소화
2. **모듈별 집중**: 하나의 파일에서 해당 모듈의 전체 흐름 파악 가능
3. **관리 용이**: 특정 모듈의 로그만 보거나 삭제 가능
4. **확장성**: 새로운 하위 모듈 추가해도 파일 수 증가 없음
5. **일관성**: 코드 구조와 로그 구조가 일치

## 사용 예제

```python
from infra.core.logging_config import get_logger

# 자동으로 logs/modules/account.log에 기록
logger = get_logger("modules.account.my_service")
logger.info("Hello from account service")

# 같은 파일(logs/modules/account.log)에 기록됨
logger2 = get_logger("modules.account.another_service")
logger2.info("Hello from another service")

# 자동으로 logs/infra/core.log에 기록
logger3 = get_logger("infra.core.my_component")
logger3.info("Hello from infra component")
```

## 환경 변수

로그 디렉터리는 환경 변수로 설정 가능:

```bash
# 기본값: ./logs
export LOG_DIR=/var/log/iacsgraph

# 파일 로깅 비활성화
export ENABLE_FILE_LOGGING=false

# 로그 레벨 설정
export LOG_LEVEL=DEBUG
```

## 주의사항

- 디렉터리는 로거가 처음 생성될 때 자동으로 생성됩니다
- 로그 파일은 Rotating 방식으로 관리됩니다 (기본: 10MB, 5개 백업)
- 프로덕션 환경에서는 로그 레벨을 `INFO` 이상으로 설정하는 것을 권장합니다
- 여러 하위 모듈이 하나의 파일에 기록되므로 로거 이름으로 구분합니다

## 로그 파일 보기

```bash
# 특정 모듈의 모든 로그 보기
tail -f logs/modules/account.log

# 특정 하위 컴포넌트만 필터링
grep "account_repository" logs/modules/account.log

# 에러만 보기
grep "ERROR" logs/modules/account.log
```
