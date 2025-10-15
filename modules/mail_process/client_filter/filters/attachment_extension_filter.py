"""첨부파일 확장자 필터"""

from typing import List, Dict, Any, Optional
from pathlib import Path


class AttachmentExtensionFilter:
    """첨부파일 확장자 기반 필터"""

    @staticmethod
    def apply(emails: List[Dict[str, Any]], extensions: List[str]) -> List[Dict[str, Any]]:
        """
        첨부파일 확장자 필터링

        Args:
            emails: 메일 리스트
            extensions: 확장자 리스트 (예: ['.pdf', '.xlsx', '.docx'])

        Returns:
            필터링된 메일 리스트 (해당 확장자의 첨부파일이 있는 메일만)
        """
        if not extensions:
            return emails

        filtered = []
        extensions_lower = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in extensions]

        for email in emails:
            attachments = AttachmentExtensionFilter._get_attachments(email)
            if AttachmentExtensionFilter._has_matching_extension(attachments, extensions_lower):
                filtered.append(email)

        return filtered

    @staticmethod
    def _get_attachments(email: Dict[str, Any]) -> List[Dict[str, Any]]:
        """첨부파일 목록 추출"""
        # GraphMailItem 형식
        if hasattr(email, 'attachments'):
            return email.attachments or []

        # Dict 형식
        if isinstance(email, dict) and 'attachments' in email:
            return email['attachments'] or []

        return []

    @staticmethod
    def _has_matching_extension(attachments: List[Dict[str, Any]], extensions: List[str]) -> bool:
        """첨부파일 중 하나라도 해당 확장자인지 확인"""
        for attachment in attachments:
            filename = attachment.get('name', '')
            if filename:
                file_ext = Path(filename).suffix.lower()
                if file_ext in extensions:
                    return True
        return False
