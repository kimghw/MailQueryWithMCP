"""
Email Processor Module
"""

from .process_options import (
    ProcessOptions,
    TempFileCleanupPolicy,
    AttachmentPathMode
)
from .email_processor import EmailProcessor
from .result import (
    EmailProcessResult,
    AttachmentResult,
    BatchProcessResult
)

__all__ = [
    'ProcessOptions',
    'TempFileCleanupPolicy',
    'AttachmentPathMode',
    'EmailProcessor',
    'EmailProcessResult',
    'AttachmentResult',
    'BatchProcessResult',
]
