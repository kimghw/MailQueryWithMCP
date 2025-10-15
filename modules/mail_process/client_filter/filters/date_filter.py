"""날짜 필터"""

from typing import List, Dict, Any, Optional
from datetime import datetime


class DateFilter:
    """날짜 범위 기반 필터"""

    @staticmethod
    def apply(
        emails: List[Dict[str, Any]],
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        날짜 범위 필터링

        Args:
            emails: 메일 리스트
            date_from: 시작 날짜 (이 날짜 이후)
            date_to: 종료 날짜 (이 날짜 이전)

        Returns:
            필터링된 메일 리스트
        """
        if not date_from and not date_to:
            return emails

        filtered = []

        for email in emails:
            received_date = DateFilter._get_received_date(email)
            if received_date and DateFilter._is_in_range(received_date, date_from, date_to):
                filtered.append(email)

        return filtered

    @staticmethod
    def _get_received_date(email: Dict[str, Any]) -> Optional[datetime]:
        """수신 날짜 추출"""
        # GraphMailItem 형식
        if hasattr(email, 'received_date_time'):
            received = email.received_date_time
            if isinstance(received, datetime):
                return received
            elif isinstance(received, str):
                return DateFilter._parse_datetime(received)

        # Dict 형식
        elif isinstance(email, dict):
            if 'received_date_time' in email:
                received = email['received_date_time']
                if isinstance(received, datetime):
                    return received
                elif isinstance(received, str):
                    return DateFilter._parse_datetime(received)

            if 'receivedDateTime' in email:
                received = email['receivedDateTime']
                if isinstance(received, datetime):
                    return received
                elif isinstance(received, str):
                    return DateFilter._parse_datetime(received)

        return None

    @staticmethod
    def _parse_datetime(date_str: str) -> Optional[datetime]:
        """문자열을 datetime으로 파싱"""
        try:
            # ISO 8601 형식 (예: "2025-01-15T09:30:00Z")
            if 'T' in date_str:
                # Z 제거 후 파싱
                clean_str = date_str.replace('Z', '+00:00')
                return datetime.fromisoformat(clean_str)
            else:
                # 간단한 날짜 형식 (예: "2025-01-15")
                return datetime.strptime(date_str, '%Y-%m-%d')
        except Exception:
            return None

    @staticmethod
    def _is_in_range(
        date: datetime,
        date_from: Optional[datetime],
        date_to: Optional[datetime]
    ) -> bool:
        """날짜가 범위 내에 있는지 확인"""
        # timezone-aware vs naive 처리
        if date_from and date_from.tzinfo and not date.tzinfo:
            date = date.replace(tzinfo=date_from.tzinfo)
        if date_to and date_to.tzinfo and not date.tzinfo:
            date = date.replace(tzinfo=date_to.tzinfo)

        if date_from and date < date_from:
            return False

        if date_to and date > date_to:
            return False

        return True
