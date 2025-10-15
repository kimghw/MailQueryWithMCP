"""읽음 상태 필터"""

from typing import List, Dict, Any, Optional


class ReadStatusFilter:
    """읽음 상태 기반 필터"""

    @staticmethod
    def apply(emails: List[Dict[str, Any]], is_read: Optional[bool]) -> List[Dict[str, Any]]:
        """
        읽음 상태 필터링

        Args:
            emails: 메일 리스트
            is_read:
                - True: 읽은 메일만
                - False: 안 읽은 메일만
                - None: 필터링 안함

        Returns:
            필터링된 메일 리스트
        """
        if is_read is None:
            return emails

        filtered = []

        for email in emails:
            email_is_read = ReadStatusFilter._get_read_status(email)

            if email_is_read == is_read:
                filtered.append(email)

        return filtered

    @staticmethod
    def _get_read_status(email: Dict[str, Any]) -> bool:
        """읽음 상태 확인"""
        # GraphMailItem 형식
        if hasattr(email, 'is_read'):
            return bool(email.is_read)

        # Dict 형식
        if isinstance(email, dict):
            if 'is_read' in email:
                return bool(email['is_read'])
            if 'isRead' in email:
                return bool(email['isRead'])

        return False  # 기본값: 안 읽음
