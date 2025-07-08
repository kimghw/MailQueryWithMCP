"""
메일 영속성 서비스
처리된 메일 데이터의 저장을 관리
modules/mail_process/services/persistence_service.py
"""

from infra.core.logger import get_logger
from infra.core.exceptions import DatabaseError
from modules.mail_process.mail_processor_schema import ProcessedMailData
from .db_service import MailDatabaseService

logger = get_logger(__name__)


class PersistenceService:
    """메일 데이터 영속성 관리 서비스"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.db_service = MailDatabaseService()

    def save_processed_mail(self, processed_mail: ProcessedMailData) -> bool:
        """
        처리된 메일 저장

        Args:
            processed_mail: 처리된 메일 데이터

        Returns:
            저장 성공 여부
        """
        try:
            # 중복 확인 (안전장치)
            if self.db_service.check_duplicate_by_id(processed_mail.mail_id):
                self.logger.warning(
                    f"저장 시도 중 중복 발견 - mail_id: {processed_mail.mail_id}"
                )
                return False

            # 메일 히스토리 저장
            success = self.db_service.save_mail_history(processed_mail)

            if success:
                self.logger.debug(
                    f"메일 저장 성공 - "
                    f"mail_id: {processed_mail.mail_id}, "
                    f"subject: {processed_mail.subject[:50]}..., "
                    f"keywords: {len(processed_mail.keywords)}개"
                )
            else:
                self.logger.warning(
                    f"메일 저장 실패 - mail_id: {processed_mail.mail_id}"
                )

            return success

        except DatabaseError as e:
            self.logger.error(
                f"데이터베이스 오류 - mail_id: {processed_mail.mail_id}, "
                f"error: {str(e)}"
            )
            return False

        except Exception as e:
            self.logger.error(
                f"예상치 못한 오류 - mail_id: {processed_mail.mail_id}, "
                f"error: {str(e)}",
                exc_info=True,
            )
            return False

    def save_batch_result(self, account_id: str, processing_stats: dict) -> bool:
        """
        배치 처리 결과 저장 (향후 확장용)

        Args:
            account_id: 계정 ID
            processing_stats: 처리 통계

        Returns:
            저장 성공 여부
        """
        # 현재는 로깅만 수행
        self.logger.info(
            f"배치 처리 결과 - "
            f"account_id: {account_id}, "
            f"new: {processing_stats.get('new_count', 0)}, "
            f"duplicate: {processing_stats.get('duplicate_count', 0)}, "
            f"failed: {processing_stats.get('failed_count', 0)}"
        )

        # 향후 여기에 다음과 같은 기능 추가 가능:
        # - 배치 처리 히스토리 테이블 저장
        # - 처리 성능 메트릭 저장
        # - 오류 상세 정보 저장

        return True

    def cleanup_old_mail_history(self, days: int = 90) -> int:
        """
        오래된 메일 히스토리 정리 (향후 확장용)

        Args:
            days: 보관 기간 (일)

        Returns:
            삭제된 레코드 수
        """
        # 향후 구현 예정
        # - 지정된 기간보다 오래된 메일 히스토리 삭제
        # - 아카이빙 옵션 제공
        # - 통계 데이터는 별도 보관

        self.logger.info(f"{days}일 이상 된 메일 히스토리 정리 기능은 향후 구현 예정")
        return 0
