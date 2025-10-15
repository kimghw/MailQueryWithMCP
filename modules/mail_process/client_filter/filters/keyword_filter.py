"""키워드 필터"""

from typing import List, Dict, Any


class KeywordFilter:
    """키워드 기반 필터 (제목 + 본문)"""

    @staticmethod
    def apply(emails: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:
        """
        키워드 필터링 (OR 조건)

        Args:
            emails: 메일 리스트
            keywords: 키워드 리스트 (하나라도 포함되면 매칭)

        Returns:
            필터링된 메일 리스트
        """
        if not keywords:
            return emails

        filtered = []
        keywords_lower = [k.lower() for k in keywords]

        for email in emails:
            searchable_text = KeywordFilter._get_searchable_text(email)
            if KeywordFilter._contains_any_keyword(searchable_text, keywords_lower):
                filtered.append(email)

        return filtered

    @staticmethod
    def _get_searchable_text(email: Dict[str, Any]) -> str:
        """검색 가능한 텍스트 추출 (제목 + 본문 미리보기)"""
        text_parts = []

        # 제목
        subject = KeywordFilter._get_subject(email)
        if subject:
            text_parts.append(subject)

        # 본문 미리보기
        body_preview = KeywordFilter._get_body_preview(email)
        if body_preview:
            text_parts.append(body_preview)

        return ' '.join(text_parts).lower()

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

    @staticmethod
    def _get_body_preview(email: Dict[str, Any]) -> str:
        """본문 미리보기 추출"""
        # GraphMailItem 형식
        if hasattr(email, 'body_preview'):
            return str(email.body_preview) if email.body_preview else ''

        # Dict 형식
        if isinstance(email, dict):
            if 'body_preview' in email:
                return str(email['body_preview']) if email['body_preview'] else ''
            if 'bodyPreview' in email:
                return str(email['bodyPreview']) if email['bodyPreview'] else ''

        return ''

    @staticmethod
    def _contains_any_keyword(text: str, keywords: List[str]) -> bool:
        """텍스트에 키워드 중 하나라도 포함되는지 확인"""
        return any(keyword in text for keyword in keywords)
