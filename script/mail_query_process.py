#!/usr/bin/env python3
"""
모든 계정의 메일 조회 및 처리 통합 테스터 (수정본)
"""

import sys
import os

# Python 경로에 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json
from collections import defaultdict

# 직접 import
from modules.mail_query.mail_query_orchestrator import MailQueryOrchestrator
from modules.mail_query.mail_query_schema import MailQueryRequest, MailQueryFilters, PaginationOptions
from modules.mail_process.mail_processor_orchestrator import MailProcessorOrchestrator

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
        
    async def get_all_active_accounts(self) -> List[Dict[str, Any]]:
        """활성화된 모든 계정 조회 (테스트 계정 제외)"""
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
            AND user_id NOT IN ('test_user', 'test', 'nonexistent', 'temp_user', 'demo_user')  -- 테스트 계정 제외
            AND user_id NOT LIKE 'test_%'  -- test_로 시작하는 계정 제외
            AND user_id NOT LIKE 'temp_%'  -- temp_로 시작하는 계정 제외
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
                "failed": 0,
                "filtered": 0,
                "duplicate": 0
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
            
            # 올바른 메서드 호출: process_mails
            process_stats = await self.mail_processor.process_mails(
                account_id=user_id,
                mails=[mail.model_dump() for mail in query_response.messages],
                publish_batch_event=False  # 테스트에서는 이벤트 발행 안함
            )
            
            result["process_success"] = True
            
            # 통계 매핑 수정
            result["mails_processed"] = process_stats.get("total_mails", 0)
            result["processing_stats"] = {
                "success": process_stats.get("saved_mails", 0),  # 실제 저장된 메일
                "skipped": process_stats.get("skipped_mails", 0),  # 필터링된 메일
                "failed": process_stats.get("db_errors", 0),  # DB 오류
                "filtered": process_stats.get("filtered_out", 0),  # 필터링된 메일
                "duplicate": process_stats.get("duplicate_mails", 0),  # 중복 메일
                "processed": process_stats.get("processed_mails", 0),  # 처리된 메일
                "events": process_stats.get("events_published", 0)  # 발행된 이벤트
            }
            
            # 필터 이유 상세
            if "filter_reasons" in process_stats:
                result["filter_details"] = {
                    "total": process_stats.get("skipped_mails", 0),
                    "reasons": process_stats["filter_reasons"]
                }
            
            # 키워드 수집
            if "keywords" in process_stats:
                result["keywords_extracted"] = process_stats["keywords"]
            
            result["execution_time"]["process_ms"] = int(
                (datetime.now() - process_start).total_seconds() * 1000
            )
            
            logger.info(
                f"✅ [{user_id}] 메일 처리 완료: "
                f"저장={process_stats.get('saved_mails', 0)}, "
                f"중복={process_stats.get('duplicate_mails', 0)}, "
                f"필터링={process_stats.get('skipped_mails', 0)}, "
                f"이벤트={process_stats.get('events_published', 0)}"
            )
            
        except Exception as e:
            error_msg = f"계정 처리 오류: {str(e)}"
            logger.error(f"❌ [{user_id}] {error_msg}", exc_info=True)
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
        print(f"  - 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n" + "=" * 80)
        
        # 1. 활성 계정 조회
        accounts = await self.get_all_active_accounts()
        print(f"\n📋 활성 계정: {len(accounts)}개 (테스트 계정 제외)")
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
            "total_saved": 0,
            "total_duplicate": 0,
            "total_filtered": 0,
            "total_events": 0,
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
            total_stats["total_saved"] += result["processing_stats"]["success"]
            total_stats["total_duplicate"] += result["processing_stats"]["duplicate"]
            total_stats["total_filtered"] += result["processing_stats"]["skipped"]
            total_stats["total_events"] += result["processing_stats"].get("events", 0)
            total_stats["all_keywords"].extend(result["keywords_extracted"])
            
            # 상세 결과 출력
            print(f"  📊 결과:")
            print(f"     - 조회된 메일: {result['total_mails_found']}개")
            print(f"     - 처리 결과: 저장={result['processing_stats']['success']}, "
                  f"중복={result['processing_stats']['duplicate']}, "
                  f"필터링={result['processing_stats']['skipped']}")
            print(f"     - 이벤트 발행: {result['processing_stats'].get('events', 0)}개")
            
            # 필터링 상세
            if result.get('filter_details') and result['filter_details'].get('reasons'):
                print(f"     - 필터링 상세:")
                for reason, count in result['filter_details']['reasons'].items():
                    print(f"       • {reason}: {count}개")
            
            print(f"     - 실행 시간: 조회={result['execution_time']['query_ms']}ms, "
                  f"처리={result['execution_time']['process_ms']}ms")
        
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
        print(f"  - 처리 시도: {total_stats['total_mails_processed']}개")
        print(f"  - 저장된 메일: {total_stats['total_saved']}개")
        print(f"  - 중복 메일: {total_stats['total_duplicate']}개")
        print(f"  - 필터링된 메일: {total_stats['total_filtered']}개")
        print(f"  - 발행된 이벤트: {total_stats['total_events']}개")
        
        # 성공률 계산
        if total_stats['total_mails_processed'] > 0:
            save_rate = (total_stats['total_saved'] / total_stats['total_mails_processed']) * 100
            print(f"  - 저장률: {save_rate:.1f}%")
        
        # 키워드 분석
        unique_keywords = list(set(total_stats["all_keywords"]))
        print(f"\n🔑 키워드 분석:")
        print(f"  - 총 키워드 수: {len(total_stats['all_keywords'])}개")
        print(f"  - 고유 키워드 수: {len(unique_keywords)}개")
        
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
        print(f"{'계정':<15} {'조회':<8} {'저장':<8} {'중복':<8} {'필터링':<8} {'이벤트':<8} {'시간(초)':<10}")
        print("-" * 85)
        
        for result in all_results:
            print(f"{result['user_id']:<15} "
                  f"{result['total_mails_found']:<8} "
                  f"{result['processing_stats']['success']:<8} "
                  f"{result['processing_stats']['duplicate']:<8} "
                  f"{result['processing_stats']['skipped']:<8} "
                  f"{result['processing_stats'].get('events', 0):<8} "
                  f"{result['execution_time']['total_ms']/1000:<10.1f}")
        
        # 5. 결과 저장
        if save_results:
            filename = f"mail_process_test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            save_data = {
                "test_info": {
                    "test_date": datetime.now().isoformat(),
                    "days_back": days_back,
                    "max_mails_per_account": max_mails_per_account
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
        await self.mail_processor.close()


async def main():
    """메인 실행 함수"""
    import sys
    
    # 명령행 인수 처리
    days_back = 60
    max_mails = 20
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("사용법: python mail_query_process.py [days] [max_mails]")
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
