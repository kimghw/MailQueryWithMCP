"""
IACS 상수 및 검증 모듈
modules/mail_process/utilities/iacs/constants.py
"""

from typing import Dict, List, Any
from collections import defaultdict
from dataclasses import dataclass


# 기관 코드 목록
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

# 도메인-조직 매핑
DOMAIN_ORG_MAP = {
    # Korean Register
    "kr.org": "KR",
    "krs.co.kr": "KR",
    "krs.com": "KR",
    # Lloyd's Register
    "lr.org": "LR",
    "lr.com": "LR",
    # DNV (Det Norske Veritas)
    "dnv.com": "DNV",
    "dnvgl.com": "DNV",
    "dnv.no": "DNV",
    # Nippon Kaiji Kyokai (ClassNK)
    "classnk.or.jp": "NK",
    "classnk.com": "NK",
    "nk.org": "NK",
    # American Bureau of Shipping
    "eagle.org": "ABS",
    "abs-group.com": "ABS",
    # Bureau Veritas
    "bureauveritas.com": "BV",
    "bv.com": "BV",
    "bureauveritas.fr": "BV",
    # China Classification Society
    "ccs.org.cn": "CCS",
    "ccs.com.cn": "CCS",
    # Registro Italiano Navale
    "rina.org": "RINA",
    "rina.it": "RINA",
    # Polski Rejestr Statków
    "prs.pl": "PRS",
    "prs.com.pl": "PRS",
    # IACS (IL - Chair)
    "iscsmaritime.com": "IL",
    "iacs.org.uk": "IL",
    "iacs.org": "IL",
    # Turk Loydu
    "tasneef.ae": "TL",
    "turkloydu.org": "TL",
    # Croatian Register of Shipping
    "crs.hr": "CRS",
    "croatiaregister.com": "CRS",
    # Indian Register of Shipping
    "irclass.org": "IRS",
    "irs.org.in": "IRS",
}

# 특수 접두사 패턴
SPECIAL_PREFIXES = [
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
URGENCY_KEYWORDS = {
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
SPECIAL_CASES = ["Multilateral", "MULTILATERAL", "multilateral"]

# 최대 라인 길이 제한
MAX_LINE_LENGTH = 500


@dataclass
class ParsedCode:
    """파싱된 코드 정보를 담는 클래스"""

    full_code: str
    document_type: str  # AGENDA(의제) or RESPONSE(회신) or SPECIAL(특수)
    panel: str  # PL, PS, JWG-SDT, JWG-CS 등
    year: str = None
    number: str = None
    agenda_version: str = None  # 의제 버전 (a, b, c)
    organization: str = None  # IR, KR, BV 등 (회신일 경우)
    response_version: str = None  # 회신 버전 (a, b, c)
    description: str = None  # 코드 뒤의 설명 텍스트
    is_response: bool = False  # 응답 여부
    is_special: bool = False  # 특수 케이스 여부 (Multilateral 등)
    parsing_method: str = ""  # 파싱에 사용된 방법 (디버깅용)


def validate_parsed_code(parsed_code: ParsedCode) -> List[str]:
    """파싱된 코드의 유효성 검증"""
    warnings = []

    # 년도 검증 (20-29 범위)
    if parsed_code.year:
        year_int = int(parsed_code.year)
        if year_int < 20 or year_int > 29:
            warnings.append(f"비정상적인 년도: 20{parsed_code.year}")

    # 조직 코드 검증
    if parsed_code.organization and parsed_code.organization not in ORGANIZATION_CODES:
        warnings.append(f"알 수 없는 조직 코드: {parsed_code.organization}")

    # 패널 타입 검증
    if (
        parsed_code.panel
        and parsed_code.panel not in PANEL_TYPES
        and not parsed_code.panel.startswith("JWG")
    ):
        warnings.append(f"알 수 없는 패널 타입: {parsed_code.panel}")

    return warnings


def get_statistics(parsed_codes: List[ParsedCode]) -> Dict[str, Any]:
    """파싱된 코드들의 통계 정보 생성"""
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
