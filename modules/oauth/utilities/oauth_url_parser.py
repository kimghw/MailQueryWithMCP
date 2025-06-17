"""URL 파싱 및 검증 유틸리티"""

from typing import Dict
from urllib.parse import urlparse, parse_qs
from infra.core.logger import get_logger


class AuthUrlParser:
    """OAuth URL 파싱 및 검증 유틸리티"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def validate_callback_url(self, callback_url: str, expected_redirect_uri: str) -> bool:
        """
        OAuth 콜백 URL의 유효성을 검증합니다.
        
        Args:
            callback_url: 수신된 콜백 URL
            expected_redirect_uri: 예상 리다이렉트 URI
            
        Returns:
            유효성 여부
        """
        try:
            callback_parsed = urlparse(callback_url)
            expected_parsed = urlparse(expected_redirect_uri)
            
            # 스키마, 호스트, 포트, 경로가 일치하는지 확인
            return (
                callback_parsed.scheme == expected_parsed.scheme and
                callback_parsed.netloc == expected_parsed.netloc and
                callback_parsed.path == expected_parsed.path
            )
        except Exception as e:
            self.logger.error(f"콜백 URL 검증 실패: {str(e)}")
            return False
    
    def parse_callback_params(self, callback_url: str) -> Dict[str, str]:
        """
        OAuth 콜백 URL에서 매개변수를 파싱합니다.
        
        Args:
            callback_url: 콜백 URL
            
        Returns:
            파싱된 매개변수 딕셔너리
        """
        try:
            parsed_url = urlparse(callback_url)
            params = parse_qs(parsed_url.query)
            
            # 단일 값으로 변환
            result = {}
            for key, value_list in params.items():
                if value_list:
                    result[key] = value_list[0]
            
            self.logger.debug(f"콜백 매개변수 파싱: {list(result.keys())}")
            return result
        except Exception as e:
            self.logger.error(f"콜백 매개변수 파싱 실패: {str(e)}")
            return {}