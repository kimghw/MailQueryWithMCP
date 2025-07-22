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
        self,
        mail: Dict[str, Any],
        iacs_info: Dict[str, Any],
        semantic_info: Dict[str, Any],
    ) -> None:
        """
        메일 수신 이벤트 발행 (통합 포맷) - null 값 방지

        Args:
            mail: 원본 메일 데이터
            iacs_info: IACS 파싱 결과의 extracted_info
            semantic_info: 추출된 semantic 정보 (keywords, deadline 등)
        """
        try:
            # 이벤트 정보 구성 - 기본값 설정으로 null 방지
            event_info = {
                # 원본 메일 정보
                "sentDateTime": mail.get("receivedDateTime", ""),
                "hasAttachments": mail.get("hasAttachments", False),
                "subject": mail.get("subject", ""),
                "webLink": mail.get("web_link", ""),
                "body": mail.get("body", {}).get("content", ""),
                # 발신자 정보 - 기본값 설정
                "sender": "",
                "sender_address": "",
                # IACS extracted_info 병합 - null 대신 기본값
                "agenda_code": iacs_info.get("agenda_code") or "",
                "agenda_base": iacs_info.get("agenda_base") or "",
                "agenda_base_version": iacs_info.get("agenda_base_version") or "",
                "agenda_panel": iacs_info.get("agenda_panel") or "",
                "agenda_year": iacs_info.get("agenda_year") or "",
                "agenda_number": iacs_info.get("agenda_number") or "",
                "agenda_version": iacs_info.get("agenda_version") or "",
                "response_org": iacs_info.get("response_org") or "",
                "response_version": iacs_info.get("response_version") or "",
                "sent_time": iacs_info.get("sent_time") or "",
                "sender_type": iacs_info.get("sender_type") or "OTHER",  # 기본값 OTHER
                "sender_organization": iacs_info.get("sender_organization") or "",  # 기본값 빈 문자열
                "parsing_method": iacs_info.get("parsing_method") or "unknown",
                # semantic_info
                "keywords": semantic_info.get("keywords", []),  # 리스트만 추출
                "deadline": semantic_info.get("deadline") or "",  # 빈 문자열 기본값
                "has_deadline": semantic_info.get("has_deadline", False),
                "mail_type": semantic_info.get("mail_type") or "OTHER",
                "decision_status": semantic_info.get("decision_status") or "created",
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

            # 간단한 로깅 - 추가 정보 포함
            subject = mail.get("subject", "")
            truncated_subject = subject[:50] + "..." if len(subject) > 50 else subject
            keywords_count = len(semantic_info.get("keywords", []))
            
            self.logger.info(
                f"메일 수신 이벤트 발행 - "
                f"ID: {mail.get('id', 'unknown')}, "
                f"제목: {truncated_subject}, "
                f"키워드: {keywords_count}개, "
                f"발신자타입: {event_info['sender_type']}, "
                f"조직: {event_info['sender_organization']}"
            )

        except Exception as e:
            self.logger.error(f"메일 이벤트 발행 실패: {str(e)}")
            # 이벤트 발행 실패는 전체 프로세스를 중단시키지 않음

    def _extract_sender_info(
        self, mail: Dict[str, Any], event_info: Dict[str, Any]
    ) -> None:
        """발신자 정보 추출하여 event_info에 설정 - 기본값 보장"""
        # 기본값 설정
        event_info["sender"] = ""
        event_info["sender_address"] = ""
        
        try:
            if mail.get("sender"):
                sender_info = mail["sender"].get("emailAddress", {})
                if isinstance(sender_info, dict):
                    event_info["sender"] = sender_info.get("name", "")
                    event_info["sender_address"] = sender_info.get("address", "")
            elif mail.get("from"):
                from_info = mail["from"].get("emailAddress", {})
                if isinstance(from_info, dict):
                    event_info["sender"] = from_info.get("name", "")
                    event_info["sender_address"] = from_info.get("address", "")
        except Exception as e:
            self.logger.warning(f"발신자 정보 추출 중 오류: {str(e)}")
            # 오류 발생 시에도 기본값 유지

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