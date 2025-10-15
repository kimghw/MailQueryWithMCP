"""메일 처리 결과 데이터클래스"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path


@dataclass
class AttachmentResult:
    """첨부파일 처리 결과"""
    original_name: str
    saved_path: Optional[Path] = None
    size: int = 0

    # 텍스트 변환 결과
    converted: bool = False
    converted_text_path: Optional[Path] = None
    converted_text_content: Optional[str] = None
    conversion_error: Optional[str] = None


@dataclass
class EmailProcessResult:
    """단일 메일 처리 결과"""
    email_id: str
    subject: str
    sender: str
    received_datetime: str

    # 메일 저장 결과
    email_saved: bool = False
    email_text_path: Optional[Path] = None
    email_html_path: Optional[Path] = None
    email_dir: Optional[Path] = None

    # 첨부파일 처리 결과
    attachments: List[AttachmentResult] = field(default_factory=list)

    # 오류
    errors: List[str] = field(default_factory=list)

    def has_errors(self) -> bool:
        """오류가 있는지 확인"""
        return len(self.errors) > 0

    def get_all_text_files(self) -> List[Path]:
        """모든 텍스트 파일 경로 반환"""
        text_files = []

        if self.email_text_path:
            text_files.append(self.email_text_path)

        for att in self.attachments:
            if att.converted and att.converted_text_path:
                text_files.append(att.converted_text_path)

        return text_files

    def get_all_text_contents(self) -> Dict[str, str]:
        """모든 텍스트 내용 반환"""
        contents = {}

        # 메일 본문
        if self.email_text_path and self.email_text_path.exists():
            contents['email'] = self.email_text_path.read_text(encoding='utf-8')

        # 첨부파일 변환 텍스트
        for att in self.attachments:
            if att.converted_text_content:
                contents[att.original_name] = att.converted_text_content

        return contents


@dataclass
class BatchProcessResult:
    """일괄 처리 결과"""
    total_emails: int
    successful: int
    failed: int

    results: List[EmailProcessResult] = field(default_factory=list)

    def get_summary(self) -> Dict:
        """처리 요약"""
        total_attachments = sum(len(r.attachments) for r in self.results)
        converted_attachments = sum(
            sum(1 for att in r.attachments if att.converted)
            for r in self.results
        )

        return {
            'total_emails': self.total_emails,
            'successful': self.successful,
            'failed': self.failed,
            'total_attachments': total_attachments,
            'converted_attachments': converted_attachments,
            'errors': [
                {'email_id': r.email_id, 'errors': r.errors}
                for r in self.results if r.has_errors()
            ]
        }
