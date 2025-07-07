#!/usr/bin/env python3
"""새로운 IACS Parser 테스트 - 수정된 파서 포함"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from collections import defaultdict


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


class NewIACSCodeParser:
    """새로운 IACS 문서 코드 파서"""

    # 기관 코드 목록 (확장)
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
        # 특수 접두사 패턴
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
            "전달:",
        ]

        # 긴급도 키워드
        self.urgency_keywords = {
            "high": ["urgent", "긴급", "asap", "immediately", "critical"],
            "medium": ["important", "중요", "priority"],
        }

    def parse_line(self, line: str) -> Optional[ParsedCode]:
        """한 줄을 파싱하여 코드 정보 추출"""
        line = line.strip()
        if not line:
            return None

        # 다중 특수 접두사 제거
        cleaned_line = line
        changed = True
        while changed:
            changed = False
            for prefix in self.special_prefixes:
                if cleaned_line.upper().startswith(prefix.upper()):
                    cleaned_line = cleaned_line[len(prefix) :].strip()
                    changed = True
                    break

        # 코드와 설명 분리
        code_part = ""
        description = ""

        # 콜론으로 분리 시도
        if ":" in cleaned_line:
            parts = cleaned_line.split(":", 1)
            code_part = parts[0].strip()
            description = parts[1].strip()
        # 공백으로 분리 시도 (특수한 경우)
        else:
            # 특수 구분자 처리 (" - ", " ")
            if " - " in cleaned_line:
                parts = cleaned_line.split(" - ", 1)
                code_part = parts[0].strip()
                description = parts[1].strip() if len(parts) > 1 else ""
            else:
                parts = cleaned_line.split(" ", 1)
                code_part = parts[0].strip()
                description = parts[1].strip() if len(parts) > 1 else ""

        # 패턴 매칭
        # 1. 표준 회신 패턴: PL25016_IRa
        match = re.match(
            r"^(PL|PS)(\d{2})(\d{3,4})([a-z]*)?_([A-Z]{2,4})([a-z]*)?$",
            code_part,
            re.IGNORECASE,
        )
        if match:
            panel, year, number, agenda_ver, org, response_ver = match.groups()
            if org.upper() in self.ORGANIZATION_CODES:
                return ParsedCode(
                    full_code=(
                        code_part.upper()
                        if not agenda_ver and not response_ver
                        else f"{panel.upper()}{year}{number}{agenda_ver.lower() if agenda_ver else ''}_{org.upper()}{response_ver.lower() if response_ver else ''}"
                    ),
                    document_type="RESPONSE",
                    panel=panel.upper(),
                    year=year,
                    number=number,
                    agenda_version=agenda_ver.lower() if agenda_ver else None,
                    organization=org.upper(),
                    response_version=response_ver.lower() if response_ver else None,
                    description=description,
                )

        # 2. 붙어있는 회신 패턴: PL25007bTLa
        match = re.match(
            r"^(PL|PS)(\d{2})(\d{3,4})([a-z]+)([A-Z]{2,4})([a-z]*)?$",
            code_part,
            re.IGNORECASE,
        )
        if match:
            panel, year, number, agenda_ver, org, response_ver = match.groups()
            if org.upper() in self.ORGANIZATION_CODES:
                return ParsedCode(
                    full_code=f"{panel.upper()}{year}{number}{agenda_ver.lower()}{org.upper()}{response_ver.lower() if response_ver else ''}",
                    document_type="RESPONSE",
                    panel=panel.upper(),
                    year=year,
                    number=number,
                    agenda_version=agenda_ver.lower(),
                    organization=org.upper(),
                    response_version=response_ver.lower() if response_ver else None,
                    description=description,
                )

        # 3. 의제 패턴: PL25016 또는 PL25016a
        match = re.match(
            r"^(PL|PS)(\d{2})(\d{3,4})([a-z]+)?$", code_part, re.IGNORECASE
        )
        if match:
            panel, year, number, version = match.groups()
            return ParsedCode(
                full_code=(
                    code_part.upper()
                    if not version
                    else f"{panel.upper()}{year}{number}{version.lower()}"
                ),
                document_type="AGENDA",
                panel=panel.upper(),
                year=year,
                number=number,
                agenda_version=version.lower() if version else None,
                description=description,
            )

        # 4. JWG 회신 패턴: JWG-SDT25001_BVa
        match = re.match(
            r"^(JWG)-(SDT|CS)(\d{2})(\d{3})_([A-Z]{2,4})([a-z]*)?$",
            code_part,
            re.IGNORECASE,
        )
        if match:
            prefix, subtype, year, number, org, response_ver = match.groups()
            if org.upper() in self.ORGANIZATION_CODES:
                return ParsedCode(
                    full_code=f"{prefix.upper()}-{subtype.upper()}{year}{number}_{org.upper()}{response_ver.lower() if response_ver else ''}",
                    document_type="RESPONSE",
                    panel=f"{prefix.upper()}-{subtype.upper()}",
                    year=year,
                    number=number,
                    organization=org.upper(),
                    response_version=response_ver.lower() if response_ver else None,
                    description=description,
                )

        # 5. JWG 의제 패턴: JWG-SDT25001 또는 JWG-SDT25001a
        match = re.match(
            r"^(JWG)-(SDT|CS)(\d{2})(\d{3})([a-z]+)?$", code_part, re.IGNORECASE
        )
        if match:
            prefix, subtype, year, number, version = match.groups()
            return ParsedCode(
                full_code=f"{prefix.upper()}-{subtype.upper()}{year}{number}{version.lower() if version else ''}",
                document_type="AGENDA",
                panel=f"{prefix.upper()}-{subtype.upper()}",
                year=year,
                number=number,
                agenda_version=version.lower() if version else None,
                description=description,
            )

        # 6. JWG 붙어있는 회신 패턴: JWG-CS25001b_PRa
        match = re.match(
            r"^(JWG)-(SDT|CS)(\d{2})(\d{3})([a-z]+)?_([A-Z]{2,4})([a-z]*)?$",
            code_part,
            re.IGNORECASE,
        )
        if match:
            prefix, subtype, year, number, agenda_ver, org, response_ver = (
                match.groups()
            )
            if org.upper() in self.ORGANIZATION_CODES:
                return ParsedCode(
                    full_code=f"{prefix.upper()}-{subtype.upper()}{year}{number}{agenda_ver.lower() if agenda_ver else ''}_{org.upper()}{response_ver.lower() if response_ver else ''}",
                    document_type="RESPONSE",
                    panel=f"{prefix.upper()}-{subtype.upper()}",
                    year=year,
                    number=number,
                    agenda_version=agenda_ver.lower() if agenda_ver else None,
                    organization=org.upper(),
                    response_version=response_ver.lower() if response_ver else None,
                    description=description,
                )

        return None

    def extract_all_patterns(self, subject: str, body: str) -> Dict[str, Any]:
        """제목과 본문에서 모든 패턴 추출"""
        result = {}

        # 1. 제목에서 IACS 코드 파싱
        parsed_code = self.parse_line(subject)
        if parsed_code:
            result["iacs_code"] = parsed_code
            result["extracted_info"] = {
                "full_code": parsed_code.full_code,
                "document_type": parsed_code.document_type,
                "panel": parsed_code.panel,
                "year": parsed_code.year,
                "number": parsed_code.number,
                "agenda_version": parsed_code.agenda_version,
                "organization": parsed_code.organization,
                "response_version": parsed_code.response_version,
                "description": parsed_code.description,
                "is_response": parsed_code.document_type == "RESPONSE",
                "is_agenda": parsed_code.document_type == "AGENDA",
                "base_agenda_no": self.extract_base_agenda_no(parsed_code),
            }

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

    def extract_base_agenda_no(self, parsed_code: ParsedCode) -> Optional[str]:
        """기본 아젠다 번호 추출"""
        if parsed_code.panel and parsed_code.year and parsed_code.number:
            base = f"{parsed_code.panel}{parsed_code.year}{parsed_code.number}"
            if parsed_code.agenda_version:
                base += parsed_code.agenda_version
            return base
        return None

    def analyze_reply_chain(self, subject: str) -> Dict[str, Any]:
        """회신 체인 분석"""
        result = {}

        # 회신 표시
        reply_prefixes = ["RE:", "Re:", "답장:", "Reply:"]
        for prefix in reply_prefixes:
            if subject.upper().startswith(prefix.upper()):
                result["is_reply"] = True
                result["reply_depth"] = subject.upper().count(prefix.upper())
                break

        # 전달 표시
        forward_prefixes = ["FW:", "Fw:", "FWD:", "Fwd:", "전달:", "Forward:"]
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

    def extract_agenda_patterns(self, text: str) -> List[str]:
        """본문에서 추가 아젠다 참조 추출"""
        patterns = []

        # IACS 아젠다 패턴들
        agenda_patterns = [
            r"\b((?:PL|PS)\d{2}\d{3,4}[a-z]?(?:_[A-Z]{2,4}[a-z]?)?)\b",
            r"\b((?:PL|PS)\d{2}\d{3,4}[a-z]?[A-Z]{2,4}[a-z]?)\b",  # 붙어있는 패턴
            r"\b(JWG-(?:SDT|CS)\d{2}\d{3}[a-z]?(?:_[A-Z]{2,4}[a-z]?)?)\b",
        ]

        for pattern in agenda_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                normalized = match.upper()
                if normalized not in patterns:
                    patterns.append(normalized)

        return patterns


def test_real_email_subjects():
    """실제 이메일 제목 테스트"""
    parser = NewIACSCodeParser()

    # 실제 이메일 제목들
    email_subjects = [
        "PL25016_IRa: IMO Expert Group on Data Harmonization (EGDH) 13 Session",
        "PL25015_KRa: Recommendation on Network Monitoring (2nd SDTP Meeting, Agenda Item 5, FUA 6)",
        "PL25007bTLa IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 2",
        "Multilateral New SDTP Secretary",
        "PL25008cILc: IMO MSC 110 7 - IACS Brief - Cybersecurity - Final",
        "Re: JWG-SDT25001a: IACS Recommendation on Cybersecurity Controls for existing ships - (PL24016) (23170)",
        "IACS SDTP Fw: PL25015_ILa: Recommendation on Network Monitoring (2nd SDTP Meeting, Agenda Item 5, FUA 6) (안종우)",
        "Re: IACS SDTP Fw: PL25015_ILa: Recommendation on Network Monitoring (2nd SDTP Meeting, Agenda Item 5, FUA 6) (안종우)",
        "PS25003pPLa MSC 110 (18-27 June 2025) - IACS Observer Report (25100e) (PL25008e)",
        "IACS SDTP PL25007bILa IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 2(안종우)",
        "Fw: IACS SDTP Fw: PL25015_ILa: Recommendation on Network Monitoring (2nd SDTP Meeting, Agenda Item 5, FUA 6) (안종우)",
        "RE: PL25013_RIa:3rd IACS Safe Digital Transformation Panel - Meeting Dates (Fall) (2nd SDTP Meeting, FUA 14)",
        "Automatic reply: PL25008aKRd: IMO MSC 110 5 - Papers 5 15, 5 16, 5 17, 5 18, 5 21 - To Review",
        "RE: JWG-SDT25001a: IACS Recommendation on Cybersecurity Controls for existing ships - (PL24016) (23170)",
        "JWG-CS25002b: JWG Revised Terms of Reference (ToR) - Final",
        "JWG-SDT25001a: IACS Recommendation on Cybersecurity Controls for existing ships - (PL24016) (23170)",
        "PL25013_NVa - :3rd IACS Safe Digital Transformation Panel - Meeting Dates (Fall) (2nd SDTP Meeting, FUA 14)",
        "PL24005_NVb - : Email thread dedicated to track observations on published URs (2nd SDTP Meeting, Agenda item 19, FUA 13)",
        "답장: 전달: PL25003_KRb",
        "pl25003_ila",
        # 추가 테스트 케이스
        "JWG-CS25001b_PRa: 28th JWG-CS Meeting - Draft Agenda",
        "PL24005_ABa: Additional item for the Email thread",
    ]

    print("=" * 80)
    print("실제 이메일 제목 파싱 테스트")
    print("=" * 80)

    # 통계 수집
    stats = {
        "total": len(email_subjects),
        "parsed": 0,
        "failed": 0,
        "by_type": defaultdict(int),
        "by_panel": defaultdict(int),
        "by_organization": defaultdict(int),
        "special_cases": {
            "with_colon": 0,
            "without_colon": 0,
            "with_prefix": 0,
            "jwg_pattern": 0,
            "unusual_format": 0,
        },
    }

    failed_subjects = []

    for subject in email_subjects:
        print(f"\n제목: {subject}")
        print("-" * 60)

        # 콜론 포함 여부 체크
        if ":" in subject:
            stats["special_cases"]["with_colon"] += 1
        else:
            stats["special_cases"]["without_colon"] += 1

        # 접두사 체크
        if any(
            subject.upper().startswith(prefix.upper())
            for prefix in [
                "RE:",
                "FW:",
                "IACS SDTP",
                "답장:",
                "전달:",
                "Automatic reply:",
            ]
        ):
            stats["special_cases"]["with_prefix"] += 1

        # JWG 패턴 체크
        if "JWG" in subject:
            stats["special_cases"]["jwg_pattern"] += 1

        # 파싱 시도
        parsed = parser.parse_line(subject)

        if parsed:
            stats["parsed"] += 1
            stats["by_type"][parsed.document_type] += 1
            stats["by_panel"][parsed.panel] += 1
            if parsed.organization:
                stats["by_organization"][parsed.organization] += 1

            print(f"✓ 파싱 성공!")
            print(f"  - 전체 코드: {parsed.full_code}")
            print(f"  - 문서 타입: {parsed.document_type}")
            print(f"  - 패널: {parsed.panel}")
            print(f"  - 연도: {parsed.year}")
            print(f"  - 번호: {parsed.number}")

            if parsed.document_type == "AGENDA":
                print(f"  - 버전: {parsed.agenda_version or '없음'}")
            else:  # RESPONSE
                print(f"  - 조직: {parsed.organization}")
                print(f"  - 회신 버전: {parsed.response_version or '없음'}")

            if parsed.description:
                print(f"  - 설명: {parsed.description[:50]}...")
        else:
            stats["failed"] += 1
            failed_subjects.append(subject)
            print("✗ 파싱 실패")

            # 실패 원인 분석
            if "Multilateral" in subject or "Bilateral" in subject:
                print("  - 원인: 다자간/양자간 메일 (IACS 코드 없음)")
            elif "SDTP Fw:" in subject and ":" in subject[subject.find("SDTP Fw:") :]:
                print("  - 원인: 복잡한 전달 체인")
            elif " - " in subject and ":" not in subject:
                print("  - 원인: 특수 형식 (콜론 없이 대시만 사용)")
                stats["special_cases"]["unusual_format"] += 1

    # 통계 출력
    print("\n" + "=" * 80)
    print("파싱 통계")
    print("=" * 80)
    print(f"총 이메일: {stats['total']}")
    print(f"파싱 성공: {stats['parsed']} ({stats['parsed']/stats['total']*100:.1f}%)")
    print(f"파싱 실패: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")

    print(f"\n문서 타입별:")
    for doc_type, count in stats["by_type"].items():
        print(f"  - {doc_type}: {count}")

    print(f"\n패널별:")
    for panel, count in sorted(stats["by_panel"].items()):
        print(f"  - {panel}: {count}")

    print(f"\n조직별 (회신만):")
    for org, count in sorted(stats["by_organization"].items()):
        print(f"  - {org}: {count}")

    print(f"\n특수 케이스:")
    print(f"  - 콜론 포함: {stats['special_cases']['with_colon']}")
    print(f"  - 콜론 없음: {stats['special_cases']['without_colon']}")
    print(f"  - 접두사 포함: {stats['special_cases']['with_prefix']}")
    print(f"  - JWG 패턴: {stats['special_cases']['jwg_pattern']}")
    print(f"  - 특수 형식: {stats['special_cases']['unusual_format']}")

    # 실패한 제목들 분석
    if failed_subjects:
        print(f"\n파싱 실패한 제목들:")
        for subject in failed_subjects:
            print(f"  - {subject}")


def test_specific_patterns():
    """특정 패턴 집중 테스트"""
    parser = NewIACSCodeParser()

    print("\n" + "=" * 80)
    print("특정 패턴 집중 테스트")
    print("=" * 80)

    test_cases = [
        # 기본 테스트
        ("PL25016_IRa", "표준 회신"),
        ("PL25007bTLa", "붙어있는 회신"),
        ("PL25016", "기본 의제"),
        ("PL25016a", "버전이 있는 의제"),
        ("JWG-SDT25001_BVa", "JWG 회신"),
        ("JWG-CS25001b_PRa", "JWG 버전+회신"),
        # 문제가 있었던 케이스
        ("pl25003_ila", "소문자"),
        ("PL25008cILc", "두 글자 버전"),
        ("PS25003pPLa", "특수 버전"),
        ("PL25013_NVa", "NV 조직"),
        ("PL25013_RIa", "RI 조직"),
    ]

    for code, description in test_cases:
        print(f"\n테스트: {code} ({description})")
        parsed = parser.parse_line(code)
        if parsed:
            print(f"  ✓ 성공: {parsed.full_code} - {parsed.document_type}")
        else:
            print(f"  ✗ 실패")


def analyze_all_patterns():
    """모든 패턴 분석"""
    parser = NewIACSCodeParser()

    # 실제 이메일에서 추출한 모든 패턴
    all_patterns = """
PL25016_IRa PL25015_KRa PL25007bTLa PL25015_BVa PL25016_BVa PL25007bPRa
PL25008cILc PL25016_ILa PL25007bBVa PL25015_CRa PL25016_NVa PL25017_ILa
PL25007bRIa PL24035_ILf PL25018_ILa PL25015_IRa PL25015_NVa PL25016_TLa
PL25007bILb PL24005_TLb PL25016_CCa JWG-SDT25001a PL24005_IRc PL25007bKRa
PL25008dILe PL25015_ILa PL25015_TLa PL24005_PRb PL25008dLRb PL24005_NKd
PL25007bABa PS25003pPLa PL25008eILa PL25016_PRa PL25015_ABa PL25016_ABa
PL25015_CCa PL25008dLRa PL25015_NKb PL25016_NKa PL25007bILa PL24033_ILf
PL25016_KRa PL25015_NKa PL25015_PRa PL25008cIRa PL25008aKRd PL25012_NVa
PL25012_IRa PL25012_CRa PL25008aNKc PL25013_LRa PL24005_NVb PL25013_IRa
PL25012_PRa PL25013_TLa PL25012_TLa PL25013_PRa PL25008aTLd PL25012_NKa
PL25008aNVd PL25008cILb PL25013_ILb PL25014_ILa PL25008aBVd PL25008aPRc
PL25008aCCc PL24005_BVc PL25013_RIa PL25008aCRc PL25008cPRa PL25008dILd
PL25008aLRa PL25013_ABa PL25008cCCa PL25008dILc PL25008cTLa PL25008cNVa
PL25008aNKd PL25008aCCd PL24005_ABc PL25012_CCa PL25008aPRd PL25008cNKa
PL25012_ILb PL25005_ILc PL25013_CRa PL24016_CRe PL25005_NVc JWG-CS25002b
PL25008aCRb PL25002_ILd PL25008aILe PL25013_NVa PL25008aTLb PL25008aNVc
PL24016_BVd PL24016_CCd PL25008aCRa JWG-CS25001e PL25013_BVa PL24016_TLe
PL25008cILa PL25008aBVb PL24016_ILh PL25008aTLc PL25013_CCa PL25008aBVa
PL25008aIRa PL24016_NVf PL24016_IRg PL25008aCCb PL25008aILf PL24016_NKe
PL25008aNVb PL24016_PRd PL24035_ILe PL24016_NKd PL25008aIRb PL25008aNVa
PL24016_ABd PL24005_ILc PL25008aPRb PL25008aPRa PL25008dILa PL25008aCCa
PL25013_ILa PL25008aNKa PL25008dILb PL25008aNKb PL24016_ILg PL25008aIRc
PL25008aBVc PL24037bBVa PL25008bILb PL24035_IRd PL24035_BVb PL24037bILb
PL25007aNVa PL25005_TLb PL24037bIRa PL25007aTLa PL25005_NKb PL25007_BVa
PL24042bIRb PL25007aPRa PL25007aCCa PL25009_ABa PL24042bTLb PL24035_TLb
PL25005_ABb PL24037bNKa PL25009_ILb PL25007aABa PL25005_IRb PL24042bNKb
PL25011_ABa PL24042bPRb PL24042bILc PL25008aTLa PL25008aILb PL25011_ILa
PL25010_ILa PL25007aIRa PL24035_NKb PL24035_ABa PL25007aILb PL25008aILd
PL24035_CCb PL25007aKRa PL24042bCRa PL24042bBVa PL24042bILb PL24037bCRa
PL24035_NVc PL24037bNVa JWG-CS25001c PL24042bTLa PL25005_ILb PL25005_NVb
PL24037bILa PL24035_ILd PL24042bNVa JWG-CS25001d PL25005_NKa PL24005_TLa
PL24005_LRa PL25006_PRa PL25006_NKa PL24031dILd PL25005_CRb PL24005_NVa
PL24041_ILg PL24042bPRa PL24042bCCb PL24041_ILh PL24042bIRa JWG-CS25001b_PRa
PL24017hCRa PL25006_BVa PL25005_NVa PL24017hIRa PL25005_CRa PL25005_IRa
PL24041_KRd PL24017hILa PL25005_RIa PL24005_BVb PL24037aCRa PL24017hNVa
PL24017hBVa PL24016_CRd PL24016_BVc PL24037aTLa PL25005_TLa PL24017hTLa
PL25006_TLa JWG-CS25001bKRa PL24016_RIa PL24037aIRa PL24037aPRa PL25005_CCa
JWG-CS25001bRIa PL24037aILb PL24037aBVa PL24037aNVa PL24017hILb PL24037aCCa
PL24017hABa PL24016_PRc PL25005_ABa PL24017hCCa PL24016_NKc PL24017hPRa
PL24037aNKa PL24035_ILc PL24017hNKa PL24030_ILf PL24005_ABa
"""

    patterns = all_patterns.strip().split()

    print("\n" + "=" * 80)
    print("모든 패턴 분석")
    print("=" * 80)

    results = {
        "total": 0,
        "success": 0,
        "failed": 0,
        "by_type": defaultdict(int),
        "by_panel": defaultdict(int),
        "by_org": defaultdict(int),
        "failed_patterns": [],
    }

    for pattern in patterns:
        results["total"] += 1
        parsed = parser.parse_line(pattern)

        if parsed:
            results["success"] += 1
            results["by_type"][parsed.document_type] += 1
            results["by_panel"][parsed.panel] += 1
            if parsed.organization:
                results["by_org"][parsed.organization] += 1
        else:
            results["failed"] += 1
            results["failed_patterns"].append(pattern)

    print(f"총 패턴: {results['total']}")
    print(
        f"성공: {results['success']} ({results['success']/results['total']*100:.1f}%)"
    )
    print(f"실패: {results['failed']} ({results['failed']/results['total']*100:.1f}%)")

    print(f"\n문서 타입별:")
    for doc_type, count in results["by_type"].items():
        print(f"  - {doc_type}: {count}")

    print(f"\n패널별:")
    for panel, count in sorted(results["by_panel"].items()):
        print(f"  - {panel}: {count}")

    print(f"\n조직별:")
    for org, count in sorted(
        results["by_org"].items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  - {org}: {count}")

    if results["failed_patterns"]:
        print(f"\n실패한 패턴들: {results['failed_patterns']}")


if __name__ == "__main__":
    # 실제 이메일 제목 테스트
    test_real_email_subjects()

    # 특정 패턴 테스트
    test_specific_patterns()

    # 모든 패턴 분석
    analyze_all_patterns()

    print("\n" + "=" * 80)
    print("테스트 완료!")
    print("=" * 80)
