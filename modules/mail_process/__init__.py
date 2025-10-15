"""
Mail Process - 메일 처리 통합 모듈

주요 기능:
- MailProcessConfig: 환경변수 기반 설정 관리
- ClientFilter: 메일 선별 (Phase 1 + Phase 2 필터, AND/OR/NOT 키워드 지원)
- EmailProcessor: 메일 저장 + 첨부파일 처리 + 텍스트 변환 파이프라인
- FileConverter: 다양한 파일 형식을 텍스트로 변환

Legacy 기능 (호환성 유지):
- AttachmentDownloader: 개별 첨부파일 다운로드
"""

# 설정
from .config import MailProcessConfig, get_mail_process_config

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
    TempFileCleanupPolicy,
    AttachmentPathMode,
    EmailProcessor,
    EmailProcessResult,
    AttachmentResult,
    BatchProcessResult
)

# 파일 변환
from .converters import FileConverterOrchestrator

# Legacy: 기존 기능 (호환성 유지)
from .attachment_downloader import AttachmentDownloader

__all__ = [
    # Config
    'MailProcessConfig',
    'get_mail_process_config',

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
    'TempFileCleanupPolicy',
    'AttachmentPathMode',
    'EmailProcessor',
    'EmailProcessResult',
    'AttachmentResult',
    'BatchProcessResult',

    # File Converter
    'FileConverterOrchestrator',

    # Legacy (호환성 유지)
    'AttachmentDownloader',
]