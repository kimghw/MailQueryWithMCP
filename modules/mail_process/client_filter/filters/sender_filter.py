"""발신자 필터"""

from typing import List, Dict, Any


class SenderFilter:
    """발신자 이메일 주소 기반 필터"""

    @staticmethod
    def apply(emails: List[Dict[str, Any]], sender_patterns: List[str]) -> List[Dict[str, Any]]:
        """
        발신자 패턴 매칭

        Args:
            emails: 메일 리스트
            sender_patterns: 발신자 패턴 (부분 문자열 매칭)
                Examples: ["user@example.com", "@company.com", "boss@"]

        Returns:
            필터링된 메일 리스트
        """
        if not sender_patterns:
            return emails

        filtered = []
        sender_patterns_lower = [p.lower() for p in sender_patterns]

        for email in emails:
            sender_email = SenderFilter._get_sender_email(email)
            if sender_email and SenderFilter._matches_any_pattern(sender_email, sender_patterns_lower):
                filtered.append(email)

        return filtered

    @staticmethod
    def _get_sender_email(email: Dict[str, Any]) -> str:
        """발신자 이메일 주소 추출"""
        # GraphMailItem 형식
        if hasattr(email, 'from_address'):
            if isinstance(email.from_address, dict):
                email_addr = email.from_address.get('emailAddress', {})
                return email_addr.get('address', '').lower()
            return ''

        # Dict 형식
        if isinstance(email, dict):
            # from_address 필드
            if 'from_address' in email:
                from_addr = email['from_address']
                if isinstance(from_addr, dict):
                    email_addr = from_addr.get('emailAddress', {})
                    return email_addr.get('address', '').lower()

            # sender 필드
            if 'sender' in email:
                sender = email['sender']
                if isinstance(sender, dict):
                    email_addr = sender.get('emailAddress', {})
                    return email_addr.get('address', '').lower()

        return ''

    @staticmethod
    def _matches_any_pattern(email: str, patterns: List[str]) -> bool:
        """이메일이 패턴 중 하나라도 매칭되는지 확인"""
        return any(pattern in email for pattern in patterns)
