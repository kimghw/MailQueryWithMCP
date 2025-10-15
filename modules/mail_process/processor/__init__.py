"""
Email Processor Module
"""

from .process_options import ProcessOptions
from .result import (
    EmailProcessResult,
    AttachmentResult,
    BatchProcessResult
)

__all__ = [
    'ProcessOptions',
    'EmailProcessResult',
    'AttachmentResult',
    'BatchProcessResult',
]
