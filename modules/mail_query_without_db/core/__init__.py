"""Core functionality for mail query without DB module"""

from .utils import sanitize_filename, ensure_directory_exists

__all__ = ['sanitize_filename', 'ensure_directory_exists']