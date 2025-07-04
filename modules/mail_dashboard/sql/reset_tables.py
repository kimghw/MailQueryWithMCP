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
        from modules.mail_dashboard.service import EmailDashboardService

        service = EmailDashboardService()
        if service._initialize_database_tables():
            logger.info("새 스키마로 테이블 생성 완료")
            return True
        else:
            logger.error("테이블 생성 실패")
            return False

    except Exception as e:
        logger.error(f"테이블 재생성 중 오류: {str(e)}")
        return False


if __name__ == "__main__":
    if reset_email_dashboard_tables():
        print("✅ Email Dashboard 테이블 재생성 완료")
    else:
        print("❌ Email Dashboard 테이블 재생성 실패")
