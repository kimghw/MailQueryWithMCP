"""발신자 필터링 서비스"""

import os
from typing import Set
from infra.core.logger import get_logger


class MailProcessorFilterService:
    """발신자 필터링 서비스"""

    def __init__(self):
        self.logger = get_logger(__name__)

        # 환경변수에서 필터링 설정 로드
        self.filtering_enabled = (
            os.getenv("ENABLE_MAIL_FILTERING", "true").lower() == "true"
        )
        self.suspicious_check_enabled = (
            os.getenv("ENABLE_SUSPICIOUS_SENDER_CHECK", "true").lower() == "true"
        )

        # 차단할 도메인 목록 (환경변수에서 로드)
        blocked_domains_str = os.getenv(
            "BLOCKED_DOMAINS",
            "noreply.com,no-reply.com,donotreply.com,notifications.com,alerts.com,system.com,mailer-daemon.com,postmaster.com,bounce.com,newsletter.com,marketing.com,promo.com",
        )
        self.blocked_domains: Set[str] = {
            domain.strip().lower()
            for domain in blocked_domains_str.split(",")
            if domain.strip()
        }

        # 차단할 키워드 목록 (환경변수에서 로드)
        blocked_keywords_str = os.getenv(
            "BLOCKED_KEYWORDS",
            "newsletter,promotion,marketing,advertisement,unsubscribe,spam,bulk,mass,광고,홍보,마케팅,뉴스레터,구독취소,noreply,no-reply,donotreply,auto-reply",
        )
        self.blocked_keywords: Set[str] = {
            keyword.strip().lower()
            for keyword in blocked_keywords_str.split(",")
            if keyword.strip()
        }

        # 차단할 발신자 패턴 (환경변수에서 로드)
        blocked_patterns_str = os.getenv(
            "BLOCKED_SENDER_PATTERNS",
            "noreply@,no-reply@,donotreply@,auto-reply@,system@,daemon@,postmaster@,mailer@,newsletter@,marketing@,promo@,ads@",
        )
        self.blocked_sender_patterns: Set[str] = {
            pattern.strip().lower()
            for pattern in blocked_patterns_str.split(",")
            if pattern.strip()
        }

        self.logger.info(
            f"메일 필터링 서비스 초기화 완료 - 필터링 활성화: {self.filtering_enabled}"
        )
        self.logger.debug(
            f"차단 도메인 {len(self.blocked_domains)}개, 차단 키워드 {len(self.blocked_keywords)}개, 차단 패턴 {len(self.blocked_sender_patterns)}개 로드됨"
        )

    def should_process(self, sender_address: str, subject: str = "") -> bool:
        """
        메일 처리 여부 결정

        Args:
            sender_address: 발신자 이메일 주소
            subject: 메일 제목

        Returns:
            True: 처리해야 함, False: 필터링해야 함
        """
        # 필터링이 비활성화된 경우 모든 메일 처리
        if not self.filtering_enabled:
            self.logger.debug("메일 필터링이 비활성화되어 모든 메일 처리")
            return True

        if not sender_address:
            self.logger.debug("발신자 주소가 없어 필터링")
            return False

        sender_lower = sender_address.lower()
        subject_lower = subject.lower() if subject else ""

        # 1. 도메인 차단 확인
        domain = self._extract_domain(sender_lower)
        if domain in self.blocked_domains:
            self.logger.debug(f"차단된 도메인으로 필터링: {domain}")
            return False

        # 2. 발신자 패턴 차단 확인
        for pattern in self.blocked_sender_patterns:
            if sender_lower.startswith(pattern):
                self.logger.debug(f"차단된 발신자 패턴으로 필터링: {pattern}")
                return False

        # 3. 키워드 차단 확인 (발신자 주소)
        for keyword in self.blocked_keywords:
            if keyword in sender_lower:
                self.logger.debug(f"발신자 주소의 차단 키워드로 필터링: {keyword}")
                return False

        # 4. 키워드 차단 확인 (제목)
        for keyword in self.blocked_keywords:
            if keyword in subject_lower:
                self.logger.debug(f"제목의 차단 키워드로 필터링: {keyword}")
                return False

        # 5. 특수 문자 패턴 확인 (스팸 메일 특징) - 설정에 따라 활성화
        if self.suspicious_check_enabled and self._is_suspicious_sender(sender_lower):
            self.logger.debug(f"의심스러운 발신자로 필터링: {sender_address}")
            return False

        return True

    def _extract_domain(self, email: str) -> str:
        """이메일에서 도메인 추출"""
        if "@" in email:
            return email.split("@")[1]
        return ""

    def _is_suspicious_sender(self, sender: str) -> bool:
        """의심스러운 발신자 패턴 확인"""
        # 과도한 숫자나 특수문자가 포함된 발신자
        import re

        # 숫자가 50% 이상인 경우
        digits = len(re.findall(r"\d", sender))
        if len(sender) > 0 and digits / len(sender) > 0.5:
            return True

        # 연속된 특수문자가 많은 경우
        special_chars = len(re.findall(r"[._-]{3,}", sender))
        if special_chars > 0:
            return True

        # 랜덤한 문자열 패턴 (예: abc123def456@domain.com)
        random_pattern = re.findall(r"[a-z]+\d+[a-z]+\d+", sender)
        if random_pattern:
            return True

        return False

    def add_blocked_domain(self, domain: str) -> None:
        """차단 도메인 추가"""
        self.blocked_domains.add(domain.lower())
        self.logger.info(f"차단 도메인 추가: {domain}")

    def remove_blocked_domain(self, domain: str) -> None:
        """차단 도메인 제거"""
        self.blocked_domains.discard(domain.lower())
        self.logger.info(f"차단 도메인 제거: {domain}")

    def add_blocked_keyword(self, keyword: str) -> None:
        """차단 키워드 추가"""
        self.blocked_keywords.add(keyword.lower())
        self.logger.info(f"차단 키워드 추가: {keyword}")

    def remove_blocked_keyword(self, keyword: str) -> None:
        """차단 키워드 제거"""
        self.blocked_keywords.discard(keyword.lower())
        self.logger.info(f"차단 키워드 제거: {keyword}")

    def get_filter_stats(self) -> dict:
        """필터링 통계 반환"""
        return {
            "blocked_domains_count": len(self.blocked_domains),
            "blocked_keywords_count": len(self.blocked_keywords),
            "blocked_patterns_count": len(self.blocked_sender_patterns),
            "blocked_domains": list(self.blocked_domains),
            "blocked_keywords": list(self.blocked_keywords),
        }
