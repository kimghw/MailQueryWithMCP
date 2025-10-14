"""System command-based file converter"""

import logging
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict
from .base import BaseConverter

logger = logging.getLogger(__name__)


class SystemCommandConverter(BaseConverter):
    """File converter using system commands"""

    # Supported formats and their required commands
    COMMAND_MAP = {
        '.pdf': ['pdftotext', 'pdf2txt'],
        '.doc': ['antiword', 'catdoc'],
        '.docx': ['python3', '-m', 'docx2txt'],
        '.hwp': ['hwp5txt'],
        '.xls': ['xls2csv'],
        '.xlsx': ['xlsx2csv'],
        '.odt': ['odt2txt'],
        '.rtf': ['unrtf'],
        '.html': ['html2text'],
        '.htm': ['html2text'],
    }

    def __init__(self):
        """Initialize and check available system commands"""
        self.available_commands = self._check_commands()

    def _check_commands(self) -> Dict[str, bool]:
        """Check which system commands are available"""
        commands = {}
        unique_commands = set()

        # Extract unique command names
        for cmd_list in self.COMMAND_MAP.values():
            if cmd_list:
                unique_commands.add(cmd_list[0])

        # Check each command
        for cmd in unique_commands:
            commands[cmd] = shutil.which(cmd) is not None
            if not commands[cmd]:
                logger.debug(f"System command '{cmd}' not found")

        return commands

    def supports_format(self, file_extension: str) -> bool:
        """Check if converter supports the format"""
        ext = file_extension.lower()

        if ext not in self.COMMAND_MAP:
            return False

        # Check if required command is available
        cmd_list = self.COMMAND_MAP[ext]
        if cmd_list:
            primary_cmd = cmd_list[0]
            # Special case for Python modules
            if primary_cmd == 'python3':
                return True  # Assume Python is available
            return self.available_commands.get(primary_cmd, False)

        return False

    def convert_to_text(self, file_path: Path) -> Optional[str]:
        """Convert file to text using system commands"""
        if not self.validate_file(file_path):
            logger.error(f"Invalid file: {file_path}")
            return None

        file_ext = file_path.suffix.lower()

        if file_ext not in self.COMMAND_MAP:
            logger.warning(f"Unsupported file type: {file_ext}")
            return None

        # Try conversion based on file type
        try:
            if file_ext == '.pdf':
                return self._convert_pdf(file_path)
            elif file_ext == '.doc':
                return self._convert_doc(file_path)
            elif file_ext == '.docx':
                return self._convert_docx(file_path)
            elif file_ext == '.hwp':
                return self._convert_hwp(file_path)
            elif file_ext in ['.xls', '.xlsx']:
                return self._convert_excel(file_path)
            elif file_ext == '.odt':
                return self._convert_odt(file_path)
            elif file_ext == '.rtf':
                return self._convert_rtf(file_path)
            elif file_ext in ['.html', '.htm']:
                return self._convert_html(file_path)
            else:
                logger.warning(f"No converter for {file_ext}")
                return None

        except Exception as e:
            logger.error(f"Error converting {file_path}: {str(e)}")
            return None

    def _run_command(self, command: list, input_file: Path) -> Optional[str]:
        """Run system command and return output"""
        try:
            # Replace placeholder with actual file path
            cmd = [str(input_file) if c == '%INPUT%' else c for c in command]

            # Handle special cases where input file is appended
            if '%INPUT%' not in command:
                cmd.append(str(input_file))

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )

            if result.returncode == 0:
                return result.stdout
            else:
                logger.error(f"Command failed: {' '.join(cmd)}")
                logger.error(f"Error output: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(command)}")
            return None
        except Exception as e:
            logger.error(f"Error running command: {str(e)}")
            return None

    def _convert_pdf(self, file_path: Path) -> Optional[str]:
        """Convert PDF using pdftotext or pdf2txt"""
        # Try pdftotext first
        if self.available_commands.get('pdftotext', False):
            result = self._run_command(['pdftotext', '-layout', '%INPUT%', '-'], file_path)
            if result:
                return result

        # Try pdf2txt as fallback
        if self.available_commands.get('pdf2txt', False):
            result = self._run_command(['pdf2txt', '%INPUT%'], file_path)
            if result:
                return result

        return None

    def _convert_doc(self, file_path: Path) -> Optional[str]:
        """Convert DOC using antiword or catdoc"""
        # Try antiword first
        if self.available_commands.get('antiword', False):
            result = self._run_command(['antiword', '%INPUT%'], file_path)
            if result:
                return result

        # Try catdoc as fallback
        if self.available_commands.get('catdoc', False):
            result = self._run_command(['catdoc', '%INPUT%'], file_path)
            if result:
                return result

        return None

    def _convert_docx(self, file_path: Path) -> Optional[str]:
        """Convert DOCX using docx2txt"""
        try:
            # Try Python module approach
            result = subprocess.run(
                ['python3', '-m', 'docx2txt', str(file_path), '-'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return result.stdout

            # Try as standalone command
            if shutil.which('docx2txt'):
                result = self._run_command(['docx2txt', '%INPUT%'], file_path)
                if result:
                    return result

        except Exception as e:
            logger.error(f"Error converting DOCX: {str(e)}")

        return None

    def _convert_hwp(self, file_path: Path) -> Optional[str]:
        """Convert HWP using hwp5txt"""
        if self.available_commands.get('hwp5txt', False):
            result = self._run_command(['hwp5txt', '%INPUT%'], file_path)
            if result:
                return result

        return None

    def _convert_excel(self, file_path: Path) -> Optional[str]:
        """Convert Excel using xls2csv or xlsx2csv"""
        file_ext = file_path.suffix.lower()

        if file_ext == '.xls':
            if self.available_commands.get('xls2csv', False):
                result = self._run_command(['xls2csv', '%INPUT%'], file_path)
                if result:
                    return result

        elif file_ext == '.xlsx':
            if self.available_commands.get('xlsx2csv', False):
                result = self._run_command(['xlsx2csv', '%INPUT%'], file_path)
                if result:
                    return result

            # Try generic xls2csv for xlsx as well
            if self.available_commands.get('xls2csv', False):
                result = self._run_command(['xls2csv', '%INPUT%'], file_path)
                if result:
                    return result

        return None

    def _convert_odt(self, file_path: Path) -> Optional[str]:
        """Convert ODT using odt2txt"""
        if self.available_commands.get('odt2txt', False):
            result = self._run_command(['odt2txt', '%INPUT%'], file_path)
            if result:
                return result

        return None

    def _convert_rtf(self, file_path: Path) -> Optional[str]:
        """Convert RTF using unrtf"""
        if self.available_commands.get('unrtf', False):
            result = self._run_command(['unrtf', '--text', '%INPUT%'], file_path)
            if result:
                # unrtf adds headers, remove them
                lines = result.split('\n')
                # Find the actual content start
                content_start = 0
                for i, line in enumerate(lines):
                    if line.strip() and not line.startswith('###'):
                        content_start = i
                        break
                return '\n'.join(lines[content_start:])

        return None

    def _convert_html(self, file_path: Path) -> Optional[str]:
        """Convert HTML using html2text"""
        if self.available_commands.get('html2text', False):
            result = self._run_command(['html2text', '%INPUT%'], file_path)
            if result:
                return result

        return None