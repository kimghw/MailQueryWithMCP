"""
Individual filter implementations
"""

# Phase 1 filters
from .sender_filter import SenderFilter
from .recipient_filter import RecipientFilter
from .keyword_filter import KeywordFilter
from .date_filter import DateFilter
from .attachment_filter import AttachmentFilter

# Phase 2 filters
from .attachment_extension_filter import AttachmentExtensionFilter
from .read_status_filter import ReadStatusFilter
from .importance_filter import ImportanceFilter
from .subject_keyword_filter import SubjectKeywordFilter

__all__ = [
    # Phase 1
    'SenderFilter',
    'RecipientFilter',
    'KeywordFilter',
    'DateFilter',
    'AttachmentFilter',
    # Phase 2
    'AttachmentExtensionFilter',
    'ReadStatusFilter',
    'ImportanceFilter',
    'SubjectKeywordFilter',
]
