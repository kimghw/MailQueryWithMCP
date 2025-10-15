"""수신자 필터"""

from typing import List, Dict, Any


class RecipientFilter:
    """수신자 이메일 주소 기반 필터"""

    @staticmethod
    def apply(emails: List[Dict[str, Any]], recipient_patterns: List[str]) -> List[Dict[str, Any]]:
        """
        수신자 패턴 매칭

        Args:
            emails: 메일 리스트
            recipient_patterns: 수신자 패턴 (부분 문자열 매칭)
                Examples: ["team@company.com", "@important-group.com"]

        Returns:
            필터링된 메일 리스트
        """
        if not recipient_patterns:
            return emails

        filtered = []
        recipient_patterns_lower = [p.lower() for p in recipient_patterns]

        for email in emails:
            recipients = RecipientFilter._get_recipients(email)
            if RecipientFilter._has_matching_recipient(recipients, recipient_patterns_lower):
                filtered.append(email)

        return filtered

    @staticmethod
    def _get_recipients(email: Dict[str, Any]) -> List[str]:
        """수신자 이메일 주소 목록 추출"""
        recipients = []

        # GraphMailItem 형식
        if hasattr(email, 'to_recipients'):
            to_recipients = email.to_recipients
            if to_recipients:
                for recipient in to_recipients:
                    if isinstance(recipient, dict):
                        email_addr = recipient.get('emailAddress', {})
                        if isinstance(email_addr, dict):
                            address = email_addr.get('address', '')
                            if address:
                                recipients.append(address.lower())

        # Dict 형식
        elif isinstance(email, dict) and 'to_recipients' in email:
            to_recipients = email['to_recipients']
            if to_recipients:
                for recipient in to_recipients:
                    if isinstance(recipient, dict):
                        email_addr = recipient.get('emailAddress', {})
                        if isinstance(email_addr, dict):
                            address = email_addr.get('address', '')
                            if address:
                                recipients.append(address.lower())

        return recipients

    @staticmethod
    def _has_matching_recipient(recipients: List[str], patterns: List[str]) -> bool:
        """수신자 중 하나라도 패턴에 매칭되는지 확인"""
        for recipient in recipients:
            if any(pattern in recipient for pattern in patterns):
                return True
        return False
