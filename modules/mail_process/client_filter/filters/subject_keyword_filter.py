"""제목 키워드 필터"""

from typing import List, Dict, Any, Optional


class SubjectKeywordFilter:
    """제목 키워드 기반 필터 (포함/제외)"""

    @staticmethod
    def apply(
        emails: List[Dict[str, Any]],
        include_keywords: Optional[List[str]] = None,
        exclude_keywords: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        제목 키워드 필터링

        Args:
            emails: 메일 리스트
            include_keywords: 포함해야 하는 키워드 (OR 조건)
            exclude_keywords: 제외해야 하는 키워드 (하나라도 있으면 제외)

        Returns:
            필터링된 메일 리스트
        """
        filtered = emails

        # Include 필터 (OR 조건)
        if include_keywords:
            filtered = SubjectKeywordFilter._apply_include(filtered, include_keywords)

        # Exclude 필터
        if exclude_keywords:
            filtered = SubjectKeywordFilter._apply_exclude(filtered, exclude_keywords)

        return filtered

    @staticmethod
    def _apply_include(emails: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:
        """포함 키워드 필터"""
        keywords_lower = [k.lower() for k in keywords]
        filtered = []

        for email in emails:
            subject = SubjectKeywordFilter._get_subject(email).lower()
            if any(keyword in subject for keyword in keywords_lower):
                filtered.append(email)

        return filtered

    @staticmethod
    def _apply_exclude(emails: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:
        """제외 키워드 필터"""
        keywords_lower = [k.lower() for k in keywords]
        filtered = []

        for email in emails:
            subject = SubjectKeywordFilter._get_subject(email).lower()
            if not any(keyword in subject for keyword in keywords_lower):
                filtered.append(email)

        return filtered

    @staticmethod
    def _get_subject(email: Dict[str, Any]) -> str:
        """제목 추출"""
        # GraphMailItem 형식
        if hasattr(email, 'subject'):
            return str(email.subject) if email.subject else ''

        # Dict 형식
        if isinstance(email, dict) and 'subject' in email:
            return str(email['subject']) if email['subject'] else ''

        return ''
