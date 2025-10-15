"""
Filter Criteria - 메일 필터링 조건 정의
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class FilterCriteria:
    """
    메일 필터링 조건

    Phase 1 필터:
    - sender: 발신자 필터
    - recipients: 수신자 필터
    - date_from, date_to: 날짜 범위 필터
    - has_attachments: 첨부파일 유무
    - keywords: 키워드 필터 (제목 + 본문)

    Phase 2 필터 (추후 구현):
    - attachment_extensions: 첨부파일 확장자
    - is_read: 읽음 상태
    - importance: 중요도
    - subject_keywords, exclude_keywords: 제목 키워드
    """

    # ===== Phase 1 필터 =====

    # 발신자 필터
    sender: Optional[List[str]] = None
    """
    발신자 이메일 주소 리스트
    Examples:
        - ["user@example.com"]
        - ["boss@", "@company.com"] (부분 매칭)
    """

    # 수신자 필터
    recipients: Optional[List[str]] = None
    """
    수신자 이메일 주소 리스트 (to_recipients에서 검색)
    Examples:
        - ["team@company.com"]
        - ["@important-group.com"] (도메인 매칭)
    """

    # 날짜 필터
    date_from: Optional[datetime] = None
    """시작 날짜 (이 날짜 이후)"""

    date_to: Optional[datetime] = None
    """종료 날짜 (이 날짜 이전)"""

    # 첨부파일 필터
    has_attachments: Optional[bool] = None
    """
    첨부파일 유무
    - True: 첨부파일이 있는 메일만
    - False: 첨부파일이 없는 메일만
    - None: 상관없음
    """

    # 키워드 필터
    keywords: Optional[List[str]] = None
    """
    제목 또는 본문에 포함되어야 하는 키워드 (OR 조건)
    Examples:
        - ["긴급", "중요"]  # "긴급" 또는 "중요" 포함
    """

    # ===== Phase 2 필터 (추후 구현) =====

    attachment_extensions: Optional[List[str]] = None
    """
    첨부파일 확장자 필터
    Examples: ['.pdf', '.xlsx', '.docx']
    """

    is_read: Optional[bool] = None
    """읽음 상태"""

    importance: Optional[str] = None
    """중요도: 'low', 'normal', 'high'"""

    subject_keywords: Optional[List[str]] = None
    """제목에만 포함되어야 하는 키워드"""

    exclude_keywords: Optional[List[str]] = None
    """제외할 키워드 (제목 + 본문)"""

    def has_any_filter(self) -> bool:
        """하나라도 필터 조건이 설정되어 있는지 확인"""
        return any([
            self.sender,
            self.recipients,
            self.date_from,
            self.date_to,
            self.has_attachments is not None,
            self.keywords,
            self.attachment_extensions,
            self.is_read is not None,
            self.importance,
            self.subject_keywords,
            self.exclude_keywords,
        ])

    def get_active_filters(self) -> List[str]:
        """활성화된 필터 목록 반환"""
        active = []

        if self.sender:
            active.append(f"sender({len(self.sender)})")
        if self.recipients:
            active.append(f"recipients({len(self.recipients)})")
        if self.date_from:
            active.append("date_from")
        if self.date_to:
            active.append("date_to")
        if self.has_attachments is not None:
            active.append(f"has_attachments={self.has_attachments}")
        if self.keywords:
            active.append(f"keywords({len(self.keywords)})")
        if self.attachment_extensions:
            active.append(f"attachment_ext({len(self.attachment_extensions)})")
        if self.is_read is not None:
            active.append(f"is_read={self.is_read}")
        if self.importance:
            active.append(f"importance={self.importance}")
        if self.subject_keywords:
            active.append(f"subject_keywords({len(self.subject_keywords)})")
        if self.exclude_keywords:
            active.append(f"exclude({len(self.exclude_keywords)})")

        return active

    def __str__(self) -> str:
        """필터 조건 요약"""
        active = self.get_active_filters()
        if not active:
            return "FilterCriteria(no filters)"
        return f"FilterCriteria({', '.join(active)})"
