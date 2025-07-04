"""
Email Dashboard 테이블 재생성 스크립트

기존 테이블을 삭제하고 새로운 스키마로 재생성합니다.
주의: 모든 데이터가 삭제됩니다!
"""

import sys
import os

# 프로젝트 루트 경로 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, project_root)

from infra.core import get_database_manager, get_logger

logger = get_logger(__name__)


def reset_email_dashboard_tables():
    """Email Dashboard 테이블 재생성"""
    db = get_database_manager()

    try:
        logger.info("Email Dashboard 테이블 재생성 시작")

        # 1. 기존 테이블 삭제 (역순으로)
        tables_to_drop = [
            "email_events_unprocessed",  # 신규 테이블
            "email_agenda_member_response_times",
            "email_agenda_member_responses",
            "email_agendas_chair",
        ]

        for table in tables_to_drop:
            try:
                db.execute_query(f"DROP TABLE IF EXISTS {table}")
                logger.info(f"테이블 삭제 완료: {table}")
            except Exception as e:
                logger.error(f"테이블 삭제 실패 {table}: {str(e)}")

        # 2. 새 스키마로 테이블 생성
        # SQL 파일 직접 실행 방식으로 변경
        try:
            from modules.mail_dashboard.sql import get_create_tables_sql

            # SQL 스크립트 가져오기
            schema_sql = get_create_tables_sql()

            # SQL 문장별로 분리하여 실행
            statements = [
                stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()
            ]

            success_count = 0
            with db.transaction():
                for i, statement in enumerate(statements):
                    if statement:
                        try:
                            db.execute_query(statement)
                            success_count += 1
                            logger.debug(f"SQL 문장 {i+1} 실행 완료")
                        except Exception as e:
                            logger.error(f"SQL 문장 {i+1} 실행 실패: {str(e)}")
                            logger.error(f"실패한 SQL: {statement[:100]}...")
                            raise

            logger.info(f"새 스키마로 테이블 생성 완료: {success_count}개 구문 실행")

            # 3. 생성된 테이블 확인
            expected_tables = [
                "email_agendas_chair",
                "email_agenda_member_responses",
                "email_agenda_member_response_times",
                "email_events_unprocessed",
            ]

            all_created = True
            for table in expected_tables:
                if db.table_exists(table):
                    logger.info(f"✓ 테이블 생성 확인: {table}")
                else:
                    logger.error(f"✗ 테이블 생성 실패: {table}")
                    all_created = False

            return all_created

        except Exception as e:
            logger.error(f"테이블 생성 중 오류: {str(e)}")
            return False

    except Exception as e:
        logger.error(f"테이블 재생성 중 오류: {str(e)}")
        return False


def verify_table_structure():
    """생성된 테이블 구조 확인"""
    db = get_database_manager()

    try:
        logger.info("\n테이블 구조 확인:")

        # email_events_unprocessed 테이블 구조 확인
        result = db.fetch_all("PRAGMA table_info(email_events_unprocessed)")

        if result:
            logger.info("\nemail_events_unprocessed 테이블 컬럼:")
            for row in result:
                logger.info(f"  - {row['name']} ({row['type']})")

        # 인덱스 확인
        indices = db.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='email_events_unprocessed'"
        )

        if indices:
            logger.info("\nemail_events_unprocessed 테이블 인덱스:")
            for idx in indices:
                logger.info(f"  - {idx['name']}")

    except Exception as e:
        logger.error(f"테이블 구조 확인 중 오류: {str(e)}")


if __name__ == "__main__":
    print("=" * 60)
    print("Email Dashboard 테이블 재생성")
    print("주의: 모든 데이터가 삭제됩니다!")
    print("=" * 60)

    # 확인 프롬프트
    response = input("\n계속하시겠습니까? (yes/no): ")
    if response.lower() != "yes":
        print("취소되었습니다.")
        sys.exit(0)

    print()

    if reset_email_dashboard_tables():
        print("\n✅ Email Dashboard 테이블 재생성 완료")

        # 테이블 구조 확인
        verify_table_structure()

        print("\n생성된 테이블:")
        print("  1. email_agendas_chair - 의장 발송 아젠다")
        print("  2. email_agenda_member_responses - 멤버 기관 응답 내용")
        print("  3. email_agenda_member_response_times - 멤버 기관 응답 시간")
        print("  4. email_events_unprocessed - 미처리 이벤트 (신규)")
    else:
        print("\n❌ Email Dashboard 테이블 재생성 실패")
        print("로그를 확인하세요.")
