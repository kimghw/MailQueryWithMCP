"""파일 텍스트 변환 핸들러"""

import logging
from pathlib import Path
from typing import Optional, Dict

from ...converters import FileConverterOrchestrator

logger = logging.getLogger(__name__)


class TextConverter:
    """파일 텍스트 변환 핸들러"""

    def __init__(self):
        self.converter = FileConverterOrchestrator(use_system_fallback=True)

    def convert_file_to_text(
        self,
        file_path: Path,
        save_text: bool = True,
        delete_original: bool = False
    ) -> Dict[str, any]:
        """
        파일을 텍스트로 변환

        Returns:
            {
                'success': bool,
                'text_content': str or None,
                'text_path': Path or None,
                'error': str or None
            }
        """
        result = {
            'success': False,
            'text_content': None,
            'text_path': None,
            'error': None
        }

        try:
            # 파일 변환
            text_content = self.converter.convert_to_text(file_path)

            # 변환 실패 체크
            if not text_content or text_content.startswith("Error:") or text_content.startswith("Unable to convert"):
                result['error'] = text_content or "Conversion failed"
                return result

            result['text_content'] = text_content
            result['success'] = True

            # 텍스트 파일로 저장 (옵션)
            if save_text:
                text_file = file_path.with_suffix(file_path.suffix + '.txt')

                # 중복 파일명 처리
                counter = 1
                while text_file.exists():
                    text_file = file_path.parent / f"{file_path.stem}_{counter}{file_path.suffix}.txt"
                    counter += 1

                text_file.write_text(text_content, encoding='utf-8')
                result['text_path'] = text_file
                logger.info(f"Saved converted text to {text_file}")

            # 원본 삭제 (옵션)
            if delete_original and result['success']:
                file_path.unlink()
                logger.info(f"Deleted original file: {file_path}")

            return result

        except Exception as e:
            logger.error(f"Error converting {file_path}: {str(e)}")
            result['error'] = str(e)
            return result

    def supports_format(self, file_extension: str) -> bool:
        """파일 형식 지원 여부"""
        return self.converter.supports_format(file_extension)

    def get_supported_formats(self) -> list:
        """지원하는 파일 형식 목록"""
        return self.converter.get_supported_formats()
