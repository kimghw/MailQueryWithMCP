"""개선된 IACS 코드 파서 - 새로운 파싱 규칙 적용"""

import re
from typing import Dict, List, Optional, Any
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
            "high": ["urgent", "긴급", "asap", "immediately", "critical", "急"],
            "medium": ["important", "중요", "priority", "attention"],
        }

        # 특수 케이스
        self.special_cases = ["Multilateral", "MULTILATERAL", "multilateral"]

    def parse_line(self, line: str) -> Optional[ParsedCode]:
        """한 줄을 파싱하여 코드 정보 추출 (새로운 규칙 적용)"""
        line = line.strip()
        if not line:
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

        # 파싱 실패 로깅
        if any(cleaned_line.upper().startswith(p) for p in ["PL", "PS", "JWG"]):
            self.logger.debug(f"IACS 코드 파싱 실패 (예외 메일): {cleaned_line}")

        return None

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
            # PL25016a_IRa - 소문자 우선, _ 삭제
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
            # PL25016_aIRa - 소문자 우선, _ 삭제
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

        # agenda_version이 있으면 무조건 붙어있는 형식으로 처리 (underscore 삭제)
        if agenda_ver and agenda_ver != "*":
            # 붙어있는 형식으로 강제
            full_code = f"{base}{org.upper()}{response_ver.lower() if response_ver and response_ver != '*' else ''}"
        elif attached:
            # 붙어있는 형식
            full_code = f"{base}{org.upper()}{response_ver.lower() if response_ver and response_ver != '*' else ''}"
        else:
            # 언더스코어 형식
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
                return parts[1].strip()

        # 공백으로 분리 (JWG가 아닌 경우만)
        if " " in line and not line.upper().startswith("JWG"):
            parts = line.split(" ", 1)
            if len(parts) > 1:
                return parts[1].strip()

        return None

    def _remove_prefixes(self, line: str) -> str:
        """특수 접두사 제거"""
        cleaned_line = line
        changed = True
        while changed:
            changed = False
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
                if normalized not in patterns:
                    patterns.append(normalized)

        return patterns

    def analyze_reply_chain(self, subject: str) -> Dict[str, Any]:
        """회신 체인 분석"""
        result = {}

        # 회신 표시
        reply_prefixes = ["RE:", "Re:", "re:", "답장:", "Reply:", "回复:"]
        for prefix in reply_prefixes:
            if subject.upper().startswith(prefix.upper()):
                result["is_reply"] = True
                result["reply_depth"] = subject.upper().count(prefix.upper())
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

        for level, keywords in self.urgency_keywords.items():
            if any(keyword in combined for keyword in keywords):
                return level.upper()

        return "NORMAL"

    def extract_all_patterns(self, subject: str, body: str) -> Dict[str, Any]:
        """제목과 본문에서 모든 패턴 추출"""
        result = {}

        # 1. 제목에서 IACS 코드 파싱
        parsed_code = self.parse_line(subject)
        if parsed_code:
            result["iacs_code"] = parsed_code
            result["extracted_info"] = self._convert_parsed_code_to_dict(parsed_code)
            self.logger.debug(
                f"파싱 성공: {parsed_code.full_code} (방법: {parsed_code.parsing_method})"
            )
        else:
            self.logger.debug(f"파싱 실패 (예외 메일): {subject}")

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

        for line in lines:
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

        return stats
