#!/bin/bash
# 기존 평면 구조의 로그 파일을 정리하는 스크립트

set -e

LOG_DIR="logs"

echo "🧹 기존 평면 구조 로그 파일 정리 중..."

# 평면 구조 로그 파일 목록
OLD_LOG_FILES=(
    "infra_core.log"
    "infra_core_config.log"
    "infra_core_database.log"
    "infra_core_kafka_client.log"
    "infra_core_oauth_client.log"
    "infra_core_token_service.log"
    "mcp_stdio.log"
    "modules_account__account_helpers.log"
    "modules_account_account_orchestrator.log"
    "modules_account_account_repository.log"
    "modules_account_account_sync_service.log"
    "modules_auth__auth_helpers.log"
    "modules_auth_auth_orchestrator.log"
    "modules_auth_auth_web_server.log"
    "modules_mail_query_graph_api_client.log"
    "modules_mail_query_mail_query_helpers.log"
    "modules_mail_query_mail_query_orchestrator.log"
    "modules_mail_query_without_db_mcp_server_config.log"
    "modules_mail_query_without_db_mcp_server_handlers.log"
    "modules_mail_query_without_db_mcp_server_http_server.log"
    "modules_mail_query_without_db_mcp_server_tools_account.log"
    "modules_mail_query_without_db_mcp_server_tools_email_query.log"
)

# 백업 디렉터리 생성
BACKUP_DIR="${LOG_DIR}/old_flat_structure_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 파일 이동 카운터
moved_count=0
not_found_count=0

for log_file in "${OLD_LOG_FILES[@]}"; do
    file_path="${LOG_DIR}/${log_file}"
    if [ -f "$file_path" ]; then
        mv "$file_path" "$BACKUP_DIR/"
        echo "  ✓ 이동: $log_file"
        ((moved_count++))
    else
        ((not_found_count++))
    fi
done

# .log.N (로테이션된 파일) 도 백업
for backup_file in ${LOG_DIR}/*_*.log.*; do
    if [ -f "$backup_file" ]; then
        mv "$backup_file" "$BACKUP_DIR/"
        echo "  ✓ 이동: $(basename $backup_file)"
        ((moved_count++))
    fi
done

echo ""
echo "✅ 정리 완료!"
echo "  - 이동된 파일: ${moved_count}개"
echo "  - 찾을 수 없는 파일: ${not_found_count}개"
echo "  - 백업 위치: $BACKUP_DIR"
echo ""
echo "💡 새로운 로그 구조:"
echo "  logs/"
echo "  ├── infra/core/        # 인프라 레이어"
echo "  └── modules/           # 모듈 레이어"
echo "      ├── account/"
echo "      ├── auth/"
echo "      ├── mail_query/"
echo "      └── mcp_server/"
echo ""
echo "백업 파일이 필요 없다면 다음 명령으로 삭제하세요:"
echo "  rm -rf $BACKUP_DIR"
