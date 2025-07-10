"""
IACS 패턴 매칭 모듈
modules/mail_process/utilities/iacs/pattern_matcher.py
"""

import re
from typing import Optional, List

from infra.core.logger import get_logger
from .constants import ParsedCode, ORGANIZATION_CODES


class PatternMatcher:
    """IACS 코드 패턴 매칭"""

    def __init__(self):
        self.logger = get_logger(__name__)

    def parse_basic_patterns(
        self, line: str, case_sensitive: bool = True
    ) -> Optional[ParsedCode]:
        """기본 패턴 파싱 (PL/PS)"""
        flags = 0 if case_sensitive else re.IGNORECASE

        patterns = [
            # 패턴1: PL25016aIRa (붙어있는 형식) - 조직은 정확히 2글자
            (
                r"^(PL|PS)(\d{2})(\d{3,4})([a-z*]?)([A-Z]{2})([a-z*]?)(?:\s|:|$)",
                "pattern1_attached",
            ),
            # 패턴2: PL25015_KRa (언더스코어 형식) - 조직은 정확히 2글자
            (
                r"^(PL|PS)(\d{2})(\d{3,4})_([A-Z]{2})([a-z]?)(?:\s|:|$)",
                "pattern2_underscore",
            ),
            # 패턴3: PL25016a_IRa (소문자+언더스코어) - 조직은 정확히 2글자
            (
                r"^(PL|PS)(\d{2})(\d{3,4})([a-z*])_([A-Z]{2})([a-z*]?)(?:\s|:|$)",
                "pattern3_version_underscore",
            ),
            # 패턴4: PL25016_aIRa (언더스코어+소문자) - 조직은 정확히 2글자
            (
                r"^(PL|PS)(\d{2})(\d{3,4})_([a-z*])([A-Z]{2})([a-z*]?)(?:\s|:|$)",
                "pattern4_underscore_version",
            ),
            # 기본 의제 패턴: PL25016a
            (r"^(PL|PS)(\d{2})(\d{3,4})([a-z*]?)(?:\s|:|$)", "basic_agenda"),
        ]

        for pattern, pattern_name in patterns:
            if not case_sensitive:
                # 대소문자 구분 없이 패턴 수정
                pattern = pattern.replace("PL|PS", "[Pp][Ll]|[Pp][Ss]")
                pattern = pattern.replace("[A-Z]", "[A-Za-z]").replace(
                    "[a-z*]", "[A-Za-z*]"
                )

            match = re.match(pattern, line, flags)
            if match:
                return self._process_basic_match(
                    match, pattern_name, line, case_sensitive
                )

        return None

    def parse_jwg_patterns(
        self, line: str, case_sensitive: bool = True
    ) -> Optional[ParsedCode]:
        """JWG 패턴 파싱"""
        flags = 0 if case_sensitive else re.IGNORECASE

        patterns = [
            # JWG-CS25001b_PRa (agenda_version + underscore + response) - 조직은 정확히 2글자
            (
                r"^(JWG)-(SDT|CS)(\d{2})(\d{3})([a-z*])_([A-Z]{2})([a-z*]?)(?:\s|:|$)",
                "jwg_version_underscore",
            ),
            # JWG-SDT25001_BVa - 조직은 정확히 2글자
            (
                r"^(JWG)-(SDT|CS)(\d{2})(\d{3})_([A-Z]{2})([a-z*]?)(?:\s|:|$)",
                "jwg_underscore",
            ),
            # JWG-SDT25001BVa (붙어있는 형식) - 조직은 정확히 2글자
            (
                r"^(JWG)-(SDT|CS)(\d{2})(\d{3})([a-z*]?)([A-Z]{2})([a-z*]?)(?:\s|:|$)",
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

    def find_iacs_patterns(self, text: str) -> List[str]:
        """
        텍스트에서 IACS 패턴 찾기 (추출만)
        패턴: 문자2 + 숫자5 + (문자1-4 또는 _문자2-3)
        예: PL25015_ILa, PL25023aKRa
        """
        # 간단한 패턴 - 문자2 + 숫자5 + 나머지
        pattern = re.compile(
            r'\b([A-Z]{2}\d{2}\d{3,4}[a-zA-Z_]{0,5})\b',
            re.IGNORECASE
        )
        
        matches = pattern.findall(text)
        # 중복 제거하고 반환
        return list(set(matches))

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
            if org.upper() in ORGANIZATION_CODES:
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
            if org.upper() in ORGANIZATION_CODES:
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
