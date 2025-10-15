"""첨부파일 필터"""

from typing import List, Dict, Any, Optional


class AttachmentFilter:
    """첨부파일 유무 기반 필터"""

    @staticmethod
    def apply(emails: List[Dict[str, Any]], has_attachments: Optional[bool]) -> List[Dict[str, Any]]:
        """
        첨부파일 유무 필터링

        Args:
            emails: 메일 리스트
            has_attachments:
                - True: 첨부파일이 있는 메일만
                - False: 첨부파일이 없는 메일만
                - None: 필터링 안함

        Returns:
            필터링된 메일 리스트
        """
        if has_attachments is None:
            return emails

        filtered = []

        for email in emails:
            email_has_attachments = AttachmentFilter._has_attachments(email)

            if email_has_attachments == has_attachments:
                filtered.append(email)

        return filtered

    @staticmethod
    def _has_attachments(email: Dict[str, Any]) -> bool:
        """첨부파일 유무 확인"""
        # GraphMailItem 형식
        if hasattr(email, 'has_attachments'):
            return bool(email.has_attachments)

        # Dict 형식
        if isinstance(email, dict):
            if 'has_attachments' in email:
                return bool(email['has_attachments'])
            if 'hasAttachments' in email:
                return bool(email['hasAttachments'])

            # attachments 배열 직접 확인
            if 'attachments' in email:
                attachments = email['attachments']
                return bool(attachments) and len(attachments) > 0

        return False
