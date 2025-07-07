"""
배치 처리 서비스
modules/mail_process/services/batch_processor.py
"""

from datetime import datetime
from typing import Dict, List, Tuple, Optional

from infra.core.logger import get_logger
from ..mail_processor_schema import (
    ProcessedMailData,
    ProcessingStatus,
    SenderType,
)


class BatchProcessor:
    """배치 처리 서비스"""

    def __init__(self, db_service, event_service):
        """
        Args:
            db_service: 데이터베이스 서비스
            event_service: 이벤트 서비스
        """
        self.logger = get_logger(__name__)
        self.db_service = db_service
        self.event_service = event_service

    async def batch_save_to_database(
        self, mails_to_save: List[Tuple[ProcessedMailData, str]]
    ) -> Dict:
        """배치 DB 저장"""
        saved = 0
        failed = 0

        try:
            # 트랜잭션으로 배치 처리
            with self.db_service.db_manager.transaction():
                for processed_mail, clean_content in mails_to_save:
                    try:
                        success = self.db_service.save_mail_with_hash(
                            processed_mail, clean_content
                        )
                        if success:
                            saved += 1
                        else:
                            failed += 1
                    except Exception as e:
                        if "UNIQUE constraint failed" in str(e):
                            self.logger.debug(
                                f"중복 저장 시도: {processed_mail.mail_id}"
                            )
                        else:
                            self.logger.error(f"DB 저장 오류: {str(e)}")
                        failed += 1

        except Exception as e:
            self.logger.error(f"배치 DB 저장 실패: {str(e)}")
            failed += len(mails_to_save)

        return {"saved": saved, "failed": failed}

    async def batch_publish_events(
        self, events_to_publish: List[Tuple[str, Dict, Dict]]
    ) -> Dict:
        """배치 이벤트 발행"""
        published = 0

        for account_id, event_mail, original_mail in events_to_publish:
            try:
                self.event_service.publish_mail_event(
                    account_id=account_id,
                    mail=event_mail,
                    keywords=original_mail.get("keywords", []),
                    clean_content=original_mail.get("clean_content", ""),
                )
                published += 1
            except Exception as e:
                self.logger.error(f"이벤트 발행 실패: {str(e)}")

        return {"published": published}

    def create_processed_mail_data(
        self, account_id: str, mail: Dict
    ) -> ProcessedMailData:
        """ProcessedMailData 객체 생성 (확장된 버전)"""
        # 기본 정보
        mail_data = {
            "mail_id": mail.get("id", "unknown"),
            "account_id": account_id,
            "subject": mail.get("subject", ""),
            "body_preview": mail.get("bodyPreview", ""),
            "sent_time": mail.get("sent_time", datetime.now()),
            "processed_at": datetime.now(),
            # 발신자 정보
            "sender_address": mail.get("sender_address", ""),
            "sender_name": mail.get("sender_name", ""),
            "sender_type": self._parse_sender_type(mail.get("sender_type")),
            "sender_organization": mail.get("sender_organization"),
            # 처리 결과
            "keywords": mail.get("keywords", []),
            "summary": mail.get("summary"),
            "processing_status": self._parse_processing_status(
                mail.get("processing_status", "SUCCESS")
            ),
            "error_message": mail.get("error_message"),
            # IACS 관련 정보 - 통일된 네이밍 적용
            "agenda_code": mail.get("agenda_code"),
            "agenda_base": mail.get("agenda_base"),
            "agenda_version": mail.get("agenda_version"),
            "agenda_panel": mail.get("agenda_panel"),  # agenda_org에서 변경
            "response_org": mail.get("response_org"),
            "response_version": mail.get("response_version"),
            "agenda_info": mail.get("agenda_info"),
            "additional_agenda_references": mail.get(
                "additional_agenda_references", []
            ),
            # 메일 메타정보
            "mail_type": mail.get("mail_type", "OTHER"),
            "decision_status": mail.get("decision_status", "created"),
            "urgency": mail.get("urgency", "NORMAL"),
            "is_reply": mail.get("is_reply", False),
            "reply_depth": mail.get("reply_depth"),
            "is_forward": mail.get("is_forward", False),
            "has_deadline": mail.get("has_deadline", False),
            "deadline": mail.get("deadline"),
            # 정제된 내용
            "clean_content": mail.get("clean_content"),
            # 추출 메타데이터
            "extraction_metadata": mail.get("extraction_metadata"),
        }

        return ProcessedMailData(**mail_data)

    def _parse_sender_type(self, sender_type: Optional[str]) -> Optional[SenderType]:
        """발신자 타입 파싱"""
        if not sender_type:
            return None

        try:
            return SenderType(sender_type.upper())
        except ValueError:
            return None

    def _parse_processing_status(self, status: str) -> ProcessingStatus:
        """처리 상태 파싱"""
        try:
            return ProcessingStatus(status.upper())
        except ValueError:
            return ProcessingStatus.FAILED
