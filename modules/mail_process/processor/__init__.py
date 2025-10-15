"""
Email Processor Module
"""

from .process_options import ProcessOptions
from .email_processor import EmailProcessor
from .result import (
    EmailProcessResult,
    AttachmentResult,
    BatchProcessResult
)

__all__ = [
    'ProcessOptions',
    'EmailProcessor',
    'EmailProcessResult',
    'AttachmentResult',
    'BatchProcessResult',
]
