"""
IACS 공통 유틸리티
modules/mail_process/utilities/iacs/common.py
"""

from typing import Dict, Optional
from .constants import ParsedCode


def convert_to_unified_naming(parsed_code: ParsedCode, mail_info: Dict = None) -> Dict:
    """ParsedCode를 통일된 네이밍으로 변환"""
    base_no = extract_base_agenda_no(parsed_code)
    
    # 기본 정보 추출
    result = {
        "agenda_code": parsed_code.full_code,
        "agenda_base": base_no,
        "agenda_panel": parsed_code.panel,
        "parsing_method": parsed_code.parsing_method,
    }
    
    # 년도와 번호가 있는 경우에만 추가
    if parsed_code.year:
        result["agenda_year"] = parsed_code.year
    if parsed_code.number:
        result["agenda_number"] = parsed_code.number
    
    # agenda_version이 있는 경우 agenda_base_version 추가
    if parsed_code.agenda_version:
        result["agenda_version"] = parsed_code.agenda_version
        if base_no:
            result["agenda_base_version"] = f"{base_no}{parsed_code.agenda_version}"
    
    # Multilateral 특수 케이스 처리
    if parsed_code.is_special and parsed_code.full_code == "Multilateral":
        # mail_info에서 sent_time 가져오기
        if mail_info and "sent_time" in mail_info:
            sent_time = mail_info["sent_time"]
            if hasattr(sent_time, 'strftime'):
                time_str = sent_time.strftime("%Y%m%d_%H%M%S")
            else:
                # 문자열인 경우 공백과 콜론 제거
                time_str = str(sent_time).replace("-", "").replace(" ", "_").replace(":", "")
            result["agenda_base_version"] = f"Multilateral_{time_str}"
        else:
            # sent_time이 없으면 현재 시간 사용
            from datetime import datetime
            time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            result["agenda_base_version"] = f"Multilateral_{time_str}"
    
    # 응답 정보가 있는 경우
    if parsed_code.organization:
        result["response_org"] = parsed_code.organization
    if parsed_code.response_version:
        result["response_version"] = parsed_code.response_version
    
    # mail_info에서 추가 정보 추출
    if mail_info:
        # sent_time 포맷팅
        if "sent_time" in mail_info:
            sent_time = mail_info["sent_time"]
            if hasattr(sent_time, 'strftime'):
                result["sent_time"] = sent_time.strftime("%Y-%m-%d %H:%M:%S UTC")
            else:
                result["sent_time"] = str(sent_time)
        
        # sender_type 추가
        if "sender_type" in mail_info:
            result["sender_type"] = mail_info["sender_type"]
        
        # sender_organization 추가
        if "sender_organization" in mail_info:
            result["sender_organization"] = mail_info["sender_organization"]
    
    return result


def extract_base_agenda_no(parsed_code: ParsedCode) -> Optional[str]:
    """기본 아젠다 번호 추출"""
    if parsed_code.panel and parsed_code.year and parsed_code.number:
        return f"{parsed_code.panel}{parsed_code.year}{parsed_code.number}"
    return None
