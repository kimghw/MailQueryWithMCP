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
from typing import List, Dict, Any, Optional
from collections import defaultdict
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.mail_query.mail_query_orchestrator import MailQueryOrchestrator
from modules.mail_query.mail_query_schema import (
    MailQueryFilters,
    PaginationOptions,
    MailQueryRequest,
)
from modules.mail_process.mail_processor_orchestrator import MailProcessorOrchestrator
from modules.mail_process.services.event_service import MailEventService
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
        self.mail_event_service = MailEventService()
        self.dashboard_event_service = DashboardEventService()

        # 발행된 이벤트 추적
        self.event_stats = defaultdict(int)
        self.sample_events = []
        self.published_events = []

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

                # 처리 결과 분석 및 이벤트 발행
                await self._process_and_publish_events(
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

            # 5. 발행된 이벤트 샘플 출력
            print(f"\n[5단계] 발행된 이벤트 샘플")
            print("-" * 40)

            await self._show_published_event_samples()

        except Exception as e:
            logger.error(f"테스트 중 오류 발생: {str(e)}", exc_info=True)
            print(f"\n❌ 오류 발생: {str(e)}")
        finally:
            await self.mail_query_orchestrator.close()

    async def _process_and_publish_events(
        self, process_results: List[Any], original_mails: List[Any]
    ):
        """처리 결과를 기반으로 실제 이벤트 발행"""

        print(f"\n📊 처리 결과 상세 및 이벤트 발행:")

        # 메일별 처리 결과 매핑
        mail_map = {mail.id: mail for mail in original_mails}

        dashboard_candidates = 0
        dashboard_published = 0
        email_events_published = 0

        for result in process_results:
            if result.success and result.mail_id in mail_map:
                mail = mail_map[result.mail_id]

                # 메일 데이터를 딕셔너리로 변환
                mail_dict = self._convert_mail_to_dict(mail)

                # IACS 정보 추출 (result.keywords에서)
                iacs_info = {}
                semantic_info = {}

                if hasattr(result, "keywords") and isinstance(result.keywords, dict):
                    # semantic_info 추출
                    semantic_info = {
                        "keywords": result.keywords.get("keywords", []),
                        "deadline": result.keywords.get("deadline"),
                        "has_deadline": result.keywords.get("has_deadline", False),
                        "mail_type": result.keywords.get("mail_type"),
                        "decision_status": result.keywords.get("decision_status"),
                    }

                    # IACS 정보 추출
                    iacs_info = {
                        "agenda_code": result.keywords.get("agenda_code"),
                        "agenda_base": result.keywords.get("agenda_base"),
                        "agenda_base_version": result.keywords.get(
                            "agenda_base_version"
                        ),
                        "agenda_panel": result.keywords.get("agenda_panel"),
                        "agenda_year": result.keywords.get("agenda_year"),
                        "agenda_number": result.keywords.get("agenda_number"),
                        "agenda_version": result.keywords.get("agenda_version"),
                        "response_org": result.keywords.get("response_org"),
                        "response_version": result.keywords.get("response_version"),
                        "sent_time": result.keywords.get("sent_time"),
                        "sender_type": result.keywords.get("sender_type"),
                        "sender_organization": result.keywords.get(
                            "sender_organization"
                        ),
                        "parsing_method": result.keywords.get("parsing_method"),
                    }

                print(f"\n  📧 메일 ID: {result.mail_id[:20]}...")
                print(f"     제목: {mail.subject[:50]}...")

                # 1. email.received 이벤트 발행
                try:
                    await self.mail_event_service.publish_mail_received_event(
                        mail=mail_dict, iacs_info=iacs_info, semantic_info=semantic_info
                    )
                    email_events_published += 1
                    self.event_stats["email.received"] += 1
                    print(f"     ✅ email.received 이벤트 발행 완료")

                    # 샘플 이벤트 저장
                    if len(self.sample_events) < 3:
                        self.sample_events.append(
                            {
                                "type": "email.received",
                                "mail_id": result.mail_id,
                                "subject": mail.subject[:50],
                                "iacs_info": iacs_info,
                                "semantic_info": semantic_info,
                            }
                        )

                except Exception as e:
                    print(f"     ❌ email.received 이벤트 발행 실패: {str(e)}")

                # 2. 대시보드 이벤트 발행 (조건 충족시)
                if iacs_info.get("agenda_code") and iacs_info.get(
                    "sender_organization"
                ):
                    dashboard_candidates += 1

                    if iacs_info.get("sender_organization") in [
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
                        try:
                            # 대시보드 이벤트용 데이터 구성
                            structured_data = {
                                **iacs_info,
                                **semantic_info,
                                "mail_id": result.mail_id,
                                "subject": mail.subject,
                                "received_date_time": mail.received_date_time,
                            }

                            await self.dashboard_event_service.publish_dashboard_event(
                                structured_data
                            )
                            dashboard_published += 1
                            self.event_stats["email-dashboard"] += 1
                            print(f"     ✅ 대시보드 이벤트 발행 완료")

                        except Exception as e:
                            print(f"     ❌ 대시보드 이벤트 발행 실패: {str(e)}")

        print(f"\n📈 이벤트 발행 결과:")
        print(f"  - email.received 이벤트 발행: {email_events_published}개")
        print(f"  - 대시보드 이벤트 후보: {dashboard_candidates}개")
        print(f"  - 대시보드 이벤트 발행: {dashboard_published}개")

    def _convert_mail_to_dict(self, mail: Any) -> Dict[str, Any]:
        """메일 객체를 딕셔너리로 변환"""
        mail_dict = {
            "id": mail.id,
            "subject": mail.subject,
            "receivedDateTime": mail.received_date_time,
            "hasAttachments": getattr(mail, "has_attachments", False),
            "webLink": getattr(mail, "web_link", ""),
            "body": {
                "content": getattr(mail, "body_preview", ""),
                "contentType": "text",
            },
        }

        # 발신자 정보 추가
        sender_info = mail.sender or mail.from_address or {}
        if isinstance(sender_info, dict):
            mail_dict["from"] = {"emailAddress": sender_info.get("emailAddress", {})}

        return mail_dict

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

        print(f"\n📊 이벤트 발행 통계:")
        for event_type, count in self.event_stats.items():
            print(f"  - {event_type}: {count}개")

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

    async def _show_published_event_samples(self):
        """발행된 이벤트 샘플 표시"""

        if not self.sample_events:
            print("\n발행된 이벤트 샘플이 없습니다.")
            return

        print(f"\n📄 발행된 이벤트 샘플 (최대 3개):")

        for i, event in enumerate(self.sample_events[:3]):
            print(f"\n  [{i+1}] 이벤트 타입: {event['type']}")
            print(f"      메일 ID: {event['mail_id'][:20]}...")
            print(f"      제목: {event['subject']}...")

            if event["type"] == "email.received":
                print(f"      IACS 정보:")
                print(
                    f"        - agenda_code: {event['iacs_info'].get('agenda_code', 'N/A')}"
                )
                print(
                    f"        - sender_organization: {event['iacs_info'].get('sender_organization', 'N/A')}"
                )
                print(f"      Semantic 정보:")
                print(
                    f"        - mail_type: {event['semantic_info'].get('mail_type', 'N/A')}"
                )
                print(
                    f"        - has_deadline: {event['semantic_info'].get('has_deadline', False)}"
                )
                keywords = event["semantic_info"].get("keywords", [])[:5]
                print(
                    f"        - keywords: {', '.join(keywords) if keywords else 'N/A'}"
                )

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
