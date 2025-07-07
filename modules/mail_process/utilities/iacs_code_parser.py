"""IACS 코드 파서 - 이메일 제목에서 IACS 문서 코드 추출

modules/mail_process/utilities/iacs_code_parser.py
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass

from infra.core.logger import get_logger


@dataclass
class ParsedCode:
    """파싱된 코드 정보를 담는 클래스"""

    full_code: str
    document_type: str  # AGENDA(의제) or RESPONSE(회신)
    panel: str  # PL, PS, JWG-SDT, JWG-CS 등
    year: Optional[str] = None
    number: Optional[str] = None
    agenda_version: Optional[str] = None  # 의제 버전 (a, b, c)
    organization: Optional[str] = None  # IR, KR, BV 등 (회신일 경우)
    response_version: Optional[str] = None  # 회신 버전 (a, b, c)
    description: Optional[str] = None  # 코드 뒤의 설명 텍스트


class IACSCodeParser:
    """IACS 문서 코드 파서"""

    # 기관 코드 목록 (email_dashboard의 ORGANIZATIONS와 동기화)
    ORGANIZATION_CODES = {
        "ABS",
        "BV",
        "CCS",
        "CRS",
        "DNV",
        "IRS",
        "KR",
        "LR",
        "NK",
        "PRS",
        "RINA",
        "IL",
        "TL",
    }

    # 패널 타입
    PANEL_TYPES = {"PL", "PS", "JWG-SDT", "JWG-CS"}

    def __init__(self):
        self.logger = get_logger(__name__)

        # 의제 패턴: PL24016 또는 PL24016a
        self.agenda_pattern = re.compile(r"^(PL|PS)(\d{2})(\d{3,4})([a-z])?$")

        # 회신 패턴: PL24016_IRa
        self.response_pattern = re.compile(
            r"^(PL|PS)(\d{2})(\d{3,4})([a-z])?_([A-Z]{2,3})([a-z]+)?$"
        )

        # JWG 의제 패턴: JWG-SDT25001 또는 JWG-SDT25001a
        self.jwg_agenda_pattern = re.compile(r"^(JWG)-(SDT|CS)(\d{2})(\d{3})([a-z])?$")

        # JWG 회신 패턴: JWG-SDT25001_IRa
        self.jwg_response_pattern = re.compile(
            r"^(JWG)-(SDT|CS)(\d{2})(\d{3})_([A-Z]{2,3})([a-z]+)?$"
        )

        # 특수 접두사 패턴
        self.special_prefixes = [
            "Multilateral",
            "Bilateral",
            "RE:",
            "Re:",
            "Fw:",
            "FW:",
            "Fwd:",
            "Automatic reply:",
            "IACS SDTP",
            "답장:",
            "전달:",
        ]

    def parse_line(self, line: str) -> Optional[ParsedCode]:
        """한 줄을 파싱하여 코드 정보 추출"""
        line = line.strip()
        if not line:
            return None

        # 특수 접두사 제거
        cleaned_line = line
        for prefix in self.special_prefixes:
            if line.upper().startswith(prefix.upper()):
                cleaned_line = line[len(prefix) :].strip()
                break

        # 코드와 설명 분리 (: 또는 공백으로)
        parts = re.split(r"[:]\s*|\s+", cleaned_line, 1)
        code_part = parts[0].strip()
        description = parts[1].strip() if len(parts) > 1 else None

        # 회신 패턴 먼저 확인 (더 구체적이므로)
        match = self.response_pattern.match(code_part)
        if match:
            panel, year, number, agenda_ver, org, response_ver = match.groups()
            # 조직 코드 검증
            if org in self.ORGANIZATION_CODES:
                return ParsedCode(
                    full_code=code_part,
                    document_type="RESPONSE",
                    panel=panel,
                    year=year,
                    number=number,
                    agenda_version=agenda_ver if agenda_ver else None,
                    organization=org,
                    response_version=response_ver if response_ver else None,
                    description=description,
                )

        # 의제 패턴 확인
        match = self.agenda_pattern.match(code_part)
        if match:
            panel, year, number, version = match.groups()
            return ParsedCode(
                full_code=code_part,
                document_type="AGENDA",
                panel=panel,
                year=year,
                number=number,
                agenda_version=version if version else None,
                description=description,
            )

        # JWG 회신 패턴 확인
        match = self.jwg_response_pattern.match(code_part)
        if match:
            prefix, subtype, year, number, org, response_ver = match.groups()
            if org in self.ORGANIZATION_CODES:
                return ParsedCode(
                    full_code=code_part,
                    document_type="RESPONSE",
                    panel=f"{prefix}-{subtype}",
                    year=year,
                    number=number,
                    organization=org,
                    response_version=response_ver if response_ver else None,
                    description=description,
                )

        # JWG 의제 패턴 확인
        match = self.jwg_agenda_pattern.match(code_part)
        if match:
            prefix, subtype, year, number, version = match.groups()
            return ParsedCode(
                full_code=code_part,
                document_type="AGENDA",
                panel=f"{prefix}-{subtype}",
                year=year,
                number=number,
                agenda_version=version if version else None,
                description=description,
            )

        # 패턴에 맞지 않는 경우 로깅
        if any(code_part.startswith(p) for p in ["PL", "PS", "JWG"]):
            self.logger.debug(f"IACS 코드 파싱 실패: {code_part}")

        return None

    def extract_base_agenda_no(self, parsed_code: ParsedCode) -> Optional[str]:
        """기본 아젠다 번호 추출"""
        if parsed_code.panel and parsed_code.year and parsed_code.number:
            base = f"{parsed_code.panel}{parsed_code.year}{parsed_code.number}"
            if parsed_code.agenda_version:
                base += parsed_code.agenda_version
            return base
        return None

    def parse_document(self, text: str) -> List[ParsedCode]:
        """전체 문서를 파싱하여 모든 코드 정보 추출"""
        results = []
        lines = text.strip().split("\n")

        for line in lines:
            parsed = self.parse_line(line)
            if parsed:
                results.append(parsed)

        return results

    def get_statistics(self, parsed_codes: List[ParsedCode]) -> Dict[str, any]:
        """파싱된 코드들의 통계 정보 생성"""
        stats = {
            "total": len(parsed_codes),
            "by_type": {"AGENDA": 0, "RESPONSE": 0, "UNKNOWN": 0},
            "by_panel": {},
            "by_year": {},
            "by_organization": {},
            "agendas": {},  # 의제별 회신 수
        }

        for code in parsed_codes:
            # 문서 타입별 집계
            stats["by_type"][code.document_type] = (
                stats["by_type"].get(code.document_type, 0) + 1
            )

            # 패널별 집계
            panel = code.panel
            stats["by_panel"][panel] = stats["by_panel"].get(panel, 0) + 1

            # 연도별 집계
            if code.year:
                year = f"20{code.year}"
                stats["by_year"][year] = stats["by_year"].get(year, 0) + 1

            # 기관별 집계 (회신만)
            if code.organization:
                stats["by_organization"][code.organization] = (
                    stats["by_organization"].get(code.organization, 0) + 1
                )

            # 의제별 회신 수 집계
            if (
                code.document_type == "RESPONSE"
                and code.panel
                and code.year
                and code.number
            ):
                agenda_key = f"{code.panel}{code.year}{code.number}"
                stats["agendas"][agenda_key] = stats["agendas"].get(agenda_key, 0) + 1

        return stats
