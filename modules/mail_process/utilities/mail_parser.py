"""메일 파싱 유틸리티 - sender 정보 추출 개선"""

from datetime import datetime
from typing import Dict, Optional, Tuple

from infra.core.logger import get_logger


class MailParser:
    """메일 파싱 유틸리티 - 순수 함수 기반"""

    def __init__(self):
        self.logger = get_logger(__name__)

    def extract_sender_info(self, mail) -> Tuple[str, str]:
        """
        발신자 주소와 이름을 함께 추출 (개선된 버전)

        Args:
            mail: 메일 딕셔너리 또는 Pydantic 모델

        Returns:
            (발신자 이메일 주소, 발신자 이름)
        """
        sender_address = ""
        sender_name = ""

        # Pydantic 모델인지 딕셔너리인지 확인
        if hasattr(mail, "model_dump"):
            # Pydantic 모델인 경우 딕셔너리로 변환
            mail_dict = mail.model_dump()
        else:
            mail_dict = mail

        # 디버깅: 메일 구조 확인
        self.logger.debug(f"메일 구조 키: {list(mail_dict.keys())}")

        # 가능한 모든 발신자 필드 확인
        sender_fields = [
            ("from", "발신자(from)"),
            ("From", "발신자(From)"),  # 대문자
            ("sender", "발신자(sender)"),
            ("Sender", "발신자(Sender)"),  # 대문자
            ("from_address", "발신자(from_address)"),
            ("fromRecipients", "발신자(fromRecipients)"),
        ]

        for field_name, field_desc in sender_fields:
            field_value = mail_dict.get(field_name)
            if field_value:
                self.logger.debug(f"{field_desc} 필드 발견: {field_value}")

                # 문자열인 경우 직접 사용
                if isinstance(field_value, str):
                    if "@" in field_value:
                        sender_address = field_value
                        # 이름은 이메일의 로컬 부분 사용
                        sender_name = field_value.split("@")[0]
                        break

                # 딕셔너리인 경우
                elif isinstance(field_value, dict):
                    # emailAddress 필드 확인
                    email_addr = field_value.get("emailAddress", {})
                    if isinstance(email_addr, dict):
                        addr = email_addr.get("address", "")
                        name = email_addr.get("name", "")
                        if addr:
                            sender_address = addr
                            sender_name = name or addr.split("@")[0]
                            break

                    # 직접 address/name 필드 확인
                    addr = field_value.get("address", "")
                    name = field_value.get("name", "")
                    if addr:
                        sender_address = addr
                        sender_name = name or addr.split("@")[0]
                        break

        # 발신자 정보를 찾지 못한 경우 전체 메일 구조 로깅
        if not sender_address:
            self.logger.warning(
                f"발신자 정보를 찾을 수 없음 - 메일 ID: {mail_dict.get('id', 'unknown')}"
            )
            # 상세 디버깅 정보
            for key, value in mail_dict.items():
                if key.lower() in ["from", "sender", "from_address"]:
                    self.logger.debug(f"  {key}: {type(value)} = {str(value)[:100]}")

        return sender_address, sender_name

    def extract_sender_address(self, mail: Dict) -> str:
        """
        발신자 주소 추출 (순수 함수)

        Args:
            mail: 메일 딕셔너리

        Returns:
            발신자 이메일 주소 또는 빈 문자열
        """
        address, _ = self.extract_sender_info(mail)
        return address

    def extract_sender_name(self, mail: Dict) -> str:
        """
        발신자 이름 추출

        Args:
            mail: 메일 딕셔너리

        Returns:
            발신자 이름 또는 빈 문자열
        """
        _, name = self.extract_sender_info(mail)
        return name

    def extract_subject(self, mail: Dict) -> str:
        """
        제목 추출

        Args:
            mail: 메일 딕셔너리

        Returns:
            메일 제목 또는 빈 문자열
        """
        # 대소문자 구분 없이 subject 찾기
        subject = mail.get("subject", mail.get("Subject", ""))
        return subject

    def extract_mail_id(self, mail: Dict) -> str:
        """
        메일 ID 추출

        Args:
            mail: 메일 딕셔너리

        Returns:
            메일 ID 또는 'unknown'
        """
        return mail.get("id", mail.get("Id", mail.get("messageId", "unknown")))

    def extract_sent_time(self, mail: Dict) -> datetime:
        """
        발송 시간 추출

        Args:
            mail: 메일 딕셔너리

        Returns:
            발송 시간 datetime 객체
        """
        # 다양한 시간 필드 확인
        time_fields = [
            "received_date_time",
            "receivedDateTime",
            "ReceivedDateTime",
            "sentDateTime",
            "SentDateTime",
            "dateTimeReceived",
            "dateTimeSent",
        ]

        received_time_str = None
        for field in time_fields:
            if field in mail:
                received_time_str = mail[field]
                break

        try:
            if isinstance(received_time_str, datetime):
                return received_time_str
            elif isinstance(received_time_str, str) and received_time_str:
                # ISO 형식 파싱
                if received_time_str.endswith("Z"):
                    received_time_str = received_time_str[:-1] + "+00:00"
                return datetime.fromisoformat(received_time_str)
            else:
                self.logger.warning(
                    f"발송 시간 없음 - 메일 ID: {self.extract_mail_id(mail)}"
                )
                return datetime.now()
        except (ValueError, TypeError) as e:
            self.logger.warning(
                f"발송 시간 파싱 실패: {received_time_str}, 오류: {str(e)}"
            )
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
        return mail.get(
            "body_preview", mail.get("bodyPreview", mail.get("BodyPreview", ""))
        )

    def extract_body_content(self, mail: Dict) -> str:
        """
        본문 내용 추출

        Args:
            mail: 메일 딕셔너리

        Returns:
            본문 내용 또는 빈 문자열
        """
        # body 필드 확인
        body = mail.get("body", mail.get("Body", {}))
        if isinstance(body, dict):
            return body.get("content", body.get("Content", ""))
        elif isinstance(body, str):
            return body

        # body가 없으면 bodyPreview 사용
        return self.extract_body_preview(mail)

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

    def debug_mail_structure(self, mail: Dict) -> None:
        """
        메일 구조 디버깅 출력

        Args:
            mail: 메일 딕셔너리
        """
        self.logger.info("=== 메일 구조 디버깅 ===")
        self.logger.info(f"메일 ID: {self.extract_mail_id(mail)}")
        self.logger.info(f"최상위 키: {list(mail.keys())}")

        # 주요 필드 상세 정보
        important_fields = [
            "from",
            "From",
            "sender",
            "Sender",
            "from_address",
            "subject",
            "body",
        ]
        for field in important_fields:
            if field in mail:
                value = mail[field]
                self.logger.info(f"{field}: {type(value)} = {str(value)[:200]}")

        self.logger.info("===================")
