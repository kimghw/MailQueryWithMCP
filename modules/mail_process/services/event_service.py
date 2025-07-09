"""
이벤트 발행 서비스
메일 처리 이벤트를 Kafka로 발행
modules/mail_process/services/event_service.py
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from infra.core.config import get_config
from infra.core.kafka_client import get_kafka_client
from infra.core.logger import get_logger


class MailEventService:
    """메일 이벤트 발행 서비스"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.kafka_client = get_kafka_client()
        self.config = get_config()

    async def publish_mail_received_event(
        self, mail: Dict[str, Any], iacs_info: Dict[str, Any], keywords: List[str]
    ) -> None:
        """
        메일 수신 이벤트 발행 (통합 포맷)

        Args:
            mail: 원본 메일 데이터
            iacs_info: IACS 파싱 결과의 extracted_info
            keywords: 추출된 키워드 리스트
        """
        try:
            # 이벤트 정보 구성
            event_info = {
                # 원본 메일 정보
                "sentDateTime": mail.get("receivedDateTime", ""),
                "hasAttachments": mail.get("hasAttachments", False),
                "subject": mail.get("subject", ""),
                "webLink": mail.get("webLink", ""),
                "body": mail.get("body", {}).get("content", ""),
                # 발신자 정보
                "sender": "",
                "sender_address": "",
                # IACS extracted_info 병합
                "agenda_code": iacs_info.get("agenda_code"),
                "agenda_base": iacs_info.get("agenda_base"),
                "agenda_base_version": iacs_info.get("agenda_base_version"),
                "agenda_panel": iacs_info.get("agenda_panel"),
                "agenda_year": iacs_info.get("agenda_year"),
                "agenda_number": iacs_info.get("agenda_number"),
                "agenda_version": iacs_info.get("agenda_version"),
                "response_org": iacs_info.get("response_org"),
                "response_version": iacs_info.get("response_version"),
                "sent_time": iacs_info.get("sent_time"),
                "sender_type": iacs_info.get("sender_type"),
                "sender_organization": iacs_info.get("sender_organization"),
                "parsing_method": iacs_info.get("parsing_method"),
                # semantic_info
                "keywords": keywords,
                "deadline": self._extract_deadline(mail),
                "has_deadline": self._check_deadline(mail),
                "mail_type": self._determine_mail_type(
                    mail.get("subject", ""), iacs_info
                ),
                "decision_status": self._determine_decision_status(
                    mail.get("subject", ""), mail.get("body", {}).get("content", "")
                ),
            }

            # 발신자 정보 추출 및 설정
            self._extract_sender_info(mail, event_info)

            # 이벤트 발행
            event_data = {
                "event_type": "email.received",
                "event_id": str(uuid.uuid4()),
                "mail_id": mail.get("id", ""),
                "occurred_at": datetime.now().isoformat(),
                "event_info": event_info,
            }

            self.kafka_client.produce_event(
                topic=self.config.kafka_topic_email_events,
                event_data=event_data,
                key=mail.get("id", ""),  # mail_id를 key로 사용
            )

            # 간단한 로깅
            subject = mail.get("subject", "")
            truncated_subject = subject[:50] + "..." if len(subject) > 50 else subject
            self.logger.info(
                f"메일 수신 이벤트 발행 - "
                f"ID: {mail.get('id', 'unknown')}, "
                f"제목: {truncated_subject}, "
                f"키워드: {len(keywords)}개"
            )

        except Exception as e:
            self.logger.error(f"메일 이벤트 발행 실패: {str(e)}")
            # 이벤트 발행 실패는 전체 프로세스를 중단시키지 않음

    def _extract_sender_info(
        self, mail: Dict[str, Any], event_info: Dict[str, Any]
    ) -> None:
        """발신자 정보 추출하여 event_info에 설정"""
        if mail.get("sender"):
            sender_info = mail["sender"].get("emailAddress", {})
            event_info["sender"] = sender_info.get("name", "")
            event_info["sender_address"] = sender_info.get("address", "")
        elif mail.get("from"):
            from_info = mail["from"].get("emailAddress", {})
            event_info["sender"] = from_info.get("name", "")
            event_info["sender_address"] = from_info.get("address", "")

    def _determine_mail_type(self, subject: str, iacs_info: Dict[str, Any]) -> str:
        """메일 타입 결정"""
        subject_lower = subject.lower()

        if iacs_info.get("is_reply"):
            return "RESPONSE"
        elif "request" in subject_lower or "req" in subject_lower:
            return "REQUEST"
        elif "notification" in subject_lower or "notice" in subject_lower:
            return "NOTIFICATION"
        elif "completed" in subject_lower or "done" in subject_lower:
            return "COMPLETED"
        else:
            return "OTHER"

    def _determine_decision_status(self, subject: str, body: str) -> str:
        """결정 상태 결정"""
        combined = f"{subject} {body}".lower()

        if "decision" in combined or "decided" in combined:
            return "decision"
        elif "review" in combined:
            return "review"
        elif "consolidated" in combined:
            return "consolidated"
        elif "comment" in combined:
            return "comment"
        else:
            return "created"

    def _check_deadline(self, mail: Dict[str, Any]) -> bool:
        """마감일 존재 여부 확인"""
        content = f"{mail.get('subject', '')} {mail.get('body', {}).get('content', '')}".lower()
        deadline_keywords = ["deadline", "due date", "by", "until", "마감", "기한"]

        return any(keyword in content for keyword in deadline_keywords)

    def _extract_deadline(self, mail: Dict[str, Any]) -> Optional[str]:
        """마감일 추출 (향후 개선 필요)"""
        # TODO: 자연어 처리나 정규식을 사용한 날짜 추출 로직 구현
        # 현재는 None 반환
        return None

    async def publish_batch_complete_event(
        self,
        account_id: str,
        processed_count: int,
        skipped_count: int,
        failed_count: int,
    ) -> None:
        """
        배치 처리 완료 이벤트 발행

        Args:
            account_id: 계정 ID
            processed_count: 처리된 메일 수
            skipped_count: 건너뛴 메일 수
            failed_count: 실패한 메일 수
        """
        try:
            event_data = {
                "event_type": "email.batch_processing_complete",
                "event_id": str(uuid.uuid4()),
                "account_id": account_id,
                "occurred_at": datetime.now().isoformat(),
                "statistics": {
                    "processed_count": processed_count,
                    "skipped_count": skipped_count,
                    "failed_count": failed_count,
                    "total_count": processed_count + skipped_count + failed_count,
                },
            }

            self.kafka_client.produce_event(
                topic=self.config.kafka_topic_email_events,
                event_data=event_data,
                key=f"{account_id}_batch",
            )

            self.logger.info(
                f"배치 완료 이벤트 발행 - 계정: {account_id}, "
                f"처리: {processed_count}, 건너뜀: {skipped_count}, 실패: {failed_count}"
            )

        except Exception as e:
            self.logger.error(f"배치 완료 이벤트 발행 실패: {str(e)}")

    def _convert_datetime_to_string(self, data: any) -> any:
        """재귀적으로 datetime 객체를 문자열로 변환"""
        if isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            return {
                key: self._convert_datetime_to_string(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._convert_datetime_to_string(item) for item in data]
        else:
            return data
