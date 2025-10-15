"""키워드 필터 (AND/OR/NOT 조건 지원)"""

from typing import List, Dict, Any, Optional


class KeywordFilter:
    """키워드 기반 필터 (제목 + 본문 + 발신자)"""

    @staticmethod
    def apply(
        emails: List[Dict[str, Any]],
        keywords: Optional[List[str]] = None,  # OR 조건 (기존 호환성)
        and_keywords: Optional[List[str]] = None,  # AND 조건 (모두 포함)
        or_keywords: Optional[List[str]] = None,  # OR 조건 (하나라도 포함)
        not_keywords: Optional[List[str]] = None   # NOT 조건 (하나도 포함 안됨)
    ) -> List[Dict[str, Any]]:
        """
        키워드 필터링 (AND/OR/NOT 조건 지원)

        Args:
            emails: 메일 리스트
            keywords: OR 키워드 리스트 (하나라도 포함되면 매칭) - 하위 호환성
            and_keywords: AND 키워드 리스트 (모두 포함되어야 매칭)
            or_keywords: OR 키워드 리스트 (하나라도 포함되면 매칭)
            not_keywords: NOT 키워드 리스트 (하나도 포함되지 않아야 매칭)

        Returns:
            필터링된 메일 리스트

        Examples:
            # OR 조건 (기존 방식)
            apply(emails, keywords=['invoice', 'receipt'])

            # AND 조건 (모든 키워드 포함)
            apply(emails, and_keywords=['github', 'PR'])

            # 복합 조건
            apply(emails, and_keywords=['payment'], not_keywords=['spam', 'ad'])
        """
        # 하위 호환성: keywords 파라미터를 or_keywords로 변환
        if keywords:
            or_keywords = (or_keywords or []) + keywords

        # 조건이 없으면 그대로 반환
        if not (and_keywords or or_keywords or not_keywords):
            return emails

        filtered = []

        for email in emails:
            searchable_text = KeywordFilter._get_searchable_text(email)
            include_email = True

            # AND 조건: 모든 키워드가 포함되어야 함
            if and_keywords:
                and_keywords_lower = [k.lower() for k in and_keywords]
                if not all(keyword in searchable_text for keyword in and_keywords_lower):
                    include_email = False

            # OR 조건: 하나라도 포함되어야 함
            if include_email and or_keywords:
                or_keywords_lower = [k.lower() for k in or_keywords]
                if not any(keyword in searchable_text for keyword in or_keywords_lower):
                    include_email = False

            # NOT 조건: 하나도 포함되지 않아야 함
            if include_email and not_keywords:
                not_keywords_lower = [k.lower() for k in not_keywords]
                if any(keyword in searchable_text for keyword in not_keywords_lower):
                    include_email = False

            if include_email:
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
