"""인증 응답 생성 유틸리티"""

from typing import Optional, Dict, Any
from infra.core.logger import get_logger


class AuthResponseGenerator:
    """OAuth 인증 응답 HTML 생성 유틸리티"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def generate_callback_success_html(self, user_id: str, session_id: str) -> str:
        """
        OAuth 콜백 성공 페이지 HTML을 생성합니다.
        
        Args:
            user_id: 사용자 ID
            session_id: 세션 ID
            
        Returns:
            HTML 문자열
        """
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>인증 완료</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .success {{ color: #4CAF50; }}
                .info {{ color: #2196F3; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1 class="success">✓ 인증이 완료되었습니다</h1>
            <div class="info">
                <p><strong>사용자:</strong> {user_id}</p>
                <p><strong>세션:</strong> {session_id[:16]}...</p>
                <p>이제 이 창을 닫으셔도 됩니다.</p>
            </div>
            <script>
                // 3초 후 자동으로 창 닫기
                setTimeout(function() {{
                    if (window.opener) {{
                        window.close();
                    }}
                }}, 3000);
            </script>
        </body>
        </html>
        """
    
    def generate_callback_error_html(self, error: str, description: Optional[str] = None) -> str:
        """
        OAuth 콜백 오류 페이지 HTML을 생성합니다.
        
        Args:
            error: 오류 코드
            description: 오류 설명
            
        Returns:
            HTML 문자열
        """
        error_message = self.format_error_message(error, description)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>인증 실패</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .error {{ color: #f44336; }}
                .info {{ color: #666; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1 class="error">✗ 인증에 실패했습니다</h1>
            <div class="info">
                <p><strong>오류:</strong> {error_message}</p>
                <p>다시 시도해 주세요.</p>
            </div>
            <script>
                // 5초 후 자동으로 창 닫기
                setTimeout(function() {{
                    if (window.opener) {{
                        window.close();
                    }}
                }}, 5000);
            </script>
        </body>
        </html>
        """
    
    def format_error_message(self, error: str, description: Optional[str] = None) -> str:
        """
        OAuth 오류 메시지를 포맷팅합니다.
        
        Args:
            error: 오류 코드
            description: 오류 설명
            
        Returns:
            포맷팅된 오류 메시지
        """
        error_messages = {
            "access_denied": "사용자가 인증을 거부했습니다",
            "invalid_request": "잘못된 인증 요청입니다",
            "unauthorized_client": "클라이언트 인증에 실패했습니다",
            "unsupported_response_type": "지원하지 않는 응답 타입입니다",
            "invalid_scope": "잘못된 권한 범위입니다",
            "server_error": "인증 서버 오류가 발생했습니다",
            "temporarily_unavailable": "인증 서비스가 일시적으로 사용할 수 없습니다"
        }
        
        base_message = error_messages.get(error, f"알 수 없는 오류: {error}")
        
        if description:
            return f"{base_message} - {description}"
        
        return base_message
    
    def mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        민감한 데이터를 마스킹합니다.
        
        Args:
            data: 원본 데이터
            
        Returns:
            마스킹된 데이터
        """
        masked = data.copy()
        sensitive_fields = ["access_token", "refresh_token", "client_secret", "password"]
        
        for field in sensitive_fields:
            if field in masked and masked[field]:
                value = str(masked[field])
                if len(value) > 8:
                    masked[field] = f"{value[:4]}...{value[-4:]}"
                else:
                    masked[field] = "***"
        
        return masked