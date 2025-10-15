"""
Mail Process - 공통 메일 처리 헬퍼 모듈

이 모듈은 다양한 메일 처리 기능을 제공합니다:
- 첨부파일 다운로드 (AttachmentDownloader)
- 메일 저장 (EmailSaver)
- 파일 변환 (FileConverterOrchestrator)
- 구독 메일 스캔 (SubscriptionEmailScanner)
- 구독 파일 수집 (SubscriptionFileCollector)
- 유틸리티 (utils)
"""

# 유틸리티
from .utils import (
    sanitize_filename,
    ensure_directory_exists,
    truncate_text,
    format_file_size,
    is_valid_email
)

# 첨부파일 다운로드
from .attachment_downloader import AttachmentDownloader

# 메일 저장
from .email_saver import EmailSaver

# 파일 변환
from .converters import FileConverterOrchestrator

# 구독 메일 스캔
from .email_scanner import SubscriptionEmailScanner

# 구독 파일 수집
from .file_collector import SubscriptionFileCollector

__all__ = [
    # Utils
    'sanitize_filename',
    'ensure_directory_exists',
    'truncate_text',
    'format_file_size',
    'is_valid_email',
    # Core processors
    'AttachmentDownloader',
    'EmailSaver',
    'FileConverterOrchestrator',
    # Subscription helpers
    'SubscriptionEmailScanner',
    'SubscriptionFileCollector',
]