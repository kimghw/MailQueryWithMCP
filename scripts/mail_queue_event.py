#!/usr/bin/env python3
# scripts/mail_queue_event.py
"""
이벤트 발행 테스트 스크립트 - 실제 메일 조회 버전
메일 처리 → 이벤트 발행 → Kafka 이벤트 확인
"""

import asyncio
import json
import os
import re
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infra.core.config import get_config
from infra.core.kafka_client import get_kafka_client
from infra.core.logger import get_logger
from modules.keyword_extractor.services.dashboard_event_service import (
    DashboardEventService,
)
from modules.mail_process.mail_processor_orchestrator import MailProcessorOrchestrator
from modules.mail_process.services.event_service import MailEventService
from modules.mail_query.mail_query_orchestrator import MailQueryOrchestrator
from modules.mail_query.mail_query_schema import (
    MailQueryFilters,
    MailQueryRequest,
    PaginationOptions,
)

logger = get_logger(__name__)

# ============================
# 기본 설정값 (수정 가능)
# ============================
DEFAULT_USER_ID = "krsdtp"  # 기본 사용자 ID
DEFAULT_RESULT_PATH = "./data/result"  # 결과 저장 경로 (상대 경로로 변경)
DEFAULT_SAVE_JSON = True  # JSON 파일 자동 저장 여부
DEFAULT_SAVE_CSV = True  # CSV 파일 자동 저장 여부
DEFAULT_SAVE_SUMMARY = True  # 요약 리포트 자동 저장 여부
DEFAULT_AUTO_SAVE = True  # 테스트 완료 후 자동 저장 여부 (False면 사용자에게 물어봄)
DEFAULT_MAX_SAMPLE_EVENTS = 10  # 샘플 이벤트 최대 저장 개수
DEFAULT_MAX_MAIL_DISPLAY = 5  # 화면에 표시할 메일 최대 개수


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
        self.processed_mail_data = {}  # 처리된 메일 데이터 저장

        # 이벤트 저장을 위한 데이터
        self.test_results = {
            "test_info": {},
            "mail_summary": {},
            "event_summary": {},
            "processed_mails": [],
            "published_events": [],
            "event_samples": [],
        }

    async def test_real_mail_events(
        self, user_id: str = "krsdtp", days_back: int = 49, max_mails: int = 7
    ):
        """실제 메일로 이벤트 발행 테스트"""

        print(f"\n🚀 실제 메일 이벤트 발행 테스트")
        print("=" * 80)
        print(f"👤 사용자: {user_id}")
        print(f"📅 기간: 최근 {days_back}일 (약 {days_back//7}주)")
        print(f"📊 메일 수: {max_mails}개")

        # 테스트 정보 저장
        self.test_results["test_info"] = {
            "user_id": user_id,
            "days_back": days_back,
            "max_mails": max_mails,
            "test_start_time": datetime.now().isoformat(),
            "test_end_time": None,
        }

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

            # 메일 요약 정보 저장
            self.test_results["mail_summary"] = {
                "total_queried": len(query_response.messages),
                "query_time_ms": query_time_ms,
                "date_from": (datetime.now() - timedelta(days=days_back)).isoformat(),
                "date_to": datetime.now().isoformat(),
            }

            # 조회된 메일 상세 정보
            print(f"\n📋 조회된 실제 메일:")
            display_count = min(len(query_response.messages), DEFAULT_MAX_MAIL_DISPLAY)
            for i, mail in enumerate(query_response.messages[:display_count]):
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

                # 메일 정보 저장
                mail_info = {
                    "mail_id": mail.id,
                    "subject": mail.subject,
                    "sender_name": sender_name,
                    "sender_address": sender_addr,
                    "received_time": str(mail.received_date_time),
                    "has_attachments": mail.has_attachments,
                }
                self.test_results["processed_mails"].append(mail_info)

            # 모든 메일 정보는 저장하되, 화면에는 일부만 표시
            if len(query_response.messages) > display_count:
                print(
                    f"\n  ... 외 {len(query_response.messages) - display_count}개 메일 (전체 데이터는 결과 파일에 저장됨)"
                )

                # 나머지 메일들도 저장
                for mail in query_response.messages[display_count:]:
                    sender_info = mail.sender or mail.from_address or {}
                    sender_addr = ""
                    sender_name = ""
                    if isinstance(sender_info, dict):
                        email_addr = sender_info.get("emailAddress", {})
                        if isinstance(email_addr, dict):
                            sender_addr = email_addr.get("address", "")
                            sender_name = email_addr.get("name", "")

                    mail_info = {
                        "mail_id": mail.id,
                        "subject": mail.subject,
                        "sender_name": sender_name,
                        "sender_address": sender_addr,
                        "received_time": str(mail.received_date_time),
                        "has_attachments": mail.has_attachments,
                    }
                    self.test_results["processed_mails"].append(mail_info)

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

                # 모든 배치가 처리될 때까지 반복
                all_process_results = []
                batch_count = 0

                while True:
                    # 큐 상태 확인
                    queue_status = (
                        await self.mail_processor_orchestrator.queue_service.get_queue_status()
                    )
                    if queue_status["is_empty"]:
                        print(f"\n✅ 모든 배치 처리 완료")
                        break

                    batch_count += 1
                    print(
                        f"\n📦 배치 #{batch_count} 처리 중 (남은 큐: {queue_status['queue_size']}개)..."
                    )

                    # process_batch는 이미 이벤트를 발행함
                    process_results = (
                        await self.mail_processor_orchestrator.process_batch()
                    )
                    all_process_results.extend(process_results)

                    print(
                        f"  - 배치 #{batch_count} 완료: {len(process_results)}개 처리"
                    )

                # 추가로 생성된 비동기 태스크들이 있다면 대기
                if hasattr(self.mail_processor_orchestrator, "_batch_tasks"):
                    if self.mail_processor_orchestrator._batch_tasks:
                        print(f"\n⏳ 남은 비동기 태스크 대기 중...")
                        await asyncio.gather(
                            *self.mail_processor_orchestrator._batch_tasks,
                            return_exceptions=True,
                        )
                        print(f"✅ 모든 비동기 태스크 완료")

                process_time_ms = (datetime.now() - start_time).total_seconds() * 1000
                process_results = all_process_results  # 전체 결과 사용

                print(f"\n✅ 전체 배치 처리 완료 (소요시간: {process_time_ms:.0f}ms)")
                print(f"  - 총 배치 수: {batch_count}")
                print(f"  - 총 처리된 메일: {len(process_results)}개")

                # 처리 결과 분석 (이벤트는 이미 발행됨)
                await self._analyze_processing_results(
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

            # 실제 이벤트 구조 안내
            print(f"\n⚠️  중요 안내:")
            print(f"   - 이 테스트는 메일 처리 결과만 추적합니다.")
            print(
                f"   - 실제 이벤트는 mail_process 모듈 내부에서 다음 구조로 발행됩니다:"
            )
            print(f"     * event_info.sentDateTime")
            print(f"     * event_info.hasAttachments")
            print(f"     * event_info.subject")
            print(f"     * event_info.webLink")
            print(f"     * event_info.body")
            print(f"     * event_info.sender / sender_address")
            print(f"     * event_info.agenda_code / agenda_base 등 IACS 정보")
            print(f"     * event_info.keywords (OpenRouter 추출)")
            print(f"     * event_info.deadline / has_deadline 등")
            print(f"   - 실제 이벤트 데이터는 Kafka 토픽에서 확인하세요.")

            # 테스트 종료 시간 기록
            self.test_results["test_info"]["test_end_time"] = datetime.now().isoformat()

            # 이벤트 요약 정보 저장
            self.test_results["event_summary"] = dict(self.event_stats)
            self.test_results["event_samples"] = self.sample_events

            # 처리 결과 정보 저장 (실제 이벤트는 아님)
            self.test_results["processing_summary"] = {
                "total_mails_queried": len(query_response.messages),
                "total_mails_enqueued": enqueue_result.get("enqueued", 0),
                "total_mails_processed": (
                    len(process_results) if "process_results" in locals() else 0
                ),
                "note": "실제 이벤트 데이터는 mail_process 모듈 내부에서 발행되며, 이 테스트는 처리 결과만 추적합니다.",
            }

            # 결과 저장 여부 확인
            if DEFAULT_AUTO_SAVE:
                print(f"\n💾 테스트 결과를 자동으로 저장합니다...")
                await self._save_test_results()
            else:
                save_results = (
                    input("\n\n💾 테스트 결과를 파일로 저장하시겠습니까? (y/n): ")
                    .strip()
                    .lower()
                )
                if save_results == "y":
                    await self._save_test_results()

        except Exception as e:
            logger.error(f"테스트 중 오류 발생: {str(e)}", exc_info=True)
            print(f"\n❌ 오류 발생: {str(e)}")
        finally:
            await self.mail_query_orchestrator.close()

    async def _analyze_processing_results(
        self, process_results: List[Any], original_mails: List[Any]
    ):
        """처리 결과 분석 (이벤트는 이미 발행됨)"""

        print(f"\n📊 처리 결과 분석:")

        # 메일별 처리 결과 매핑
        mail_map = {mail.id: mail for mail in original_mails}

        for result in process_results:
            if result.success and result.mail_id in mail_map:
                mail = mail_map[result.mail_id]

                print(f"\n  📧 메일 ID: {result.mail_id[:20]}...")
                print(f"     제목: {mail.subject[:50]}...")
                print(f"     ✅ 처리 성공")

                # keywords가 리스트인 경우
                if isinstance(result.keywords, list):
                    print(f"     키워드: {len(result.keywords)}개")
                    if result.keywords:
                        print(f"     - {', '.join(result.keywords[:5])}")

                # 이벤트 발행 성공으로 간주 (process_batch에서 이미 발행)
                self.event_stats["email.received"] += 1

                # 샘플 이벤트 저장
                if len(self.sample_events) < DEFAULT_MAX_SAMPLE_EVENTS:
                    self.sample_events.append(
                        {
                            "type": "email.received",
                            "mail_id": result.mail_id,
                            "subject": mail.subject[:50],
                            "keywords": (
                                result.keywords
                                if isinstance(result.keywords, list)
                                else []
                            ),
                        }
                    )

                # 참고: 실제 이벤트 데이터는 process_batch 내부에서 발행되므로
                # 여기서는 예상되는 구조만 저장 (실제 이벤트와 다를 수 있음)
                print(
                    f"\n     ⚠️  주의: 실제 이벤트 데이터는 mail_process 모듈 내부에서 발행됩니다."
                )
                print(f"     실제 이벤트 확인은 Kafka 토픽에서 직접 확인하세요.")

        print(f"\n📈 처리 결과 요약:")
        print(f"  - 총 처리된 메일: {len(process_results)}개")
        print(f"  - 성공: {sum(1 for r in process_results if r.success)}개")
        print(f"  - 실패: {sum(1 for r in process_results if not r.success)}개")

    def _convert_mail_to_dict(self, mail: Any) -> Dict[str, Any]:
        """메일 객체를 딕셔너리로 변환 - 실제 이벤트 필드만 포함"""
        # 실제 event_service.py에서 사용하는 필드들만 포함
        mail_dict = {
            "id": mail.id,
            "subject": mail.subject or "",
            "receivedDateTime": mail.received_date_time,
            "hasAttachments": getattr(mail, "has_attachments", False),
            "webLink": getattr(mail, "web_link", ""),
            "body": {
                "content": getattr(mail, "body_preview", "") or "",
            },
        }

        # 발신자 정보 추가 (실제 이벤트 구조에 맞춤)
        sender_info = mail.sender or mail.from_address or {}
        if isinstance(sender_info, dict):
            email_addr = sender_info.get("emailAddress", {})
            mail_dict["sender"] = {"emailAddress": email_addr}
            mail_dict["from"] = {"emailAddress": email_addr}

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
        print(f"  - email.received: 모든 처리된 메일에 대해 발행")
        print(f"     포함 정보: 메일 정보, 본문, IACS 정보, 키워드, 구조화된 분석")

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
                # IACS 정보가 제대로 추출되었다면 대시보드 이벤트도 발행되었을 것
                self.event_stats["email-dashboard"] += 1

                # 실제 이벤트 구조에 맞춘 이벤트 정보 저장
                dashboard_event = {
                    "event_type": "email.received",
                    "event_id": str(uuid.uuid4()),
                    "mail_id": mail.id,
                    "occurred_at": datetime.now().isoformat(),
                    "event_info": {
                        # 실제 event_service.py에서 발행하는 필드들만 포함
                        "sentDateTime": str(mail.received_date_time),
                        "hasAttachments": getattr(mail, "has_attachments", False),
                        "subject": subject,
                        "webLink": getattr(mail, "web_link", ""),
                        "body": getattr(mail, "body_preview", "") or "",
                        "sender": "",
                        "sender_address": sender_addr,
                        "agenda_code": agenda_pattern,
                        "agenda_base": agenda_pattern,
                        "sender_organization": sender_org,
                        "sender_type": "MEMBER" if is_iacs else "UNKNOWN",
                        "keywords": [],  # 실제로는 OpenRouter에서 추출됨
                        "deadline": None,
                        "has_deadline": False,
                        "mail_type": None,
                        "decision_status": None,
                    },
                }
                self.test_results["published_events"].append(dashboard_event)
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
                keywords = event.get("keywords", [])
                if keywords:
                    print(f"      키워드: {', '.join(keywords[:5])}")
                else:
                    print(f"      키워드: 없음")

    async def cleanup(self):
        """리소스 정리"""
        try:
            # 메일 처리 오케스트레이터 정리
            if hasattr(self, "mail_processor_orchestrator"):
                await self.mail_processor_orchestrator.cleanup()

            # 메일 쿼리 오케스트레이터 정리
            if hasattr(self, "mail_query_orchestrator"):
                await self.mail_query_orchestrator.close()

            # 약간의 대기 시간을 주어 모든 비동기 작업이 완료되도록 함
            await asyncio.sleep(0.1)

            self.logger.info("모든 리소스 정리 완료")
        except Exception as e:
            self.logger.error(f"리소스 정리 중 오류: {str(e)}")

    async def _save_test_results(self):
        """테스트 결과를 파일로 저장"""
        try:
            # 저장 디렉토리 생성
            output_dir = Path(DEFAULT_RESULT_PATH)

            # 디렉토리 생성 시도
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                print(f"\n📁 저장 디렉토리 확인: {output_dir}")
            except PermissionError:
                print(f"\n❌ 권한 오류: {output_dir} 디렉토리를 생성할 수 없습니다.")
                # 대체 경로 사용
                output_dir = Path("./test_results")
                output_dir.mkdir(parents=True, exist_ok=True)
                print(f"📁 대체 경로 사용: {output_dir}")
            except Exception as e:
                print(f"\n❌ 디렉토리 생성 오류: {str(e)}")
                # 현재 디렉토리 사용
                output_dir = Path(".")
                print(f"📁 현재 디렉토리 사용: {output_dir}")

            # 절대 경로 출력
            print(f"📁 실제 저장 경로: {output_dir.absolute()}")

            # 파일명 생성 (timestamp 포함)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            user_id = self.test_results["test_info"]["user_id"]
            days = self.test_results["test_info"]["days_back"]
            mails = self.test_results["test_info"]["max_mails"]

            saved_files = []

            # JSON 파일로 저장
            if DEFAULT_SAVE_JSON:
                filename = f"event_test_{user_id}_{days}d_{mails}m_{timestamp}.json"
                filepath = output_dir / filename

                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(self.test_results, f, ensure_ascii=False, indent=2)

            # 이벤트 상세 파일 별도 저장
            if DEFAULT_SAVE_JSON:
                # 이벤트 상세 정보만 별도 파일로 저장
                events_detail_filename = (
                    f"event_details_{user_id}_{days}d_{mails}m_{timestamp}.json"
                )
                events_detail_filepath = output_dir / events_detail_filename

                events_detail = {
                    "test_info": self.test_results["test_info"],
                    "event_summary": self.test_results["event_summary"],
                    "total_events": len(self.test_results["published_events"]),
                    "events": self.test_results["published_events"],
                }

                with open(events_detail_filepath, "w", encoding="utf-8") as f:
                    json.dump(events_detail, f, ensure_ascii=False, indent=2)

                saved_files.append(("이벤트 상세", events_detail_filepath))
                print(f"✅ 이벤트 상세 파일 저장 완료: {events_detail_filepath}")
                print(
                    f"   → 총 {len(self.test_results['published_events'])}개의 이벤트 상세 정보 포함"
                )

                # 파일 크기 확인
                file_size = events_detail_filepath.stat().st_size
                print(f"   파일 크기: {file_size:,} bytes")

            # 요약 리포트 생성
            if DEFAULT_SAVE_SUMMARY:
                summary_filename = (
                    f"event_test_summary_{user_id}_{days}d_{mails}m_{timestamp}.txt"
                )
                summary_filepath = output_dir / summary_filename

                with open(summary_filepath, "w", encoding="utf-8") as f:
                    f.write("=" * 80 + "\n")
                    f.write("메일 이벤트 발행 테스트 결과 요약\n")
                    f.write("=" * 80 + "\n\n")

                    # 테스트 정보
                    f.write("## 테스트 정보\n")
                    f.write(f"- 사용자: {user_id}\n")
                    f.write(f"- 조회 기간: {days}일\n")
                    f.write(f"- 메일 수: {mails}개\n")
                    f.write(
                        f"- 테스트 시작: {self.test_results['test_info']['test_start_time']}\n"
                    )
                    f.write(
                        f"- 테스트 종료: {self.test_results['test_info']['test_end_time']}\n\n"
                    )

                    # 메일 요약
                    f.write("## 메일 처리 요약\n")
                    mail_summary = self.test_results.get("mail_summary", {})
                    f.write(
                        f"- 조회된 메일: {mail_summary.get('total_queried', 0)}개\n"
                    )
                    f.write(
                        f"- 조회 시간: {mail_summary.get('query_time_ms', 0):.0f}ms\n\n"
                    )

                    # 이벤트 발행 요약
                    f.write("## 이벤트 발행 요약\n")
                    for event_type, count in self.test_results.get(
                        "event_summary", {}
                    ).items():
                        f.write(f"- {event_type}: {count}개\n")
                    f.write(
                        f"\n총 발행된 이벤트: {len(self.test_results.get('published_events', []))}개\n\n"
                    )

                    # 발행된 모든 이벤트 상세 정보
                    f.write("\n## 주의사항\n")
                    f.write(
                        "이 테스트는 메일 처리 결과를 추적한 것이며, 실제 Kafka 이벤트와는 다를 수 있습니다.\n"
                    )
                    f.write(
                        "실제 이벤트는 mail_process.services.event_service에서 다음 구조로 발행됩니다:\n"
                    )
                    f.write("- event_info.sentDateTime (발송 시간)\n")
                    f.write("- event_info.hasAttachments (첨부파일 여부)\n")
                    f.write("- event_info.subject (제목)\n")
                    f.write("- event_info.webLink (웹 링크)\n")
                    f.write("- event_info.body (본문)\n")
                    f.write("- event_info.sender / sender_address (발신자 정보)\n")
                    f.write("- event_info.agenda_code / agenda_base 등 (IACS 정보)\n")
                    f.write("- event_info.keywords (추출된 키워드)\n")
                    f.write("- event_info.deadline / has_deadline (마감일 정보)\n\n")

                    f.write("\n## 처리 결과 요약\n")
                    f.write("-" * 80 + "\n")

                    if "processing_summary" in self.test_results:
                        ps = self.test_results["processing_summary"]
                        f.write(f"조회된 메일: {ps.get('total_mails_queried', 0)}개\n")
                        f.write(
                            f"큐에 저장된 메일: {ps.get('total_mails_enqueued', 0)}개\n"
                        )
                        f.write(
                            f"처리된 메일: {ps.get('total_mails_processed', 0)}개\n"
                        )

                    f.write("\n" + "-" * 80 + "\n")

                saved_files.append(("요약 리포트", summary_filepath))
                print(f"✅ 요약 리포트 저장 완료: {summary_filepath}")

                # 파일 크기 확인
                file_size = summary_filepath.stat().st_size
                print(f"   파일 크기: {file_size:,} bytes")

            # CSV 파일로도 저장
            if DEFAULT_SAVE_CSV:
                await self._save_as_csv(output_dir, timestamp, user_id, days, mails)
                csv_filename = f"events_{user_id}_{days}d_{mails}m_{timestamp}.csv"
                saved_files.append(("CSV", output_dir / csv_filename))
            elif not DEFAULT_AUTO_SAVE:
                # 자동 저장이 아닌 경우에만 CSV 저장 여부 묻기
                save_csv = (
                    input("\n📊 CSV 파일로도 저장하시겠습니까? (y/n): ").strip().lower()
                )
                if save_csv == "y":
                    await self._save_as_csv(output_dir, timestamp, user_id, days, mails)
                    csv_filename = f"events_{user_id}_{days}d_{mails}m_{timestamp}.csv"
                    saved_files.append(("CSV", output_dir / csv_filename))

            # 저장 완료 메시지
            print(f"\n{'=' * 60}")
            print(f"📁 모든 파일이 다음 경로에 저장되었습니다:")
            print(f"   {output_dir.absolute()}")
            print(f"\n📄 저장된 파일 목록:")
            for file_type, file_path in saved_files:
                print(f"   - {file_type}: {file_path.name}")
            print(f"\n⚠️  참고: 저장된 데이터는 테스트 추적 정보입니다.")
            print(f"   실제 Kafka 이벤트 구조는 mail_process 모듈 문서를 참조하세요.")
            print(f"{'=' * 60}")

        except Exception as e:
            print(f"\n❌ 결과 저장 중 오류 발생: {str(e)}")
            logger.error("결과 저장 실패", exc_info=True)

    async def _save_as_csv(
        self, output_dir: Path, timestamp: str, user_id: str, days: int, mails: int
    ):
        """CSV 형식으로 저장"""
        import csv

        try:
            # 이벤트 목록 CSV
            events_csv_filename = f"events_{user_id}_{days}d_{mails}m_{timestamp}.csv"
            events_csv_path = output_dir / events_csv_filename

            with open(events_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "Event Type",
                        "Mail ID",
                        "Subject",
                        "Sender Name",
                        "Sender Address",
                        "Body Preview",
                        "Keywords",
                        "Keywords Count",
                        "Has Attachments",
                        "Received Time",
                        "Event Timestamp",
                    ]
                )

                for event in self.test_results.get("published_events", []):
                    if event.get("event_type") == "email.received":
                        event_info = event.get("event_info", {})
                        writer.writerow(
                            [
                                event.get("event_type", ""),
                                event.get("mail_id", ""),
                                event_info.get("subject", "")[:100],
                                event_info.get("sender", ""),
                                event_info.get("sender_address", ""),
                                event_info.get("body", "")[:200],  # 본문 미리보기 200자
                                ", ".join(event_info.get("keywords", [])),
                                len(event_info.get("keywords", [])),
                                "Y" if event_info.get("hasAttachments") else "N",
                                event_info.get("sentDateTime", ""),
                                event.get("occurred_at", ""),
                            ]
                        )

            print(f"✅ CSV 파일 저장 완료: {events_csv_path}")

            # 파일 크기 확인
            file_size = events_csv_path.stat().st_size
            print(f"   파일 크기: {file_size:,} bytes")

        except Exception as e:
            print(f"❌ CSV 저장 중 오류: {str(e)}")


# 사전 정의된 테스트 시나리오
TEST_SCENARIOS = {
    "1": {
        "name": "기본 테스트",
        "user_id": DEFAULT_USER_ID,
        "days": 7,
        "mails": 7,
        "description": "최근 1주일, 7개 메일",
    },
    "2": {
        "name": "30일 테스트",
        "user_id": DEFAULT_USER_ID,
        "days": 30,
        "mails": 300,
        "description": "최근 30일, 300개 메일",
    },
    "3": {
        "name": "90일 테스트",
        "user_id": DEFAULT_USER_ID,
        "days": 90,
        "mails": 900,
        "description": "최근 90일, 900개 메일",
    },
    "4": {
        "name": "사용자 정의",
        "user_id": None,
        "days": None,
        "mails": None,
        "description": "직접 입력",
    },
}


async def main():
    """메인 함수"""
    print("\n📮 실제 메일 이벤트 발행 테스트")
    print("=" * 80)

    # 현재 설정 표시
    print("\n⚙️  현재 설정:")
    print(f"  - 기본 사용자: {DEFAULT_USER_ID}")
    print(f"  - 결과 저장 경로: {DEFAULT_RESULT_PATH}")
    print(f"  - 자동 저장: {'활성화' if DEFAULT_AUTO_SAVE else '비활성화'}")
    if DEFAULT_AUTO_SAVE:
        print(f"    - JSON: {'저장' if DEFAULT_SAVE_JSON else '저장 안함'}")
        print(f"    - CSV: {'저장' if DEFAULT_SAVE_CSV else '저장 안함'}")
        print(f"    - 요약: {'저장' if DEFAULT_SAVE_SUMMARY else '저장 안함'}")

    test = EventPublishingTest()

    try:
        print("\n테스트 시나리오 선택:")
        print("-" * 40)
        for key, scenario in TEST_SCENARIOS.items():
            print(f"[{key}] {scenario['name']}: {scenario['description']}")

        print("\n[0] 종료")

        choice = input("\n선택하세요 (0-4): ").strip()

        if choice == "0":
            print("테스트를 종료합니다.")
            return

        if choice not in TEST_SCENARIOS:
            print("잘못된 선택입니다.")
            return

        scenario = TEST_SCENARIOS[choice]

        if choice == "4":
            # 사용자 정의
            print("\n사용자 정의 테스트 설정")
            print("-" * 40)
            user_id = (
                input(f"사용자 ID (기본: {DEFAULT_USER_ID}): ").strip()
                or DEFAULT_USER_ID
            )
            days = int(input("조회할 일 수 (기본: 7): ") or "7")
            mails = int(input("메일 수 (기본: 7): ") or "7")
        else:
            user_id = scenario["user_id"]
            days = scenario["days"]
            mails = scenario["mails"]

            print(f"\n선택한 시나리오: {scenario['name']}")
            print(f"- 사용자: {user_id}")
            print(f"- 기간: {days}일")
            print(f"- 메일 수: {mails}개")

            confirm = input("\n계속 진행하시겠습니까? (y/n): ").strip().lower()
            if confirm != "y":
                print("테스트를 취소합니다.")
                return

        # 테스트 실행
        await test.test_real_mail_events(
            user_id=user_id, days_back=days, max_mails=mails
        )

    except KeyboardInterrupt:
        print("\n\n테스트가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {str(e)}")
        logger.error("메인 함수 오류", exc_info=True)
    finally:
        await test.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
