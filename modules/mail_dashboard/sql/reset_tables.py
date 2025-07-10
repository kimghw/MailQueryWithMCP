"""
Email Dashboard 테이블 내용 삭제 스크립트

모든 테이블의 데이터를 삭제합니다. (테이블 구조는 유지)
주의: 모든 데이터가 삭제됩니다!
"""

import os
import sys

# 프로젝트 루트 경로 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, project_root)

from infra.core import get_database_manager, get_logger

logger = get_logger(__name__)


def clear_email_dashboard_tables():
    """Email Dashboard 테이블 내용 삭제"""
    db = get_database_manager()

    try:
        logger.info("Email Dashboard 테이블 데이터 삭제 시작")

        # 삭제할 테이블 목록 (의존성 순서 고려)
        tables_to_clear = [
            "agenda_pending",
            "agenda_responses_receivedtime",
            "agenda_responses_content",
            "agenda_chair",
            "agenda_all",
        ]

        total_deleted = 0
        table_results = []

        with db.transaction():
            for table in tables_to_clear:
                try:
                    if db.table_exists(table):
                        # 테이블 레코드 수 확인
                        count_result = db.fetch_one(
                            f"SELECT COUNT(*) as count FROM {table}"
                        )
                        before_count = count_result["count"] if count_result else 0

                        # 데이터 삭제
                        db.execute_query(f"DELETE FROM {table}")

                        # 삭제 후 확인
                        count_result = db.fetch_one(
                            f"SELECT COUNT(*) as count FROM {table}"
                        )
                        after_count = count_result["count"] if count_result else 0

                        deleted_count = before_count - after_count
                        total_deleted += deleted_count

                        table_results.append(
                            {
                                "table": table,
                                "before": before_count,
                                "after": after_count,
                                "deleted": deleted_count,
                                "status": "✓" if after_count == 0 else "✗",
                            }
                        )

                        logger.info(
                            f"테이블 데이터 삭제 완료: {table} ({deleted_count}개 레코드)"
                        )
                    else:
                        logger.warning(f"테이블이 존재하지 않음: {table}")
                        table_results.append(
                            {
                                "table": table,
                                "before": 0,
                                "after": 0,
                                "deleted": 0,
                                "status": "⚠",
                            }
                        )

                except Exception as e:
                    logger.error(f"테이블 데이터 삭제 실패 {table}: {str(e)}")
                    table_results.append(
                        {
                            "table": table,
                            "before": "?",
                            "after": "?",
                            "deleted": 0,
                            "status": "✗",
                        }
                    )

            # SQLite의 경우 VACUUM으로 공간 정리
            try:
                db.execute_query("VACUUM")
                logger.info("데이터베이스 공간 정리 완료 (VACUUM)")
            except Exception as e:
                logger.warning(f"VACUUM 실행 실패: {str(e)}")

        return {
            "success": True,
            "total_deleted": total_deleted,
            "table_results": table_results,
        }

    except Exception as e:
        logger.error(f"테이블 데이터 삭제 중 오류: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "total_deleted": 0,
            "table_results": [],
        }


def verify_table_status():
    """테이블 상태 확인"""
    db = get_database_manager()

    try:
        logger.info("\n테이블 상태 확인:")

        tables = [
            ("agenda_all", "모든 이벤트 로그"),
            ("agenda_chair", "의장 발송 의제"),
            ("agenda_responses_content", "기관별 응답 내용"),
            ("agenda_responses_receivedtime", "기관별 응답 시간"),
            ("agenda_pending", "미처리 이벤트"),
        ]

        status_results = []

        for table_name, description in tables:
            if db.table_exists(table_name):
                # 레코드 수 확인
                count_result = db.fetch_one(
                    f"SELECT COUNT(*) as count FROM {table_name}"
                )
                record_count = count_result["count"] if count_result else 0

                # 테이블 정보 조회
                table_info = db.fetch_all(f"PRAGMA table_info({table_name})")
                column_count = len(table_info) if table_info else 0

                status_results.append(
                    {
                        "table": table_name,
                        "description": description,
                        "exists": True,
                        "records": record_count,
                        "columns": column_count,
                        "status": (
                            "✓" if record_count == 0 else f"⚠ ({record_count}개 레코드)"
                        ),
                    }
                )

                logger.info(f"{table_name} - {description}")
                logger.info(
                    f"  상태: {'비어있음' if record_count == 0 else f'{record_count}개 레코드 존재'}"
                )
                logger.info(f"  컬럼: {column_count}개")
            else:
                status_results.append(
                    {
                        "table": table_name,
                        "description": description,
                        "exists": False,
                        "records": 0,
                        "columns": 0,
                        "status": "✗",
                    }
                )
                logger.error(f"{table_name} - 테이블이 존재하지 않음")

        return status_results

    except Exception as e:
        logger.error(f"테이블 상태 확인 중 오류: {str(e)}")
        return []


def print_results(result):
    """실행 결과 출력"""
    print("\n" + "=" * 60)
    print("실행 결과")
    print("=" * 60)

    if result["success"]:
        print(f"\n✅ 성공적으로 완료")
        print(f"총 삭제된 레코드: {result['total_deleted']}개")

        if result["table_results"]:
            print("\n테이블별 결과:")
            print("-" * 60)
            print(f"{'테이블':30} {'삭제전':>10} {'삭제후':>10} {'삭제수':>10}")
            print("-" * 60)

            for tr in result["table_results"]:
                print(
                    f"{tr['status']} {tr['table']:28} {str(tr['before']):>10} "
                    f"{str(tr['after']):>10} {str(tr['deleted']):>10}"
                )
    else:
        print(f"\n❌ 실행 실패")
        print(f"오류: {result.get('error', '알 수 없는 오류')}")


if __name__ == "__main__":
    print("=" * 60)
    print("Email Dashboard 테이블 데이터 삭제")
    print("주의: 모든 데이터가 삭제됩니다! (테이블 구조는 유지)")
    print("=" * 60)

    # 현재 상태 확인
    print("\n현재 테이블 상태:")
    verify_table_status()

    # 확인 프롬프트
    response = input("\n모든 데이터를 삭제하시겠습니까? (yes/no): ")
    if response.lower() not in ["yes", "y"]:
        print("취소되었습니다.")
        sys.exit(0)

    print()

    # 데이터 삭제 실행
    result = clear_email_dashboard_tables()

    # 결과 출력
    print_results(result)

    if result["success"]:
        # 삭제 후 상태 확인
        print("\n삭제 후 테이블 상태:")
        verify_table_status()

        print("\n✅ Email Dashboard 테이블 데이터 삭제 완료")
        print("테이블 구조는 그대로 유지되었습니다.")
    else:
        print("\n❌ Email Dashboard 테이블 데이터 삭제 실패")
        print("로그를 확인하세요.")
