"""System command based file converter for document formats"""

import logging
import subprocess
from pathlib import Path
from typing import Optional
import tempfile
import os

logger = logging.getLogger(__name__)


class SystemFileConverter:
    """시스템 명령어를 사용한 파일 변환기"""
    
    def __init__(self):
        """Initialize and check available system commands"""
        self.available_tools = self._check_system_tools()
    
    def _check_system_tools(self) -> dict:
        """Check which conversion tools are available"""
        tools = {
            'pdftotext': False,
            'antiword': False,
            'catdoc': False,
            'libreoffice': False,
            'pandoc': False,
            'tesseract': False,
        }
        
        for tool in tools:
            try:
                subprocess.run([tool, '--version'], capture_output=True, timeout=5)
                tools[tool] = True
                logger.info(f"{tool} is available")
            except (subprocess.SubprocessError, FileNotFoundError):
                logger.debug(f"{tool} is not available")
        
        return tools
    
    def convert_pdf_to_text(self, file_path: Path) -> str:
        """Convert PDF to text using system tools"""
        
        # Method 1: pdftotext (poppler-utils)
        if self.available_tools.get('pdftotext'):
            try:
                result = subprocess.run(
                    ['pdftotext', '-enc', 'UTF-8', str(file_path), '-'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout
            except Exception as e:
                logger.warning(f"pdftotext failed: {e}")
        
        # Method 2: pdftohtml + text extraction
        try:
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
                tmp_path = tmp.name
            
            result = subprocess.run(
                ['pdftohtml', '-i', '-noframes', '-stdout', str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                # Extract text from HTML
                import re
                text = re.sub('<[^<]+?>', '', result.stdout)
                text = text.replace('&nbsp;', ' ')
                text = text.replace('&lt;', '<')
                text = text.replace('&gt;', '>')
                text = text.replace('&amp;', '&')
                
                os.unlink(tmp_path)
                
                if text.strip():
                    return text
        except Exception as e:
            logger.warning(f"pdftohtml failed: {e}")
        
        # Method 3: strings command (last resort)
        try:
            result = subprocess.run(
                ['strings', str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout:
                # Filter printable text
                lines = [line for line in result.stdout.splitlines() 
                        if len(line) > 3 and line.isprintable()]
                if lines:
                    return "Note: Basic text extraction using strings command\n\n" + '\n'.join(lines)
        except Exception as e:
            logger.warning(f"strings command failed: {e}")
        
        return "Unable to convert PDF. Install poppler-utils (pdftotext) for better results."
    
    def convert_docx_to_text(self, file_path: Path) -> str:
        """Convert DOCX to text using system tools"""
        
        # Method 1: pandoc
        if self.available_tools.get('pandoc'):
            try:
                result = subprocess.run(
                    ['pandoc', '-f', 'docx', '-t', 'plain', str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout
            except Exception as e:
                logger.warning(f"pandoc failed: {e}")
        
        # Method 2: libreoffice
        if self.available_tools.get('libreoffice'):
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    result = subprocess.run(
                        ['libreoffice', '--headless', '--convert-to', 'txt:Text', 
                         '--outdir', tmpdir, str(file_path)],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    # Find converted file
                    txt_file = Path(tmpdir) / file_path.with_suffix('.txt').name
                    if txt_file.exists():
                        with open(txt_file, 'r', encoding='utf-8') as f:
                            return f.read()
            except Exception as e:
                logger.warning(f"libreoffice failed: {e}")
        
        # Method 3: unzip and extract XML
        try:
            import zipfile
            import xml.etree.ElementTree as ET
            
            text_parts = []
            
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                # Extract document.xml
                with zip_file.open('word/document.xml') as xml_file:
                    tree = ET.parse(xml_file)
                    root = tree.getroot()
                    
                    # Extract text from w:t elements
                    namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                    for elem in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                        if elem.text:
                            text_parts.append(elem.text)
            
            if text_parts:
                return ' '.join(text_parts)
        except Exception as e:
            logger.warning(f"XML extraction failed: {e}")
        
        return "Unable to convert DOCX. Install pandoc or libreoffice for better results."
    
    def convert_doc_to_text(self, file_path: Path) -> str:
        """Convert DOC to text using system tools"""
        
        # Method 1: antiword
        if self.available_tools.get('antiword'):
            try:
                result = subprocess.run(
                    ['antiword', str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout
            except Exception as e:
                logger.warning(f"antiword failed: {e}")
        
        # Method 2: catdoc
        if self.available_tools.get('catdoc'):
            try:
                result = subprocess.run(
                    ['catdoc', '-d', 'utf-8', str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout
            except Exception as e:
                logger.warning(f"catdoc failed: {e}")
        
        # Method 3: libreoffice
        if self.available_tools.get('libreoffice'):
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    result = subprocess.run(
                        ['libreoffice', '--headless', '--convert-to', 'txt:Text', 
                         '--outdir', tmpdir, str(file_path)],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    txt_file = Path(tmpdir) / file_path.with_suffix('.txt').name
                    if txt_file.exists():
                        with open(txt_file, 'r', encoding='utf-8') as f:
                            return f.read()
            except Exception as e:
                logger.warning(f"libreoffice failed: {e}")
        
        return "Unable to convert DOC. Install antiword, catdoc, or libreoffice."
    
    def convert_hwp_to_text(self, file_path: Path) -> str:
        """Convert HWP to text using system tools"""
        
        # Method 1: hwp5html + HTML parsing (best quality)
        try:
            # Create temp directory for HTML output
            import tempfile
            import shutil
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Convert HWP to HTML
                result = subprocess.run(
                    ['hwp5html', '--output', temp_dir, str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    # Read the generated HTML file
                    html_file = Path(temp_dir) / 'index.xhtml'
                    if html_file.exists():
                        return self._extract_text_from_html(html_file)
                    
        except Exception as e:
            logger.warning(f"hwp5html conversion failed: {e}")
        
        # Method 2: hwp5txt (fallback - limited table support)
        try:
            result = subprocess.run(
                ['hwp5txt', str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
        except Exception as e:
            logger.warning(f"hwp5txt not available: {e}")
        
        # Method 2: pyhwp command line
        try:
            result = subprocess.run(
                ['python', '-m', 'pyhwp', 'cat', str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
        except Exception as e:
            logger.warning(f"pyhwp command failed: {e}")
        
        # Method 3: strings command for basic extraction
        try:
            result = subprocess.run(
                ['strings', '-e', 'l', str(file_path)],  # UTF-16LE encoding
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout:
                lines = [line for line in result.stdout.splitlines() 
                        if len(line) > 5 and any(c.isalpha() for c in line)]
                if lines:
                    return "Note: Basic HWP text extraction\n\n" + '\n'.join(lines)
        except Exception as e:
            logger.warning(f"strings command failed: {e}")
        
        return "Unable to convert HWP. Install hwp5txt or pyhwp for better results."
    
    def _extract_text_from_html(self, html_file: Path) -> str:
        """Extract text from HTML file"""
        try:
            import re
            
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remove style tags
            content = re.sub(r'<style.*?</style>', '', content, flags=re.DOTALL)
            
            # Extract title
            title_match = re.search(r'<p[^>]*class="Normal"[^>]*>(.*?)</p>', content)
            text_parts = []
            
            if title_match:
                title_text = re.sub(r'<[^>]+>', '', title_match.group(1))
                title_text = title_text.replace('&#13;', '').strip()
                if title_text:
                    text_parts.append(title_text)
                    text_parts.append("=" * len(title_text))
                    text_parts.append("")
            
            # Extract table data
            table_match = re.search(r'<table[^>]*>(.*?)</table>', content, re.DOTALL)
            if table_match:
                table_content = table_match.group(1)
                rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_content, re.DOTALL)
                
                table_text = []
                for row in rows:
                    cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                    cell_values = []
                    
                    for cell in cells:
                        # Remove HTML tags and clean up
                        cell_text = re.sub(r'<[^>]+>', ' ', cell)
                        cell_text = ' '.join(cell_text.split())
                        cell_text = cell_text.replace('&#13;', '').strip()
                        if cell_text:
                            cell_values.append(cell_text)
                    
                    if cell_values:
                        table_text.append(" | ".join(cell_values))
                
                if table_text:
                    text_parts.append("표 내용:")
                    text_parts.append("-" * 80)
                    text_parts.extend(table_text)
            
            # Extract remaining paragraphs
            paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL)
            for para in paragraphs:
                para_text = re.sub(r'<[^>]+>', '', para)
                para_text = para_text.replace('&#13;', '').strip()
                if para_text and para_text not in text_parts:
                    text_parts.append(para_text)
            
            return '\n'.join(text_parts) if text_parts else "No text content found"
            
        except Exception as e:
            logger.error(f"HTML text extraction failed: {e}")
            return f"HTML text extraction failed: {str(e)}"
    
    def convert_image_to_text(self, file_path: Path) -> str:
        """Convert image to text using OCR"""
        
        if self.available_tools.get('tesseract'):
            try:
                # Try Korean + English
                result = subprocess.run(
                    ['tesseract', str(file_path), 'stdout', '-l', 'kor+eng'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout
                
                # Fallback to English only
                result = subprocess.run(
                    ['tesseract', str(file_path), 'stdout', '-l', 'eng'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout
                    
            except Exception as e:
                logger.warning(f"tesseract failed: {e}")
        
        return "OCR unavailable. Install tesseract-ocr for text extraction from images."
    
    def convert_to_text(self, file_path: Path) -> str:
        """Convert file to text based on extension"""
        
        if not file_path.exists():
            return f"Error: File not found - {file_path}"
        
        ext = file_path.suffix.lower()
        
        try:
            if ext == '.pdf':
                return self.convert_pdf_to_text(file_path)
            elif ext == '.docx':
                return self.convert_docx_to_text(file_path)
            elif ext == '.doc':
                return self.convert_doc_to_text(file_path)
            elif ext == '.hwp':
                return self.convert_hwp_to_text(file_path)
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
                return self.convert_image_to_text(file_path)
            else:
                return f"Unsupported format: {ext}"
        except Exception as e:
            logger.error(f"Conversion failed for {file_path}: {e}")
            return f"Conversion error: {str(e)}"