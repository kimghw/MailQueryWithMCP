"""
Email Dashboard 테이블 생성 스크립트

migrations/create_tables.sql 파일을 읽어서 테이블을 생성합니다.
기존 테이블이 있으면 삭제하고 새로 생성합니다.
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, project_root)

from infra.core import get_database_manager, get_logger

logger = get_logger(__name__)


def drop_existing_tables(db, tables_to_drop):
    """기존 테이블 삭제"""
    dropped_tables = []

    for table in tables_to_drop:
        try:
            if db.table_exists(table):
                db.execute_query(f"DROP TABLE IF EXISTS {table}")
                dropped_tables.append(table)
                logger.info(f"기존 테이블 삭제 완료: {table}")
        except Exception as e:
            logger.error(f"테이블 삭제 실패 {table}: {str(e)}")
            raise

    if dropped_tables:
        logger.info(f"삭제된 테이블: {dropped_tables}")
    else:
        logger.info("삭제할 기존 테이블이 없습니다.")

    return dropped_tables


def create_email_dashboard_tables(force_recreate=False):
    """
    Email Dashboard 테이블 생성

    Args:
        force_recreate: True일 경우 기존 테이블 삭제 후 재생성
    """
    db = get_database_manager()

    try:
        logger.info("Email Dashboard 테이블 생성 시작")

        # SQL 파일 경로
        sql_file_path = Path(__file__).parent / "migrations" / "create_tables.sql"

        if not sql_file_path.exists():
            logger.error(f"SQL 파일을 찾을 수 없습니다: {sql_file_path}")
            return False

        # SQL 파일 읽기
        with open(sql_file_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        logger.info(f"SQL 파일 로드 완료: {sql_file_path}")

        # 필요한 테이블 목록
        required_tables = [
            "email_agendas_chair",
            "email_agenda_member_responses",
            "email_agenda_member_response_times",
            "email_events_unprocessed",
        ]

        # 기존 테이블 확인
        existing_tables = []
        for table in required_tables:
            if db.table_exists(table):
                existing_tables.append(table)

        # force_recreate가 True이거나 기존 테이블이 있으면 삭제
        if force_recreate or existing_tables:
            if existing_tables:
                logger.warning(f"기존 테이블 발견: {existing_tables}")

                if not force_recreate:
                    response = input(
                        "\n기존 테이블을 삭제하고 새로 생성하시겠습니까? (yes/no): "
                    )
                    if response.lower() != "yes":
                        logger.info("테이블 생성 취소됨")
                        return False

                # 테이블 삭제 (외래키 제약 때문에 역순으로)
                tables_to_drop = [
                    "email_events_unprocessed",
                    "email_agenda_member_response_times",
                    "email_agenda_member_responses",
                    "email_agendas_chair",
                ]

                logger.info("\n기존 테이블 삭제 중...")
                dropped_tables = drop_existing_tables(db, tables_to_drop)
                logger.info(f"총 {len(dropped_tables)}개 테이블 삭제 완료\n")

        # SQL 문장별로 분리하여 실행
        statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]

        success_count = 0
        error_count = 0

        logger.info(f"총 {len(statements)}개의 SQL 문장을 실행합니다.")

        with db.transaction():
            for i, statement in enumerate(statements):
                if statement:
                    try:
                        # 디버깅용 로그
                        if "CREATE TABLE" in statement:
                            table_name = (
                                statement.split("CREATE TABLE IF NOT EXISTS")[1]
                                .split("(")[0]
                                .strip()
                            )
                            logger.info(f"테이블 생성 중: {table_name}")

                        db.execute_query(statement)
                        success_count += 1

                    except Exception as e:
                        # CREATE IF NOT EXISTS는 오류가 아님
                        if "already exists" in str(e):
                            logger.debug(f"테이블/인덱스가 이미 존재함 (정상)")
                            success_count += 1
                        else:
                            error_count += 1
                            logger.error(f"SQL 문장 {i+1} 실행 실패: {str(e)}")
                            logger.error(f"실패한 SQL:\n{statement[:200]}...")
                            raise

        logger.info(f"\nSQL 실행 완료: 성공 {success_count}개, 실패 {error_count}개")

        # 생성 결과 확인
        verify_result = verify_tables()

        return verify_result and error_count == 0

    except Exception as e:
        logger.error(f"테이블 생성 중 오류: {str(e)}")
        return False


def verify_tables():
    """생성된 테이블 확인"""
    db = get_database_manager()

    try:
        logger.info("\n테이블 생성 확인:")

        expected_tables = [
            ("email_agendas_chair", "의장 발송 아젠다"),
            ("email_agenda_member_responses", "멤버 기관 응답 내용"),
            ("email_agenda_member_response_times", "멤버 기관 응답 시간"),
            ("email_events_unprocessed", "미처리 이벤트"),
        ]

        all_created = True
        for table_name, description in expected_tables:
            if db.table_exists(table_name):
                # 테이블 정보 조회
                result = db.fetch_one(f"SELECT COUNT(*) as count FROM {table_name}")
                row_count = result["count"] if result else 0
                logger.info(f"✓ {table_name} - {description} (레코드: {row_count}개)")

                # TL 컬럼 확인 (email_agenda_member_responses, email_agenda_member_response_times)
                if table_name in [
                    "email_agenda_member_responses",
                    "email_agenda_member_response_times",
                ]:
                    columns = db.fetch_all(f"PRAGMA table_info({table_name})")
                    has_tl = any(col["name"] == "TL" for col in columns)
                    if has_tl:
                        logger.info(f"  └─ TL 컬럼 확인: ✓")
                    else:
                        logger.error(f"  └─ TL 컬럼 확인: ✗ (누락됨)")
                        all_created = False
            else:
                logger.error(f"✗ {table_name} - 생성 실패")
                all_created = False

        # 인덱스 확인
        if all_created:
            verify_indices()

        return all_created

    except Exception as e:
        logger.error(f"테이블 확인 중 오류: {str(e)}")
        return False


def verify_indices():
    """인덱스 생성 확인"""
    db = get_database_manager()

    try:
        logger.info("\n인덱스 생성 확인:")

        # 모든 인덱스 조회
        indices = db.fetch_all(
            """
            SELECT name, tbl_name 
            FROM sqlite_master 
            WHERE type='index' 
            AND tbl_name LIKE 'email_%'
            AND name NOT LIKE 'sqlite_%'
            ORDER BY tbl_name, name
            """
        )

        if indices:
            current_table = None
            index_count = 0
            for idx in indices:
                if current_table != idx["tbl_name"]:
                    if current_table:
                        logger.info(f"  └─ 총 {index_count}개 인덱스")
                    current_table = idx["tbl_name"]
                    index_count = 0
                    logger.info(f"\n{current_table}:")
                logger.info(f"  - {idx['name']}")
                index_count += 1
            if current_table:
                logger.info(f"  └─ 총 {index_count}개 인덱스")
        else:
            logger.warning("생성된 인덱스가 없습니다.")

    except Exception as e:
        logger.error(f"인덱스 확인 중 오류: {str(e)}")


def show_table_schema(table_name: str):
    """테이블 스키마 출력"""
    db = get_database_manager()

    try:
        logger.info(f"\n{table_name} 테이블 스키마:")

        columns = db.fetch_all(f"PRAGMA table_info({table_name})")

        if columns:
            for col in columns:
                pk = " (PK)" if col["pk"] else ""
                notnull = " NOT NULL" if col["notnull"] else ""
                default = f" DEFAULT {col['dflt_value']}" if col["dflt_value"] else ""
                logger.info(f"  - {col['name']}: {col['type']}{pk}{notnull}{default}")
        else:
            logger.warning(f"{table_name} 테이블의 컬럼 정보를 가져올 수 없습니다.")

    except Exception as e:
        logger.error(f"테이블 스키마 조회 중 오류: {str(e)}")


if __name__ == "__main__":
    print("=" * 60)
    print("Email Dashboard 테이블 생성")
    print("=" * 60)
    print()

    # 명령줄 인자 확인
    force_recreate = False
    show_schema = False

    if len(sys.argv) > 1:
        if "--force" in sys.argv:
            force_recreate = True
            print("강제 재생성 모드: 기존 테이블을 삭제하고 새로 생성합니다.")
        if "--schema" in sys.argv:
            show_schema = True

    # 테이블 생성
    if create_email_dashboard_tables(force_recreate=force_recreate):
        print("\n✅ Email Dashboard 테이블 생성 완료")

        # 테이블 스키마 정보 출력
        if show_schema:
            print("\n테이블 스키마 정보:")
            show_table_schema("email_agendas_chair")
            show_table_schema("email_agenda_member_responses")
            show_table_schema("email_agenda_member_response_times")
            show_table_schema("email_events_unprocessed")
    else:
        print("\n❌ Email Dashboard 테이블 생성 실패")
        print("로그를 확인하세요.")
        sys.exit(1)
