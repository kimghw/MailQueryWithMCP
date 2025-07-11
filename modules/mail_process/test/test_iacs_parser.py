#!/usr/bin/env python3
"""
IACS 파서 테스트 스크립트
사용법: python test_iacs_parser.py
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict, List

# 프로젝트 루트 경로 추가 (필요에 따라 수정)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from modules.mail_process.utilities.iacs import IACSCodeParser
    from modules.mail_process.utilities.iacs.constants import ParsedCode
except ImportError:
    print("Error: IACS 모듈을 찾을 수 없습니다.")
    print("경로를 확인하거나 sys.path를 수정하세요.")
    sys.exit(1)


class TestCase:
    """테스트 케이스 클래스"""

    def __init__(
        self, input_text: str, expected: Dict[str, Any], description: str = ""
    ):
        self.input_text = input_text
        self.expected = expected
        self.description = description


def create_test_cases() -> List[TestCase]:
    """테스트 케이스 생성"""
    return [
        # 기본 의제 패턴
        TestCase(
            "PL25015: Equipment",
            {
                "document_type": "AGENDA",
                "panel": "PL",
                "year": "25",
                "number": "015",
                "full_code": "PL25015",
            },
            "기본 의제",
        ),
        TestCase(
            "PL25015a: Equipment with version",
            {
                "document_type": "AGENDA",
                "panel": "PL",
                "year": "25",
                "number": "015",
                "agenda_version": "a",
                "full_code": "PL25015a",
            },
            "버전이 있는 의제",
        ),
        # 응답 패턴 - 언더스코어
        TestCase(
            "PL25015_KRa: Response from KR",
            {
                "document_type": "RESPONSE",
                "panel": "PL",
                "year": "25",
                "number": "015",
                "organization": "KR",
                "response_version": "a",
                "full_code": "PL25015_KRa",
            },
            "언더스코어 응답",
        ),
        # 응답 패턴 - 붙어있는 형식
        TestCase(
            "PL25016aIRa: Response with agenda version",
            {
                "document_type": "RESPONSE",
                "panel": "PL",
                "year": "25",
                "number": "016",
                "agenda_version": "a",
                "organization": "IR",
                "response_version": "a",
                "full_code": "PL25016aIRa",
            },
            "의제 버전이 있는 응답",
        ),
        # JWG 패턴
        TestCase(
            "JWG-SDT25001: JWG agenda",
            {
                "document_type": "AGENDA",
                "panel": "JWG-SDT",
                "year": "25",
                "number": "001",
                "full_code": "JWG-SDT25001",
            },
            "JWG 의제",
        ),
        TestCase(
            "JWG-CS25001_BVa: JWG response",
            {
                "document_type": "RESPONSE",
                "panel": "JWG-CS",
                "year": "25",
                "number": "001",
                "organization": "BV",
                "response_version": "a",
                "full_code": "JWG-CS25001_BVa",
            },
            "JWG 응답",
        ),
        # 특수 케이스
        TestCase(
            "Multilateral discussion",
            {
                "document_type": "SPECIAL",
                "panel": "MULTILATERAL",
                "full_code": "Multilateral",
                "is_special": True,
            },
            "Multilateral 특수 케이스",
        ),
        # 복잡한 접두사가 있는 케이스
        TestCase(
            "RE: RE: PL25017_DNVb",
            {
                "document_type": "RESPONSE",
                "panel": "PL",
                "year": "25",
                "number": "017",
                "organization": "DNV",
                "response_version": "b",
                "full_code": "PL25017_DNVb",
            },
            "다중 RE: 접두사",
        ),
        TestCase(
            "Fw: [IACS SDTP] Fw: PL25015_ILa",
            {
                "document_type": "RESPONSE",
                "panel": "PL",
                "year": "25",
                "number": "015",
                "organization": "IL",
                "response_version": "a",
                "full_code": "PL25015_ILa",
            },
            "[IACS SDTP] 접두사 (유연한 패턴 테스트)",
        ),
        # 대소문자 혼용
        TestCase(
            "pl25018_kra",
            {
                "document_type": "RESPONSE",
                "panel": "PL",
                "year": "25",
                "number": "018",
                "organization": "KR",
                "response_version": "a",
                "full_code": "PL25018_KRa",
            },
            "소문자 입력",
        ),
        # 텍스트 중간에 있는 패턴 (유연한 패턴)
        TestCase(
            "Some random text with PL25019_NKc embedded in it",
            {
                "document_type": "RESPONSE",
                "panel": "PL",
                "year": "25",
                "number": "019",
                "organization": "NK",
                "response_version": "c",
                "full_code": "PL25019_NKc",
            },
            "텍스트 중간의 패턴",
        ),
        # 실패 케이스
        TestCase(
            "This is just random text without any pattern",
            {"parsing_failed": True},
            "패턴 없음 (실패 예상)",
        ),
        TestCase(
            "XX25001_KRa",  # 잘못된 패널 코드
            {"parsing_failed": True},
            "잘못된 패널 코드 (실패 예상)",
        ),
    ]


def test_parser():
    """파서 테스트 실행"""
    parser = IACSCodeParser()
    test_cases = create_test_cases()

    print("=" * 80)
    print(f"IACS 파서 테스트 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    for i, test_case in enumerate(test_cases, 1):
        print(f"테스트 {i}: {test_case.description}")
        print(f"입력: '{test_case.input_text}'")

        # 파싱 실행
        result = parser.parse_line(test_case.input_text)

        # 결과 검증
        if test_case.expected.get("parsing_failed"):
            if result is None:
                print("✓ 예상대로 파싱 실패")
                passed += 1
            else:
                print(f"✗ 파싱이 성공했지만 실패를 예상함")
                print(f"  결과: {result}")
                failed += 1
        else:
            if result is None:
                print(f"✗ 파싱 실패")
                # 디버깅을 위해 각 단계별로 테스트
                print(f"  디버깅:")
                # 특수 접두사 제거 후 테스트
                cleaned = parser._remove_prefixes(test_case.input_text)
                print(f"  - 접두사 제거 후: '{cleaned}'")
                # 유연한 패턴으로 직접 테스트
                found_patterns = parser.pattern_matcher.find_iacs_patterns(
                    test_case.input_text
                )
                if found_patterns:
                    print(f"  - 유연한 패턴으로 찾은 것: {found_patterns}")
                    # 찾은 패턴을 다시 파싱해보기
                    for pattern in found_patterns:
                        retry_result = parser.parse_line(pattern)
                        if retry_result:
                            print(
                                f"  - '{pattern}' 재파싱 성공: {retry_result.full_code}"
                            )
                else:
                    print(f"  - 유연한 패턴으로도 찾지 못함")
                failed += 1
            else:
                # 각 필드 검증
                all_match = True
                mismatches = []

                for key, expected_value in test_case.expected.items():
                    actual_value = getattr(result, key, None)
                    if actual_value != expected_value:
                        # parsing_method는 flexible_extraction_ 접두사가 붙을 수 있으므로 특별 처리
                        if (
                            key == "parsing_method"
                            and actual_value
                            and "flexible_extraction_" in actual_value
                        ):
                            continue  # 유연한 추출은 성공으로 간주
                        all_match = False
                        mismatches.append(
                            f"  {key}: 예상={expected_value}, 실제={actual_value}"
                        )

                if all_match:
                    print(f"✓ 성공")
                    print(f"  파싱 방법: {result.parsing_method}")
                    passed += 1
                else:
                    print(f"✗ 필드 불일치")
                    for mismatch in mismatches:
                        print(mismatch)
                    print(f"  전체 결과: {result}")
                    failed += 1

        print("-" * 40)
        print()

    # 요약
    print("=" * 80)
    print(f"테스트 완료: 총 {len(test_cases)}개")
    print(f"성공: {passed}개")
    print(f"실패: {failed}개")
    print(f"성공률: {(passed/len(test_cases)*100):.1f}%")
    print("=" * 80)

    # 추가 테스트: extract_all_patterns_from_mail
    print("\n추가 테스트: extract_all_patterns_from_mail()")
    print("=" * 80)

    test_mail = {
        "subject": "Fw: [IACS SDTP] Fw: PL25015_ILa: Important update",
        "body": {
            "content": "Please review PL25016a and respond. Also check PS25001_BVb for reference."
        },
        "receivedDateTime": "2025-01-16T10:30:00Z",
        "from": {"emailAddress": {"address": "john.doe@kr.org", "name": "John Doe"}},
    }

    result = parser.extract_all_patterns_from_mail(test_mail)

    print("메일 제목:", test_mail["subject"])
    print("\n추출된 정보:")

    if "iacs_code" in result:
        code = result["iacs_code"]
        print(f"- IACS 코드: {code.full_code}")
        print(f"- 문서 타입: {code.document_type}")
        print(f"- 파싱 방법: {code.parsing_method}")

    if "extracted_info" in result:
        info = result["extracted_info"]
        print("\n통일된 네이밍:")
        for key, value in info.items():
            if value:  # 값이 있는 것만 출력
                print(f"- {key}: {value}")

    if "additional_agenda_references" in result:
        refs = result["additional_agenda_references"]
        print(f"\n본문에서 찾은 추가 참조: {refs}")

    if "sender_address" in result:
        print(f"\n발신자: {result['sender_address']} ({result.get('sender_name', '')})")
        if "sender_type" in result.get("extracted_info", {}):
            print(f"발신자 타입: {result['extracted_info']['sender_type']}")
            print(
                f"발신자 조직: {result['extracted_info'].get('sender_organization', 'N/A')}"
            )


def interactive_test():
    """대화형 테스트 모드"""
    parser = IACSCodeParser()

    print("\n" + "=" * 80)
    print("대화형 테스트 모드")
    print("텍스트를 입력하면 파싱 결과를 보여줍니다.")
    print("종료하려면 'quit' 또는 'exit'를 입력하세요.")
    print("=" * 80)

    while True:
        try:
            text = input("\n입력> ").strip()

            if text.lower() in ["quit", "exit", "q"]:
                print("테스트를 종료합니다.")
                break

            if not text:
                continue

            # 파싱 실행
            result = parser.parse_line(text)

            if result:
                print(f"\n파싱 성공!")
                print(f"- Full Code: {result.full_code}")
                print(f"- Document Type: {result.document_type}")
                print(f"- Panel: {result.panel}")
                print(f"- Year: {result.year}")
                print(f"- Number: {result.number}")
                if result.agenda_version:
                    print(f"- Agenda Version: {result.agenda_version}")
                if result.organization:
                    print(f"- Organization: {result.organization}")
                if result.response_version:
                    print(f"- Response Version: {result.response_version}")
                print(f"- Parsing Method: {result.parsing_method}")
            else:
                print("\n파싱 실패 - 패턴을 찾을 수 없습니다.")

        except KeyboardInterrupt:
            print("\n\n테스트를 종료합니다.")
            break
        except Exception as e:
            print(f"\n오류 발생: {e}")


if __name__ == "__main__":
    # 기본 테스트 실행
    test_parser()

    # 대화형 테스트 실행 여부 확인
    response = input("\n대화형 테스트를 실행하시겠습니까? (y/N): ")
    if response.lower() in ["y", "yes"]:
        interactive_test()
