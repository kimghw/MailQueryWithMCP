#!/usr/bin/env python3
"""
Account 모듈 오케스트레이터 테스트

구현된 AccountOrchestrator를 사용하여 enrollment 파일 동기화 및 계정 관리 기능을 테스트합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_module_import():
    """모듈 import 테스트"""
    print("=== 1. 모듈 Import 테스트 ===")
    try:
        from modules.account import AccountOrchestrator, get_account_orchestrator
        print("✓ Account 모듈 import 성공")
        return True
    except Exception as e:
        print(f"✗ Import 실패: {e}")
        return False

def test_orchestrator_initialization():
    """오케스트레이터 초기화 테스트"""
    print("\n=== 2. 오케스트레이터 초기화 테스트 ===")
    try:
        from modules.account import get_account_orchestrator
        
        orchestrator = get_account_orchestrator()
        print("✓ AccountOrchestrator 초기화 성공")
        
        # 상태 확인
        health = orchestrator.account_get_health_status()
        print(f"✓ 모듈 상태: {health['status']}")
        
        if health['status'] != 'healthy':
            print(f"⚠️  상태 세부정보: {health}")
        
        return orchestrator
    except Exception as e:
        print(f"✗ 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_enrollment_file_validation(orchestrator):
    """Enrollment 파일 검증 테스트"""
    print("\n=== 3. Enrollment 파일 검증 테스트 ===")
    try:
        # kimghw.yaml 파일 검증
        file_path = "enrollment/kimghw.yaml"
        result = orchestrator.account_validate_enrollment_file(file_path)
        
        print(f"파일: {file_path}")
        print(f"유효성: {'✓ 유효' if result['valid'] else '✗ 무효'}")
        
        if result['errors']:
            print("오류:")
            for error in result['errors']:
                print(f"  - {error}")
        
        if result['warnings']:
            print("경고:")
            for warning in result['warnings']:
                print(f"  - {warning}")
        
        return result['valid']
    except Exception as e:
        print(f"✗ 파일 검증 실패: {e}")
        return False

def test_account_sync(orchestrator):
    """계정 동기화 테스트"""
    print("\n=== 4. Enrollment 동기화 테스트 ===")
    try:
        # 모든 enrollment 파일 동기화
        result = orchestrator.account_sync_all_enrollments()
        
        print(f"총 파일 수: {result.total_files}")
        print(f"생성된 계정: {result.created_accounts}")
        print(f"업데이트된 계정: {result.updated_accounts}")
        print(f"비활성화된 계정: {result.deactivated_accounts}")
        print(f"오류 수: {len(result.errors)}")
        
        if result.errors:
            print("\n오류 목록:")
            for error in result.errors:
                print(f"  - {error}")
        
        print(f"동기화 완료 시간: {result.sync_time}")
        
        # 오류가 없으면 성공으로 간주 (변경사항이 없어도 정상 동작)
        return len(result.errors) == 0
    except Exception as e:
        print(f"✗ 동기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_account_operations(orchestrator):
    """계정 조회 및 관리 테스트"""
    print("\n=== 5. 계정 조회 및 관리 테스트 ===")
    try:
        # kimghw 계정 조회
        user_id = "kimghw"
        account = orchestrator.account_get_by_user_id(user_id)
        
        if account:
            print(f"✓ {user_id} 계정 조회 성공:")
            print(f"  - 이름: {account.user_name}")
            print(f"  - 이메일: {account.email}")
            print(f"  - 상태: {account.status}")
            print(f"  - 활성화: {account.is_active}")
            print(f"  - 생성일: {account.created_at}")
            
            # 계정 활성화 테스트
            if account.status.name != 'ACTIVE':
                print(f"\n계정 활성화 시도...")
                success = orchestrator.account_activate(user_id)
                if success:
                    print(f"✓ {user_id} 계정 활성화 성공")
                    
                    # 다시 조회해서 상태 확인
                    updated_account = orchestrator.account_get_by_user_id(user_id)
                    if updated_account:
                        print(f"  - 업데이트된 상태: {updated_account.status}")
                else:
                    print(f"✗ {user_id} 계정 활성화 실패")
            else:
                print(f"  (이미 활성화된 계정)")
                
            return True
        else:
            print(f"✗ {user_id} 계정을 찾을 수 없음")
            return False
            
    except Exception as e:
        print(f"✗ 계정 조회/관리 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_single_file_sync(orchestrator):
    """단일 파일 동기화 테스트"""
    print("\n=== 6. 단일 파일 동기화 테스트 ===")
    try:
        file_path = "enrollment/kimghw.yaml"
        result = orchestrator.account_sync_single_file(file_path)
        
        print(f"파일: {file_path}")
        print(f"동기화 성공: {'✓' if result.get('success') else '✗'}")
        print(f"수행된 액션: {result.get('action', 'N/A')}")
        print(f"사용자 ID: {result.get('user_id', 'N/A')}")
        
        if not result.get('success'):
            print(f"오류: {result.get('error', 'N/A')}")
        
        return result.get('success', False)
    except Exception as e:
        print(f"✗ 단일 파일 동기화 실패: {e}")
        return False

def main():
    print("=== IACSGRAPH Account 모듈 오케스트레이터 테스트 ===\n")
    
    # 테스트 단계별 실행
    success_count = 0
    total_tests = 6
    
    # 1. 모듈 import 테스트
    if test_module_import():
        success_count += 1
    else:
        print("\n❌ 기본 import가 실패해서 테스트를 중단합니다.")
        return
    
    # 2. 오케스트레이터 초기화
    orchestrator = test_orchestrator_initialization()
    if orchestrator:
        success_count += 1
    else:
        print("\n❌ 오케스트레이터 초기화가 실패해서 테스트를 중단합니다.")
        return
    
    # 3. Enrollment 파일 검증
    if test_enrollment_file_validation(orchestrator):
        success_count += 1
    
    # 4. 계정 동기화
    if test_account_sync(orchestrator):
        success_count += 1
    
    # 5. 계정 조회 및 관리
    if test_account_operations(orchestrator):
        success_count += 1
    
    # 6. 단일 파일 동기화
    if test_single_file_sync(orchestrator):
        success_count += 1
    
    # 결과 요약
    print(f"\n=== 테스트 결과 요약 ===")
    print(f"성공: {success_count}/{total_tests}")
    print(f"성공률: {success_count/total_tests*100:.1f}%")
    
    if success_count == total_tests:
        print("🎉 모든 테스트가 성공했습니다!")
    elif success_count >= total_tests * 0.8:
        print("✅ 대부분의 테스트가 성공했습니다.")
    else:
        print("⚠️  일부 테스트가 실패했습니다. 로그를 확인해주세요.")

if __name__ == "__main__":
    main()
