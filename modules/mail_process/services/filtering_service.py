"""필터링 서비스 - Pydantic 모델 배치 처리"""

import os
from typing import Dict, List, Set, Tuple

from infra.core.logger import get_logger
from ..mail_processor_schema import GraphMailItem


class FilteringService:
    """메일 필터링 서비스 - Pydantic 모델 배치 처리"""

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

        # 통계 초기화
        self._stats = {
            "total_checked": 0,
            "filtered_out": 0,
            "passed": 0,
            "filtered_by_domain": 0,
            "filtered_by_pattern": 0,
            "filtered_by_keyword": 0,
            "filtered_by_no_sender": 0,
        }

        self.logger.info(
            f"메일 필터링 서비스 초기화 - 필터링 활성화: {self.filtering_enabled}"
        )
        self.logger.debug(
            f"차단 도메인: {len(self.blocked_domains)}개, "
            f"차단 키워드: {len(self.blocked_keywords)}개, "
            f"차단 패턴: {len(self.blocked_sender_patterns)}개"
        )

    def is_enabled(self) -> bool:
        """필터링 활성화 여부 반환"""
        return self.filtering_enabled

    async def filter_mail_single(self, mail_item: GraphMailItem) -> Dict[str, any]:
        """
        단일 Pydantic 모델 필터링 (기존 호환성 유지)

        Args:
            mail_item: GraphMailItem

        Returns:
            {"filtered": bool, "reason": str or None}
        """
        if not self.filtering_enabled:
            return {"filtered": False, "reason": None}

        # 발신자 주소 추출
        sender_address = self._extract_sender_address(mail_item)
        subject = mail_item.subject or ""

        # 필터링 체크
        should_process, reason = self._should_process_mail(sender_address, subject)

        if not should_process:
            self._stats["total_checked"] += 1
            self._stats["filtered_out"] += 1
            self._update_filter_stats(reason)

            return {"filtered": True, "reason": reason}

        self._stats["total_checked"] += 1
        self._stats["passed"] += 1

        return {"filtered": False, "reason": None}

    # 기존 호환성을 위한 메서드 (deprecated)
    async def filter_mail(self, mail_data: Dict) -> Dict[str, any]:
        """
        기존 딕셔너리 방식 필터링 (호환성 유지용)

        Args:
            mail_data: {"mail": 메일 딕셔너리, "cleaned_content": 정제된 내용}

        Returns:
            {"filtered": bool, "reason": str or None}
        """
        self.logger.warning(
            "filter_mail 메서드는 deprecated입니다. filter_mail_single 또는 filter_mail_batch를 사용하세요."
        )

        if not self.filtering_enabled:
            return {"filtered": False, "reason": None}

        mail = mail_data.get("mail", {})

        try:
            # 딕셔너리를 GraphMailItem으로 변환
            mail_item = GraphMailItem(**mail)
            return await self.filter_mail_single(mail_item)
        except Exception as e:
            self.logger.error(f"메일 데이터 변환 실패: {str(e)}")
            return {"filtered": True, "reason": "invalid_data"}

    def _extract_sender_address(self, mail_item: GraphMailItem) -> str:
        """Pydantic 모델에서 발신자 주소 추출"""
        if mail_item.from_address and isinstance(mail_item.from_address, dict):
            email_address = mail_item.from_address.get("emailAddress", {})
            if isinstance(email_address, dict):
                return email_address.get("address", "")

        # sender 필드도 확인
        if mail_item.sender and isinstance(mail_item.sender, dict):
            email_address = mail_item.sender.get("emailAddress", {})
            if isinstance(email_address, dict):
                return email_address.get("address", "")

        return ""

    def _should_process_mail(
        self, sender_address: str, subject: str = ""
    ) -> Tuple[bool, str]:
        """
        메일 처리 여부 결정

        Args:
            sender_address: 발신자 이메일 주소
            subject: 메일 제목

        Returns:
            (처리 여부, 필터링 이유)
        """
        if not sender_address:
            return False, "no_sender"

        sender_lower = sender_address.lower()
        subject_lower = subject.lower() if subject else ""

        # 1. 도메인 차단 확인
        domain = self._extract_domain(sender_lower)
        if domain in self.blocked_domains:
            return False, f"blocked_domain:{domain}"

        # 2. 발신자 패턴 차단 확인
        for pattern in self.blocked_sender_patterns:
            if sender_lower.startswith(pattern):
                return False, f"blocked_pattern:{pattern}"

        # 3. 키워드 차단 확인 (발신자 주소)
        for keyword in self.blocked_keywords:
            if keyword in sender_lower:
                return False, f"blocked_keyword_sender:{keyword}"

        # 4. 키워드 차단 확인 (제목)
        for keyword in self.blocked_keywords:
            if keyword in subject_lower:
                return False, f"blocked_keyword_subject:{keyword}"

        return True, "passed"

    def _extract_domain(self, email: str) -> str:
        """이메일에서 도메인 추출"""
        if "@" in email:
            return email.split("@")[1]
        return ""

    def _update_filter_stats(self, reason: str):
        """필터링 통계 업데이트"""
        if reason.startswith("blocked_domain"):
            self._stats["filtered_by_domain"] += 1
        elif reason.startswith("blocked_pattern"):
            self._stats["filtered_by_pattern"] += 1
        elif reason.startswith("blocked_keyword"):
            self._stats["filtered_by_keyword"] += 1
        elif reason == "no_sender":
            self._stats["filtered_by_no_sender"] += 1

    def get_filter_stats(self) -> Dict:
        """필터링 통계 반환"""
        return {
            "filtering_enabled": self.filtering_enabled,
            "blocked_domains_count": len(self.blocked_domains),
            "blocked_keywords_count": len(self.blocked_keywords),
            "blocked_patterns_count": len(self.blocked_sender_patterns),
            "statistics": self._stats.copy(),
        }

    def reset_stats(self):
        """통계 초기화"""
        for key in self._stats:
            self._stats[key] = 0
        self.logger.debug("필터링 통계 초기화됨")
