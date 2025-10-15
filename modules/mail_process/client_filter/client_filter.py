"""
Client-side Email Filter
메일 선별 메인 클래스
"""

import logging
from typing import List, Dict, Any

from .filter_criteria import FilterCriteria
from .filters import (
    SenderFilter,
    RecipientFilter,
    DateFilter,
    AttachmentFilter,
    KeywordFilter,
)

logger = logging.getLogger(__name__)


class ClientFilter:
    """
    클라이언트 사이드 메일 필터

    Phase 1 필터 적용 순서:
    1. Sender (발신자)
    2. Recipients (수신자)
    3. Date (날짜 범위)
    4. Attachments (첨부파일 유무)
    5. Keywords (키워드)
    """

    def __init__(self, criteria: FilterCriteria):
        """
        Args:
            criteria: 필터링 조건
        """
        self.criteria = criteria

    def apply(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        필터 적용

        Args:
            emails: 필터링할 메일 리스트

        Returns:
            필터링된 메일 리스트
        """
        if not self.criteria.has_any_filter():
            logger.info("No filter criteria set, returning all emails")
            return emails

        original_count = len(emails)
        filtered = emails

        # Phase 1 필터 순차 적용
        filtered = self._apply_phase1_filters(filtered)

        # TODO: Phase 2 필터 (추후 구현)
        # filtered = self._apply_phase2_filters(filtered)

        filtered_count = len(filtered)
        removed_count = original_count - filtered_count

        logger.info(
            f"Filter applied: {self.criteria} | "
            f"Original: {original_count}, Filtered: {filtered_count}, Removed: {removed_count}"
        )

        return filtered

    def _apply_phase1_filters(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Phase 1 필터 적용"""
        filtered = emails

        # 1. Sender 필터
        if self.criteria.sender:
            before = len(filtered)
            filtered = SenderFilter.apply(filtered, self.criteria.sender)
            logger.debug(f"Sender filter: {before} → {len(filtered)}")

        # 2. Recipients 필터
        if self.criteria.recipients:
            before = len(filtered)
            filtered = RecipientFilter.apply(filtered, self.criteria.recipients)
            logger.debug(f"Recipients filter: {before} → {len(filtered)}")

        # 3. Date 필터
        if self.criteria.date_from or self.criteria.date_to:
            before = len(filtered)
            filtered = DateFilter.apply(
                filtered,
                self.criteria.date_from,
                self.criteria.date_to
            )
            logger.debug(f"Date filter: {before} → {len(filtered)}")

        # 4. Attachment 필터
        if self.criteria.has_attachments is not None:
            before = len(filtered)
            filtered = AttachmentFilter.apply(filtered, self.criteria.has_attachments)
            logger.debug(f"Attachment filter: {before} → {len(filtered)}")

        # 5. Keyword 필터
        if self.criteria.keywords:
            before = len(filtered)
            filtered = KeywordFilter.apply(filtered, self.criteria.keywords)
            logger.debug(f"Keyword filter: {before} → {len(filtered)}")

        return filtered

    def get_filter_summary(self) -> Dict[str, Any]:
        """필터 설정 요약"""
        return {
            'criteria': str(self.criteria),
            'active_filters': self.criteria.get_active_filters(),
            'has_filters': self.criteria.has_any_filter(),
        }
