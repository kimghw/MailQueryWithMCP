"""중요도 필터"""

from typing import List, Dict, Any, Optional


class ImportanceFilter:
    """중요도 기반 필터"""

    @staticmethod
    def apply(emails: List[Dict[str, Any]], importance: Optional[str]) -> List[Dict[str, Any]]:
        """
        중요도 필터링

        Args:
            emails: 메일 리스트
            importance: 'low', 'normal', 'high' 중 하나 (None이면 필터링 안함)

        Returns:
            필터링된 메일 리스트
        """
        if not importance:
            return emails

        importance = importance.lower()
        filtered = []

        for email in emails:
            email_importance = ImportanceFilter._get_importance(email)

            if email_importance == importance:
                filtered.append(email)

        return filtered

    @staticmethod
    def _get_importance(email: Dict[str, Any]) -> str:
        """중요도 추출"""
        # GraphMailItem 형식
        if hasattr(email, 'importance'):
            return str(email.importance).lower() if email.importance else 'normal'

        # Dict 형식
        if isinstance(email, dict) and 'importance' in email:
            return str(email['importance']).lower() if email['importance'] else 'normal'

        return 'normal'  # 기본값
