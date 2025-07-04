import asyncio
from infra.core.database import get_database_manager
from infra.core.logger import get_logger

logger = get_logger(__name__)


async def clear_all_data():
    """
    'accounts', 'mail_history', 'processing_logs', 'account_audit_logs' 테이블의 모든 데이터를 삭제합니다.
    """
    db = get_database_manager()
    try:
        logger.info("모든 테이블의 데이터 삭제를 시작합니다.")

        # 외래 키 제약 조건을 고려하여 자식 테이블부터 삭제합니다.
        with db.transaction():
            logger.info("'mail_history' 테이블 데이터 삭제 중...")
            history_rows = db.delete("mail_history", "1=1")
            logger.info(
                f"'mail_history' 테이블에서 {history_rows}개 행이 삭제되었습니다."
            )

            logger.info("'processing_logs' 테이블 데이터 삭제 중...")
            log_rows = db.delete("processing_logs", "1=1")
            logger.info(
                f"'processing_logs' 테이블에서 {log_rows}개 행이 삭제되었습니다."
            )

            logger.info("'account_audit_logs' 테이블 데이터 삭제 중...")
            audit_log_rows = db.delete("account_audit_logs", "1=1")
            logger.info(
                f"'account_audit_logs' 테이블에서 {audit_log_rows}개 행이 삭제되었습니다."
            )

            logger.info("'accounts' 테이블 데이터 삭제 중...")
            account_rows = db.delete("accounts", "1=1")
            logger.info(f"'accounts' 테이블에서 {account_rows}개 행이 삭제되었습니다.")

        logger.info("모든 관련 테이블의 데이터 삭제가 완료되었습니다.")

    except Exception as e:
        logger.error(f"데이터 삭제 중 오류 발생: {e}", exc_info=True)
    finally:
        db.close()
        logger.info("데이터베이스 연결이 종료되었습니다.")


if __name__ == "__main__":
    # uvloop가 설치되어 있다면 더 빠른 이벤트 루프를 사용할 수 있습니다.
    try:
        import uvloop

        uvloop.install()
    except ImportError:
        pass

    asyncio.run(clear_all_data())
