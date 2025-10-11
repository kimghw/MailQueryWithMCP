"""File converter orchestrator that tries multiple conversion strategies"""

import logging
from pathlib import Path
from typing import Optional, List
from .base import BaseConverter
from .python_converter import PythonLibraryConverter
from .system_converter import SystemCommandConverter

logger = logging.getLogger(__name__)


class FileConverterOrchestrator:
    """
    Orchestrator that manages multiple conversion strategies
    Tries Python libraries first, then falls back to system commands
    """

    def __init__(self, use_system_fallback: bool = True):
        """
        Initialize the orchestrator

        Args:
            use_system_fallback: Whether to use system commands as fallback
        """
        self.converters: List[BaseConverter] = []

        # Initialize Python converter (primary)
        try:
            self.python_converter = PythonLibraryConverter()
            self.converters.append(self.python_converter)
            logger.info("Python library converter initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Python converter: {str(e)}")
            self.python_converter = None

        # Initialize system converter (fallback)
        if use_system_fallback:
            try:
                self.system_converter = SystemCommandConverter()
                self.converters.append(self.system_converter)
                logger.info("System command converter initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize system converter: {str(e)}")
                self.system_converter = None
        else:
            self.system_converter = None

        if not self.converters:
            logger.warning("No converters available!")

    def convert_to_text(self, file_path: Path) -> str:
        """
        Convert file to text using available converters

        Args:
            file_path: Path to the file to convert

        Returns:
            Extracted text or error message
        """
        # Validate file exists
        if not file_path.exists():
            error_msg = f"Error: File not found - {file_path}"
            logger.error(error_msg)
            return error_msg

        if not file_path.is_file():
            error_msg = f"Error: Not a file - {file_path}"
            logger.error(error_msg)
            return error_msg

        file_ext = file_path.suffix.lower()
        file_size = file_path.stat().st_size

        # Log file info
        logger.info(f"Converting file: {file_path.name} ({file_ext}, {file_size:,} bytes)")

        # Try text file first (simple read)
        if file_ext in ['.txt', '.log', '.md', '.csv']:
            text = self._read_text_file(file_path)
            if text:
                return text

        # Try each converter in order
        for converter in self.converters:
            if converter.supports_format(file_ext):
                logger.debug(f"Trying {converter.__class__.__name__} for {file_ext}")
                try:
                    text = converter.convert_to_text(file_path)
                    if text:
                        logger.info(f"Successfully converted with {converter.__class__.__name__}")
                        return text
                except Exception as e:
                    logger.warning(f"{converter.__class__.__name__} failed: {str(e)}")
                    continue

        # No converter succeeded
        error_msg = f"Unable to convert file: {file_path.name} ({file_ext})"
        logger.warning(error_msg)
        return error_msg

    def _read_text_file(self, file_path: Path) -> Optional[str]:
        """Direct text file reading with encoding detection"""
        encodings = ['utf-8', 'cp949', 'euc-kr', 'latin-1']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    logger.debug(f"Read text file with {encoding} encoding")
                    return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"Error reading file: {str(e)}")
                return None

        logger.warning(f"Could not read text file with any encoding: {file_path}")
        return None

    def supports_format(self, file_extension: str) -> bool:
        """
        Check if any converter supports the format

        Args:
            file_extension: File extension to check

        Returns:
            True if at least one converter supports the format
        """
        ext = file_extension.lower()

        # Text files are always supported
        if ext in ['.txt', '.log', '.md', '.csv']:
            return True

        # Check each converter
        for converter in self.converters:
            if converter.supports_format(ext):
                return True

        return False

    def get_supported_formats(self) -> List[str]:
        """
        Get list of all supported file formats

        Returns:
            List of supported extensions
        """
        formats = set(['.txt', '.log', '.md', '.csv'])  # Always supported

        # Collect from all converters
        if self.python_converter:
            for extensions in self.python_converter.SUPPORTED_EXTENSIONS.values():
                formats.update(extensions)

        if self.system_converter:
            formats.update(self.system_converter.COMMAND_MAP.keys())

        return sorted(list(formats))

    def get_converter_status(self) -> dict:
        """
        Get status of available converters and their capabilities

        Returns:
            Dictionary with converter status information
        """
        status = {
            'python_converter': {
                'available': self.python_converter is not None,
                'dependencies': {}
            },
            'system_converter': {
                'available': self.system_converter is not None,
                'commands': {}
            },
            'supported_formats': self.get_supported_formats()
        }

        if self.python_converter:
            status['python_converter']['dependencies'] = self.python_converter.dependencies

        if self.system_converter:
            status['system_converter']['commands'] = self.system_converter.available_commands

        return status