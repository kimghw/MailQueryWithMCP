"""이벤트 발행 서비스"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional
from infra.core.logger import get_logger
from infra.core.kafka_client import get_kafka_client
from infra.core.config import get_config


class MailEventService:
    """메일 이벤트 발행 서비스"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.kafka_client = get_kafka_client()
        self.config = get_config()

    def publish_mail_event(self, account_id: str, mail: Dict, keywords: List[str], clean_content: str) -> None:
        """
        메일 처리 이벤트 발행
        
        Args:
            account_id: 계정 ID
            mail: 원본 메일 데이터
            keywords: 추출된 키워드
            clean_content: 정제된 내용
        """
        try:
            # datetime 객체들을 문자열로 변환
            mail_copy = self._convert_datetime_to_string(mail.copy())

            # 키워드 추가
            mail_copy['extracted_keywords'] = keywords
            
            # body.content를 clean_content로 교체
            if 'body' in mail_copy and isinstance(mail_copy['body'], dict):
                mail_copy['body']['content'] = clean_content
                # contentType이 HTML인 경우 text로 변경 (정제된 내용이므로)
                if mail_copy['body'].get('contentType') == 'html':
                    mail_copy['body']['contentType'] = 'text'

            # 이벤트 구조 생성
            event_data = {
                "event_type": "email_type",
                "event_id": str(uuid.uuid4()),
                "account_id": account_id,
                "occurred_at": datetime.now().isoformat(),
                "api_endpoint": "/v1.0/me/messages",
                "response_status": 200,
                "request_params": {
                    "$select": "id,subject,from,body,bodyPreview,receivedDateTime",
                    "$top": 50
                },
                "response_data": {
                    "value": [mail_copy],
                    "@odata.context": f"https://graph.microsoft.com/v1.0/$metadata#users('{account_id}')/messages",
                    "@odata.nextLink": "https://graph.microsoft.com/v1.0/me/messages?$skip=50"
                },
                "response_timestamp": datetime.now().isoformat()
            }

            self.kafka_client.produce_event(
                topic=self.config.kafka_topic_email_events,
                event_data=event_data,
                key=account_id
            )

            # 이벤트 데이터의 일부를 로그로 남겨 확인이 용이하도록 함
            log_payload = {
                "event_type": event_data["event_type"],
                "account_id": account_id,
                "mail_id": mail.get("id"),
                "subject": mail.get("subject", "")[:30] + "...",
                "keywords_count": len(keywords)
            }
            self.logger.info(f"메일 처리 이벤트 발행: {log_payload}")

        except Exception as e:
            self.logger.error(f"Kafka 이벤트 발행 실패: {str(e)}")
            # 이벤트 발행 실패는 전체 프로세스를 중단시키지 않음

    def _convert_datetime_to_string(self, data: any) -> any:
        """재귀적으로 datetime 객체를 문자열로 변환"""
        if isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            return {key: self._convert_datetime_to_string(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._convert_datetime_to_string(item) for item in data]
        else:
            return data

    def publish_batch_complete_event(self, account_id: str, processed_count: int, 
                                   skipped_count: int, failed_count: int) -> None:
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
                    "total_count": processed_count + skipped_count + failed_count
                }
            }

            self.kafka_client.produce_event(
                topic=self.config.kafka_topic_email_events,
                event_data=event_data,
                key=f"{account_id}_batch"
            )

            self.logger.info(
                f"배치 완료 이벤트 발행 - 계정: {account_id}, "
                f"처리: {processed_count}, 건너뜀: {skipped_count}, 실패: {failed_count}"
            )

        except Exception as e:
            self.logger.error(f"배치 완료 이벤트 발행 실패: {str(e)}")