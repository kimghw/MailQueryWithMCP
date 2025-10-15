"""
Mail Process - 메일 처리 통합 모듈

주요 기능:
- ClientFilter: 메일 선별 (Phase 1 + Phase 2 필터 지원)
- EmailProcessor: 메일 저장 + 첨부파일 처리 + 텍스트 변환 파이프라인
- FileConverter: 다양한 파일 형식을 텍스트로 변환

Legacy 기능:
- 첨부파일 다운로드 (AttachmentDownloader)
- 메일 저장 (EmailSaver)
- 구독 메일 스캔 (SubscriptionEmailScanner, SubscriptionFileCollector)
"""

# 유틸리티
from .utils import (
    sanitize_filename,
    ensure_directory_exists,
    truncate_text,
    format_file_size,
    is_valid_email
)

# 클라이언트 필터
from .client_filter import ClientFilter, FilterCriteria

# 메일 프로세서
from .processor import (
    ProcessOptions,
    EmailProcessor,
    EmailProcessResult,
    AttachmentResult,
    BatchProcessResult
)

# 파일 변환
from .converters import FileConverterOrchestrator

# Legacy: 기존 기능 (호환성 유지)
from .attachment_downloader import AttachmentDownloader
from .email_saver import EmailSaver
from .email_scanner import SubscriptionEmailScanner
from .file_collector import SubscriptionFileCollector

__all__ = [
    # Utils
    'sanitize_filename',
    'ensure_directory_exists',
    'truncate_text',
    'format_file_size',
    'is_valid_email',

    # Client Filter
    'ClientFilter',
    'FilterCriteria',

    # Email Processor
    'ProcessOptions',
    'EmailProcessor',
    'EmailProcessResult',
    'AttachmentResult',
    'BatchProcessResult',

    # File Converter
    'FileConverterOrchestrator',

    # Legacy (호환성 유지)
    'AttachmentDownloader',
    'EmailSaver',
    'SubscriptionEmailScanner',
    'SubscriptionFileCollector',
]