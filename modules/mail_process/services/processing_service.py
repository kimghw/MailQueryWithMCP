"""
메일 처리 서비스
개별 메일의 처리 로직 구현
modules/mail_process/services/processing_service.py
"""

from datetime import datetime
from typing import Dict, Optional, Any

from infra.core.logger import get_logger
from modules.mail_process.mail_processor_schema import (
    ProcessedMailData,
    ProcessingStatus,
    GraphMailItem,
    SenderType,
    MailType,
    DecisionStatus,
)
from ..utilities.mail_parser import MailParser
from ..utilities.text_cleaner import TextCleaner
from ..utilities.iacs import IACSCodeParser

logger = get_logger(__name__)


class ProcessingService:
    """메일 처리 서비스"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.mail_parser = MailParser()
        self.text_cleaner = TextCleaner()
        self.iacs_parser = IACSCodeParser()

    async def process_mail(
        self, account_id: str, mail: GraphMailItem
    ) -> ProcessedMailData:
        """
        개별 메일 처리

        Args:
            account_id: 계정 ID
            mail: Graph API 메일 아이템

        Returns:
            ProcessedMailData: 처리된 메일 데이터
        """
        try:
            # 1. 기본 정보 추출
            mail_dict = mail.model_dump()
            sender_address, sender_name = self.mail_parser.extract_sender_info(
                mail_dict
            )
            subject = self.mail_parser.extract_subject(mail_dict)
            sent_time = self.mail_parser.extract_sent_time(mail_dict)
            body_preview = self.mail_parser.extract_body_preview(mail_dict)
            body_content = self.mail_parser.extract_body_content(mail_dict)

            # 2. 텍스트 정제
            clean_content = self.text_cleaner.clean_text(f"{subject}\n\n{body_content}")

            # 3. IACS 정보 추출
            iacs_info = self.iacs_parser.extract_all_patterns(
                subject=subject, body=body_content, mail=mail_dict
            )

            # 4. 키워드 추출 (현재는 간단한 구현)
            keywords = self._extract_keywords(subject, clean_content, iacs_info)

            # 5. 메일 타입 및 상태 결정
            mail_type = self._determine_mail_type(subject, iacs_info)
            decision_status = self._determine_decision_status(subject, body_content)

            # 6. ProcessedMailData 생성
            processed_mail = ProcessedMailData(
                mail_id=mail.id,
                account_id=account_id,
                subject=subject,
                body_preview=body_preview,
                sent_time=sent_time,
                sender_address=sender_address,
                sender_name=sender_name,
                sender_type=(
                    SenderType(iacs_info.get("sender_type"))
                    if iacs_info.get("sender_type")
                    else None
                ),
                sender_organization=iacs_info.get("sender_organization"),
                keywords=keywords,
                summary=self._generate_summary(subject, body_preview),
                processing_status=ProcessingStatus.SUCCESS,
                # IACS 관련 정보
                agenda_code=iacs_info.get("extracted_info", {}).get("agenda_code"),
                agenda_base=iacs_info.get("extracted_info", {}).get("agenda_base"),
                agenda_version=iacs_info.get("extracted_info", {}).get(
                    "agenda_version"
                ),
                agenda_panel=iacs_info.get("extracted_info", {}).get("agenda_panel"),
                response_org=iacs_info.get("response_org"),
                response_version=iacs_info.get("response_version"),
                agenda_info=iacs_info.get("extracted_info"),
                additional_agenda_references=iacs_info.get(
                    "additional_agenda_references", []
                ),
                # 메일 메타정보
                mail_type=mail_type,
                decision_status=decision_status,
                urgency=iacs_info.get("urgency", "NORMAL"),
                is_reply=iacs_info.get("is_reply", False),
                reply_depth=iacs_info.get("reply_depth"),
                is_forward=iacs_info.get("is_forward", False),
                has_deadline=self._check_deadline(body_content),
                deadline=self._extract_deadline(body_content),
                clean_content=clean_content,
                extraction_metadata={
                    "iacs_parsing": iacs_info,
                    "text_length": len(clean_content),
                    "processing_time": datetime.now().isoformat(),
                },
            )

            self.logger.debug(
                f"메일 처리 완료 - ID: {mail.id}, "
                f"제목: {subject[:50]}..., "
                f"IACS: {processed_mail.agenda_code}"
            )

            return processed_mail

        except Exception as e:
            self.logger.error(f"메일 처리 실패 - ID: {mail.id}, error: {str(e)}")

            # 실패한 경우 최소한의 정보만 포함하여 반환
            return ProcessedMailData(
                mail_id=mail.id,
                account_id=account_id,
                subject=getattr(mail, "subject", "Unknown"),
                body_preview=getattr(mail, "body_preview", ""),
                sent_time=getattr(mail, "received_date_time", datetime.now()),
                sender_address="unknown@unknown.com",
                keywords=[],
                processing_status=ProcessingStatus.FAILED,
                error_message=str(e),
                mail_type=MailType.OTHER,
                decision_status=DecisionStatus.CREATED,
                urgency="NORMAL",
            )

    def _extract_keywords(
        self, subject: str, content: str, iacs_info: Dict[str, Any]
    ) -> list[str]:
        """키워드 추출 (간단한 구현)"""
        keywords = []

        # IACS 코드를 키워드로 추가
        if iacs_info.get("extracted_info", {}).get("agenda_code"):
            keywords.append(iacs_info["extracted_info"]["agenda_code"])

        # 제목에서 중요 단어 추출
        important_words = [
            "urgent",
            "important",
            "deadline",
            "action",
            "review",
            "approval",
        ]
        for word in important_words:
            if word.lower() in subject.lower():
                keywords.append(word.upper())

        # 발신자 조직 추가
        if iacs_info.get("sender_organization"):
            keywords.append(iacs_info["sender_organization"])

        # 추가 아젠다 참조 중 처음 3개만
        additional_refs = iacs_info.get("additional_agenda_references", [])
        keywords.extend(additional_refs[:3])

        # 중복 제거 후 최대 10개까지만 반환
        return list(dict.fromkeys(keywords))[:10]

    def _determine_mail_type(self, subject: str, iacs_info: Dict[str, Any]) -> MailType:
        """메일 타입 결정"""
        subject_lower = subject.lower()

        if iacs_info.get("is_reply"):
            return MailType.RESPONSE
        elif "request" in subject_lower or "req" in subject_lower:
            return MailType.REQUEST
        elif "notification" in subject_lower or "notice" in subject_lower:
            return MailType.NOTIFICATION
        elif "completed" in subject_lower or "done" in subject_lower:
            return MailType.COMPLETED
        else:
            return MailType.OTHER

    def _determine_decision_status(self, subject: str, body: str) -> DecisionStatus:
        """결정 상태 결정"""
        combined = f"{subject} {body}".lower()

        if "decision" in combined or "decided" in combined:
            return DecisionStatus.DECISION
        elif "review" in combined:
            return DecisionStatus.REVIEW
        elif "consolidated" in combined:
            return DecisionStatus.CONSOLIDATED
        elif "comment" in combined:
            return DecisionStatus.COMMENT
        else:
            return DecisionStatus.CREATED

    def _generate_summary(self, subject: str, body_preview: str) -> Optional[str]:
        """간단한 요약 생성"""
        if not body_preview:
            return None

        # 제목과 본문 미리보기를 결합하여 요약
        summary = f"{subject}. {body_preview}"

        # 최대 200자로 제한
        if len(summary) > 200:
            summary = summary[:197] + "..."

        return summary

    def _check_deadline(self, content: str) -> bool:
        """마감일 존재 여부 확인"""
        deadline_keywords = ["deadline", "due date", "by", "until", "마감", "기한"]
        content_lower = content.lower()

        return any(keyword in content_lower for keyword in deadline_keywords)

    def _extract_deadline(self, content: str) -> Optional[datetime]:
        """마감일 추출 (향후 개선 필요)"""
        # 현재는 간단한 구현
        # 향후 자연어 처리나 정규식을 사용한 날짜 추출 로직 추가
        return None
