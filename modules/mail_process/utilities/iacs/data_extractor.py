"""
IACS 데이터 추출 모듈
modules/mail_process/utilities/iacs/data_extractor.py
"""

import re
from datetime import datetime
from typing import Dict, Tuple, Optional, List, Any

from infra.core.logger import get_logger
from .constants import DOMAIN_ORG_MAP, URGENCY_KEYWORDS, ORGANIZATION_CODES


class DataExtractor:
    """메일에서 데이터 추출"""

    # 하드코딩된 Chair 이메일 목록
    DEFAULT_CHAIR_EMAILS = [
        "sdtpchair@eagle.org",  # SDTP Chair (ABS 도메인이지만 Chair)
    ]

    # 하드코딩된 Member 이메일 목록 (조직별)
    DEFAULT_MEMBER_EMAILS = {}

    def __init__(self):
        self.logger = get_logger(__name__)

        # 텍스트 정제를 위한 패턴들
        self.email_pattern = re.compile(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        )
        self.url_pattern = re.compile(r"https?://[^\s]+|www\.[^\s]+")
        self.html_pattern = re.compile(r"<[^>]+>")
        self.separator_pattern = re.compile(r"[-=_*]{5,}")

        # Chair와 Member 이메일 주소 리스트 (기본값으로 초기화)
        self.chair_emails: List[str] = [
            email.lower() for email in self.DEFAULT_CHAIR_EMAILS
        ]
        self.member_emails: Dict[str, List[str]] = {
            org: [email.lower() for email in emails]
            for org, emails in self.DEFAULT_MEMBER_EMAILS.items()
        }

        self.logger.info(f"기본 Chair 이메일 {len(self.chair_emails)}개 로드됨")
        self.logger.info(f"기본 Member 조직 {len(self.member_emails)}개 로드됨")

    def set_chair_emails(self, emails: List[str]):
        """Chair 이메일 주소 설정 (기본값을 덮어씀)"""
        self.chair_emails = [email.lower() for email in emails]
        self.logger.info(f"Chair 이메일 {len(self.chair_emails)}개 설정됨")

    def add_chair_emails(self, emails: List[str]):
        """Chair 이메일 주소 추가 (기본값에 추가)"""
        new_emails = [
            email.lower() for email in emails if email.lower() not in self.chair_emails
        ]
        self.chair_emails.extend(new_emails)
        self.logger.info(
            f"Chair 이메일 {len(new_emails)}개 추가됨 (총 {len(self.chair_emails)}개)"
        )

    def set_member_emails(self, organization: str, emails: List[str]):
        """특정 조직의 멤버 이메일 주소 설정 (기본값을 덮어씀)"""
        self.member_emails[organization.upper()] = [email.lower() for email in emails]
        self.logger.info(f"{organization} 멤버 이메일 {len(emails)}개 설정됨")

    def add_member_emails(self, organization: str, emails: List[str]):
        """특정 조직의 멤버 이메일 주소 추가 (기본값에 추가)"""
        org = organization.upper()
        if org not in self.member_emails:
            self.member_emails[org] = []

        existing = self.member_emails[org]
        new_emails = [
            email.lower() for email in emails if email.lower() not in existing
        ]
        self.member_emails[org].extend(new_emails)
        self.logger.info(f"{org} 멤버 이메일 {len(new_emails)}개 추가됨")

    def extract_sender_info(
        self, mail: Dict
    ) -> Tuple[str, str, str, Optional[str]]:
        """
        발신자 정보 추출 및 sender_type, sender_organization 결정

        Returns:
            (sender_address, sender_name, sender_type, sender_organization)
        """
        sender_address, sender_name = self._extract_basic_sender_info(mail)
        sender_type = "OTHER"  # 기본값 설정
        sender_organization = None

        if sender_address:
            sender_type = self._determine_sender_type(sender_address, mail)
            # 이메일 도메인에서 조직 코드 추출
            sender_organization = self.extract_organization_from_email(sender_address)

        return sender_address, sender_name, sender_type, sender_organization

    def _extract_basic_sender_info(self, mail: Dict) -> Tuple[str, str]:
        """기본 발신자 정보 추출"""
        sender_address = ""
        sender_name = ""

        # 가능한 모든 발신자 필드 확인
        sender_fields = [
            ("from", "발신자(from)"),
            ("From", "발신자(From)"),
            ("sender", "발신자(sender)"),
            ("Sender", "발신자(Sender)"),
            ("from_address", "발신자(from_address)"),
            ("fromRecipients", "발신자(fromRecipients)"),
        ]

        for field_name, field_desc in sender_fields:
            field_value = mail.get(field_name)
            if field_value:
                # 문자열인 경우
                if isinstance(field_value, str):
                    if "@" in field_value:
                        sender_address = field_value
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

        return sender_address, sender_name

    def _determine_sender_type(self, sender_address: str, mail: Dict) -> str:
        """발신자 타입 결정 (CHAIR/MEMBER/OTHER) - 항상 문자열 반환"""
        sender_address_lower = sender_address.lower()

        # Chair 확인
        if sender_address_lower in self.chair_emails:
            self.logger.debug(f"Chair 이메일 감지: {sender_address}")
            return "CHAIR"

        # Member 조직 확인
        for org, emails in self.member_emails.items():
            if sender_address_lower in emails:
                self.logger.debug(f"{org} 멤버 이메일 감지: {sender_address}")
                return "MEMBER"

        # 도메인 기반 추정
        org_code = self.extract_organization_from_email(sender_address)
        if org_code:
            # IL은 보통 Chair
            if org_code == "IL":
                return "CHAIR"
            # 다른 IACS 멤버는 MEMBER
            else:
                return "MEMBER"

        # 위 모든 조건에 해당하지 않으면 OTHER 반환
        self.logger.debug(f"알 수 없는 발신자 타입 - OTHER로 분류: {sender_address}")
        return "OTHER"

    def extract_organization_from_email(self, email_address: str) -> Optional[str]:
        """이메일 도메인에서 조직 코드 추출"""
        if not email_address or "@" not in email_address:
            return None

        # 이메일에서 도메인 추출
        domain = email_address.split("@")[1].lower()

        # 정확한 도메인 매칭 시도
        for domain_pattern, org in DOMAIN_ORG_MAP.items():
            if domain == domain_pattern:
                self.logger.debug(f"도메인 {domain}에서 조직 {org} 추출 (정확한 매칭)")
                return org

        # 부분 도메인 매칭 시도 (서브도메인 고려)
        for domain_pattern, org in DOMAIN_ORG_MAP.items():
            if domain.endswith(f".{domain_pattern}") or domain == domain_pattern:
                self.logger.debug(f"도메인 {domain}에서 조직 {org} 추출 (부분 매칭)")
                return org

        # 특수 케이스: 도메인에서 조직 코드 직접 추출 시도
        for org in ORGANIZATION_CODES:
            if org.lower() in domain and len(org) >= 2:
                self.logger.debug(f"도메인 {domain}에서 조직 {org} 추출 (패턴 매칭)")
                return org.upper()

        self.logger.debug(f"도메인 {domain}에서 조직 코드를 찾을 수 없음")
        return None

    def extract_sent_time(self, mail: Dict) -> Optional[datetime]:
        """발송 시간 추출"""
        # 다양한 시간 필드 확인
        time_fields = [
            "received_date_time",
            "receivedDateTime",
            "ReceivedDateTime",
            "sentDateTime",
            "SentDateTime",
            "dateTimeReceived",
            "dateTimeSent",
            "sent_time",
        ]

        for field in time_fields:
            if field in mail:
                received_time = mail[field]
                try:
                    if isinstance(received_time, datetime):
                        return received_time
                    elif isinstance(received_time, str) and received_time:
                        # ISO 형식 파싱
                        if received_time.endswith("Z"):
                            received_time = received_time[:-1] + "+00:00"
                        return datetime.fromisoformat(received_time)
                except (ValueError, TypeError) as e:
                    self.logger.warning(
                        f"시간 파싱 실패: {received_time}, 오류: {str(e)}"
                    )
                    continue

        return None

    def extract_clean_content(self, mail: Dict) -> str:
        """메일에서 정제된 내용 추출"""
        # 제목 추출
        subject = mail.get("subject", mail.get("Subject", ""))

        # 본문 추출
        body_content = ""
        body = mail.get("body", mail.get("Body", {}))
        if isinstance(body, dict):
            body_content = body.get("content", body.get("Content", ""))
        elif isinstance(body, str):
            body_content = body

        # 본문이 없으면 미리보기 사용
        if not body_content:
            body_content = mail.get("bodyPreview", mail.get("body_preview", ""))

        # 제목과 본문 결합 후 정제
        full_content = f"{subject}\n\n{body_content}"
        return self.clean_content(full_content)

    def clean_content(self, text: str) -> str:
        """텍스트 정제"""
        if not text:
            return ""

        # 1. HTML 태그 제거
        clean = self.html_pattern.sub("", text)

        # 2. 이메일 주소를 공백으로 변환
        clean = self.email_pattern.sub(" ", clean)

        # 3. URL 제거
        clean = self.url_pattern.sub(" ", clean)

        # 4. 구분선 제거
        clean = self.separator_pattern.sub(" ", clean)

        # 5. 줄바꿈 통일
        clean = clean.replace("\r\n", "\n").replace("\r", "\n")

        # 6. 메일 서명 제거 (일반적인 서명 패턴)
        signature_patterns = [
            r"--\s*\n.*$",  # -- 로 시작하는 서명
            r"Best regards[\s\S]*$",  # Best regards로 시작
            r"Sincerely[\s\S]*$",  # Sincerely로 시작
            r"감사합니다[\s\S]*$",  # 한국어 서명
        ]

        for pattern in signature_patterns:
            clean = re.sub(pattern, "", clean, flags=re.MULTILINE | re.IGNORECASE)

        # 7. 연속된 줄바꿈을 하나의 공백으로
        clean = re.sub(r"\n+", " ", clean)

        # 8. 탭을 공백으로
        clean = clean.replace("\t", " ")

        # 9. 특수문자 정리 (더 많은 허용 문자)
        clean = re.sub(r"[^\w\s가-힣.,!?():;@#$%&*+=\-/]", " ", clean)

        # 10. 과도한 공백 정리
        clean = re.sub(r"\s+", " ", clean)

        return clean.strip()

    def analyze_reply_chain(self, subject: str) -> Dict[str, Any]:
        """회신 체인 분석"""
        result: Dict[str, Any] = {}

        # 회신 표시
        reply_prefixes = ["RE:", "Re:", "re:", "답장:", "Reply:", "回复:"]
        for prefix in reply_prefixes:
            if subject.upper().startswith(prefix.upper()):
                result["is_reply"] = True
                # 회신 깊이 계산 (연속된 RE: 개수)
                depth = 0
                temp_subject = subject
                while any(
                    temp_subject.upper().startswith(p.upper()) for p in reply_prefixes
                ):
                    depth += 1
                    for p in reply_prefixes:
                        if temp_subject.upper().startswith(p.upper()):
                            temp_subject = temp_subject[len(p) :].strip()
                            break
                result["reply_depth"] = depth
                break

        # 전달 표시
        forward_prefixes = [
            "FW:",
            "Fw:",
            "fw:",
            "FWD:",
            "Fwd:",
            "fwd:",
            "전달:",
            "Forward:",
            "转发:",
        ]
        for prefix in forward_prefixes:
            if subject.upper().startswith(prefix.upper()):
                result["is_forward"] = True
                break

        return result

    def extract_urgency(self, subject: str, text: str) -> str:
        """긴급도 추출"""
        combined = f"{subject} {text}".lower()

        # HIGH 우선 체크
        for keyword in URGENCY_KEYWORDS.get("HIGH", []):
            if keyword in combined:
                return "HIGH"

        # MEDIUM 체크
        for keyword in URGENCY_KEYWORDS.get("MEDIUM", []):
            if keyword in combined:
                return "MEDIUM"

        return "NORMAL"

    def extract_agenda_patterns(self, text: str) -> List[str]:
        """본문에서 추가 아젠다 참조 추출"""
        patterns: List[str] = []
        seen: set[str] = set()  # 중복 제거용

        # 대소문자 구분 없이 패턴 검색
        agenda_patterns = [
            # PL/PS 패턴 (모든 변형)
            r"\b((?:PL|PS)\d{2}\d{3,4}[a-zA-Z*]?(?:_?[A-Z]{2,4}[a-zA-Z*]?)?)\b",
            # JWG 패턴
            r"\b(JWG-(?:SDT|CS)\d{2}\d{3}[a-zA-Z*]?(?:_?[A-Z]{2,4}[a-zA-Z*]?)?)\b",
        ]

        for pattern in agenda_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                normalized = match.upper()
                if normalized not in seen:
                    seen.add(normalized)
                    patterns.append(normalized)

        # 최대 20개까지만 반환
        return patterns[:20]