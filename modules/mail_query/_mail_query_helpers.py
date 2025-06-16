"""
Mail Query 모듈 헬퍼 함수들
350줄 제한 대응을 위한 유틸리티 함수 분리
"""
from typing import Dict, Any, Optional, Union
from datetime import datetime
import re
import json
import os
from pathlib import Path

from .mail_query_schema import GraphMailItem
from infra.core import get_logger

logger = get_logger(__name__)


def escape_odata_string(value: str) -> str:
    """OData 문자열 이스케이프"""
    if not value:
        return ""
    
    # OData에서 특수 문자 이스케이프
    # 작은따옴표는 두 번 연속으로 표시
    escaped = value.replace("'", "''")
    # 백슬래시 이스케이프
    escaped = escaped.replace("\\", "\\\\")
    
    return escaped


def parse_graph_mail_item(item: Dict[str, Any]) -> GraphMailItem:
    """Graph API 응답을 GraphMailItem으로 변환"""
    try:
        # 날짜 파싱 처리
        received_date = item.get('receivedDateTime')
        if isinstance(received_date, str):
            # ISO 8601 형식 파싱 (Z 또는 +00:00 처리)
            if received_date.endswith('Z'):
                received_date = received_date.replace('Z', '+00:00')
            received_date = datetime.fromisoformat(received_date)
        elif not isinstance(received_date, datetime):
            received_date = datetime.utcnow()
        
        # from 필드 처리 (Python 예약어이므로 from_address로 매핑)
        from_field = item.get('from')
        
        return GraphMailItem(
            id=item.get('id', ''),
            subject=item.get('subject'),
            sender=item.get('sender'),
            from_address=from_field,
            to_recipients=item.get('toRecipients', []),
            received_date_time=received_date,
            body_preview=item.get('bodyPreview'),
            body=item.get('body'),
            is_read=item.get('isRead', False),
            has_attachments=item.get('hasAttachments', False),
            importance=item.get('importance', 'normal'),
            web_link=item.get('webLink')
        )
    
    except Exception as e:
        # 파싱 실패 시 기본값으로 생성
        return GraphMailItem(
            id=item.get('id', 'unknown'),
            received_date_time=datetime.utcnow(),
            subject=f"파싱 오류: {str(e)}"
        )


def format_query_summary(
    user_id: str, 
    result_count: int, 
    execution_time_ms: int,
    has_error: bool = False
) -> str:
    """쿼리 결과 요약 포맷"""
    status = "ERROR" if has_error else "SUCCESS"
    return f"[{status}] user_id={user_id}, count={result_count}, time={execution_time_ms}ms"


def validate_pagination_params(top: int, skip: int, max_pages: int) -> bool:
    """페이징 매개변수 유효성 검사"""
    if not (1 <= top <= 1000):
        return False
    if skip < 0:
        return False
    if not (1 <= max_pages <= 50):
        return False
    return True


def extract_email_address(email_obj: Optional[Dict[str, Any]]) -> Optional[str]:
    """Graph API 이메일 객체에서 이메일 주소 추출"""
    if not email_obj:
        return None
    
    # emailAddress 객체에서 address 추출
    if isinstance(email_obj, dict):
        email_address = email_obj.get('emailAddress')
        if isinstance(email_address, dict):
            return email_address.get('address')
        
        # 직접 address 필드가 있는 경우
        return email_obj.get('address')
    
    return None


def sanitize_filter_input(filter_value: str) -> str:
    """필터 입력값 정제 (보안 및 안정성)"""
    if not filter_value:
        return ""
    
    # 기본 정제: 제어 문자 제거
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filter_value)
    
    # 길이 제한 (너무 긴 필터는 성능 문제 야기)
    if len(sanitized) > 500:
        sanitized = sanitized[:500]
    
    return sanitized.strip()


def parse_graph_error_response(error_response: Dict[str, Any]) -> Dict[str, Any]:
    """Graph API 오류 응답 파싱"""
    error_info = {
        'code': 'unknown',
        'message': 'Unknown error',
        'inner_error': None
    }
    
    if 'error' in error_response:
        error_data = error_response['error']
        error_info['code'] = error_data.get('code', 'unknown')
        error_info['message'] = error_data.get('message', 'Unknown error')
        error_info['inner_error'] = error_data.get('innerError')
    
    return error_info


def calculate_retry_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    """지수 백오프 재시도 지연 시간 계산"""
    delay = base_delay * (2 ** attempt)
    return min(delay, max_delay)


def is_transient_error(status_code: int, error_code: Optional[str] = None) -> bool:
    """일시적 오류인지 판단 (재시도 가능 여부)"""
    # HTTP 상태 코드 기반 판단
    transient_status_codes = {429, 500, 502, 503, 504}
    
    if status_code in transient_status_codes:
        return True
    
    # 특정 오류 코드 기반 판단
    if error_code:
        transient_error_codes = {
            'TooManyRequests',
            'ServiceUnavailable', 
            'InternalServerError',
            'BadGateway',
            'GatewayTimeout'
        }
        return error_code in transient_error_codes
    
    return False


def format_odata_datetime(dt: datetime) -> str:
    """datetime을 OData 호환 형식으로 포맷"""
    # UTC로 변환하고 ISO 8601 형식으로 포맷
    if dt.tzinfo is None:
        # naive datetime은 UTC로 가정
        dt = dt.replace(tzinfo=None)
    
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def validate_email_address(email: str) -> bool:
    """이메일 주소 형식 검증"""
    if not email:
        return False
    
    # 기본적인 이메일 형식 검증
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))


def truncate_text(text: str, max_length: int = 100) -> str:
    """텍스트 길이 제한 (로깅용)"""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."


def extract_domain_from_email(email: str) -> Optional[str]:
    """이메일 주소에서 도메인 추출"""
    if not email or '@' not in email:
        return None
    
    try:
        return email.split('@')[1].lower()
    except IndexError:
        return None


def normalize_importance_level(importance: Optional[str]) -> str:
    """중요도 레벨 정규화"""
    if not importance:
        return 'normal'
    
    importance_lower = importance.lower()
    
    if importance_lower in ['high', 'urgent', 'important']:
        return 'high'
    elif importance_lower in ['low', 'minor']:
        return 'low'
    else:
        return 'normal'


def build_query_cache_key(user_id: str, filters_dict: Dict[str, Any], 
                         pagination_dict: Dict[str, Any]) -> str:
    """쿼리 캐시 키 생성"""
    import hashlib
    import json
    
    # 캐시 키 구성 요소
    cache_data = {
        'user_id': user_id,
        'filters': filters_dict,
        'pagination': pagination_dict
    }
    
    # JSON 직렬화 후 해시 생성
    cache_string = json.dumps(cache_data, sort_keys=True, default=str)
    return hashlib.md5(cache_string.encode()).hexdigest()


def save_mail_to_json(mail_data: Union[Dict[str, Any], GraphMailItem], 
                      save_dir: str = "./data/mail_samples") -> str:
    """
    메일 데이터를 JSON 파일로 저장
    
    Args:
        mail_data: Graph API 원본 응답 또는 GraphMailItem 객체
        save_dir: 저장 디렉토리 경로
        
    Returns:
        저장된 파일 경로
    """
    try:
        # 디렉토리 생성
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        
        # GraphMailItem인 경우 dict로 변환
        if isinstance(mail_data, GraphMailItem):
            mail_dict = mail_data.model_dump(mode='json')
            message_id = mail_data.id
        else:
            mail_dict = mail_data
            message_id = mail_data.get('id', 'unknown')
        
        # 파일명 생성 (메시지 ID와 타임스탬프 사용)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:21]  # 마이크로초 포함
        # 메시지 ID에서 파일명에 사용할 수 없는 문자 제거
        safe_message_id = re.sub(r'[^\w\-_]', '_', message_id)[:30]  # 길이 제한
        filename = f"mail_{safe_message_id}_{timestamp}.json"
        filepath = os.path.join(save_dir, filename)
        
        # 메타데이터 추가
        save_data = {
            "metadata": {
                "saved_at": datetime.now().isoformat(),
                "message_id": message_id,
                "subject": mail_dict.get('subject', 'No Subject'),
                "received_date": mail_dict.get('receivedDateTime', 
                                              mail_dict.get('received_date_time'))
            },
            "mail_data": mail_dict
        }
        
        # JSON 파일로 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"메일 저장 완료: {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"메일 JSON 저장 실패: {e}")
        raise


def save_multiple_mails_to_json(mail_list: list, 
                                save_dir: str = "./data/mail_samples") -> list:
    """
    여러 메일을 JSON 파일로 저장
    
    Args:
        mail_list: 메일 데이터 리스트
        save_dir: 저장 디렉토리 경로
        
    Returns:
        저장된 파일 경로 리스트
    """
    saved_files = []
    
    for mail_data in mail_list:
        try:
            filepath = save_mail_to_json(mail_data, save_dir)
            saved_files.append(filepath)
        except Exception as e:
            logger.error(f"메일 저장 중 오류 발생: {e}")
            continue
    
    return saved_files
