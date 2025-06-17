"""발신자 필터링 유틸리티"""

import os
from typing import Set
from infra.core.logger import get_logger


class MailFilter:
    """발신자 필터링 유틸리티 - 순수 함수 기반"""

    def __init__(self):
        self.logger = get_logger(__name__)

        # 환경변수에서 필터링 설정 로드
        self.filtering_enabled = (
            os.getenv("ENABLE_MAIL_FILTERING", "true").lower() == "true"
        )

        # 차단할 도메인 목록
        blocked_domains_str = os.getenv(
            "BLOCKED_DOMAINS",
            "noreply.com,no-reply.com,donotreply.com,notifications.com,alerts.com,system.com,mailer-daemon.com,postmaster.com,bounce.com,newsletter.com,marketing.com,promo.com",
        )
        self.blocked_domains: Set[str] = {
            domain.strip().lower()
            for domain in blocked_domains_str.split(",")
            if domain.strip()
        }

        # 차단할 키워드 목록
        blocked_keywords_str = os.getenv(
            "BLOCKED_KEYWORDS",
            "newsletter,promotion,marketing,advertisement,unsubscribe,spam,bulk,mass,광고,홍보,마케팅,뉴스레터,구독취소,noreply,no-reply,donotreply,auto-reply",
        )
        self.blocked_keywords: Set[str] = {
            keyword.strip().lower()
            for keyword in blocked_keywords_str.split(",")
            if keyword.strip()
        }

        # 차단할 발신자 패턴
        blocked_patterns_str = os.getenv(
            "BLOCKED_SENDER_PATTERNS",
            "noreply@,no-reply@,donotreply@,auto-reply@,system@,daemon@,postmaster@,mailer@,newsletter@,marketing@,promo@,ads@",
        )
        self.blocked_sender_patterns: Set[str] = {
            pattern.strip().lower()
            for pattern in blocked_patterns_str.split(",")
            if pattern.strip()
        }

        self.logger.info(f"메일 필터 초기화 - 필터링 활성화: {self.filtering_enabled}")

    def should_process(self, sender_address: str, subject: str = "") -> bool:
        """
        메일 처리 여부 결정 (순수 함수)
        
        Args:
            sender_address: 발신자 이메일 주소
            subject: 메일 제목
            
        Returns:
            True: 처리해야 함, False: 필터링해야 함
        """
        # 필터링이 비활성화된 경우 모든 메일 처리
        if not self.filtering_enabled:
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

        return True

    def _extract_domain(self, email: str) -> str:
        """이메일에서 도메인 추출"""
        if "@" in email:
            return email.split("@")[1]
        return ""

    def get_filter_stats(self) -> dict:
        """필터링 통계 반환"""
        return {
            "filtering_enabled": self.filtering_enabled,
            "blocked_domains_count": len(self.blocked_domains),
            "blocked_keywords_count": len(self.blocked_keywords),
            "blocked_patterns_count": len(self.blocked_sender_patterns),
        }

