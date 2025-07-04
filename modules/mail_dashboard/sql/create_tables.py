"""
Email Dashboard 테이블 생성 스크립트

migrations/create_tables.sql 파일을 읽어서 테이블을 생성합니다.
기존 테이블이 있으면 건너뜁니다.
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, project_root)

from infra.core import get_database_manager, get_logger

logger = get_logger(__name__)


def create_email_dashboard_tables():
    """Email Dashboard 테이블 생성"""
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

        # 이미 존재하는 테이블 확인
        existing_tables = []
        missing_tables = []

        for table in required_tables:
            if db.table_exists(table):
                existing_tables.append(table)
            else:
                missing_tables.append(table)

        if existing_tables:
            logger.info(f"이미 존재하는 테이블: {existing_tables}")

        if not missing_tables:
            logger.info("모든 테이블이 이미 존재합니다.")
            return True

        logger.info(f"생성할 테이블: {missing_tables}")

        # SQL 문장별로 분리하여 실행
        statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]

        success_count = 0
        error_count = 0

        # 디버깅: SQL 문장 확인
        logger.debug(f"총 {len(statements)}개의 SQL 문장을 실행합니다.")

        with db.transaction():
            for i, statement in enumerate(statements):
                if statement:
                    try:
                        # email_events_unprocessed 테이블인 경우 전체 SQL 출력
                        if (
                            "email_events_unprocessed" in statement
                            and "CREATE TABLE" in statement
                        ):
                            logger.debug(
                                f"email_events_unprocessed 테이블 생성 SQL:\n{statement}"
                            )

                        db.execute_query(statement)
                        success_count += 1
                        logger.debug(f"SQL 문장 {i+1}/{len(statements)} 실행 완료")
                    except Exception as e:
                        # CREATE IF NOT EXISTS는 오류가 아님
                        if "already exists" in str(e):
                            logger.debug(f"테이블/인덱스가 이미 존재함 (정상)")
                            success_count += 1
                        else:
                            error_count += 1
                            logger.error(f"SQL 문장 {i+1} 실행 실패: {str(e)}")
                            logger.error(f"실패한 SQL:\n{statement}")
                            # SQL 파일 수정 안내
                            if 'near "INDEX"' in str(e):
                                logger.error(
                                    "\n⚠️  SQLite는 CREATE TABLE 내부에 INDEX를 정의할 수 없습니다."
                                )
                                logger.error(
                                    "해결 방법: INDEX 구문을 테이블 생성 후 별도의 CREATE INDEX 문으로 이동하세요.\n"
                                )
                            elif 'near ")"' in str(e):
                                logger.error(
                                    "\n⚠️  SQL 구문 오류: 마지막 컬럼 뒤에 쉼표가 있거나 구문이 잘못되었습니다."
                                )
                                logger.error(
                                    "해결 방법: CREATE TABLE 문의 마지막 컬럼 정의를 확인하세요.\n"
                                )

        logger.info(f"SQL 실행 완료: 성공 {success_count}개, 실패 {error_count}개")

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
            else:
                logger.error(f"✗ {table_name} - 생성 실패")
                all_created = False

        # 인덱스 확인 (선택사항)
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
            for idx in indices:
                if current_table != idx["tbl_name"]:
                    current_table = idx["tbl_name"]
                    logger.info(f"\n{current_table}:")
                logger.info(f"  - {idx['name']}")
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

    # 테이블 생성
    if create_email_dashboard_tables():
        print("\n✅ Email Dashboard 테이블 생성 완료")

        # 특정 테이블의 스키마를 보고 싶은 경우
        if len(sys.argv) > 1 and sys.argv[1] == "--schema":
            print("\n테이블 스키마 정보:")
            show_table_schema("email_agendas_chair")
            show_table_schema("email_agenda_member_responses")
            show_table_schema("email_agenda_member_response_times")
            show_table_schema("email_events_unprocessed")
    else:
        print("\n❌ Email Dashboard 테이블 생성 실패")
        print("로그를 확인하세요.")
        sys.exit(1)
