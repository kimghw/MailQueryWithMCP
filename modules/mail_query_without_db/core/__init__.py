"""Core functionality for mail query without DB module"""

from .utils import sanitize_filename, ensure_directory_exists
from .attachment_downloader import AttachmentDownloader
from .email_saver import EmailSaver
from .converters import FileConverterOrchestrator

__all__ = [
    'sanitize_filename',
    'ensure_directory_exists',
    'AttachmentDownloader',
    'EmailSaver',
    'FileConverterOrchestrator'
]