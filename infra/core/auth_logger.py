"""
Authentication-specific logger module
인증 관련 이벤트만 별도로 기록하는 로거
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler

class AuthLogger:
    """인증 전용 로거"""
    
    def __init__(self, log_dir: str = "./logs/auth",
                 max_bytes: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 인증 전용 로거 생성
        self.logger = logging.getLogger("auth_logger")
        self.logger.setLevel(logging.INFO)

        # 기존 핸들러 제거 (중복 방지)
        self.logger.handlers.clear()

        # RotatingFileHandler 설정 (단일 파일 + 자동 로테이션)
        log_filename = "auth.log"
        log_path = self.log_dir / log_filename

        # 다른 로그와 일관성 있게 RotatingFileHandler 사용
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        
        # 포맷 설정
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # 핸들러 추가
        self.logger.addHandler(file_handler)
        
        # 콘솔 핸들러 추가 (선택적)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
    def log_token_refresh(self, user_id: str, success: bool, method: str = "auto", 
                         error: Optional[str] = None):
        """토큰 갱신 이벤트 로그"""
        status = "SUCCESS" if success else "FAILED"
        msg = f"TOKEN_REFRESH | {user_id} | {status} | method={method}"
        if error:
            msg += f" | error={error}"
        
        if success:
            self.logger.info(msg)
        else:
            self.logger.error(msg)
    
    def log_authentication(self, user_id: str, status: str, details: Optional[str] = None):
        """인증 상태 로그"""
        msg = f"AUTH_STATUS | {user_id} | {status}"
        if details:
            msg += f" | {details}"
        
        if status in ["ACTIVE", "VALID"]:
            self.logger.info(msg)
        else:
            self.logger.warning(msg)
    
    def log_login_attempt(self, user_id: str, success: bool, ip_address: Optional[str] = None,
                         error: Optional[str] = None):
        """로그인 시도 로그"""
        status = "SUCCESS" if success else "FAILED"
        msg = f"LOGIN_ATTEMPT | {user_id} | {status}"
        if ip_address:
            msg += f" | ip={ip_address}"
        if error:
            msg += f" | error={error}"
            
        if success:
            self.logger.info(msg)
        else:
            self.logger.warning(msg)
    
    def log_token_expiry(self, user_id: str, token_type: str, expiry_time: datetime):
        """토큰 만료 예정 로그"""
        # expiry_time을 timezone-aware로 변환 (필요시)
        if expiry_time.tzinfo is None:
            expiry_time = expiry_time.replace(tzinfo=timezone.utc)

        remaining = expiry_time - datetime.now(timezone.utc)
        hours = remaining.total_seconds() / 3600

        msg = f"TOKEN_EXPIRY | {user_id} | {token_type} | expires_in={hours:.1f}h | expiry_time={expiry_time.isoformat()}"

        if hours < 1:
            self.logger.warning(msg)
        else:
            self.logger.info(msg)
    
    def log_account_status_change(self, user_id: str, old_status: str, new_status: str, 
                                 reason: Optional[str] = None):
        """계정 상태 변경 로그"""
        msg = f"ACCOUNT_STATUS_CHANGE | {user_id} | {old_status} -> {new_status}"
        if reason:
            msg += f" | reason={reason}"
            
        self.logger.info(msg)
    
    def log_oauth_event(self, event_type: str, user_id: Optional[str] = None, 
                       success: bool = True, details: Optional[str] = None):
        """OAuth 관련 이벤트 로그"""
        status = "SUCCESS" if success else "FAILED"
        msg = f"OAUTH_EVENT | {event_type} | {status}"
        if user_id:
            msg += f" | user_id={user_id}"
        if details:
            msg += f" | {details}"
            
        if success:
            self.logger.info(msg)
        else:
            self.logger.error(msg)
    
    def log_batch_auth_check(self, total_accounts: int, valid: int, refresh_needed: int, 
                            expired: int):
        """배치 인증 확인 로그"""
        msg = (f"BATCH_AUTH_CHECK | total={total_accounts} | valid={valid} | "
               f"refresh_needed={refresh_needed} | expired={expired}")
        self.logger.info(msg)
    
    def get_log_path(self) -> Path:
        """현재 로그 파일 경로 반환"""
        # 이제 단일 파일이므로 고정된 이름 반환
        return self.log_dir / "auth.log"


# 싱글톤 인스턴스
_auth_logger: Optional[AuthLogger] = None


def get_auth_logger() -> AuthLogger:
    """인증 로거 싱글톤 인스턴스 반환"""
    global _auth_logger
    if _auth_logger is None:
        _auth_logger = AuthLogger()
    return _auth_logger