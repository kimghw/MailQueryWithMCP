"""Mail query without database - Attachment processing and email saving module"""

from .attachment_downloader import AttachmentDownloader
from .email_saver import EmailSaver

# Import from new structure for backward compatibility
try:
    from .core.converters import FileConverterOrchestrator as FileConverter
except ImportError:
    # Fallback to old structure if new one not available
    from .file_converter import FileConverter

__all__ = ['AttachmentDownloader', 'FileConverter', 'EmailSaver']