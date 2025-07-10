#!/usr/bin/env python3
"""
이벤트 데이터 수집 및 저장 스크립트

Kafka에서 이벤트를 가져와서 Email Dashboard에 저장합니다.

사용법:
    python event_data_collector.py [옵션]

옵션:
    --topic TOPIC           Kafka 토픽 (기본값: email.received)
    --max-messages N        최대 처리 메시지 수 (기본값: 100)
    --dry-run              실제 저장하지 않고 테스트만 실행
    --verbose              상세 로그 출력
    --from-beginning       처음부터 모든 이벤트 읽기 (새 컨슈머 그룹 사용)
    --reset-offset         기존 컨슈머 그룹의 offset 초기화
    --consumer-group ID    사용할 컨슈머 그룹 ID

예시:
    # 기본 실행 (100개 메시지 처리)
    python event_data_collector.py

    # 처음부터 모든 이벤트 읽기
    python event_data_collector.py --from-beginning --max-messages 1000

    # 기존 컨슈머 그룹 offset 초기화 후 읽기
    python event_data_collector.py --reset-offset --max-messages 1000

    # 새로운 컨슈머 그룹으로 처음부터 읽기
    python event_data_collector.py --consumer-group new-collector-group --from-beginning

    # 드라이런 모드로 테스트
    python event_data_collector.py --dry-run --verbose --from-beginning
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from infra.core import get_config, get_kafka_client, get_logger
from modules.mail_dashboard import EmailDashboardOrchestrator


class EventDataCollector:
    """Kafka에서 이벤트 데이터를 수집하여 Email Dashboard에 저장"""

    def __init__(
        self, dry_run: bool = False, verbose: bool = False, reset_tables: bool = True
    ):
        self.dry_run = dry_run
        self.verbose = verbose
        self.reset_tables = reset_tables
        self.logger = get_logger(__name__)

        # Kafka 클라이언트
        self.kafka_client = get_kafka_client()
        self.config = get_config()

        # Email Dashboard 오케스트레이터
        self.orchestrator = EmailDashboardOrchestrator()

        # 테이블 초기화 (옵션)
        if self.reset_tables:
            self._reset_dashboard_tables()

        # 수집된 이벤트들
        self.collected_events = []

        # 통계
        self.stats = {
            "total_consumed": 0,
            "email_events": 0,
            "other_events": 0,
            "chair_events": 0,
            "member_events": 0,
            "unknown_sender_events": 0,
            "other_sender_events": 0,
            "processed_success": 0,
            "processed_failed": 0,
            "errors": [],
        }

        # 분류된 이벤트들
        self.classified_events = {"chair": [], "member": [], "unknown": [], "other": []}

    def _reset_dashboard_tables(self) -> None:
        """Dashboard 테이블을 초기화합니다"""
        try:
            self.logger.info("Email Dashboard 테이블 초기화 시작")

            # 기존 데이터 삭제
            result = self.orchestrator.clear_all_data()

            if result.get("success"):
                self.logger.info(
                    f"테이블 초기화 완료: {result.get('total_deleted', 0)}개 레코드 삭제"
                )
            else:
                self.logger.warning(
                    f"테이블 초기화 실패: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            self.logger.error(f"테이블 초기화 중 오류: {str(e)}")

    def classify_event(self, event: Dict[str, Any]) -> str:
        """이벤트를 chair, member, unknown, other로 분류합니다"""
        try:
            event_info = event.get("event_info", {})
            sender_type = event_info.get("sender_type")

            # sender_type이 None이거나 빈 문자열인 경우 처리
            if not sender_type:
                # 디버깅을 위해 상세 정보 출력
                event_id = event.get("event_id", "unknown")
                event_type = event.get("event_type", "unknown")
                subject = event_info.get("subject", "No Subject")[:50]
                sender = event_info.get("sender", "unknown")
                self.logger.warning(
                    f"sender_type이 None인 이벤트 발견: "
                    f"event_id={event_id}, event_type={event_type}, "
                    f"sender={sender}, subject='{subject}'"
                )
                return "other"

            sender_type = str(sender_type).upper()

            if sender_type == "CHAIR":
                return "chair"
            elif sender_type == "MEMBER":
                return "member"
            elif sender_type == "UNKNOWN":
                return "unknown"
            else:
                return "other"

        except Exception as e:
            event_id = event.get("event_id", "unknown")
            self.logger.warning(f"이벤트 분류 실패 (event_id={event_id}): {str(e)}")
            return "other"

    def collect_events_from_kafka_original(
        self,
        topic: str,
        max_messages: int = 100,
        from_beginning: bool = False,
        reset_offset: bool = False,
        consumer_group: str = None,
    ) -> List[Dict[str, Any]]:
        """기존 Kafka 클라이언트를 사용해서 이벤트를 수집합니다"""

        self.logger.info(f"기존 Kafka 클라이언트로 이벤트 수집 시작")
        self.logger.info(f"토픽: {topic}")
        self.logger.info(f"최대 메시지: {max_messages}")
        self.logger.info(f"처음부터 읽기: {from_beginning}")
        self.logger.info(f"offset 초기화: {reset_offset}")

        # 컨슈머 그룹 ID 결정
        final_consumer_group = self.get_consumer_group_id(
            from_beginning, reset_offset, consumer_group
        )
        self.logger.info(f"컨슈머 그룹: {final_consumer_group}")

        # offset 초기화가 필요한 경우
        if reset_offset and not from_beginning:
            if self.reset_consumer_offset(topic, final_consumer_group):
                self.logger.info("offset 초기화 완료")
            else:
                self.logger.warning("offset 초기화 실패, 계속 진행")

        def message_handler(topic_name: str, message: Dict[str, Any]):
            """메시지 처리 핸들러"""
            self.collected_events.append(message)
            self.stats["total_consumed"] += 1

            event_type = message.get("event_type", "unknown")
            if event_type == "email.received":
                self.stats["email_events"] += 1

                # 이벤트 분류
                classification = self.classify_event(message)
                self.classified_events[classification].append(message)

                if classification == "chair":
                    self.stats["chair_events"] += 1
                elif classification == "member":
                    self.stats["member_events"] += 1
                else:
                    self.stats["unknown_sender_events"] += 1

            else:
                self.stats["other_events"] += 1
                self.classified_events["other"].append(message)

            if self.verbose:
                event_id = message.get("event_id", "unknown")
                if event_type == "email.received":
                    classification = self.classify_event(message)
                    sender_org = message.get("event_info", {}).get(
                        "sender_organization", "unknown"
                    )
                    self.logger.info(
                        f"수집: {classification.upper()} - {sender_org} - {event_id}"
                    )
                else:
                    self.logger.info(f"수집: {event_type} - {event_id}")

            # 최대 개수 도달 시 중단
            if len(self.collected_events) >= max_messages:
                return False  # 수집 중단

        try:
            # Kafka에서 이벤트 소비
            self.kafka_client.consume_events(
                topics=[topic],
                message_handler=message_handler,
                consumer_group_id=final_consumer_group,
                max_messages=max_messages,
            )

        except Exception as e:
            self.logger.error(f"기존 Kafka 이벤트 수집 실패: {str(e)}")
            raise

        self.logger.info(f"수집 완료: {len(self.collected_events)}개 이벤트")
        return self.collected_events
        """컨슈머 그룹의 offset을 초기화합니다"""
        try:
            self.logger.info(f"컨슈머 그룹 offset 초기화: {consumer_group}")

            # kafka-python을 사용한 offset 초기화
            from kafka import KafkaConsumer
            from kafka.structs import TopicPartition

            # 임시 컨슈머 생성
            consumer = KafkaConsumer(
                bootstrap_servers=self.config.get_setting(
                    "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
                ).split(","),
                group_id=consumer_group,
                auto_offset_reset="earliest",
                enable_auto_commit=False,
                consumer_timeout_ms=5000,  # 5초 타임아웃
            )

            # 토픽의 파티션 정보 가져오기
            partitions = consumer.partitions_for_topic(topic)
            if not partitions:
                self.logger.error(f"토픽 파티션 정보를 가져올 수 없음: {topic}")
                consumer.close()
                return False

            # 각 파티션의 offset을 earliest로 설정
            topic_partitions = [TopicPartition(topic, p) for p in partitions]
            consumer.assign(topic_partitions)

            # earliest offset으로 이동
            consumer.seek_to_beginning(*topic_partitions)

            # offset 커밋
            consumer.commit()

            consumer.close()
            self.logger.info(f"offset 초기화 완료: {len(topic_partitions)}개 파티션")
            return True

        except Exception as e:
            self.logger.error(f"offset 초기화 실패: {str(e)}")
            return False

    def get_consumer_group_id(
        self, from_beginning: bool, reset_offset: bool, custom_group: str = None
    ) -> str:
        """적절한 컨슈머 그룹 ID를 반환합니다"""
        if custom_group:
            return custom_group

        base_group = self.config.get_setting("KAFKA_CONSUMER_GROUP_ID", "dashboard")

        if from_beginning:
            # 처음부터 읽기 위해 타임스탬프 기반 새 그룹 생성
            timestamp = int(time.time())
            return f"{base_group}-collector-{timestamp}"
        elif reset_offset:
            # 기존 그룹의 offset 초기화
            return f"{base_group}-collector"
        else:
            # 기본 컨슈머 그룹
            return f"{base_group}-collector"

    def collect_events_from_kafka_direct(
        self,
        topic: str,
        max_messages: int = 100,
        from_beginning: bool = False,
    ) -> List[Dict[str, Any]]:
        """직접 kafka-python을 사용해서 이벤트를 수집합니다"""

        try:
            import json

            from kafka import KafkaConsumer

            self.logger.info(f"직접 Kafka 연결로 이벤트 수집 시작")
            self.logger.info(
                f"토픽: {topic}, 최대 메시지: {max_messages}, 처음부터: {from_beginning}"
            )

            # 컨슈머 설정
            consumer_config = {
                "bootstrap_servers": self.config.get_setting(
                    "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
                ).split(","),
                "auto_offset_reset": "earliest" if from_beginning else "latest",
                "enable_auto_commit": False,
                "consumer_timeout_ms": 10000,  # 10초 타임아웃
                "value_deserializer": lambda x: (
                    json.loads(x.decode("utf-8")) if x else None
                ),
            }

            if from_beginning:
                # 새로운 그룹 ID로 처음부터 읽기
                consumer_config["group_id"] = f"collector-{int(time.time())}"
            else:
                # 기존 그룹 ID 사용
                consumer_config["group_id"] = (
                    f"{self.config.get_setting('KAFKA_CONSUMER_GROUP_ID', 'dashboard')}-collector"
                )

            consumer = KafkaConsumer(topic, **consumer_config)

            self.logger.info(f"컨슈머 그룹: {consumer_config['group_id']}")

            collected_count = 0

            try:
                for message in consumer:
                    try:
                        event_data = message.value
                        if event_data:
                            self.collected_events.append(event_data)
                            self.stats["total_consumed"] += 1
                            collected_count += 1

                            # 이벤트 분류
                            event_type = event_data.get("event_type", "unknown")
                            if event_type == "email.received":
                                self.stats["email_events"] += 1
                                classification = self.classify_event(event_data)
                                self.classified_events[classification].append(
                                    event_data
                                )

                                if classification == "chair":
                                    self.stats["chair_events"] += 1
                                elif classification == "member":
                                    self.stats["member_events"] += 1
                                elif classification == "unknown":
                                    self.stats["unknown_sender_events"] += 1
                                else:
                                    # other로 분류된 경우
                                    self.stats["other_sender_events"] += 1
                            else:
                                self.stats["other_events"] += 1
                                self.classified_events["other"].append(event_data)

                            if self.verbose:
                                event_id = event_data.get("event_id", "unknown")
                                if event_type == "email.received":
                                    classification = self.classify_event(event_data)
                                    sender_org = event_data.get("event_info", {}).get(
                                        "sender_organization", "unknown"
                                    )
                                    self.logger.info(
                                        f"수집: {classification.upper()} - {sender_org} - {event_id}"
                                    )
                                else:
                                    self.logger.info(f"수집: {event_type} - {event_id}")

                            # 최대 개수 도달 시 중단
                            if collected_count >= max_messages:
                                break

                    except Exception as e:
                        self.logger.error(f"메시지 처리 오류: {str(e)}")
                        continue

            except Exception as e:
                if "timeout" not in str(e).lower():
                    self.logger.error(f"메시지 소비 오류: {str(e)}")
                else:
                    self.logger.info("소비 타임아웃 - 더 이상 메시지가 없습니다")

            finally:
                consumer.close()

            self.logger.info(f"수집 완료: {len(self.collected_events)}개 이벤트")
            return self.collected_events

        except Exception as e:
            self.logger.error(f"직접 Kafka 수집 실패: {str(e)}")
            raise

    def print_classification_summary(self) -> None:
        """분류 결과 요약 출력"""
        print("\n" + "=" * 50)
        print("이벤트 분류 결과")
        print("=" * 50)

        print(f"CHAIR 이벤트: {len(self.classified_events['chair'])}개")
        if self.classified_events["chair"] and self.verbose:
            print("  상세:")
            for event in self.classified_events["chair"][:5]:  # 최대 5개만 표시
                event_info = event.get("event_info", {})
                sender_org = event_info.get("sender_organization", "unknown")
                agenda_code = event_info.get("agenda_code", "unknown")
                subject = event_info.get("subject", "No Subject")[:50]
                print(f"    - {sender_org}: {agenda_code} - {subject}")
            if len(self.classified_events["chair"]) > 5:
                print(f"    - ... 외 {len(self.classified_events['chair']) - 5}개")

        print(f"\nMEMBER 이벤트: {len(self.classified_events['member'])}개")
        if self.classified_events["member"] and self.verbose:
            print("  상세:")
            for event in self.classified_events["member"][:5]:  # 최대 5개만 표시
                event_info = event.get("event_info", {})
                sender_org = event_info.get("sender_organization", "unknown")
                response_org = event_info.get("response_org", "unknown")
                agenda_code = event_info.get("agenda_code", "unknown")
                print(f"    - {sender_org} ({response_org}): {agenda_code}")
            if len(self.classified_events["member"]) > 5:
                print(f"    - ... 외 {len(self.classified_events['member']) - 5}개")

        print(f"\nUNKNOWN 이벤트: {len(self.classified_events['unknown'])}개")
        if self.classified_events["unknown"]:
            print("  상세:")
            for event in self.classified_events["unknown"][
                :10
            ]:  # UNKNOWN은 더 많이 표시
                event_info = event.get("event_info", {})
                sender_org = event_info.get("sender_organization", "unknown")
                sender = event_info.get("sender", "unknown")
                subject = event_info.get("subject", "No Subject")[:30]
                agenda_code = event_info.get("agenda_code", "unknown")
                event_id = event.get("event_id", "unknown")

                print(
                    f"    - {sender_org} | sender: {sender} | agenda: {agenda_code} | '{subject}' | {event_id[:8]}"
                )
            if len(self.classified_events["unknown"]) > 10:
                print(f"    - ... 외 {len(self.classified_events['unknown']) - 10}개")

        print(f"\nOTHER 이벤트: {len(self.classified_events['other'])}개")
        if self.classified_events["other"]:
            print("  상세:")
            for event in self.classified_events["other"][:10]:  # OTHER는 더 많이 표시
                event_type = event.get("event_type", "unknown")
                event_id = event.get("event_id", "unknown")
                event_info = event.get("event_info", {})
                sender_type = event_info.get("sender_type", "None")
                sender = event_info.get("sender", "unknown")
                subject = event_info.get("subject", "No Subject")[:30]

                print(
                    f"    - {event_type} | sender_type: {sender_type} | sender: {sender} | '{subject}' | {event_id[:8]}"
                )
            if len(self.classified_events["other"]) > 10:
                print(f"    - ... 외 {len(self.classified_events['other']) - 10}개")

        # sender_type별 통계 추가
        print(f"\nsender_type 통계:")
        sender_type_stats = {}
        for event in self.collected_events:
            event_info = event.get("event_info", {})
            sender_type = event_info.get("sender_type", "None")
            sender_type_stats[sender_type] = sender_type_stats.get(sender_type, 0) + 1

        for sender_type, count in sorted(sender_type_stats.items()):
            print(f"  - {sender_type}: {count}개")

    def process_events_by_classification(self, process_all: bool = True) -> None:
        """분류별로 이벤트를 처리합니다"""

        categories_to_process = []

        if process_all:
            categories_to_process = ["chair", "member", "unknown", "other"]
        else:
            # 사용자가 선택할 수 있도록 (향후 확장 가능)
            categories_to_process = ["chair", "member", "unknown", "other"]

        for category in categories_to_process:
            events = self.classified_events[category]
            if not events:
                continue

            self.logger.info(f"\n{category.upper()} 이벤트 처리 시작: {len(events)}개")

            for i, event in enumerate(events, 1):
                try:
                    event_id = event.get("event_id", "unknown")
                    event_info = event.get("event_info", {})
                    sender_org = event_info.get("sender_organization", "unknown")

                    if self.verbose:
                        self.logger.info(
                            f"[{category.upper()} {i}/{len(events)}] 처리 중: {sender_org} - {event_id}"
                        )

                    # 드라이런 모드
                    if self.dry_run:
                        self.logger.info(
                            f"[DRY RUN] {category.upper()} 처리 시뮬레이션: {event_id}"
                        )
                        self.stats["processed_success"] += 1
                        continue

                    # 분류에 따른 실제 처리
                    if category in ["chair", "member"]:
                        # CHAIR와 MEMBER는 기존 로직 사용 (적절한 테이블에 저장)
                        result = self.orchestrator.handle_email_event(event)
                    elif category == "unknown":
                        # UNKNOWN은 pending 테이블에 저장 (미식별로 처리)
                        result = self._save_as_pending(
                            event, "unknown_sender_type", "발신자 타입이 UNKNOWN"
                        )
                    else:  # other
                        # OTHER는 pending 테이블에 저장 (미식별로 처리)
                        result = self._save_as_pending(
                            event, "other_sender_type", "알 수 없는 발신자 타입"
                        )

                    if result.get("success"):
                        self.stats["processed_success"] += 1
                        if self.verbose:
                            action = result.get("action", "processed")
                            self.logger.info(f"성공: {event_id} - {action}")
                    else:
                        self.stats["processed_failed"] += 1
                        error_msg = result.get("message", "Unknown error")
                        self.logger.error(f"실패: {event_id} - {error_msg}")
                        self.stats["errors"].append(
                            {
                                "event_id": event_id,
                                "category": category,
                                "error": error_msg,
                            }
                        )

                except Exception as e:
                    self.stats["processed_failed"] += 1
                    error_msg = f"처리 중 예외: {str(e)}"
                    event_id = event.get("event_id", "unknown")
                    self.logger.error(f"예외 발생: {event_id} - {error_msg}")
                    self.stats["errors"].append(
                        {"event_id": event_id, "category": category, "error": error_msg}
                    )

    def _save_as_pending(
        self, event: Dict[str, Any], reason: str, description: str
    ) -> Dict[str, Any]:
        """이벤트를 pending 테이블에 저장하고 agenda_all에도 저장"""
        try:
            # 1. agenda_all에는 모든 이벤트 저장 (기존 로직 활용)
            result = self.orchestrator.handle_email_event(event)

            # 2. pending으로도 저장 (미식별 처리)
            from modules.mail_dashboard.event_processor import (
                EmailDashboardEventProcessor,
            )

            processor = EmailDashboardEventProcessor()

            # 이벤트 파싱
            try:
                parsed_event = processor._validate_and_parse_event(event)
                processor._save_to_pending(parsed_event, reason, description)
            except Exception as e:
                self.logger.warning(f"Pending 저장 실패: {str(e)}")

            return {"success": True, "action": "saved_as_pending", "reason": reason}

        except Exception as e:
            return {"success": False, "error": "pending_save_error", "message": str(e)}

    def print_summary(self) -> None:
        """처리 결과 요약 출력"""
        print("\n" + "=" * 50)
        print("처리 결과 요약")
        print("=" * 50)
        print(f"총 수집된 메시지: {self.stats['total_consumed']}")
        print(f"  - email.received: {self.stats['email_events']}")
        print(f"    └─ CHAIR: {self.stats['chair_events']} (→ agenda_chair)")
        print(
            f"    └─ MEMBER: {self.stats['member_events']} (→ agenda_responses_content/receivedtime)"
        )
        print(
            f"    └─ UNKNOWN: {self.stats['unknown_sender_events']} (→ agenda_pending)"
        )
        print(f"    └─ OTHER: {self.stats['other_sender_events']} (→ agenda_pending)")
        print(f"  - 기타 타입: {self.stats['other_events']}")
        print(f"  - 모든 이벤트 → agenda_all")
        print(f"처리 성공: {self.stats['processed_success']}")
        print(f"처리 실패: {self.stats['processed_failed']}")

        if self.stats["errors"]:
            print(f"\n오류 상세 (최대 5개):")
            for error in self.stats["errors"][:5]:
                category = error.get("category", "unknown")
                print(f"  - [{category.upper()}] {error['event_id']}: {error['error']}")
            if len(self.stats["errors"]) > 5:
                print(f"  - ... 외 {len(self.stats['errors']) - 5}개 오류")

        if self.dry_run:
            print(f"\n[DRY RUN 모드] 실제로 저장되지 않았습니다.")
        else:
            print(f"\n📊 저장 결과:")
            print(f"  - agenda_all: 모든 이벤트 저장됨")
            print(f"  - agenda_chair: CHAIR 이벤트 저장됨")
            print(f"  - agenda_responses_content: MEMBER 응답 내용 (조직별 컬럼에)")
            print(
                f"  - agenda_responses_receivedtime: MEMBER 응답 시간 (조직별 컬럼에)"
            )
            print(f"  - agenda_pending: UNKNOWN/OTHER 이벤트 저장됨")

    def run(
        self,
        topic: str = "email.received",
        max_messages: int = 100,
        classify_only: bool = False,
        from_beginning: bool = False,
        reset_offset: bool = False,
        consumer_group: str = None,
    ) -> bool:
        """메인 실행"""
        try:
            print(f"이벤트 수집 및 처리 시작")
            print(f"토픽: {topic}")
            print(f"최대 메시지: {max_messages}")
            print(f"드라이런 모드: {self.dry_run}")
            print(f"처음부터 읽기: {from_beginning}")
            print(f"offset 초기화: {reset_offset}")
            print(f"분류만 실행: {classify_only}")

            # 1. 이벤트 수집 - 항상 직접 kafka-python 사용
            print("직접 kafka-python 사용하여 이벤트 수집 중...")
            events = self.collect_events_from_kafka_direct(
                topic, max_messages, from_beginning=(from_beginning or reset_offset)
            )

            if not events:
                print("수집된 이벤트가 없습니다.")
                return True

            # 2. 분류 결과 출력
            self.print_classification_summary()

            # 3. 이벤트 처리 (분류만 하는 경우 건너뜀)
            if not classify_only:
                self.process_events_by_classification()

                # 4. 결과 출력
                self.print_summary()
            else:
                print("\n✅ 분류만 완료되었습니다!")

            return True

        except Exception as e:
            self.logger.error(f"실행 실패: {str(e)}")
            return False


def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(
        description="Kafka에서 이벤트를 수집하여 Email Dashboard에 저장",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--topic", default="email.received", help="Kafka 토픽 (기본값: email.received)"
    )

    parser.add_argument(
        "--max-messages",
        type=int,
        default=100,
        help="최대 처리 메시지 수 (기본값: 100)",
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="실제 저장하지 않고 테스트만 실행"
    )

    parser.add_argument("--verbose", action="store_true", help="상세 로그 출력")

    parser.add_argument(
        "--classify-only", action="store_true", help="분류만 하고 처리하지 않음"
    )

    parser.add_argument(
        "--from-beginning",
        action="store_true",
        help="처음부터 모든 이벤트 읽기 (새 컨슈머 그룹 사용)",
    )

    parser.add_argument(
        "--reset-offset", action="store_true", help="기존 컨슈머 그룹의 offset 초기화"
    )

    parser.add_argument(
        "--consumer-group", help="사용할 컨슈머 그룹 ID (기본값: 자동 생성)"
    )

    parser.add_argument(
        "--no-reset", action="store_true", help="테이블 초기화 건너뛰기"
    )

    return parser.parse_args()


def main():
    """메인 함수"""
    args = parse_arguments()

    try:
        # 수집기 초기화 (기본적으로 테이블 리셋)
        reset_tables = not args.no_reset if hasattr(args, "no_reset") else True
        collector = EventDataCollector(
            dry_run=args.dry_run, verbose=args.verbose, reset_tables=reset_tables
        )

        # 실행
        success = collector.run(
            topic=args.topic,
            max_messages=args.max_messages,
            classify_only=args.classify_only,
            from_beginning=args.from_beginning,
            reset_offset=args.reset_offset,
            consumer_group=args.consumer_group,
        )

        if success:
            print("\n✅ 완료되었습니다!")
        else:
            print("\n❌ 실행 실패")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
