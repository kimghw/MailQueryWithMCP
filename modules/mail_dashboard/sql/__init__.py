# modules/mail_dashboard/sql/__init__.py
"""
Email Dashboard SQL 스크립트 관리

모듈별 SQL 스크립트와 마이그레이션을 관리합니다.
"""

from pathlib import Path
from typing import Any, Dict, List

from infra.core import get_logger

logger = get_logger(__name__)

# SQL 파일들이 위치한 디렉터리
SQL_DIR = Path(__file__).parent


def get_create_tables_sql() -> str:
    """테이블 생성 SQL을 반환합니다"""
    # migrations 폴더에서 create_table.sql 파일을 찾습니다
    sql_file = SQL_DIR / "migrations" / "create_table.sql"
    
    if sql_file.exists():
        with open(sql_file, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise FileNotFoundError(f"SQL 파일을 찾을 수 없습니다: {sql_file}")


def get_drop_old_tables_sql() -> str:
    """기존 테이블 삭제 SQL을 반환합니다"""
    sql_file = SQL_DIR / "migrations" / "drop_old_tables.sql"
    
    if sql_file.exists():
        with open(sql_file, "r", encoding="utf-8") as f:
            return f.read()
    else:
        # 파일이 없으면 기본 SQL 반환
        return """
        -- 기존 Email Dashboard 테이블 삭제
        DROP TABLE IF EXISTS email_events_unprocessed;
        DROP TABLE IF EXISTS email_agenda_member_response_times;
        DROP TABLE IF EXISTS email_agenda_member_responses;
        DROP TABLE IF EXISTS email_agendas_chair;
        """


def get_migration_files() -> List[Path]:
    """마이그레이션 파일 목록을 반환합니다 (버전 순서대로)"""
    migrations_dir = SQL_DIR / "migrations"
    if not migrations_dir.exists():
        return []
    
    # v로 시작하는 SQL 파일들을 찾아서 정렬
    migration_files = []
    for sql_file in migrations_dir.glob("v*.sql"):
        migration_files.append(sql_file)
    
    # 파일명으로 정렬 (버전 순서)
    migration_files.sort(key=lambda x: x.name)
    
    return migration_files


def get_migration_sql(version: str) -> str:
    """특정 버전의 마이그레이션 SQL을 반환합니다"""
    migrations_dir = SQL_DIR / "migrations"
    sql_file = migrations_dir / f"{version}.sql"
    
    if sql_file.exists():
        with open(sql_file, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise FileNotFoundError(f"마이그레이션 파일을 찾을 수 없습니다: {sql_file}")


def get_required_tables() -> List[str]:
    """이 모듈에서 필요한 테이블 목록을 반환합니다"""
    return [
        "agenda_all",
        "agenda_chair",
        "agenda_responses_content", 
        "agenda_responses_receivedtime",
        "agenda_pending"
    ]


def get_old_tables() -> List[str]:
    """삭제해야 할 기존 테이블 목록을 반환합니다"""
    return [
        "email_agendas_chair",
        "email_agenda_member_responses",
        "email_agenda_member_response_times",
        "email_events_unprocessed"
    ]