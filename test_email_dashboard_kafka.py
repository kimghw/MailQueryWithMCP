#!/usr/bin/env python3
"""
Email Dashboard Kafka 통합 테스트
기존 email.received 토픽을 사용하여 이벤트 발행 및 처리 테스트
"""

import sys
import os
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import threading

# 프로젝트 루트 경로 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from infra.core import get_kafka_client, get_database_manager, get_logger, get_config
from modules.mail_dashboard import (
    EmailDashboardService,
    EmailDashboardRepository,
    EmailDashboardQuery,
    get_dashboard_service,
)


class EmailDashboardKafkaTest:
    """Email Dashboard Kafka 통합 테스트"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.kafka = get_kafka_client()
        self.db = get_database_manager()

        # Email Dashboard 서비스 가져오기
        self.service = get_dashboard_service()
        self.repository = EmailDashboardRepository()
        self.query = EmailDashboardQuery()

        # Kafka 토픽 설정
        self.topic = self.config.get_setting(
            "KAFKA_TOPIC_EMAIL_EVENTS", "email.received"
        )
        self.logger.info(f"사용할 Kafka 토픽: {self.topic}")

    def setup(self) -> bool:
        """테스트 환경 설정"""
        try:
            self.logger.info("테스트 환경 설정 시작...")

            # 1. Email Dashboard 모듈 초기화
            if not self.service.initialize():
                self.logger.error("Email Dashboard 모듈 초기화 실패")
                return False

            # 2. 기존 데이터 정리 (선택적)
            if "--clean" in sys.argv:
                self.logger.info("기존 데이터 정리 중...")
                self.repository.clear_all_data()

            # 3. 이벤트 구독 시작
            if not self.service.start_event_subscription():
                self.logger.error("이벤트 구독 시작 실패")
                return False

            # 구독이 준비될 때까지 대기
            time.sleep(2)

            self.logger.info("테스트 환경 설정 완료")
            return True

        except Exception as e:
            self.logger.error(f"테스트 환경 설정 실패: {str(e)}")
            return False

    def create_test_events(self) -> List[Dict[str, Any]]:
        """테스트용 이벤트 생성"""
        events = []

        # 1. 의장 발송 이벤트
        chair_event = {
            "event_type": "email.received",
            "event_id": f"test-chair-{int(time.time()*1000)}",
            "mail_id": "AAMkADY4YzAyZTE3-CHAIR",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "event_info": {
                "sentDateTime": "",
                "hasAttachments": False,
                "subject": "PL25016_ILa: IMO Expert Group on Data Harmonization (EGDH) 13 Session",
                "webLink": "",
                "body": """Dear SDTP Members,

1. This is to inform you that the IMO Expert Group on Data Harmonization (EGDH) 13th Session will be held from 15 to 19 July 2025.

2. The meeting will be held remotely.

3. Please find attached the provisional agenda for the meeting.

4. We would like to know whether SDTP representation is considered essential at this meeting.

Best regards,
IL SDTP Chair""",
                "sender": "SdtpPanelmail",
                "sender_address": "sdtp.panel@il.com",
                "agenda_code": "PL25016_ILa",
                "agenda_base": "PL25016",
                "agenda_base_version": "PL25016",
                "agenda_panel": "PL",
                "agenda_year": "25",
                "agenda_number": "016",
                "agenda_version": "",
                "response_org": None,
                "response_version": None,
                "sent_time": datetime.now(timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S UTC"
                ),
                "sender_type": "CHAIR",
                "sender_organization": "IL",
                "parsing_method": "pattern2_underscore_case_sensitive",
                "keywords": ["IMO", "EGDH", "meeting", "representation", "session"],
                "deadline": (datetime.now(timezone.utc) + timedelta(days=7)).strftime(
                    "%Y-%m-%d %H:%M:%S UTC"
                ),
                "has_deadline": True,
                "mail_type": "REQUEST",
                "decision_status": "created",
            },
        }
        events.append(chair_event)

        # 2. 멤버 응답 이벤트들
        member_responses = [
            ("BV", "BV does not consider SDTP representation essential"),
            ("KR", "KR supports SDTP representation at the meeting"),
            ("DNV", "DNV agrees with the proposal and will participate"),
            ("ABS", "ABS has no objection to the proposal"),
            ("CCS", "CCS will send representatives to the meeting"),
        ]

        for i, (org, response_text) in enumerate(member_responses):
            # 시간차를 두고 응답 생성
            response_time = datetime.now(timezone.utc) + timedelta(minutes=10 + i * 5)

            response_event = {
                "event_type": "email.received",
                "event_id": f"test-member-{org}-{int(time.time()*1000)}",
                "mail_id": f"AAMkADY4YzAyZTE3-{org}",
                "occurred_at": response_time.isoformat(),
                "event_info": {
                    "sentDateTime": "",
                    "hasAttachments": False,
                    "subject": f"PL25016_{org}a: IMO Expert Group on Data Harmonization (EGDH) 13 Session",
                    "webLink": "",
                    "body": f"""PL25016_{org}a: IMO Expert Group on Data Harmonization (EGDH) 13 Session

Dear Chair,

1. Reference is made to PL25016_ILa dated 05 Jun. 2025.

2. Answering item 4., {response_text} in the IMO Expert Group on Data Harmonization (EGDH) 13 Session.

Best Regards,
{org} SDTP Member""",
                    "sender": "SdtpPanelmail",
                    "sender_address": f"sdtp.panel@{org.lower()}.com",
                    "agenda_code": f"PL25016_{org}a",
                    "agenda_base": "PL25016",
                    "agenda_base_version": "PL25016",
                    "agenda_panel": "PL",
                    "agenda_year": "25",
                    "agenda_number": "016",
                    "agenda_version": "",
                    "response_org": org,
                    "response_version": "a",
                    "sent_time": response_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "sender_type": "MEMBER",
                    "sender_organization": org,
                    "parsing_method": "pattern2_underscore_case_sensitive",
                    "keywords": ["IMO", "EGDH", "response", "meeting"],
                    "deadline": None,
                    "has_deadline": False,
                    "mail_type": "RESPONSE",
                    "decision_status": "comment",
                },
            }
            events.append(response_event)

        # 3. agenda_code가 없는 이벤트 (pending 처리 테스트)
        invalid_event = {
            "event_type": "email.received",
            "event_id": f"test-invalid-{int(time.time()*1000)}",
            "mail_id": "AAMkADY4YzAyZTE3-INVALID",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "event_info": {
                "sentDateTime": "",
                "hasAttachments": False,
                "subject": "General Information - No Agenda Code",
                "webLink": "",
                "body": "This is a general information email without agenda code.",
                "sender": "SdtpPanelmail",
                "sender_address": "sdtp.panel@example.com",
                "agenda_code": None,  # agenda_code 없음
                "sent_time": datetime.now(timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S UTC"
                ),
                "sender_type": "CHAIR",
                "sender_organization": "IL",
                "parsing_method": "unknown",
                "keywords": ["information"],
                "deadline": None,
                "has_deadline": False,
                "mail_type": "NOTIFICATION",
                "decision_status": "created",
            },
        }
        events.append(invalid_event)

        return events

    def publish_events(self, events: List[Dict[str, Any]]) -> bool:
        """Kafka에 이벤트 발행"""
        try:
            self.logger.info(f"\n{len(events)}개 이벤트를 Kafka에 발행 중...")

            for i, event in enumerate(events):
                # 이벤트 발행
                success = self.kafka.produce_event(
                    topic=self.topic, event_data=event, key=event.get("event_id")
                )

                if success:
                    self.logger.info(
                        f"✓ 이벤트 발행 성공 [{i+1}/{len(events)}]: {event['event_id']}"
                    )
                    if event["event_info"].get("agenda_code"):
                        self.logger.info(
                            f"  - Agenda: {event['event_info']['agenda_code']}"
                        )
                        self.logger.info(
                            f"  - Type: {event['event_info']['sender_type']}"
                        )
                else:
                    self.logger.error(f"✗ 이벤트 발행 실패: {event['event_id']}")
                    return False

                # 처리 시간을 위한 딜레이
                time.sleep(0.5)

            self.logger.info("모든 이벤트 발행 완료")
            return True

        except Exception as e:
            self.logger.error(f"이벤트 발행 중 오류: {str(e)}")
            return False

    def wait_for_processing(self, wait_seconds: int = 5):
        """이벤트 처리 대기"""
        self.logger.info(f"\n이벤트 처리를 위해 {wait_seconds}초 대기 중...")
        for i in range(wait_seconds):
            print(f"\r대기 중... {wait_seconds - i}초 남음", end="", flush=True)
            time.sleep(1)
        print("\r대기 완료!                    ")

    def verify_results(self) -> bool:
        """처리 결과 검증"""
        try:
            self.logger.info("\n" + "=" * 60)
            self.logger.info("처리 결과 검증")
            self.logger.info("=" * 60)

            # 1. 통계 조회
            stats = self.repository.get_dashboard_stats(1)  # 오늘 데이터만
            self.logger.info("\n1. 대시보드 통계:")
            self.logger.info(f"  - 총 아젠다: {stats.get('total_agendas', 0)}")
            self.logger.info(f"  - 진행중 아젠다: {stats.get('pending_agendas', 0)}")
            self.logger.info(f"  - 완료된 아젠다: {stats.get('completed_agendas', 0)}")
            self.logger.info(f"  - 총 응답: {stats.get('total_responses', 0)}")
            self.logger.info(f"  - 미처리 이벤트: {stats.get('pending_events', 0)}")

            # 2. 아젠다 목록 조회
            agendas = self.query.get_agendas(limit=10)
            self.logger.info(f"\n2. 저장된 아젠다: {len(agendas)}개")

            for agenda in agendas:
                self.logger.info(f"\n  ✓ {agenda.agenda_code}")
                self.logger.info(f"    - 발송: {agenda.sender_organization}")
                self.logger.info(f"    - 시간: {agenda.sent_time}")
                self.logger.info(f"    - 상태: {agenda.decision_status}")

                # 응답 정보 조회
                detail = self.query.get_agenda_detail(agenda.agenda_base_version)
                if detail:
                    response_summary = detail.get("response_summary", {})
                    self.logger.info(
                        f"    - 응답: {response_summary.get('responded_count', 0)}/{response_summary.get('total_organizations', 0)}"
                    )

                    # 응답한 기관 표시
                    responded_orgs = response_summary.get("responded_organizations", [])
                    if responded_orgs:
                        self.logger.info(
                            f"    - 응답 기관: {', '.join(responded_orgs)}"
                        )

            # 3. 미처리 이벤트 확인
            pending_events = self.repository.get_pending_events(limit=10)
            if pending_events:
                self.logger.info(f"\n3. 미처리 이벤트: {len(pending_events)}개")
                for event in pending_events:
                    self.logger.info(f"  - {event.event_id}: {event.error_reason}")

            # 4. 테이블별 레코드 수 확인
            self.logger.info("\n4. 테이블별 레코드 수:")
            tables = [
                ("agenda_all", "모든 이벤트"),
                ("agenda_chair", "의장 아젠다"),
                ("agenda_responses_content", "응답 내용"),
                ("agenda_responses_receivedtime", "응답 시간"),
                ("agenda_pending", "미처리 이벤트"),
            ]

            for table_name, description in tables:
                count_result = self.db.fetch_one(
                    f"SELECT COUNT(*) as count FROM {table_name}"
                )
                count = count_result["count"] if count_result else 0
                self.logger.info(f"  - {table_name}: {count}개 ({description})")

            return True

        except Exception as e:
            self.logger.error(f"결과 검증 중 오류: {str(e)}")
            return False

    def run_test(self):
        """전체 테스트 실행"""
        try:
            print("\n" + "=" * 60)
            print("Email Dashboard Kafka 통합 테스트")
            print("=" * 60)

            # 1. 환경 설정
            if not self.setup():
                self.logger.error("테스트 환경 설정 실패")
                return False

            # 2. 테스트 이벤트 생성
            events = self.create_test_events()
            self.logger.info(f"\n생성된 테스트 이벤트: {len(events)}개")

            # 3. Kafka에 이벤트 발행
            if not self.publish_events(events):
                self.logger.error("이벤트 발행 실패")
                return False

            # 4. 처리 대기
            self.wait_for_processing(5)

            # 5. 결과 검증
            if not self.verify_results():
                self.logger.error("결과 검증 실패")
                return False

            self.logger.info("\n✅ 테스트 완료!")
            return True

        except Exception as e:
            self.logger.error(f"테스트 실행 중 오류: {str(e)}")
            return False
        finally:
            # 이벤트 구독 중지
            self.service.stop_event_subscription()

    def test_single_event(self, event_type: str = "chair"):
        """단일 이벤트 테스트"""
        try:
            print(f"\n단일 이벤트 테스트: {event_type}")

            if not self.setup():
                return False

            # 이벤트 생성
            if event_type == "chair":
                event = self.create_test_events()[0]  # 의장 이벤트
            elif event_type == "member":
                event = self.create_test_events()[1]  # 첫번째 멤버 응답
            elif event_type == "invalid":
                event = self.create_test_events()[-1]  # 잘못된 이벤트
            else:
                self.logger.error(f"알 수 없는 이벤트 타입: {event_type}")
                return False

            # 발행
            self.publish_events([event])

            # 대기
            self.wait_for_processing(3)

            # 검증
            self.verify_results()

            return True

        finally:
            self.service.stop_event_subscription()


def main():
    """메인 함수"""
    tester = EmailDashboardKafkaTest()

    # 명령행 인자 확인
    if len(sys.argv) > 1:
        if sys.argv[1] == "--single":
            # 단일 이벤트 테스트
            event_type = sys.argv[2] if len(sys.argv) > 2 else "chair"
            tester.test_single_event(event_type)
        elif sys.argv[1] == "--clean":
            # 전체 테스트 (데이터 정리 포함)
            tester.run_test()
        else:
            print("사용법:")
            print("  python test_email_dashboard_kafka.py          # 전체 테스트")
            print(
                "  python test_email_dashboard_kafka.py --clean  # 데이터 정리 후 테스트"
            )
            print(
                "  python test_email_dashboard_kafka.py --single chair   # 의장 이벤트만"
            )
            print(
                "  python test_email_dashboard_kafka.py --single member  # 멤버 응답만"
            )
            print(
                "  python test_email_dashboard_kafka.py --single invalid # 잘못된 이벤트"
            )
    else:
        # 전체 테스트 실행
        tester.run_test()


if __name__ == "__main__":
    main()
