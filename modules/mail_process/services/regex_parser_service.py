"""정규식 기반 패턴 추출 서비스 - 본문에서 추가 정보 추출

modules/mail_process/services/regex_parser_service.py
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from infra.core.logger import get_logger


class RegexParserService:
    """정규식으로 메일 본문에서 패턴 기반 정보 추출"""

    def __init__(self):
        self.logger = get_logger(__name__)

        # 도메인-조직 매핑 (email_dashboard의 ORGANIZATIONS와 동기화)
        self.domain_to_org = {
            "kr.org": "KR",
            "krs.co.kr": "KR",
            "lr.org": "LR",
            "dnv.com": "DNV",
            "dnvgl.com": "DNV",
            "classnk.or.jp": "NK",
            "classnk.com": "NK",
            "eagle.org": "ABS",
            "abs-group.com": "ABS",
            "bureauveritas.com": "BV",
            "veristar.com": "BV",
            "ccs.org.cn": "CCS",
            "rina.org": "RINA",
            "prs.pl": "PRS",
            "iscsmaritime.com": "IL",
            "iacs.org.uk": "IL",
            "tasneef.ae": "TL",
            "turkloydu.org": "TL",
            "crs.hr": "CRS",
            "irclass.org": "IRS",
        }

        # 마감일 관련 키워드
        self.deadline_keywords = [
            "deadline",
            "due",
            "by",
            "까지",
            "마감",
            "기한",
            "期限",
            "until",
            "before",
            "no later than",
            "응답 요청",
        ]

        # 시간 표현 패턴
        self.time_expressions = {
            "COB": "17:00:00",  # Close of Business
            "EOD": "23:59:59",  # End of Day
            "noon": "12:00:00",
            "midnight": "23:59:59",
        }

    def extract_pattern_based_info(
        self, subject: str, text: str, sender_address: str
    ) -> Dict[str, Any]:
        """
        정규식으로 추출 가능한 패턴 정보 추출

        Args:
            subject: 메일 제목
            text: 메일 본문
            sender_address: 발신자 이메일 주소

        Returns:
            추출된 정보 딕셔너리
        """
        result = {}

        try:
            # 1. 발신 조직 추출 (이메일 도메인 기반)
            sender_org = self._extract_sender_organization(sender_address)
            if sender_org:
                result["sender_organization"] = sender_org

            # 2. 날짜/시간 정보 추출
            combined_text = f"{subject}\n{text}"
            deadline_info = self._extract_deadline_info(combined_text)
            if deadline_info:
                result.update(deadline_info)

            # 3. 추가 아젠다 패턴 추출 (본문에서)
            agenda_patterns = self._extract_agenda_patterns(combined_text)
            if agenda_patterns:
                result["additional_agenda_references"] = agenda_patterns

            # 4. 회신 체인 분석
            reply_info = self._analyze_reply_chain(subject)
            if reply_info:
                result.update(reply_info)

            # 5. 긴급도 추출
            urgency = self._extract_urgency(subject, text)
            if urgency:
                result["urgency"] = urgency

        except Exception as e:
            self.logger.error(f"정규식 패턴 추출 중 오류: {str(e)}")

        return result

    def _extract_sender_organization(self, sender_address: str) -> Optional[str]:
        """이메일 주소에서 발신 조직 추출"""
        if not sender_address or "@" not in sender_address:
            return None

        domain = sender_address.split("@")[1].lower()

        # 직접 매핑 확인
        for domain_pattern, org in self.domain_to_org.items():
            if domain_pattern in domain or domain in domain_pattern:
                self.logger.debug(f"도메인 {domain}에서 조직 {org} 추출")
                return org

        # 조직 코드가 도메인에 포함된 경우 (예: kr-marine.com)
        for org in [
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
        ]:
            if org.lower() in domain:
                self.logger.debug(f"도메인 {domain}에서 조직 코드 {org} 발견")
                return org

        return None

    def _extract_deadline_info(self, text: str) -> Dict[str, Any]:
        """마감일 정보 추출"""
        result = {}

        # 마감일 키워드 근처에서 날짜 찾기
        for keyword in self.deadline_keywords:
            pattern = rf"{keyword}[:\s]*([^\n.]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                context = match.group(1)

                # 날짜 추출
                date_info = self._extract_date_from_text(context)
                if date_info:
                    result["deadline_date"] = date_info

                # 시간 추출
                time_info = self._extract_time_from_text(context)
                if time_info:
                    result["deadline_time"] = time_info
                else:
                    # 기본 시간 설정
                    result["deadline_time"] = "23:59:59"

                if result:
                    result["has_deadline"] = True
                    break

        return result

    def _extract_date_from_text(self, text: str) -> Optional[str]:
        """텍스트에서 날짜 추출"""
        # 다양한 날짜 패턴
        date_patterns = [
            # YYYY-MM-DD, YYYY/MM/DD
            (
                r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})",
                lambda m: f"{m[1]}-{m[2]:0>2}-{m[3]:0>2}",
            ),
            # DD-MM-YYYY, DD/MM/YYYY
            (
                r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})",
                lambda m: f"{m[3]}-{m[2]:0>2}-{m[1]:0>2}",
            ),
            # YYYY년 MM월 DD일
            (
                r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일",
                lambda m: f"{m[1]}-{m[2]:0>2}-{m[3]:0>2}",
            ),
            # MM월 DD일 (현재 연도 사용)
            (
                r"(\d{1,2})월\s*(\d{1,2})일",
                lambda m: f"{datetime.now().year}-{m[1]:0>2}-{m[2]:0>2}",
            ),
            # January 15, 2024 형식
            (
                r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s*(\d{4})",
                self._parse_month_name_date,
            ),
            # 15 January 2024 형식
            (
                r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})",
                self._parse_day_month_year,
            ),
        ]

        for pattern, formatter in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return formatter(match.groups())
                except:
                    continue

        return None

    def _extract_time_from_text(self, text: str) -> Optional[str]:
        """텍스트에서 시간 추출"""
        # 시간 패턴
        time_patterns = [
            # HH:MM:SS
            r"(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\s*([AP]M))?",
            # HH시 MM분
            r"(\d{1,2})시\s*(\d{2})?분?",
            # COB, EOD 등
            r"\b(COB|EOD|noon|midnight)\b",
        ]

        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()

                # COB, EOD 등 특수 표현
                if groups[0] in self.time_expressions:
                    return self.time_expressions[groups[0]]

                # 일반 시간 형식
                try:
                    hour = int(groups[0])
                    minute = int(groups[1]) if groups[1] else 0
                    second = int(groups[2]) if len(groups) > 2 and groups[2] else 0

                    # AM/PM 처리
                    if len(groups) > 3 and groups[3]:
                        if groups[3].upper() == "PM" and hour < 12:
                            hour += 12
                        elif groups[3].upper() == "AM" and hour == 12:
                            hour = 0

                    return f"{hour:02d}:{minute:02d}:{second:02d}"
                except:
                    continue

        return None

    def _extract_agenda_patterns(self, text: str) -> List[str]:
        """본문에서 추가 아젠다 참조 추출"""
        patterns = []

        # IACS 아젠다 패턴
        agenda_pattern = (
            r"\b(PL|PS|JWG-SDT|JWG-CS)\d{2}\d{3,4}[a-z]?(?:_[A-Z]{2,3}[a-z]?)?\b"
        )
        matches = re.findall(agenda_pattern, text)

        for match in matches:
            if match not in patterns:
                patterns.append(match)

        return patterns

    def _analyze_reply_chain(self, subject: str) -> Dict[str, Any]:
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

    def _extract_urgency(self, subject: str, text: str) -> Optional[str]:
        """긴급도 추출"""
        combined = f"{subject} {text}".lower()

        if any(
            word in combined
            for word in ["urgent", "긴급", "asap", "immediately", "critical"]
        ):
            return "HIGH"
        elif any(word in combined for word in ["important", "중요", "priority"]):
            return "MEDIUM"
        else:
            return "NORMAL"

    def _parse_month_name_date(self, groups: tuple) -> str:
        """월 이름 형식 날짜 파싱"""
        months = {
            "january": "01",
            "february": "02",
            "march": "03",
            "april": "04",
            "may": "05",
            "june": "06",
            "july": "07",
            "august": "08",
            "september": "09",
            "october": "10",
            "november": "11",
            "december": "12",
        }
        month_name, day, year = groups
        month = months.get(month_name.lower(), "01")
        return f"{year}-{month}-{int(day):02d}"

    def _parse_day_month_year(self, groups: tuple) -> str:
        """일-월-년 형식 날짜 파싱"""
        months = {
            "january": "01",
            "february": "02",
            "march": "03",
            "april": "04",
            "may": "05",
            "june": "06",
            "july": "07",
            "august": "08",
            "september": "09",
            "october": "10",
            "november": "11",
            "december": "12",
        }
        day, month_name, year = groups
        month = months.get(month_name.lower(), "01")
        return f"{year}-{month}-{int(day):02d}"
