#!/usr/bin/env python3
"""
krsdtp@krs.co.kr 계정을 데이터베이스에 등록

enrollment/krsdpt.yaml 파일의 설정을 사용하여 계정을 등록합니다.
"""

from modules.account import get_account_orchestrator
from infra.core.logger import get_logger

logger = get_logger(__name__)

def register_krsdtp_account():
    """krsdtp@krs.co.kr 계정 등록 (enrollment 파일 동기화)"""
    
    try:
        # Account 오케스트레이터 가져오기
        orchestrator = get_account_orchestrator()
        
        print("🚀 krsdtp@krs.co.kr 계정을 등록합니다...")
        print("=" * 60)
        
        # enrollment 파일 동기화를 통한 계정 등록
        print("📁 enrollment/krsdpt.yaml 파일을 동기화합니다...")
        sync_result = orchestrator.account_sync_all_enrollments()
        
        print(f"✅ 동기화 완료!")
        print(f"   - 처리된 파일: {sync_result.processed_files}개")
        print(f"   - 생성된 계정: {sync_result.created_accounts}개")
        print(f"   - 업데이트된 계정: {sync_result.updated_accounts}개")
        print(f"   - 실패한 계정: {sync_result.failed_accounts}개")
        print()
        
        # krsdtp 계정 확인
        try:
            account = orchestrator.account_get_by_user_id("krsdtp@krs.co.kr")
            print("📋 등록된 krsdtp 계정 정보:")
            print(f"   - 사용자 ID: {account.user_id}")
            print(f"   - 사용자 이름: {account.user_name}")
            print(f"   - 이메일: {account.email}")
            print(f"   - 상태: {account.status}")
            print(f"   - OAuth 클라이언트 ID: {account.oauth_client_id[:8]}..." if account.oauth_client_id else "   - OAuth 클라이언트 ID: 없음")
            print(f"   - 활성 상태: {account.is_active}")
            print()
            
            return True
            
        except Exception as e:
            print(f"❌ krsdtp 계정을 찾을 수 없습니다: {str(e)}")
            return False
        
    except Exception as e:
        print(f"\n❌ 계정 등록 실패: {str(e)}")
        logger.error(f"krsdtp 계정 등록 실패: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    print("📝 krsdtp@krs.co.kr 계정 등록 (enrollment 동기화)")
    print("=" * 60)
    
    # 동기 실행
    result = register_krsdtp_account()
    
    if result:
        print("\n🎯 계정 등록 성공!")
        print("이제 OAuth 인증을 진행할 수 있습니다.")
    else:
        print("\n💥 계정 등록 실패!")
