"""
IACS 코드 파서 - 메인 모듈
modules/mail_process/utilities/iacs/iacs_code_parser.py
"""

from typing import Dict, List, Optional, Any, Tuple

from infra.core.logger import get_logger
from .constants import (
    ParsedCode,
    SPECIAL_CASES,
    SPECIAL_PREFIXES,
    MAX_LINE_LENGTH,
    validate_parsed_code,
    get_statistics,
)
from .pattern_matcher import PatternMatcher
from .data_extractor import DataExtractor
from .common import convert_to_unified_naming, extract_base_agenda_no


class IACSCodeParser:
    """IACS 문서 코드 파서 - 통합 모듈"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.pattern_matcher = PatternMatcher()
        self.data_extractor = DataExtractor()

    def parse_line(self, line: str) -> Optional[ParsedCode]:
        """한 줄을 파싱하여 코드 정보 추출"""
        try:
            line = line.strip()
            if not line:
                return None

            # 길이 제한 체크
            if len(line) > MAX_LINE_LENGTH:
                self.logger.warning(f"너무 긴 라인 무시: {line[:50]}...")
                return None

            # 특수 케이스 먼저 체크
            for special in SPECIAL_CASES:
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
            result = self.pattern_matcher.parse_basic_patterns(
                cleaned_line, case_sensitive=True
            )
            if result:
                return result

            # 2단계: JWG 패턴 검색 (대소문자 구분)
            result = self.pattern_matcher.parse_jwg_patterns(
                cleaned_line, case_sensitive=True
            )
            if result:
                return result

            # 3단계: 대소문자 구분 없이 재검색
            result = self.pattern_matcher.parse_basic_patterns(
                cleaned_line, case_sensitive=False
            )
            if result:
                return result

            # 4단계: JWG 패턴 대소문자 구분 없이 재검색
            result = self.pattern_matcher.parse_jwg_patterns(
                cleaned_line, case_sensitive=False
            )
            if result:
                return result

            return None

        except Exception as e:
            self.logger.error(f"파싱 중 예외 발생: {str(e)}, 라인: {line[:100]}")
            return None

    def extract_all_patterns(
        self, subject: str, body: str, mail: Dict = None
    ) -> Dict[str, Any]:
        """제목과 본문에서 모든 패턴 추출 - 통일된 네이밍 적용"""
        result = {}

        # 1. 제목에서 IACS 코드 파싱
        parsed_code = self.parse_line(subject)
        if parsed_code:
            result["iacs_code"] = parsed_code
            result["extracted_info"] = convert_to_unified_naming(parsed_code)

            # 조직 정보 추출
            if parsed_code.organization:
                result["response_org"] = parsed_code.organization
                if parsed_code.response_version:
                    result["response_version"] = parsed_code.response_version

            self.logger.debug(
                f"파싱 성공: {parsed_code.full_code} "
                f"(방법: {parsed_code.parsing_method})"
            )
        else:
            # 본문 첫 줄에서도 시도
            self._try_parse_from_body(body, result)

        # 2. 회신 체인 분석
        reply_info = self.data_extractor.analyze_reply_chain(subject)
        if reply_info:
            result.update(reply_info)

        # 3. 긴급도 추출
        result["urgency"] = self.data_extractor.extract_urgency(subject, body)

        # 4. 본문에서 추가 아젠다 참조 추출
        additional_refs = self.data_extractor.extract_agenda_patterns(body)
        if additional_refs:
            result["additional_agenda_references"] = additional_refs

        # 5. 메일 정보가 제공된 경우 추가 정보 추출
        if mail:
            self._extract_mail_info(mail, result)

        return result

    def _try_parse_from_body(self, body: str, result: Dict):
        """본문에서 IACS 코드 파싱 시도"""
        body_lines = body.split("\n")
        for line in body_lines[:5]:  # 처음 5줄만 확인
            line = line.strip()
            if line:
                parsed_code = self.parse_line(line)
                if parsed_code:
                    result["iacs_code"] = parsed_code
                    result["extracted_info"] = convert_to_unified_naming(parsed_code)

                    if parsed_code.organization:
                        result["response_org"] = parsed_code.organization
                        if parsed_code.response_version:
                            result["response_version"] = parsed_code.response_version

                    self.logger.debug(f"본문에서 파싱 성공: {parsed_code.full_code}")
                    break

    def _extract_mail_info(self, mail: Dict, result: Dict):
        """메일 정보 추출"""
        # 발신자 정보 추출
        sender_address, sender_name, sender_type, sender_organization = (
            self.data_extractor.extract_sender_info(mail)
        )

        if sender_address:
            result["sender_address"] = sender_address
            result["sender_name"] = sender_name
            if sender_type:
                result["sender_type"] = sender_type
            if sender_organization:
                result["sender_organization"] = sender_organization
                self.logger.debug(
                    f"이메일에서 발신자 조직 추출: {sender_organization} "
                    f"(from: {sender_address})"
                )

        # 발송 시간 추출
        sent_time = self.data_extractor.extract_sent_time(mail)
        if sent_time:
            result["sent_time"] = sent_time

        # 정제된 내용 추출
        clean_content = self.data_extractor.extract_clean_content(mail)
        if clean_content:
            result["clean_content"] = clean_content

    def _remove_prefixes(self, line: str) -> str:
        """특수 접두사 제거"""
        cleaned_line = line
        changed = True
        max_iterations = 5  # 무한 루프 방지
        iterations = 0

        while changed and iterations < max_iterations:
            changed = False
            iterations += 1
            for prefix in SPECIAL_PREFIXES:
                if cleaned_line.upper().startswith(prefix.upper()):
                    cleaned_line = cleaned_line[len(prefix) :].strip()
                    changed = True
                    break

        return cleaned_line

    def extract_base_agenda_no(self, parsed_code: ParsedCode) -> Optional[str]:
        """기본 아젠다 번호 추출"""
        return extract_base_agenda_no(parsed_code)

    # 위임 메서드들
    def set_chair_emails(self, emails: List[str]):
        """Chair 이메일 주소 설정"""
        self.data_extractor.set_chair_emails(emails)

    def set_member_emails(self, organization: str, emails: List[str]):
        """특정 조직의 멤버 이메일 주소 설정"""
        self.data_extractor.set_member_emails(organization, emails)

    def extract_organization_from_email(self, email_address: str) -> Optional[str]:
        """이메일 도메인에서 조직 코드 추출"""
        return self.data_extractor.extract_organization_from_email(email_address)

    def extract_sender_info(
        self, mail: Dict
    ) -> Tuple[str, str, Optional[str], Optional[str]]:
        """발신자 정보 추출"""
        return self.data_extractor.extract_sender_info(mail)

    def extract_sent_time(self, mail: Dict) -> Optional[datetime]:
        """발송 시간 추출"""
        return self.data_extractor.extract_sent_time(mail)

    def extract_clean_content(self, mail: Dict) -> str:
        """메일에서 정제된 내용 추출"""
        return self.data_extractor.extract_clean_content(mail)

    def clean_content(self, text: str) -> str:
        """텍스트 정제"""
        return self.data_extractor.clean_content(text)

    def analyze_reply_chain(self, subject: str) -> Dict[str, Any]:
        """회신 체인 분석"""
        return self.data_extractor.analyze_reply_chain(subject)

    def extract_urgency(self, subject: str, text: str) -> str:
        """긴급도 추출"""
        return self.data_extractor.extract_urgency(subject, text)

    def extract_agenda_patterns(self, text: str) -> List[str]:
        """본문에서 추가 아젠다 참조 추출"""
        return self.data_extractor.extract_agenda_patterns(text)

    def validate_parsed_code(self, parsed_code: ParsedCode) -> List[str]:
        """파싱된 코드의 유효성 검증"""
        return validate_parsed_code(parsed_code)

    def get_statistics(self, parsed_codes: List[ParsedCode]) -> Dict[str, Any]:
        """파싱된 코드들의 통계 정보 생성"""
        return get_statistics(parsed_codes)
