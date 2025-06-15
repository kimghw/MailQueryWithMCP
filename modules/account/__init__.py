"""
Account 모듈 - 계정 관리 시스템

enrollment 파일 기반 계정 동기화 및 관리 기능을 제공합니다.
오케스트레이터 패턴을 통해 깔끔한 의존성 관리와 비즈니스 로직 분리를 구현합니다.

주요 기능:
- Enrollment 파일 동기화
- 계정 생성 및 업데이트
- 계정 상태 관리 (활성화/비활성화)
- 토큰 정보 관리
- 감사 로그

사용 예시:
    from modules.account import AccountOrchestrator
    
    orchestrator = AccountOrchestrator()
    
    # 모든 enrollment 파일 동기화
    result = orchestrator.account_sync_all_enrollments()
    
    # 계정 조회
    account = orchestrator.account_get_by_user_id("kimghw")
    
    # 계정 활성화
    success = orchestrator.account_activate("kimghw")
"""

# 주요 클래스 및 스키마 내보내기
from .account_orchestrator import AccountOrchestrator
from .account_schema import (
    # 데이터 모델
    AccountResponse,
    AccountCreate,
    AccountUpdate,
    AccountSyncResult,
    AccountAuditLog,
    AccountListFilter,
    EnrollmentFileData,
    OAuthConfig,
    TokenInfo,
    
    # 열거형
    AccountStatus,
    AuthType,
)

# 내부 서비스들 (필요시 직접 접근 가능)
from .account_repository import AccountRepository
from .account_sync_service import AccountSyncService

__all__ = [
    # 메인 오케스트레이터 (권장 사용법)
    "AccountOrchestrator",
    
    # 스키마 클래스들
    "AccountResponse",
    "AccountCreate", 
    "AccountUpdate",
    "AccountSyncResult",
    "AccountAuditLog",
    "AccountListFilter",
    "EnrollmentFileData",
    "OAuthConfig",
    "TokenInfo",
    
    # 열거형
    "AccountStatus",
    "AuthType",
    
    # 내부 서비스들 (고급 사용자용)
    "AccountRepository",
    "AccountSyncService",
]

# 모듈 메타데이터
__version__ = "1.0.0"
__author__ = "IACSGRAPH Team"
__description__ = "Account management module for IACSGRAPH project"

# 모듈 레벨 편의 함수들
def get_account_orchestrator() -> AccountOrchestrator:
    """
    Account 오케스트레이터 인스턴스 반환
    
    Returns:
        AccountOrchestrator: 계정 관리 오케스트레이터
    """
    return AccountOrchestrator()

def sync_all_enrollments() -> AccountSyncResult:
    """
    모든 enrollment 파일 동기화 (편의 함수)
    
    Returns:
        AccountSyncResult: 동기화 결과
    """
    orchestrator = get_account_orchestrator()
    return orchestrator.account_sync_all_enrollments()

def get_account_by_user_id(user_id: str) -> AccountResponse:
    """
    사용자 ID로 계정 조회 (편의 함수)
    
    Args:
        user_id: 사용자 ID
        
    Returns:
        AccountResponse: 계정 정보
    """
    orchestrator = get_account_orchestrator()
    return orchestrator.account_get_by_user_id(user_id)

def validate_enrollment_file(file_path: str) -> dict:
    """
    Enrollment 파일 유효성 검사 (편의 함수)
    
    Args:
        file_path: 검사할 파일 경로
        
    Returns:
        dict: 검사 결과
    """
    orchestrator = get_account_orchestrator()
    return orchestrator.account_validate_enrollment_file(file_path)
