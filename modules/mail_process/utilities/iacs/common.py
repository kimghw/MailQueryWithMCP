"""
IACS 공통 유틸리티
modules/mail_process/utilities/iacs/common.py
"""

from typing import Dict, Optional
from .constants import ParsedCode


def convert_to_unified_naming(parsed_code: ParsedCode) -> Dict:
    """ParsedCode를 통일된 네이밍으로 변환"""
    base_no = extract_base_agenda_no(parsed_code)

    return {
        "full_code": parsed_code.full_code,
        "document_type": parsed_code.document_type,
        "panel": parsed_code.panel,
        "year": parsed_code.year,
        "number": parsed_code.number,
        "agenda_version": parsed_code.agenda_version,
        "organization": parsed_code.organization,
        "response_version": parsed_code.response_version,
        "description": parsed_code.description,
        "is_response": parsed_code.is_response,
        "is_special": parsed_code.is_special,
        "is_agenda": not parsed_code.is_response and not parsed_code.is_special,
        "base_agenda_no": base_no,
        "parsing_method": parsed_code.parsing_method,
        # 통일된 네이밍 추가
        "agenda_code": parsed_code.full_code,
        "agenda_base": base_no,
        "agenda_panel": parsed_code.panel,  # agenda_panel로 변경
    }


def extract_base_agenda_no(parsed_code: ParsedCode) -> Optional[str]:
    """기본 아젠다 번호 추출"""
    if parsed_code.panel and parsed_code.year and parsed_code.number:
        return f"{parsed_code.panel}{parsed_code.year}{parsed_code.number}"
    return None
