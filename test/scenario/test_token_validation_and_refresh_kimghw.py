"""
infra/core 토큰 서비스 테스트 시나리오
user_id 'kimghw'에 대해 토큰 유효성 확인 후 무효한 경우 refresh token으로 갱신하는 테스트
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from infra.core.token_service import get_token_service
from infra.core.database import get_database_manager
from infra.core.config import get_config
from infra.core.logger import get_logger

logger = get_logger(__name__)


class TokenValidationRefreshTest:
    """토큰 유효성 검증 및 갱신 테스트 클래스"""
    
    def __init__(self):
        self.token_service = get_token_service()
        self.db = get_database_manager()
        self.config = get_config()
        self.test_user_id = "kimghw"
        
    async def setup_test_data(self):
        """테스트용 데이터 설정"""
        logger.info("=== 테스트 데이터 설정 시작 ===")
        
        # kimghw 계정 정보 확인
        account = self.db.fetch_one(
            "SELECT * FROM accounts WHERE user_id = ?",
            (self.test_user_id,)
        )
        
        if account:
            logger.info(f"기존 계정 발견: {self.test_user_id}")
            logger.info(f"계정 상태: {account['status'] if 'status' in account.keys() else 'N/A'}")
            logger.info(f"토큰 만료시간: {account['token_expiry'] if 'token_expiry' in account.keys() else 'N/A'}")
            logger.info(f"활성 상태: {account['is_active'] if 'is_active' in account.keys() else 'N/A'}")
        else:
            logger.warning(f"계정을 찾을 수 없음: {self.test_user_id}")
            
        return account
    
    async def test_scenario_1_valid_token(self):
        """시나리오 1: 유효한 토큰이 있는 경우"""
        logger.info("\n=== 시나리오 1: 유효한 토큰 확인 테스트 ===")
        
        try:
            # 토큰 유효성 검증 및 갱신
            result = await self.token_service.validate_and_refresh_token(self.test_user_id)
            
            logger.info(f"토큰 검증 결과: {result['status']}")
            logger.info(f"재인증 필요: {result.get('requires_reauth', 'N/A')}")
            logger.info(f"메시지: {result.get('message', 'N/A')}")
            
            if result['status'] == 'valid':
                logger.info("✅ 토큰이 유효합니다")
                return True
            elif result['status'] == 'refreshed':
                logger.info("✅ 토큰이 갱신되었습니다")
                return True
            else:
                logger.warning(f"⚠️ 토큰 상태: {result['status']}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 시나리오 1 실패: {str(e)}")
            return False
    
    async def test_scenario_2_expired_token_with_valid_refresh(self):
        """시나리오 2: 만료된 access_token이지만 유효한 refresh_token이 있는 경우"""
        logger.info("\n=== 시나리오 2: 만료된 토큰 갱신 테스트 ===")
        
        try:
            # 현재 계정 정보 조회
            account = self.db.fetch_one(
                "SELECT * FROM accounts WHERE user_id = ?",
                (self.test_user_id,)
            )
            
            if not account:
                logger.error("계정을 찾을 수 없습니다")
                return False
            
            # access_token을 강제로 만료시키기 (과거 시간으로 설정) - UTC 시간 사용
            expired_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            
            logger.info("access_token을 강제로 만료시킵니다...")
            self.db.update(
                table="accounts",
                data={
                    "token_expiry": expired_time,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                },
                where_clause="user_id = ?",
                where_params=(self.test_user_id,)
            )
            
            # 토큰 유효성 검증 및 갱신 시도
            result = await self.token_service.validate_and_refresh_token(self.test_user_id)
            
            logger.info(f"토큰 갱신 결과: {result['status']}")
            logger.info(f"재인증 필요: {result.get('requires_reauth', 'N/A')}")
            logger.info(f"메시지: {result.get('message', 'N/A')}")
            
            if result['status'] == 'refreshed':
                logger.info("✅ 만료된 토큰이 성공적으로 갱신되었습니다")
                
                # 갱신된 토큰 정보 확인
                updated_account = self.db.fetch_one(
                    "SELECT token_expiry, status FROM accounts WHERE user_id = ?",
                    (self.test_user_id,)
                )
                
                if updated_account:
                    logger.info(f"새로운 토큰 만료시간: {updated_account['token_expiry']}")
                    logger.info(f"계정 상태: {updated_account['status']}")
                
                return True
            elif result['status'] == 'valid':
                logger.info("✅ 토큰이 이미 유효합니다")
                return True
            else:
                logger.warning(f"⚠️ 토큰 갱신 실패: {result['status']}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 시나리오 2 실패: {str(e)}")
            return False
    
    async def test_scenario_3_get_valid_access_token(self):
        """시나리오 3: get_valid_access_token 메서드 테스트"""
        logger.info("\n=== 시나리오 3: 유효한 액세스 토큰 조회 테스트 ===")
        
        try:
            # 유효한 액세스 토큰 조회
            access_token = await self.token_service.get_valid_access_token(self.test_user_id)
            
            if access_token:
                logger.info("✅ 유효한 액세스 토큰을 성공적으로 조회했습니다")
                logger.info(f"토큰 길이: {len(access_token)} 문자")
                logger.info(f"토큰 시작: {access_token[:20]}...")
                return True
            else:
                logger.warning("⚠️ 유효한 액세스 토큰을 조회할 수 없습니다")
                return False
                
        except Exception as e:
            logger.error(f"❌ 시나리오 3 실패: {str(e)}")
            return False
    
    async def test_scenario_4_authentication_status_check(self):
        """시나리오 4: 인증 상태 확인 테스트"""
        logger.info("\n=== 시나리오 4: 인증 상태 확인 테스트 ===")
        
        try:
            # 인증 상태 확인
            auth_status = await self.token_service.check_authentication_status(self.test_user_id)
            
            logger.info(f"사용자 ID: {auth_status['user_id']}")
            logger.info(f"인증 상태: {auth_status['status']}")
            logger.info(f"재인증 필요: {auth_status['requires_reauth']}")
            logger.info(f"메시지: {auth_status['message']}")
            
            if auth_status['status'] in ['ACTIVE', 'REAUTH_REQUIRED']:
                logger.info("✅ 인증 상태 확인 성공")
                return True
            else:
                logger.warning(f"⚠️ 예상치 못한 인증 상태: {auth_status['status']}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 시나리오 4 실패: {str(e)}")
            return False
    
    async def test_scenario_5_force_token_refresh(self):
        """시나리오 5: 강제 토큰 갱신 테스트"""
        logger.info("\n=== 시나리오 5: 강제 토큰 갱신 테스트 ===")
        
        try:
            # 강제 토큰 갱신
            refresh_result = await self.token_service.force_token_refresh(self.test_user_id)
            
            if refresh_result:
                logger.info("✅ 강제 토큰 갱신 성공")
                
                # 갱신된 토큰으로 유효성 재확인
                access_token = await self.token_service.get_valid_access_token(self.test_user_id)
                if access_token:
                    logger.info("✅ 갱신된 토큰이 유효합니다")
                    return True
                else:
                    logger.warning("⚠️ 갱신된 토큰을 조회할 수 없습니다")
                    return False
            else:
                logger.warning("⚠️ 강제 토큰 갱신 실패")
                return False
                
        except Exception as e:
            logger.error(f"❌ 시나리오 5 실패: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """모든 테스트 시나리오 실행"""
        logger.info("🚀 kimghw 사용자 토큰 유효성 검증 및 갱신 테스트 시작")
        logger.info("=" * 60)
        
        # 테스트 데이터 설정
        account = await self.setup_test_data()
        if not account:
            logger.error("❌ 테스트 계정이 존재하지 않습니다. 테스트를 중단합니다.")
            return
        
        test_results = []
        
        # 시나리오 1: 유효한 토큰 확인
        result1 = await self.test_scenario_1_valid_token()
        test_results.append(("시나리오 1: 유효한 토큰 확인", result1))
        
        # 시나리오 2: 만료된 토큰 갱신
        result2 = await self.test_scenario_2_expired_token_with_valid_refresh()
        test_results.append(("시나리오 2: 만료된 토큰 갱신", result2))
        
        # 시나리오 3: 유효한 액세스 토큰 조회
        result3 = await self.test_scenario_3_get_valid_access_token()
        test_results.append(("시나리오 3: 유효한 액세스 토큰 조회", result3))
        
        # 시나리오 4: 인증 상태 확인
        result4 = await self.test_scenario_4_authentication_status_check()
        test_results.append(("시나리오 4: 인증 상태 확인", result4))
        
        # 시나리오 5: 강제 토큰 갱신
        result5 = await self.test_scenario_5_force_token_refresh()
        test_results.append(("시나리오 5: 강제 토큰 갱신", result5))
        
        # 테스트 결과 요약
        logger.info("\n" + "=" * 60)
        logger.info("📊 테스트 결과 요약")
        logger.info("=" * 60)
        
        passed = 0
        failed = 0
        
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{status} {test_name}")
            if result:
                passed += 1
            else:
                failed += 1
        
        logger.info("-" * 60)
        logger.info(f"총 테스트: {len(test_results)}개")
        logger.info(f"성공: {passed}개")
        logger.info(f"실패: {failed}개")
        logger.info(f"성공률: {(passed/len(test_results)*100):.1f}%")
        
        if failed == 0:
            logger.info("🎉 모든 테스트가 성공했습니다!")
        else:
            logger.warning(f"⚠️ {failed}개의 테스트가 실패했습니다.")
        
        return failed == 0


async def main():
    """메인 실행 함수"""
    try:
        test = TokenValidationRefreshTest()
        success = await test.run_all_tests()
        
        if success:
            print("\n🎉 모든 테스트가 성공적으로 완료되었습니다!")
            sys.exit(0)
        else:
            print("\n❌ 일부 테스트가 실패했습니다.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ 테스트가 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 테스트 실행 중 예상치 못한 오류 발생: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
