"""Base converter interface"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class BaseConverter(ABC):
    """Base abstract class for all file converters"""

    @abstractmethod
    def convert_to_text(self, file_path: Path) -> Optional[str]:
        """
        Convert file to text

        Args:
            file_path: Path to the file to convert

        Returns:
            Extracted text content or None if conversion failed
        """
        pass

    @abstractmethod
    def supports_format(self, file_extension: str) -> bool:
        """
        Check if converter supports the given file format

        Args:
            file_extension: File extension (e.g., '.pdf', '.docx')

        Returns:
            True if format is supported
        """
        pass

    def validate_file(self, file_path: Path) -> bool:
        """
        Validate if file exists and is readable

        Args:
            file_path: Path to validate

        Returns:
            True if file is valid
        """
        if not file_path.exists():
            return False
        if not file_path.is_file():
            return False
        if not file_path.stat().st_size > 0:
            return False
        return True