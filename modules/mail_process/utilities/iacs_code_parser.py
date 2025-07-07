"""개선된 IACS 코드 파서 - 새로운 파싱 규칙 적용 및 발신자 정보 추출"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from infra.core.logger import get_logger


@dataclass
class ParsedCode:
    """파싱된 코드 정보를 담는 클래스"""

    full_code: str
    document_type: str  # AGENDA(의제) or RESPONSE(회신) or SPECIAL(특수)
    panel: str  # PL, PS, JWG-SDT, JWG-CS 등
    year: Optional[str] = None
    number: Optional[str] = None
    agenda_version: Optional[str] = None  # 의제 버전 (a, b, c)
    organization: Optional[str] = None  # IR, KR, BV 등 (회신일 경우)
    response_version: Optional[str] = None  # 회신 버전 (a, b, c)
    description: Optional[str] = None  # 코드 뒤의 설명 텍스트
    is_response: bool = False  # 응답 여부
    is_special: bool = False  # 특수 케이스 여부 (Multilateral 등)
    parsing_method: str = ""  # 파싱에 사용된 방법 (디버깅용)


class IACSCodeParser:
    """IACS 문서 코드 파서 - 새로운 파싱 규칙 적용"""

    # 기관 코드 목록 (실제 데이터에서 발견된 모든 코드 포함)
    ORGANIZATION_CODES = {
        "AB",
        "ABS",
        "BV",
        "CC",
        "CCS",
        "CR",
        "CRS",
        "DNV",
        "NV",
        "IR",
        "IRS",
        "KR",
        "LR",
        "NK",
        "PR",
        "PRS",
        "PL",
        "RI",
        "RINA",
        "IL",
        "TL",
    }

    # 패널 타입
    PANEL_TYPES = {"PL", "PS", "JWG-SDT", "JWG-CS"}

    # 최대 라인 길이 제한
    MAX_LINE_LENGTH = 500

    def __init__(self):
        self.logger = get_logger(__name__)

        # 특수 접두사 패턴
        self.special_prefixes = [
            "Multilateral",
            "Bilateral",
            "RE:",
            "Re:",
            "re:",
            "답장:",
            "Reply:",
            "回复:",
            "FW:",
            "Fw:",
            "fw:",
            "FWD:",
            "Fwd:",
            "fwd:",
            "전달:",
            "Forward:",
            "转发:",
            "Automatic reply:",
            "IACS SDTP",
        ]

        # 긴급도 키워드
        self.urgency_keywords = {
            "high": [
                "urgent",
                "긴급",
                "asap",
                "immediately",
                "critical",
                "急",
                "high priority",
            ],
            "medium": ["important", "중요", "priority", "attention", "please review"],
        }

        # 특수 케이스
        self.special_cases = ["Multilateral", "MULTILATERAL", "multilateral"]

        # Chair와 Member 이메일 주소 리스트
        self.chair_emails = []  # 초기화 시 설정 가능
        self.member_emails = {}  # {organization: [email_list]}

        # 텍스트 정제를 위한 패턴들
        self.email_pattern = re.compile(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        )
        self.url_pattern = re.compile(r"https?://[^\s]+|www\.[^\s]+")
        self.html_pattern = re.compile(r"<[^>]+>")

        # 구분선 패턴
        self.separator_pattern = re.compile(r"[-=_*]{5,}")

    def set_chair_emails(self, emails: List[str]):
        """Chair 이메일 주소 설정"""
        self.chair_emails = [email.lower() for email in emails]
        self.logger.info(f"Chair 이메일 {len(self.chair_emails)}개 설정됨")

    def set_member_emails(self, organization: str, emails: List[str]):
        """특정 조직의 멤버 이메일 주소 설정"""
        self.member_emails[organization.upper()] = [email.lower() for email in emails]
        self.logger.info(f"{organization} 멤버 이메일 {len(emails)}개 설정됨")

    def parse_line(self, line: str) -> Optional[ParsedCode]:
        """한 줄을 파싱하여 코드 정보 추출 (새로운 규칙 적용)"""
        try:
            line = line.strip()
            if not line:
                return None

            # 길이 제한 체크
            if len(line) > self.MAX_LINE_LENGTH:
                self.logger.warning(f"너무 긴 라인 무시: {line[:50]}...")
                return None

            # 특수 케이스 먼저 체크
            for special in self.special_cases:
                if special.lower() in line.lower():
                    return ParsedCode(
                        full_code="Multilateral",
                        document_type="SPECIAL",
                        panel="MULTILATERAL",
                        is_special=True,
                        parsing_method="special_case",
                    )

            # 특수 접두사 제거
            cleaned_line = self._remove_prefixes(line)

            # 1단계: 기본 패턴 검색 (대소문자 구분)
            result = self._parse_basic_patterns(cleaned_line, case_sensitive=True)
            if result:
                return result

            # 2단계: JWG 패턴 검색 (대소문자 구분)
            result = self._parse_jwg_patterns(cleaned_line, case_sensitive=True)
            if result:
                return result

            # 3단계: 대소문자 구분 없이 재검색
            result = self._parse_basic_patterns(cleaned_line, case_sensitive=False)
            if result:
                return result

            # 4단계: JWG 패턴 대소문자 구분 없이 재검색
            result = self._parse_jwg_patterns(cleaned_line, case_sensitive=False)
            if result:
                return result

            # 파싱 실패 로깅 (IACS 관련 라인만)
            if any(cleaned_line.upper().startswith(p) for p in ["PL", "PS", "JWG"]):
                self.logger.debug(
                    f"IACS 코드 파싱 실패 (예외 메일): {cleaned_line[:100]}"
                )

            return None

        except Exception as e:
            self.logger.error(f"파싱 중 예외 발생: {str(e)}, 라인: {line[:100]}")
            return None

    def extract_sender_info(self, mail: Dict) -> Tuple[str, str, Optional[str]]:
        """
        발신자 정보 추출 및 sender_type 결정

        Returns:
            (sender_address, sender_name, sender_type)
        """
        sender_address, sender_name = self._extract_basic_sender_info(mail)
        sender_type = None

        if sender_address:
            sender_type = self._determine_sender_type(sender_address, mail)

        return sender_address, sender_name, sender_type

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

    def _determine_sender_type(self, sender_address: str, mail: Dict) -> Optional[str]:
        """발신자 타입 결정"""
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

        # 도메인 기반 추정 (설정된 이메일이 없는 경우)
        if "@" in sender_address:
            domain = sender_address.split("@")[1].lower()
            # IL 도메인은 보통 Chair
            if "il." in domain or domain.endswith(".il"):
                return "CHAIR"
            # 다른 IACS 멤버 도메인 패턴 확인
            elif any(org.lower() in domain for org in self.ORGANIZATION_CODES):
                return "MEMBER"

        # 제목에서 추가 단서 확인
        subject = mail.get("subject", "")
        if subject:
            parsed_code = self.parse_line(subject)
            if parsed_code and parsed_code.is_response:
                return "MEMBER"

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

    def clean_content(self, text: str) -> str:
        """텍스트 정제 (향상된 버전)"""
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

    def _parse_basic_patterns(
        self, line: str, case_sensitive: bool = True
    ) -> Optional[ParsedCode]:
        """기본 패턴 파싱 (PL/PS)"""
        flags = 0 if case_sensitive else re.IGNORECASE

        patterns = [
            # 패턴1: PL25016aIRa (붙어있는 형식)
            (
                r"^([A-Z]{2})(\d{2})(\d{3,4})([a-z*]?)([A-Z]{2,4})([a-z*]?)(?:\s|:|$)",
                "pattern1_attached",
            ),
            # 패턴2: PL25015_KRa (언더스코어 형식)
            (
                r"^([A-Z]{2})(\d{2})(\d{3,4})_([A-Z]{2,4})([a-z*]?)(?:\s|:|$)",
                "pattern2_underscore",
            ),
            # 패턴3: PL25016a_IRa (소문자+언더스코어)
            (
                r"^([A-Z]{2})(\d{2})(\d{3,4})([a-z*])_([A-Z]{2,4})([a-z*]?)(?:\s|:|$)",
                "pattern3_version_underscore",
            ),
            # 패턴4: PL25016_aIRa (언더스코어+소문자)
            (
                r"^([A-Z]{2})(\d{2})(\d{3,4})_([a-z*])([A-Z]{2,4})([a-z*]?)(?:\s|:|$)",
                "pattern4_underscore_version",
            ),
            # 기본 의제 패턴: PL25016a
            (r"^([A-Z]{2})(\d{2})(\d{3,4})([a-z*]?)(?:\s|:|$)", "basic_agenda"),
        ]

        for pattern, pattern_name in patterns:
            if not case_sensitive:
                pattern = pattern.replace("[A-Z]", "[A-Za-z]").replace(
                    "[a-z*]", "[A-Za-z*]"
                )

            match = re.match(pattern, line, flags)
            if match:
                return self._process_basic_match(
                    match, pattern_name, line, case_sensitive
                )

        return None

    def _parse_jwg_patterns(
        self, line: str, case_sensitive: bool = True
    ) -> Optional[ParsedCode]:
        """JWG 패턴 파싱"""
        flags = 0 if case_sensitive else re.IGNORECASE

        patterns = [
            # JWG-CS25001b_PRa (agenda_version + underscore + response)
            (
                r"^(JWG)-(SDT|CS)(\d{2})(\d{3})([a-z*])_([A-Z]{2,4})([a-z*]?)(?:\s|:|$)",
                "jwg_version_underscore",
            ),
            # JWG-SDT25001_BVa
            (
                r"^(JWG)-(SDT|CS)(\d{2})(\d{3})_([A-Z]{2,4})([a-z*]?)(?:\s|:|$)",
                "jwg_underscore",
            ),
            # JWG-SDT25001BVa (붙어있는 형식)
            (
                r"^(JWG)-(SDT|CS)(\d{2})(\d{3})([a-z*]?)([A-Z]{2,4})([a-z*]?)(?:\s|:|$)",
                "jwg_attached",
            ),
            # JWG-SDT25001a (기본 의제)
            (r"^(JWG)-(SDT|CS)(\d{2})(\d{3})([a-z*]?)(?:\s|:|$)", "jwg_agenda"),
        ]

        for pattern, pattern_name in patterns:
            if not case_sensitive:
                pattern = pattern.replace("[A-Z]", "[A-Za-z]").replace(
                    "[a-z*]", "[A-Za-z*]"
                )

            match = re.match(pattern, line, flags)
            if match:
                return self._process_jwg_match(
                    match, pattern_name, line, case_sensitive
                )

        return None

    def _process_basic_match(
        self, match, pattern_name: str, full_line: str, case_sensitive: bool
    ) -> ParsedCode:
        """기본 패턴 매치 처리"""
        groups = match.groups()
        parsing_method = f"{pattern_name}{'_case_sensitive' if case_sensitive else '_case_insensitive'}"

        # 설명 부분 추출
        description = self._extract_description(full_line)

        if pattern_name == "pattern1_attached":
            # PL25016aIRa
            panel, year, number, agenda_ver, org, response_ver = groups

            # 조직 코드 검증
            if org.upper() in self.ORGANIZATION_CODES:
                return self._create_response_code(
                    panel,
                    year,
                    number,
                    agenda_ver,
                    org,
                    response_ver,
                    description,
                    parsing_method,
                    attached=True,
                )
            else:
                # 조직 코드가 아니면 기본 의제로 처리
                return self._create_agenda_code(
                    panel, year, number, agenda_ver, description, parsing_method
                )

        elif pattern_name == "pattern2_underscore":
            # PL25015_KRa
            panel, year, number, org, response_ver = groups
            return self._create_response_code(
                panel,
                year,
                number,
                None,
                org,
                response_ver,
                description,
                parsing_method,
                underscore=True,
            )

        elif pattern_name == "pattern3_version_underscore":
            # PL25016a_IRa
            panel, year, number, agenda_ver, org, response_ver = groups
            return self._create_response_code(
                panel,
                year,
                number,
                agenda_ver,
                org,
                response_ver,
                description,
                parsing_method,
                attached=True,
            )

        elif pattern_name == "pattern4_underscore_version":
            # PL25016_aIRa
            panel, year, number, agenda_ver, org, response_ver = groups
            return self._create_response_code(
                panel,
                year,
                number,
                agenda_ver,
                org,
                response_ver,
                description,
                parsing_method,
                attached=True,
            )

        elif pattern_name == "basic_agenda":
            # PL25016a
            panel, year, number, version = groups
            return self._create_agenda_code(
                panel, year, number, version, description, parsing_method
            )

        return None

    def _process_jwg_match(
        self, match, pattern_name: str, full_line: str, case_sensitive: bool
    ) -> ParsedCode:
        """JWG 패턴 매치 처리"""
        groups = match.groups()
        parsing_method = f"{pattern_name}{'_case_sensitive' if case_sensitive else '_case_insensitive'}"

        # 설명 부분 추출
        description = self._extract_description(full_line)

        if pattern_name == "jwg_version_underscore":
            # JWG-CS25001b_PRa
            prefix, subtype, year, number, agenda_ver, org, response_ver = groups
            panel = f"{prefix.upper()}-{subtype.upper()}"
            return self._create_response_code(
                panel,
                year,
                number,
                agenda_ver,
                org,
                response_ver,
                description,
                parsing_method,
                underscore=True,
            )

        elif pattern_name == "jwg_underscore":
            # JWG-SDT25001_BVa
            prefix, subtype, year, number, org, response_ver = groups
            panel = f"{prefix.upper()}-{subtype.upper()}"
            return self._create_response_code(
                panel,
                year,
                number,
                None,
                org,
                response_ver,
                description,
                parsing_method,
                underscore=True,
            )

        elif pattern_name == "jwg_attached":
            # JWG-SDT25001BVa
            prefix, subtype, year, number, agenda_ver, org, response_ver = groups
            panel = f"{prefix.upper()}-{subtype.upper()}"

            # 조직 코드 검증
            if org.upper() in self.ORGANIZATION_CODES:
                return self._create_response_code(
                    panel,
                    year,
                    number,
                    agenda_ver,
                    org,
                    response_ver,
                    description,
                    parsing_method,
                    attached=True,
                )
            else:
                # 조직 코드가 아니면 기본 의제로 처리
                return self._create_agenda_code(
                    panel, year, number, agenda_ver, description, parsing_method
                )

        elif pattern_name == "jwg_agenda":
            # JWG-SDT25001a
            prefix, subtype, year, number, version = groups
            panel = f"{prefix.upper()}-{subtype.upper()}"
            return self._create_agenda_code(
                panel, year, number, version, description, parsing_method
            )

        return None

    def _create_response_code(
        self,
        panel: str,
        year: str,
        number: str,
        agenda_ver: Optional[str],
        org: str,
        response_ver: Optional[str],
        description: str,
        parsing_method: str,
        attached: bool = False,
        underscore: bool = False,
    ) -> ParsedCode:
        """응답 코드 생성"""
        # full_code 구성
        base = f"{panel.upper()}{year}{number}"
        if agenda_ver and agenda_ver != "*":
            base += agenda_ver.lower()

        # agenda_version이 있으면 무조건 붙어있는 형식으로 처리
        if agenda_ver and agenda_ver != "*":
            full_code = f"{base}{org.upper()}{response_ver.lower() if response_ver and response_ver != '*' else ''}"
        elif attached:
            full_code = f"{base}{org.upper()}{response_ver.lower() if response_ver and response_ver != '*' else ''}"
        else:
            full_code = f"{base}_{org.upper()}{response_ver.lower() if response_ver and response_ver != '*' else ''}"

        return ParsedCode(
            full_code=full_code,
            document_type="RESPONSE",
            panel=panel.upper(),
            year=year,
            number=number,
            agenda_version=(
                agenda_ver.lower() if agenda_ver and agenda_ver != "*" else None
            ),
            organization=org.upper(),
            response_version=(
                response_ver.lower() if response_ver and response_ver != "*" else None
            ),
            description=description,
            is_response=True,
            parsing_method=parsing_method,
        )

    def _create_agenda_code(
        self,
        panel: str,
        year: str,
        number: str,
        version: Optional[str],
        description: str,
        parsing_method: str,
    ) -> ParsedCode:
        """의제 코드 생성"""
        full_code = f"{panel.upper()}{year}{number}"
        if version and version != "*":
            full_code += version.lower()

        return ParsedCode(
            full_code=full_code,
            document_type="AGENDA",
            panel=panel.upper(),
            year=year,
            number=number,
            agenda_version=version.lower() if version and version != "*" else None,
            description=description,
            is_response=False,
            parsing_method=parsing_method,
        )

    def _extract_description(self, line: str) -> Optional[str]:
        """설명 부분 추출"""
        # 콜론으로 분리
        if ":" in line:
            parts = line.split(":", 1)
            if len(parts) > 1:
                desc = parts[1].strip()
                # 설명이 너무 길면 자르기
                if len(desc) > 200:
                    desc = desc[:197] + "..."
                return desc

        # 공백으로 분리 (JWG가 아닌 경우만)
        if " " in line and not line.upper().startswith("JWG"):
            parts = line.split(" ", 1)
            if len(parts) > 1:
                desc = parts[1].strip()
                if len(desc) > 200:
                    desc = desc[:197] + "..."
                return desc

        return None

    def _remove_prefixes(self, line: str) -> str:
        """특수 접두사 제거"""
        cleaned_line = line
        changed = True
        max_iterations = 5  # 무한 루프 방지
        iterations = 0

        while changed and iterations < max_iterations:
            changed = False
            iterations += 1
            for prefix in self.special_prefixes:
                if cleaned_line.upper().startswith(prefix.upper()):
                    cleaned_line = cleaned_line[len(prefix) :].strip()
                    changed = True
                    break

        return cleaned_line

    def extract_base_agenda_no(self, parsed_code: ParsedCode) -> Optional[str]:
        """기본 아젠다 번호 추출"""
        if parsed_code.panel and parsed_code.year and parsed_code.number:
            base = f"{parsed_code.panel}{parsed_code.year}{parsed_code.number}"
            if parsed_code.agenda_version:
                base += parsed_code.agenda_version
            return base
        return None

    def extract_agenda_patterns(self, text: str) -> List[str]:
        """본문에서 추가 아젠다 참조 추출"""
        patterns = []
        seen = set()  # 중복 제거용

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

    def analyze_reply_chain(self, subject: str) -> Dict[str, Any]:
        """회신 체인 분석"""
        result = {}

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
        for keyword in self.urgency_keywords.get("high", []):
            if keyword in combined:
                return "HIGH"

        # MEDIUM 체크
        for keyword in self.urgency_keywords.get("medium", []):
            if keyword in combined:
                return "MEDIUM"

        return "NORMAL"

    def extract_all_patterns(
        self, subject: str, body: str, mail: Dict = None
    ) -> Dict[str, Any]:
        """제목과 본문에서 모든 패턴 추출 (메일 정보 포함)"""
        result = {}

        # 1. 제목에서 IACS 코드 파싱
        parsed_code = self.parse_line(subject)
        if parsed_code:
            result["iacs_code"] = parsed_code
            result["extracted_info"] = self._convert_parsed_code_to_dict(parsed_code)
            self.logger.debug(
                f"파싱 성공: {parsed_code.full_code} "
                f"(방법: {parsed_code.parsing_method})"
            )
        else:
            # 본문 첫 줄에서도 시도
            body_lines = body.split("\n")
            for line in body_lines[:5]:  # 처음 5줄만 확인
                line = line.strip()
                if line:
                    parsed_code = self.parse_line(line)
                    if parsed_code:
                        result["iacs_code"] = parsed_code
                        result["extracted_info"] = self._convert_parsed_code_to_dict(
                            parsed_code
                        )
                        self.logger.debug(
                            f"본문에서 파싱 성공: {parsed_code.full_code}"
                        )
                        break

        # 2. 회신 체인 분석
        reply_info = self.analyze_reply_chain(subject)
        if reply_info:
            result.update(reply_info)

        # 3. 긴급도 추출
        result["urgency"] = self.extract_urgency(subject, body)

        # 4. 본문에서 추가 아젠다 참조 추출
        additional_refs = self.extract_agenda_patterns(body)
        if additional_refs:
            result["additional_agenda_references"] = additional_refs

        # 5. 메일 정보가 제공된 경우 추가 정보 추출
        if mail:
            # 발신자 정보 추출
            sender_address, sender_name, sender_type = self.extract_sender_info(mail)
            if sender_address:
                result["sender_address"] = sender_address
                result["sender_name"] = sender_name
                if sender_type:
                    result["sender_type"] = sender_type

            # 발송 시간 추출
            sent_time = self.extract_sent_time(mail)
            if sent_time:
                result["sent_time"] = sent_time

            # 정제된 내용 추출
            clean_content = self.extract_clean_content(mail)
            if clean_content:
                result["clean_content"] = clean_content

        return result

    def _convert_parsed_code_to_dict(self, parsed_code: ParsedCode) -> Dict:
        """ParsedCode 객체를 딕셔너리로 변환"""
        return {
            "full_code": parsed_code.full_code,
            "document_type": parsed_code.document_type,
            "panel": parsed_code.panel,
            "year": parsed_code.year,
            "number": parsed_code.number,
            "agenda_version": parsed_code.agenda_version,
            "organization": parsed_code.organization,
            "response_version": parsed_code.response_version,
            "description": parsed_code.description,
            "is_response": parsed_code.is_response,
            "is_special": parsed_code.is_special,
            "is_agenda": not parsed_code.is_response and not parsed_code.is_special,
            "base_agenda_no": self.extract_base_agenda_no(parsed_code),
            "parsing_method": parsed_code.parsing_method,
        }

    def parse_document(self, text: str) -> List[ParsedCode]:
        """전체 문서를 파싱하여 모든 코드 정보 추출"""
        results = []
        lines = text.strip().split("\n")

        for line in lines[:100]:  # 최대 100줄까지만 파싱
            parsed = self.parse_line(line)
            if parsed:
                results.append(parsed)

        return results

    def get_statistics(self, parsed_codes: List[ParsedCode]) -> Dict[str, Any]:
        """파싱된 코드들의 통계 정보 생성"""
        from collections import defaultdict

        stats = {
            "total": len(parsed_codes),
            "by_type": defaultdict(int),
            "by_panel": defaultdict(int),
            "by_year": defaultdict(int),
            "by_organization": defaultdict(int),
            "by_parsing_method": defaultdict(int),
            "special_cases": 0,
            "case_insensitive_parsed": 0,
            "agendas": defaultdict(int),
            "response_rate": 0.0,
        }

        for code in parsed_codes:
            # 문서 타입별 집계
            stats["by_type"][code.document_type] += 1

            # 패널별 집계
            stats["by_panel"][code.panel] += 1

            # 년도별 집계
            if code.year:
                year = f"20{code.year}"
                stats["by_year"][year] += 1

            # 기관별 집계 (회신만)
            if code.organization:
                stats["by_organization"][code.organization] += 1

            # 파싱 방법별 집계
            stats["by_parsing_method"][code.parsing_method] += 1

            # 특수 케이스 집계
            if code.is_special:
                stats["special_cases"] += 1

            # 대소문자 구분 없이 파싱된 케이스
            if "case_insensitive" in code.parsing_method:
                stats["case_insensitive_parsed"] += 1

            # 의제별 회신 수 집계
            if (
                code.document_type == "RESPONSE"
                and code.panel
                and code.year
                and code.number
            ):
                agenda_key = f"{code.panel}{code.year}{code.number}"
                stats["agendas"][agenda_key] += 1

        # 응답률 계산
        total_responses = stats["by_type"].get("RESPONSE", 0)
        total_agendas = stats["by_type"].get("AGENDA", 0)
        if total_agendas > 0:
            stats["response_rate"] = round((total_responses / total_agendas) * 100, 2)

        # defaultdict를 일반 dict로 변환
        stats["by_type"] = dict(stats["by_type"])
        stats["by_panel"] = dict(stats["by_panel"])
        stats["by_year"] = dict(stats["by_year"])
        stats["by_organization"] = dict(stats["by_organization"])
        stats["by_parsing_method"] = dict(stats["by_parsing_method"])
        stats["agendas"] = dict(stats["agendas"])

        return stats

    def validate_parsed_code(self, parsed_code: ParsedCode) -> List[str]:
        """파싱된 코드의 유효성 검증"""
        warnings = []

        # 년도 검증 (20-29 범위)
        if parsed_code.year:
            year_int = int(parsed_code.year)
            if year_int < 20 or year_int > 29:
                warnings.append(f"비정상적인 년도: 20{parsed_code.year}")

        # 조직 코드 검증
        if (
            parsed_code.organization
            and parsed_code.organization not in self.ORGANIZATION_CODES
        ):
            warnings.append(f"알 수 없는 조직 코드: {parsed_code.organization}")

        # 패널 타입 검증
        if (
            parsed_code.panel
            and parsed_code.panel not in self.PANEL_TYPES
            and not parsed_code.panel.startswith("JWG")
        ):
            warnings.append(f"알 수 없는 패널 타입: {parsed_code.panel}")

        return warnings
