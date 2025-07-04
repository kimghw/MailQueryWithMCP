"""메일 파싱 유틸리티"""

from typing import Dict, Optional
from datetime import datetime
from infra.core.logger import get_logger


class MailParser:
    """메일 파싱 유틸리티 - 순수 함수 기반"""

    def __init__(self):
        self.logger = get_logger(__name__)

    def extract_sender_address(self, mail: Dict) -> str:
        """
        발신자 주소 추출 (순수 함수)

        Args:
            mail: 메일 딕셔너리

        Returns:
            발신자 이메일 주소 또는 빈 문자열
        """
        # 1. from 필드 확인
        from_field = mail.get("from", {})
        if from_field and isinstance(from_field, dict):
            email_addr = from_field.get("emailAddress", {})
            if email_addr and email_addr.get("address"):
                return email_addr["address"]

        # 2. sender 필드 확인
        sender_field = mail.get("sender", {})
        if sender_field and isinstance(sender_field, dict):
            email_addr = sender_field.get("emailAddress", {})
            if email_addr and email_addr.get("address"):
                return email_addr["address"]

        # 3. from_address 필드 확인 (GraphMailItem 호환)
        from_address = mail.get("from_address", {})
        if from_address and isinstance(from_address, dict):
            email_addr = from_address.get("emailAddress", {})
            if email_addr and email_addr.get("address"):
                return email_addr["address"]

        # 4. 초안 메일의 경우 빈 문자열 반환
        if mail.get("isDraft", False):
            self.logger.debug(
                f"초안 메일로 발신자 정보 없음: {mail.get('id', 'unknown')}"
            )
            return ""

        # 5. 발신자 정보가 없는 경우 로깅
        self.logger.debug(
            f"발신자 정보 없음",
            extra={
                "mail_id": mail.get("id", "unknown"),
                "is_draft": mail.get("isDraft", False),
                "has_from": bool(mail.get("from")),
                "has_sender": bool(mail.get("sender")),
                "has_from_address": bool(mail.get("from_address")),
                "subject": mail.get("subject", "")[:50],
            },
        )

        return ""

    def extract_sender_name(self, mail: Dict) -> str:
        """
        발신자 이름 추출

        Args:
            mail: 메일 딕셔너리

        Returns:
            발신자 이름 또는 빈 문자열
        """
        # 1. from 필드에서 이름 확인
        from_field = mail.get("from", {})
        if from_field and isinstance(from_field, dict):
            email_addr = from_field.get("emailAddress", {})
            if email_addr and email_addr.get("name"):
                return email_addr["name"]

        # 2. sender 필드에서 이름 확인
        sender_field = mail.get("sender", {})
        if sender_field and isinstance(sender_field, dict):
            email_addr = sender_field.get("emailAddress", {})
            if email_addr and email_addr.get("name"):
                return email_addr["name"]

        # 3. from_address 필드에서 이름 확인
        from_address = mail.get("from_address", {})
        if from_address and isinstance(from_address, dict):
            email_addr = from_address.get("emailAddress", {})
            if email_addr and email_addr.get("name"):
                return email_addr["name"]

        # 4. 이름이 없으면 이메일 주소의 로컬 부분 반환
        sender_address = self.extract_sender_address(mail)
        if sender_address and "@" in sender_address:
            return sender_address.split("@")[0]

        return ""

    def extract_subject(self, mail: Dict) -> str:
        """
        제목 추출

        Args:
            mail: 메일 딕셔너리

        Returns:
            메일 제목 또는 빈 문자열
        """
        return mail.get("subject", "")

    def extract_mail_id(self, mail: Dict) -> str:
        """
        메일 ID 추출

        Args:
            mail: 메일 딕셔너리

        Returns:
            메일 ID 또는 'unknown'
        """
        return mail.get("id", "unknown")

    def extract_sent_time(self, mail: Dict) -> datetime:
        """
        발송 시간 추출

        Args:
            mail: 메일 딕셔너리

        Returns:
            발송 시간 datetime 객체
        """
        # received_date_time 또는 receivedDateTime 필드 지원
        received_time_str = mail.get(
            "received_date_time", mail.get("receivedDateTime", "")
        )

        try:
            if isinstance(received_time_str, datetime):
                return received_time_str
            elif isinstance(received_time_str, str):
                if received_time_str.endswith("Z"):
                    received_time_str = received_time_str[:-1] + "+00:00"
                return datetime.fromisoformat(received_time_str)
            else:
                return datetime.now()
        except (ValueError, TypeError):
            self.logger.warning(f"발송 시간 파싱 실패: {received_time_str}")
            return datetime.now()

    def extract_body_preview(self, mail: Dict) -> str:
        """
        본문 미리보기 추출

        Args:
            mail: 메일 딕셔너리

        Returns:
            본문 미리보기 또는 빈 문자열
        """
        # body_preview 또는 bodyPreview 필드 지원
        return mail.get("body_preview", mail.get("bodyPreview", ""))

    def convert_datetime_to_string(self, data: any) -> any:
        """
        재귀적으로 datetime 객체를 문자열로 변환

        Args:
            data: 변환할 데이터

        Returns:
            datetime이 문자열로 변환된 데이터
        """
        if isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            return {
                key: self.convert_datetime_to_string(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self.convert_datetime_to_string(item) for item in data]
        else:
            return data
