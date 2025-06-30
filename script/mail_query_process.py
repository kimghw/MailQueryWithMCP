# test_all_accounts_full_process.py
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json

from modules.mail_query import (
    MailQueryOrchestrator,
    MailQueryRequest,
    MailQueryFilters,
    PaginationOptions
)
from modules.mail_process import (
    MailProcessorOrchestrator,
    ProcessingStatus
)
from infra.core.database import get_database_manager
from infra.core.logger import get_logger, update_all_loggers_level
from infra.core.config import get_config

# 로그 레벨 설정
update_all_loggers_level("INFO")
logger = get_logger(__name__)

class AllAccountsFullProcessTester:
    """모든 계정의 메일 조회 및 처리 통합 테스터"""
    
    def __init__(self):
        self.mail_query = MailQueryOrchestrator()
        self.mail_processor = MailProcessorOrchestrator()
        self.db = get_database_manager()
        self.config = get_config()
        
        # 중복 검토 상태 확인
        self.duplicate_check_enabled = self.mail_processor.get_duplicate_check_status()
        logger.info(f"중복 검토 상태: {'활성화' if self.duplicate_check_enabled else '비활성화'}")
        
    async def get_all_active_accounts(self) -> List[Dict[str, Any]]:
        """활성화된 모든 계정 조회"""
        query = """
            SELECT 
                user_id, 
                user_name, 
                email,
                is_active,
                status,
                last_sync_time
            FROM accounts 
            WHERE is_active = 1
            ORDER BY user_id
        """
        
        accounts = self.db.fetch_all(query)
        return [dict(account) for account in accounts]
    
    async def process_account(
        self, 
        user_id: str,
        user_name: str,
        days_back: int = 60,
        max_mails: int = 10
    ) -> Dict[str, Any]:
        """단일 계정의 메일 조회 및 처리"""
        
        start_time = datetime.now()
        result = {
            "user_id": user_id,
            "user_name": user_name,
            "query_success": False,
            "process_success": False,
            "total_mails_found": 0,
            "mails_processed": 0,
            "processing_stats": {
                "success": 0,
                "skipped": 0,
                "failed": 0
            },
            "keywords_extracted": [],
            "execution_time": {
                "query_ms": 0,
                "process_ms": 0,
                "total_ms": 0
            },
            "errors": []
        }
        
        try:
            # 1. Mail Query - 메일 조회
            logger.info(f"\n📥 [{user_id}] 메일 조회 시작...")
            query_start = datetime.now()
            
            request = MailQueryRequest(
                user_id=user_id,
                filters=MailQueryFilters(
                    date_from=datetime.now() - timedelta(days=days_back)
                ),
                pagination=PaginationOptions(
                    top=max_mails,
                    skip=0,
                    max_pages=1
                ),
                select_fields=[
                    "id", "subject", "from", "sender", 
                    "receivedDateTime", "bodyPreview", "body",
                    "hasAttachments", "importance", "isRead"
                ]
            )
            
            async with self.mail_query as orchestrator:
                query_response = await orchestrator.mail_query_user_emails(request)
            
            result["query_success"] = True
            result["total_mails_found"] = query_response.total_fetched
            result["execution_time"]["query_ms"] = query_response.execution_time_ms
            
            logger.info(f"✅ [{user_id}] 메일 조회 완료: {query_response.total_fetched}개")
            
            if query_response.total_fetched == 0:
                logger.info(f"⚠️ [{user_id}] 조회된 메일이 없습니다.")
                result["execution_time"]["total_ms"] = int(
                    (datetime.now() - start_time).total_seconds() * 1000
                )
                return result
            
            # 2. Mail Process - 메일 처리
            logger.info(f"🔧 [{user_id}] 메일 처리 시작...")
            process_start = datetime.now()
            
            # 배치 처리
            process_stats = await self.mail_processor.process_mail_batch(
                account_id=user_id,
                mails=[mail.model_dump() for mail in query_response.messages],
                publish_batch_event=False  # 테스트에서는 이벤트 발행 안함
            )
            
            result["process_success"] = True
            result["mails_processed"] = process_stats["total"]
            result["processing_stats"] = {
                "success": process_stats["processed"],
                "skipped": process_stats["skipped"],
                "failed": process_stats["failed"]
            }
            result["execution_time"]["process_ms"] = int(
                (datetime.now() - process_start).total_seconds() * 1000
            )
            
            # 3. 키워드 수집 (샘플)
            if process_stats["processed"] > 0:
                # 처리된 메일 중 일부의 키워드 수집
                for mail in query_response.messages[:3]:  # 상위 3개만
                    try:
                        mail_result = await self.mail_processor.process_single_mail(
                            user_id, mail.model_dump()
                        )
                        if mail_result.keywords:
                            result["keywords_extracted"].extend(mail_result.keywords)
                    except:
                        pass
                
                # 중복 제거
                result["keywords_extracted"] = list(set(result["keywords_extracted"]))[:10]
            
            logger.info(
                f"✅ [{user_id}] 메일 처리 완료: "
                f"성공={process_stats['processed']}, "
                f"건너뜀={process_stats['skipped']}, "
                f"실패={process_stats['failed']}"
            )
            
        except Exception as e:
            error_msg = f"계정 처리 오류: {str(e)}"
            logger.error(f"❌ [{user_id}] {error_msg}")
            result["errors"].append(error_msg)
        
        finally:
            result["execution_time"]["total_ms"] = int(
                (datetime.now() - start_time).total_seconds() * 1000
            )
        
        return result
    
    async def test_all_accounts(
        self,
        days_back: int = 60,
        max_mails_per_account: int = 20,
        save_results: bool = True
    ):
        """모든 계정 통합 테스트"""
        
        print("\n" + "🚀 " * 20)
        print("모든 계정 메일 조회 및 처리 통합 테스트")
        print("🚀 " * 20)
        print(f"\n📅 설정:")
        print(f"  - 조회 기간: 최근 {days_back}일")
        print(f"  - 계정당 최대 메일: {max_mails_per_account}개")
        print(f"  - 중복 검토: {'활성화' if self.duplicate_check_enabled else '비활성화'}")
        print(f"  - 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n" + "=" * 80)
        
        # 1. 활성 계정 조회
        accounts = await self.get_all_active_accounts()
        print(f"\n📋 활성 계정: {len(accounts)}개")
        for i, account in enumerate(accounts, 1):
            print(f"  {i}. {account['user_id']} ({account['user_name']})")
        
        # 2. 각 계정 처리
        print("\n" + "=" * 80)
        print("📧 계정별 처리 시작")
        print("=" * 80)
        
        all_results = []
        total_stats = {
            "accounts": len(accounts),
            "successful_accounts": 0,
            "total_mails_found": 0,
            "total_mails_processed": 0,
            "total_success": 0,
            "total_skipped": 0,
            "total_failed": 0,
            "all_keywords": []
        }
        
        for i, account in enumerate(accounts, 1):
            print(f"\n[{i}/{len(accounts)}] 처리 중: {account['user_id']}")
            print("-" * 60)
            
            result = await self.process_account(
                user_id=account['user_id'],
                user_name=account['user_name'],
                days_back=days_back,
                max_mails=max_mails_per_account
            )
            
            all_results.append(result)
            
            # 통계 업데이트
            if result["query_success"] and result["process_success"]:
                total_stats["successful_accounts"] += 1
            
            total_stats["total_mails_found"] += result["total_mails_found"]
            total_stats["total_mails_processed"] += result["mails_processed"]
            total_stats["total_success"] += result["processing_stats"]["success"]
            total_stats["total_skipped"] += result["processing_stats"]["skipped"]
            total_stats["total_failed"] += result["processing_stats"]["failed"]
            total_stats["all_keywords"].extend(result["keywords_extracted"])
            
            # 간단한 결과 출력
            print(f"  📊 결과:")
            print(f"     - 조회된 메일: {result['total_mails_found']}개")
            print(f"     - 처리 결과: 성공={result['processing_stats']['success']}, "
                  f"건너뜀={result['processing_stats']['skipped']}, "
                  f"실패={result['processing_stats']['failed']}")
            print(f"     - 실행 시간: 조회={result['execution_time']['query_ms']}ms, "
                  f"처리={result['execution_time']['process_ms']}ms")
            
            if result["keywords_extracted"]:
                print(f"     - 추출 키워드: {', '.join(result['keywords_extracted'][:5])}...")
        
        # 3. 전체 통계
        print("\n" + "=" * 80)
        print("📊 전체 통계")
        print("=" * 80)
        
        print(f"\n✅ 계정 처리 결과:")
        print(f"  - 전체 계정: {total_stats['accounts']}개")
        print(f"  - 성공 계정: {total_stats['successful_accounts']}개")
        print(f"  - 실패 계정: {total_stats['accounts'] - total_stats['successful_accounts']}개")
        
        print(f"\n📧 메일 처리 통계:")
        print(f"  - 조회된 총 메일: {total_stats['total_mails_found']}개")
        print(f"  - 처리된 총 메일: {total_stats['total_mails_processed']}개")
        print(f"  - 처리 결과:")
        print(f"    • 성공: {total_stats['total_success']}개")
        print(f"    • 건너뜀: {total_stats['total_skipped']}개")
        print(f"    • 실패: {total_stats['total_failed']}개")
        
        # 처리율 계산
        if total_stats['total_mails_processed'] > 0:
            success_rate = (total_stats['total_success'] / total_stats['total_mails_processed']) * 100
            print(f"  - 성공률: {success_rate:.1f}%")
        
        # 키워드 분석
        unique_keywords = list(set(total_stats["all_keywords"]))
        print(f"\n🔑 키워드 분석:")
        print(f"  - 총 키워드 수: {len(total_stats['all_keywords'])}개")
        print(f"  - 고유 키워드 수: {len(unique_keywords)}개")
        if unique_keywords:
            print(f"  - 상위 키워드: {', '.join(unique_keywords[:10])}")
        
        # 실행 시간 분석
        total_query_time = sum(r['execution_time']['query_ms'] for r in all_results)
        total_process_time = sum(r['execution_time']['process_ms'] for r in all_results)
        total_time = sum(r['execution_time']['total_ms'] for r in all_results)
        
        print(f"\n⏱️  실행 시간 분석:")
        print(f"  - 총 조회 시간: {total_query_time:,}ms ({total_query_time/1000:.1f}초)")
        print(f"  - 총 처리 시간: {total_process_time:,}ms ({total_process_time/1000:.1f}초)")
        print(f"  - 총 실행 시간: {total_time:,}ms ({total_time/1000:.1f}초)")
        print(f"  - 평균 시간/계정: {total_time/len(accounts):.0f}ms")
        
        # 4. 상세 결과 테이블
        print(f"\n📋 계정별 상세 결과:")
        print(f"{'계정':<15} {'조회':<8} {'성공':<8} {'건너뜀':<8} {'실패':<8} {'시간(초)':<10}")
        print("-" * 65)
        
        for result in all_results:
            print(f"{result['user_id']:<15} "
                  f"{result['total_mails_found']:<8} "
                  f"{result['processing_stats']['success']:<8} "
                  f"{result['processing_stats']['skipped']:<8} "
                  f"{result['processing_stats']['failed']:<8} "
                  f"{result['execution_time']['total_ms']/1000:<10.1f}")
        
        # 5. 결과 저장
        if save_results:
            filename = f"mail_process_test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            save_data = {
                "test_info": {
                    "test_date": datetime.now().isoformat(),
                    "days_back": days_back,
                    "max_mails_per_account": max_mails_per_account,
                    "duplicate_check_enabled": self.duplicate_check_enabled
                },
                "summary": total_stats,
                "detailed_results": all_results
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"\n💾 결과 저장: {filename}")
        
        print(f"\n✅ 테스트 완료!")
        print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        return {
            "summary": total_stats,
            "results": all_results
        }
    
    async def close(self):
        """리소스 정리"""
        await self.mail_query.close()
        # mail_processor는 별도의 close 메서드가 없음


async def main():
    """메인 실행 함수"""
    import sys
    
    # 명령행 인수 처리
    days_back = 60
    max_mails = 20
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("사용법: python test_all_accounts_full_process.py [days] [max_mails]")
            print("  days: 조회할 과거 일수 (기본: 60)")
            print("  max_mails: 계정당 최대 메일 수 (기본: 20)")
            return
        
        days_back = int(sys.argv[1]) if len(sys.argv) > 1 else 60
        max_mails = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    
    tester = AllAccountsFullProcessTester()
    
    try:
        await tester.test_all_accounts(
            days_back=days_back,
            max_mails_per_account=max_mails,
            save_results=True
        )
        
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())