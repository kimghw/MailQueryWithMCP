#!/usr/bin/env python3
"""
이벤트 발행 테스트 스크립트 - 실제 메일 조회 버전
메일 처리 → 이벤트 발행 → Kafka 이벤트 확인
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.mail_query.mail_query_orchestrator import MailQueryOrchestrator
from modules.mail_query.mail_query_schema import (
    MailQueryFilters,
    PaginationOptions,
    MailQueryRequest,
)
from modules.mail_process.mail_processor_orchestrator import MailProcessorOrchestrator
from modules.keyword_extractor.services.dashboard_event_service import (
    DashboardEventService,
)
from infra.core.logger import get_logger
from infra.core.kafka_client import get_kafka_client
from infra.core.config import get_config

logger = get_logger(__name__)


class EventPublishingTest:
    """이벤트 발행 테스트 클래스"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.kafka_client = get_kafka_client()
        self.mail_query_orchestrator = MailQueryOrchestrator()
        self.mail_processor_orchestrator = MailProcessorOrchestrator()
        self.dashboard_event_service = DashboardEventService()

        # 발행된 이벤트 추적
        self.event_stats = defaultdict(int)
        self.sample_events = []

    async def test_real_mail_events(
        self, user_id: str = "krsdtp", days_back: int = 49, max_mails: int = 7  # 7주일
    ):
        """실제 메일로 이벤트 발행 테스트"""

        print(f"\n🚀 실제 메일 이벤트 발행 테스트")
        print("=" * 80)
        print(f"👤 사용자: {user_id}")
        print(f"📅 기간: 최근 {days_back}일 (약 {days_back//7}주)")
        print(f"📊 메일 수: {max_mails}개")

        try:
            # 1. 실제 메일 조회
            print(f"\n[1단계] 실제 메일 조회")
            print("-" * 40)

            query_request = MailQueryRequest(
                user_id=user_id,
                filters=MailQueryFilters(
                    date_from=datetime.now() - timedelta(days=days_back)
                ),
                pagination=PaginationOptions(top=max_mails, max_pages=1),
            )

            print(f"⏳ Graph API에서 메일 조회 중...")
            start_time = datetime.now()

            query_response = await self.mail_query_orchestrator.mail_query_user_emails(
                query_request
            )

            query_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            if not query_response.messages:
                print("❌ 조회된 메일이 없습니다.")
                return

            print(
                f"✅ {len(query_response.messages)}개 메일 조회 완료 (소요시간: {query_time_ms:.0f}ms)"
            )

            # 조회된 메일 상세 정보
            print(f"\n📋 조회된 실제 메일:")
            for i, mail in enumerate(query_response.messages):
                # 발신자 정보 추출
                sender_info = mail.sender or mail.from_address or {}
                sender_addr = ""
                sender_name = ""
                if isinstance(sender_info, dict):
                    email_addr = sender_info.get("emailAddress", {})
                    if isinstance(email_addr, dict):
                        sender_addr = email_addr.get("address", "")
                        sender_name = email_addr.get("name", "")

                print(f"\n  [{i+1}] 제목: {mail.subject[:60]}...")
                print(f"      발신자: {sender_name} <{sender_addr}>")
                print(f"      수신시간: {mail.received_date_time}")
                print(f"      ID: {mail.id}")

            # 2. 메일 처리 및 이벤트 발행
            print(f"\n[2단계] 메일 처리 및 이벤트 발행")
            print("-" * 40)

            # 큐에 추가
            print(f"⏳ 메일을 큐에 추가 중...")
            enqueue_result = await self.mail_processor_orchestrator.enqueue_mail_batch(
                account_id=user_id, mails=query_response.messages
            )

            print(f"✅ 큐 추가 완료:")
            print(f"  - 큐 저장: {enqueue_result['enqueued']}개")
            print(f"  - 필터링: {enqueue_result['filtered']}개")
            print(f"  - 중복: {enqueue_result['duplicates']}개")

            # 배치 처리
            if enqueue_result["queue_size"] > 0:
                print(f"\n⏳ 배치 처리 시작...")
                start_time = datetime.now()

                process_results = await self.mail_processor_orchestrator.process_batch()

                process_time_ms = (datetime.now() - start_time).total_seconds() * 1000

                print(f"✅ 배치 처리 완료 (소요시간: {process_time_ms:.0f}ms)")
                print(f"  - 처리된 메일: {len(process_results)}개")

                # 처리 결과 분석
                await self._analyze_process_results(
                    process_results, query_response.messages
                )

            # 3. 이벤트 발행 결과 분석
            print(f"\n[3단계] 이벤트 발행 결과 분석")
            print("-" * 40)

            await self._check_event_publishing_status()

            # 4. 대시보드 이벤트 상세 분석
            print(f"\n[4단계] 대시보드 이벤트 상세 분석")
            print("-" * 40)

            await self._analyze_dashboard_event_details(query_response.messages)

        except Exception as e:
            logger.error(f"테스트 중 오류 발생: {str(e)}", exc_info=True)
            print(f"\n❌ 오류 발생: {str(e)}")
        finally:
            await self.mail_query_orchestrator.close()

    async def _analyze_process_results(
        self, process_results: List[Any], original_mails: List[Any]
    ):
        """처리 결과 분석"""

        print(f"\n📊 처리 결과 상세:")

        # 메일별 처리 결과 매핑
        mail_map = {mail.id: mail for mail in original_mails}

        dashboard_candidates = 0
        dashboard_published = 0

        for result in process_results:
            if result.success and result.mail_id in mail_map:
                mail = mail_map[result.mail_id]

                # 발신자 조직 확인
                sender_org = None
                if hasattr(result, "keywords") and isinstance(result.keywords, dict):
                    sender_org = result.keywords.get("sender_organization")

                # 키워드에서 아젠다 정보 확인
                agenda_info = None
                if hasattr(result, "keywords") and isinstance(result.keywords, dict):
                    if result.keywords.get("agenda_code"):
                        agenda_info = result.keywords.get("agenda_code")

                print(f"\n  📧 메일 ID: {result.mail_id[:20]}...")
                print(f"     제목: {mail.subject[:50]}...")

                if isinstance(result.keywords, list):
                    print(f"     키워드: {', '.join(result.keywords[:5])}")
                elif isinstance(result.keywords, dict):
                    # 구조화된 응답인 경우
                    print(f"     메일타입: {result.keywords.get('mail_type', 'N/A')}")
                    print(
                        f"     발신조직: {result.keywords.get('sender_organization', 'N/A')}"
                    )
                    print(f"     아젠다: {result.keywords.get('agenda_code', 'N/A')}")
                    print(f"     마감일: {result.keywords.get('deadline', 'N/A')}")

                    # 대시보드 이벤트 조건 확인
                    if result.keywords.get("agenda_code") and result.keywords.get(
                        "sender_organization"
                    ):
                        dashboard_candidates += 1
                        if result.keywords.get("sender_organization") in [
                            "ABS",
                            "BV",
                            "CCS",
                            "CRS",
                            "DNV",
                            "IRS",
                            "KR",
                            "NK",
                            "PRS",
                            "RINA",
                            "IL",
                            "TL",
                        ]:
                            dashboard_published += 1
                            print(f"     ✅ 대시보드 이벤트 발행 예상")

        print(f"\n📈 이벤트 발행 예상:")
        print(f"  - email.received 이벤트: {len(process_results)}개")
        print(f"  - 대시보드 이벤트 후보: {dashboard_candidates}개")
        print(f"  - 대시보드 이벤트 발행: {dashboard_published}개")

    async def _check_event_publishing_status(self):
        """이벤트 발행 상태 확인"""

        # Kafka 설정 정보
        email_topic = self.config.kafka_topic_email_events
        dashboard_topic = self.config.get_setting(
            "KAFKA_TOPIC_DASHBOARD_EVENTS", "email.api.response"
        )

        print(f"\n📡 Kafka 이벤트 발행 정보:")
        print(f"  - 이메일 이벤트 토픽: {email_topic}")
        print(f"  - 대시보드 이벤트 토픽: {dashboard_topic}")
        print(
            f"  - 대시보드 이벤트 활성화: {self.dashboard_event_service.dashboard_events_enabled}"
        )

        # 이벤트 타입별 설명
        print(f"\n📝 이벤트 타입 설명:")
        print(f"  1. email.received")
        print(f"     - 발행 조건: 모든 처리된 메일")
        print(f"     - 포함 정보: 메일 정보, IACS 정보, 키워드, 구조화된 분석")

        print(f"\n  2. email-dashboard")
        print(f"     - 발행 조건: agenda_no가 있고 sender_organization이 IACS 멤버")
        print(
            f"     - IACS 멤버: ABS, BV, CCS, CRS, DNV, IRS, KR, NK, PRS, RINA, IL, TL"
        )
        print(f"     - 포함 정보: 구조화된 추출 결과, 처리 메타데이터")

    async def _analyze_dashboard_event_details(self, mails: List[Any]):
        """대시보드 이벤트 상세 분석"""

        print(f"\n🎯 메일별 대시보드 이벤트 발행 가능성 분석:")

        for i, mail in enumerate(mails):
            # 발신자 정보 추출
            sender_info = mail.sender or mail.from_address or {}
            sender_addr = ""
            if isinstance(sender_info, dict):
                email_addr = sender_info.get("emailAddress", {})
                if isinstance(email_addr, dict):
                    sender_addr = email_addr.get("address", "")

            # 도메인에서 조직 추정
            sender_org = "UNKNOWN"
            if sender_addr and "@" in sender_addr:
                domain = sender_addr.split("@")[1].lower()
                # 간단한 도메인-조직 매핑
                domain_org_map = {
                    "kr.org": "KR",
                    "krs.co.kr": "KR",
                    "lr.org": "LR",
                    "dnv.com": "DNV",
                    "classnk.or.jp": "NK",
                    "eagle.org": "ABS",
                    "bureauveritas.com": "BV",
                    "ccs.org.cn": "CCS",
                    "rina.org": "RINA",
                    "prs.pl": "PRS",
                    "iacs.org.uk": "IL",
                    "turkloydu.org": "TL",
                    "crs.hr": "CRS",
                    "irclass.org": "IRS",
                }

                for domain_pattern, org in domain_org_map.items():
                    if domain_pattern in domain:
                        sender_org = org
                        break

            # 제목에서 아젠다 패턴 찾기
            subject = mail.subject or ""
            agenda_pattern = None

            # 간단한 아젠다 패턴 매칭
            import re

            patterns = [
                r"(PL\d{5}[a-z]?)",
                r"(PS\d{5}[a-z]?)",
                r"(JWG-SDT\d{5}[a-z]?)",
                r"(JWG-CS\d{5}[a-z]?)",
                r"(Multilateral)",
            ]

            for pattern in patterns:
                match = re.search(pattern, subject, re.IGNORECASE)
                if match:
                    agenda_pattern = match.group(1)
                    break

            print(f"\n  [{i+1}] {subject[:50]}...")
            print(
                f"      발신 도메인: {sender_addr.split('@')[1] if '@' in sender_addr else 'N/A'}"
            )
            print(f"      추정 조직: {sender_org}")
            print(f"      아젠다 패턴: {agenda_pattern or 'N/A'}")

            # 대시보드 이벤트 발행 가능성
            is_iacs = sender_org in [
                "ABS",
                "BV",
                "CCS",
                "CRS",
                "DNV",
                "IRS",
                "KR",
                "NK",
                "PRS",
                "RINA",
                "IL",
                "TL",
            ]
            has_agenda = agenda_pattern is not None

            if is_iacs and has_agenda:
                print(f"      ✅ 대시보드 이벤트 발행 가능")
            elif not is_iacs and has_agenda:
                print(f"      ❌ 대시보드 이벤트 불가 (비IACS 조직)")
            elif is_iacs and not has_agenda:
                print(f"      ❌ 대시보드 이벤트 불가 (아젠다 없음)")
            else:
                print(f"      ❌ 대시보드 이벤트 불가 (조건 미충족)")

    async def cleanup(self):
        """리소스 정리"""
        await self.mail_query_orchestrator.close()
        await self.mail_processor_orchestrator.cleanup()


async def main():
    """메인 함수"""
    print("\n📮 실제 메일 이벤트 발행 테스트")
    print("=" * 80)

    test = EventPublishingTest()

    try:
        print("\n기본 설정:")
        print("- 사용자: krsdtp")
        print("- 기간: 최근 7주 (49일)")
        print("- 메일 수: 7개")

        confirm = input("\n이 설정으로 진행하시겠습니까? (y/n): ").strip().lower()

        if confirm == "y":
            await test.test_real_mail_events(
                user_id="krsdtp", days_back=49, max_mails=7  # 7주
            )
        else:
            # 사용자 정의
            user_id = input("사용자 ID (기본: krsdtp): ").strip() or "krsdtp"
            weeks = int(input("조회할 주 수 (기본: 7): ") or "7")
            mails = int(input("메일 수 (기본: 7): ") or "7")

            await test.test_real_mail_events(
                user_id=user_id, days_back=weeks * 7, max_mails=mails
            )

    finally:
        await test.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
