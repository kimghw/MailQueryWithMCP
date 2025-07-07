"""수정된 IACS 코드 파서 - 실제 데이터 기반"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

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
    is_response: bool = False  # 응답 여부


class IACSCodeParser:
    """IACS 문서 코드 파서 - 실제 데이터 기반 수정 버전"""

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
        "NV",  # NV 추가
        "IR",
        "IRS",
        "KR",
        "LR",
        "NK",
        "PR",
        "PRS",
        "PL",  # PR, PL 추가
        "RI",
        "RINA",
        "IL",
        "TL",  # RI 추가 (RINA의 축약형)
    }

    # 패널 타입
    PANEL_TYPES = {"PL", "PS", "JWG-SDT", "JWG-CS"}

    def __init__(self):
        self.logger = get_logger(__name__)

        # 특수 접두사 패턴 (개선: 다중 접두사 처리)
        self.special_prefixes = [
            "Multilateral",
            "Bilateral",
            "RE:",
            "Re:",
            "re:",
            "Fw:",
            "FW:",
            "fw:",
            "Fwd:",
            "FWD:",
            "fwd:",
            "Automatic reply:",
            "IACS SDTP",
            "답장:",
            "전달:",  # 한글 접두사
            "回复:",
            "转发:",  # 중국어 접두사
        ]

        # 긴급도 키워드
        self.urgency_keywords = {
            "high": ["urgent", "긴급", "asap", "immediately", "critical", "急"],
            "medium": ["important", "중요", "priority", "attention"],
        }

    def parse_line(self, line: str) -> Optional[ParsedCode]:
        """한 줄을 파싱하여 코드 정보 추출 (완전 재작성)"""
        line = line.strip()
        if not line:
            return None

        # 다중 특수 접두사 제거
        cleaned_line = self._remove_prefixes(line)

        # 실제 데이터에서 발견된 패턴들을 모두 처리할 수 있는 정규식
        # 패턴 1: PL25007bTLa (의제버전+조직+응답버전이 붙어있음)
        # 패턴 2: PL25016_IRa (표준 응답 형식)
        # 패턴 3: PL25016 (기본 의제)
        # 패턴 4: PS25003pPLa (특수 버전)

        # 먼저 전체 매칭을 시도
        patterns = [
            # 붙어있는 응답 패턴: PL25007bTLa
            (
                r"^(PL|PS)(\d{2})(\d{3,4})([a-z])?([A-Z]{2,4})([a-z])?(?:\s|:|$)",
                "ATTACHED_RESPONSE",
            ),
            # 표준 응답 패턴: PL25016_IRa
            (
                r"^(PL|PS)(\d{2})(\d{3,4})([a-z])?_([A-Z]{2,4})([a-z])?(?:\s|:|$)",
                "STANDARD_RESPONSE",
            ),
            # JWG 응답 패턴: JWG-SDT25001_BVa
            (
                r"^(JWG)-(SDT|CS)(\d{2})(\d{3})_([A-Z]{2,4})([a-z])?(?:\s|:|$)",
                "JWG_RESPONSE",
            ),
            # 기본 의제 패턴: PL25016a
            (r"^(PL|PS)(\d{2})(\d{3,4})([a-z])?(?:\s|:|$)", "STANDARD_AGENDA"),
            # JWG 의제 패턴: JWG-SDT25001a
            (r"^(JWG)-(SDT|CS)(\d{2})(\d{3})([a-z])?(?:\s|:|$)", "JWG_AGENDA"),
            # 특수 붙어있는 패턴 with underbar: JWG-CS25001b_PRa
            (
                r"^(JWG)-(SDT|CS)(\d{2})(\d{3})([a-z])?_([A-Z]{2,4})([a-z])?(?:\s|:|$)",
                "JWG_ATTACHED_RESPONSE",
            ),
        ]

        for pattern, pattern_type in patterns:
            match = re.match(pattern, cleaned_line, re.IGNORECASE)
            if match:
                # 설명 부분 추출
                description = None
                if ":" in cleaned_line:
                    parts = cleaned_line.split(":", 1)
                    if len(parts) > 1:
                        description = parts[1].strip()
                elif " " in cleaned_line and not cleaned_line.startswith("JWG"):
                    # 공백으로 분리 (JWG가 아닌 경우만)
                    parts = cleaned_line.split(" ", 1)
                    if len(parts) > 1:
                        description = parts[1].strip()

                return self._parse_matched_pattern(
                    match, pattern_type, cleaned_line, description
                )

        # 패턴에 맞지 않는 경우 로깅
        if any(cleaned_line.upper().startswith(p) for p in ["PL", "PS", "JWG"]):
            self.logger.debug(f"IACS 코드 파싱 실패: {cleaned_line}")

        return None

    def _remove_prefixes(self, line: str) -> str:
        """다중 접두사 제거"""
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

    def _parse_matched_pattern(
        self, match, pattern_type: str, full_line: str, description: str
    ) -> ParsedCode:
        """매칭된 패턴을 ParsedCode로 변환"""
        groups = match.groups()

        if pattern_type == "ATTACHED_RESPONSE":
            # PL25007bTLa 형식
            panel, year, number, agenda_ver, org, response_ver = groups
            # 조직 코드 검증
            if org.upper() in self.ORGANIZATION_CODES:
                # full_code 재구성
                base = f"{panel.upper()}{year}{number}"
                if agenda_ver:
                    base += agenda_ver.lower()
                full_code = (
                    f"{base}{org.upper()}{response_ver.lower() if response_ver else ''}"
                )

                return ParsedCode(
                    full_code=full_code,
                    document_type="RESPONSE",
                    panel=panel.upper(),
                    year=year,
                    number=number,
                    agenda_version=agenda_ver.lower() if agenda_ver else None,
                    organization=org.upper(),
                    response_version=response_ver.lower() if response_ver else None,
                    description=description,
                    is_response=True,
                )

        elif pattern_type == "STANDARD_RESPONSE":
            # PL25016_IRa 형식
            panel, year, number, agenda_ver, org, response_ver = groups
            if org.upper() in self.ORGANIZATION_CODES:
                base = f"{panel.upper()}{year}{number}"
                if agenda_ver:
                    base += agenda_ver.lower()
                full_code = f"{base}_{org.upper()}{response_ver.lower() if response_ver else ''}"

                return ParsedCode(
                    full_code=full_code,
                    document_type="RESPONSE",
                    panel=panel.upper(),
                    year=year,
                    number=number,
                    agenda_version=agenda_ver.lower() if agenda_ver else None,
                    organization=org.upper(),
                    response_version=response_ver.lower() if response_ver else None,
                    description=description,
                    is_response=True,
                )

        elif pattern_type == "JWG_RESPONSE" or pattern_type == "JWG_ATTACHED_RESPONSE":
            # JWG-SDT25001_BVa 형식
            if pattern_type == "JWG_RESPONSE":
                prefix, subtype, year, number, org, response_ver = groups
                agenda_ver = None
            else:
                prefix, subtype, year, number, agenda_ver, org, response_ver = groups

            if org.upper() in self.ORGANIZATION_CODES:
                base = f"{prefix.upper()}-{subtype.upper()}{year}{number}"
                if agenda_ver:
                    base += agenda_ver.lower()
                full_code = f"{base}_{org.upper()}{response_ver.lower() if response_ver else ''}"

                return ParsedCode(
                    full_code=full_code,
                    document_type="RESPONSE",
                    panel=f"{prefix.upper()}-{subtype.upper()}",
                    year=year,
                    number=number,
                    agenda_version=agenda_ver.lower() if agenda_ver else None,
                    organization=org.upper(),
                    response_version=response_ver.lower() if response_ver else None,
                    description=description,
                    is_response=True,
                )

        elif pattern_type == "STANDARD_AGENDA":
            # PL25016a 형식
            panel, year, number, version = groups
            full_code = f"{panel.upper()}{year}{number}"
            if version:
                full_code += version.lower()

            return ParsedCode(
                full_code=full_code,
                document_type="AGENDA",
                panel=panel.upper(),
                year=year,
                number=number,
                agenda_version=version.lower() if version else None,
                description=description,
                is_response=False,
            )

        elif pattern_type == "JWG_AGENDA":
            # JWG-SDT25001a 형식
            prefix, subtype, year, number, version = groups
            full_code = f"{prefix.upper()}-{subtype.upper()}{year}{number}"
            if version:
                full_code += version.lower()

            return ParsedCode(
                full_code=full_code,
                document_type="AGENDA",
                panel=f"{prefix.upper()}-{subtype.upper()}",
                year=year,
                number=number,
                agenda_version=version.lower() if version else None,
                description=description,
                is_response=False,
            )

        # 기본값으로 None 반환
        return None

    def extract_base_agenda_no(self, parsed_code: ParsedCode) -> Optional[str]:
        """기본 아젠다 번호 추출"""
        if parsed_code.panel and parsed_code.year and parsed_code.number:
            base = f"{parsed_code.panel}{parsed_code.year}{parsed_code.number}"
            if parsed_code.agenda_version:
                base += parsed_code.agenda_version
            return base
        return None

    def extract_agenda_patterns(self, text: str) -> List[str]:
        """본문에서 추가 아젠다 참조 추출 (수정됨)"""
        patterns = []

        # 더 정확한 패턴으로 수정
        agenda_patterns = [
            # PL/PS 패턴
            r"\b((?:PL|PS)\d{2}\d{3,4}[a-z]?(?:_[A-Z]{2,4}[a-z]?)?)\b",
            # JWG 패턴
            r"\b(JWG-(?:SDT|CS)\d{2}\d{3}[a-z]?(?:_[A-Z]{2,4}[a-z]?)?)\b",
            # 붙어있는 패턴
            r"\b((?:PL|PS)\d{2}\d{3,4}[a-z]?[A-Z]{2,4}[a-z]?)\b",
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
        reply_prefixes = ["RE:", "Re:", "답장:", "Reply:", "回复:"]
        for prefix in reply_prefixes:
            if subject.upper().startswith(prefix.upper()):
                result["is_reply"] = True
                result["reply_depth"] = subject.upper().count(prefix.upper())
                break

        # 전달 표시
        forward_prefixes = ["FW:", "Fw:", "FWD:", "Fwd:", "전달:", "Forward:", "转发:"]
        for prefix in forward_prefixes:
            if subject.upper().startswith(prefix.upper()):
                result["is_forward"] = True
                break

        return result

    def extract_urgency(self, subject: str, text: str) -> Optional[str]:
        """긴급도 추출"""
        combined = f"{subject} {text}".lower()

        for level, keywords in self.urgency_keywords.items():
            if any(keyword in combined for keyword in keywords):
                return level.upper()

        return "NORMAL"

    def extract_all_patterns(self, subject: str, body: str) -> Dict[str, Any]:
        """제목과 본문에서 모든 패턴 추출 (통합 메서드)"""
        result = {}

        # 1. 제목에서 IACS 코드 파싱
        parsed_code = self.parse_line(subject)
        if parsed_code:
            result["iacs_code"] = parsed_code
            result["extracted_info"] = self._convert_parsed_code_to_dict(parsed_code)

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
            # 추가 유용한 정보
            "is_response": parsed_code.is_response,
            "is_agenda": not parsed_code.is_response,
            "base_agenda_no": self.extract_base_agenda_no(parsed_code),
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

    def get_statistics(self, parsed_codes: List[ParsedCode]) -> Dict[str, any]:
        """파싱된 코드들의 통계 정보 생성"""
        from collections import defaultdict

        stats = {
            "total": len(parsed_codes),
            "by_type": {"AGENDA": 0, "RESPONSE": 0},
            "by_panel": defaultdict(int),
            "by_year": defaultdict(int),
            "by_organization": defaultdict(int),
            "agendas": defaultdict(int),  # 의제별 회신 수
        }

        for code in parsed_codes:
            # 문서 타입별 집계
            stats["by_type"][code.document_type] += 1

            # 패널별 집계
            stats["by_panel"][code.panel] += 1

            # 연도별 집계
            if code.year:
                year = f"20{code.year}"
                stats["by_year"][year] += 1

            # 기관별 집계 (회신만)
            if code.organization:
                stats["by_organization"][code.organization] += 1

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
