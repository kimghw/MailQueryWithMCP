#!/usr/bin/env python3
"""
이벤트 데이터 수집 및 저장 스크립트 (배치 처리 버전)

Kafka에서 이벤트를 배치로 가져와서 Email Dashboard에 저장합니다.
모든 이벤트를 처리할 때까지 자동으로 계속 실행됩니다.

사용 예시:
    # 1. 모든 이벤트를 배치로 처리 (500개씩)
    python scripts/event_data_collector_batch.py --from-beginning --batch-size 500

    # 2. 대용량 빠른 처리 (1000개씩, 0.5초 대기)
    python scripts/event_data_collector_batch.py --batch-size 1000 --batch-delay 0.5 --from-beginning

    # 3. 제한된 처리 - 최대 10개 배치만 (총 1000개)
    python scripts/event_data_collector_batch.py --batch-size 100 --max-batches 10

    # 4. 제한된 처리 - 총 5000개까지만
    python scripts/event_data_collector_batch.py --batch-size 200 --max-total 5000

    # 5. 증분 처리 (기존 데이터 유지하고 새 이벤트만 추가)
    python scripts/event_data_collector_batch.py --no-reset --batch-size 200

    # 6. 전체 이벤트 수 확인 (드라이런)
    python scripts/event_data_collector_batch.py --dry-run --from-beginning --verbose

    # 7. 특정 컨슈머 그룹으로 처리
    python scripts/event_data_collector_batch.py --consumer-group "my-batch-group" --from-beginning

    # 8. 상세 로그와 함께 처리
    python scripts/event_data_collector_batch.py --verbose --batch-size 50 --from-beginning

옵션:
    --topic TOPIC           Kafka 토픽 (기본값: email.received)
    --batch-size N         배치당 처리할 메시지 수 (기본값: 100)
    --max-batches N        최대 배치 수 (기본값: 제한 없음)
    --max-total N          최대 총 메시지 수 (기본값: 제한 없음)
    --batch-delay N        배치 간 대기 시간(초) (기본값: 1)
    --dry-run              실제 저장하지 않고 테스트만 실행
    --verbose              상세 로그 출력
    --from-beginning       처음부터 모든 이벤트 읽기
    --consumer-group ID    사용할 컨슈머 그룹 ID
    --no-reset             테이블 초기화 건너뛰기
    --empty-batch-limit N  빈 배치 허용 횟수 (기본값: 3)
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 프로젝트 루트 경로 추가 (scripts 폴더에서 실행 시)
script_dir = Path(__file__).parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from infra.core import get_config, get_kafka_client, get_logger
from modules.mail_dashboard import EmailDashboardOrchestrator


class BatchEventCollector:
    """배치 단위로 Kafka 이벤트를 수집하여 처리"""

    def __init__(
        self,
        dry_run: bool = False,
        verbose: bool = False,
        reset_tables: bool = True,
        batch_size: int = 100,
        batch_delay: float = 1.0,
        empty_batch_limit: int = 3,
    ):
        self.dry_run = dry_run
        self.verbose = verbose
        self.reset_tables = reset_tables
        self.batch_size = batch_size
        self.batch_delay = batch_delay
        self.empty_batch_limit = empty_batch_limit
        self.logger = get_logger(__name__)

        # Kafka 클라이언트
        self.kafka_client = get_kafka_client()
        self.config = get_config()

        # Email Dashboard 오케스트레이터
        self.orchestrator = EmailDashboardOrchestrator()

        # 테이블 초기화 (옵션)
        if self.reset_tables:
            self._reset_dashboard_tables()

        # 배치 처리 통계
        self.batch_stats = {
            "batch_count": 0,
            "total_processed": 0,
            "empty_batch_count": 0,
            "consecutive_empty_batches": 0,
            "batches": [],  # 각 배치의 상세 정보
        }

        # 전체 통계
        self.global_stats = {
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
            "start_time": datetime.now(),
            "end_time": None,
        }

        # 분류된 이벤트들 (전체)
        self.all_classified_events = {
            "chair": [],
            "member": [],
            "unknown": [],
            "other": [],
        }

    def _reset_dashboard_tables(self) -> None:
        """Dashboard 테이블을 초기화합니다"""
        try:
            self.logger.info("Email Dashboard 테이블 초기화 시작")
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

            if not sender_type:
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

    def process_batch(
        self, topic: str, consumer_group: str, timeout_ms: int = 10000
    ) -> Dict[str, Any]:
        """한 배치의 이벤트를 처리합니다"""

        batch_start_time = datetime.now()
        batch_events = []
        batch_classified = {"chair": [], "member": [], "unknown": [], "other": []}

        try:
            import json

            from kafka import KafkaConsumer

            # 컨슈머 설정
            consumer_config = {
                "bootstrap_servers": self.config.get_setting(
                    "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
                ).split(","),
                "group_id": consumer_group,
                "auto_offset_reset": "earliest",
                "enable_auto_commit": True,  # 배치 처리에서는 auto commit 사용
                "consumer_timeout_ms": timeout_ms,
                "max_poll_records": self.batch_size,  # 배치 크기 제한
                "value_deserializer": lambda x: (
                    json.loads(x.decode("utf-8")) if x else None
                ),
            }

            consumer = KafkaConsumer(topic, **consumer_config)

            # 배치만큼 이벤트 수집
            collected_count = 0

            for message in consumer:
                try:
                    event_data = message.value
                    if event_data:
                        batch_events.append(event_data)
                        collected_count += 1

                        # 이벤트 분류
                        event_type = event_data.get("event_type", "unknown")
                        if event_type == "email.received":
                            self.global_stats["email_events"] += 1
                            classification = self.classify_event(event_data)
                            batch_classified[classification].append(event_data)
                            self.all_classified_events[classification].append(
                                event_data
                            )

                            if classification == "chair":
                                self.global_stats["chair_events"] += 1
                            elif classification == "member":
                                self.global_stats["member_events"] += 1
                            elif classification == "unknown":
                                self.global_stats["unknown_sender_events"] += 1
                            else:
                                self.global_stats["other_sender_events"] += 1
                        else:
                            self.global_stats["other_events"] += 1
                            batch_classified["other"].append(event_data)
                            self.all_classified_events["other"].append(event_data)

                        if self.verbose and collected_count % 10 == 0:
                            self.logger.info(
                                f"배치 수집 중: {collected_count}/{self.batch_size}"
                            )

                        # 배치 크기 도달 시 중단
                        if collected_count >= self.batch_size:
                            break

                except Exception as e:
                    self.logger.error(f"메시지 처리 오류: {str(e)}")
                    continue

            consumer.close()

            self.global_stats["total_consumed"] += collected_count

            # 배치 처리
            batch_processed = 0
            batch_success = 0
            batch_failed = 0

            if not self.dry_run and batch_events:
                self.logger.info(
                    f"배치 #{self.batch_stats['batch_count'] + 1}: {len(batch_events)}개 이벤트 처리 시작"
                )

                for category in ["chair", "member", "unknown", "other"]:
                    events = batch_classified[category]
                    if not events:
                        continue

                    for event in events:
                        try:
                            # 분류에 따른 처리
                            if category in ["chair", "member"]:
                                result = self.orchestrator.handle_email_event(event)
                            else:
                                result = self._save_as_pending(
                                    event,
                                    f"{category}_sender_type",
                                    f"발신자 타입이 {category.upper()}",
                                )

                            batch_processed += 1
                            if result.get("success"):
                                batch_success += 1
                                self.global_stats["processed_success"] += 1
                            else:
                                batch_failed += 1
                                self.global_stats["processed_failed"] += 1
                                self.global_stats["errors"].append(
                                    {
                                        "event_id": event.get("event_id", "unknown"),
                                        "category": category,
                                        "error": result.get("message", "Unknown error"),
                                    }
                                )

                        except Exception as e:
                            batch_failed += 1
                            self.global_stats["processed_failed"] += 1
                            self.logger.error(f"이벤트 처리 예외: {str(e)}")

            # 배치 통계 업데이트
            batch_end_time = datetime.now()
            batch_duration = (batch_end_time - batch_start_time).total_seconds()

            batch_info = {
                "batch_number": self.batch_stats["batch_count"] + 1,
                "events_collected": collected_count,
                "events_processed": batch_processed,
                "success": batch_success,
                "failed": batch_failed,
                "duration_seconds": batch_duration,
                "timestamp": batch_start_time.isoformat(),
                "classification": {
                    "chair": len(batch_classified["chair"]),
                    "member": len(batch_classified["member"]),
                    "unknown": len(batch_classified["unknown"]),
                    "other": len(batch_classified["other"]),
                },
            }

            self.batch_stats["batches"].append(batch_info)
            self.batch_stats["batch_count"] += 1
            self.batch_stats["total_processed"] += batch_processed

            # 빈 배치 추적
            if collected_count == 0:
                self.batch_stats["empty_batch_count"] += 1
                self.batch_stats["consecutive_empty_batches"] += 1
            else:
                self.batch_stats["consecutive_empty_batches"] = 0

            return {
                "success": True,
                "collected": collected_count,
                "processed": batch_processed,
                "batch_info": batch_info,
            }

        except Exception as e:
            self.logger.error(f"배치 처리 실패: {str(e)}")
            return {"success": False, "error": str(e), "collected": 0, "processed": 0}

    def _save_as_pending(
        self, event: Dict[str, Any], reason: str, description: str
    ) -> Dict[str, Any]:
        """이벤트를 pending 테이블에 저장"""
        try:
            # 1. agenda_all에는 모든 이벤트 저장
            result = self.orchestrator.handle_email_event(event)

            # 2. pending으로도 저장
            from modules.mail_dashboard.event_processor import (
                EmailDashboardEventProcessor,
            )

            processor = EmailDashboardEventProcessor()

            try:
                parsed_event = processor._validate_and_parse_event(event)
                processor._save_to_pending(parsed_event, reason, description)
            except Exception as e:
                self.logger.warning(f"Pending 저장 실패: {str(e)}")

            return {"success": True, "action": "saved_as_pending", "reason": reason}

        except Exception as e:
            return {"success": False, "error": "pending_save_error", "message": str(e)}

    def print_batch_summary(self, batch_info: Dict[str, Any]) -> None:
        """배치 처리 결과 출력"""
        if not self.verbose:
            # 간단한 진행 상황만 출력
            print(
                f"\r배치 #{batch_info['batch_number']}: "
                f"{batch_info['events_collected']}개 수집, "
                f"{batch_info['events_processed']}개 처리 "
                f"(누적: {self.global_stats['total_consumed']}개)",
                end="",
                flush=True,
            )
        else:
            # 상세 정보 출력
            print(f"\n배치 #{batch_info['batch_number']} 완료:")
            print(f"  - 수집: {batch_info['events_collected']}개")
            print(
                f"  - 분류: CHAIR={batch_info['classification']['chair']}, "
                f"MEMBER={batch_info['classification']['member']}, "
                f"UNKNOWN={batch_info['classification']['unknown']}, "
                f"OTHER={batch_info['classification']['other']}"
            )
            print(
                f"  - 처리: 성공={batch_info['success']}, 실패={batch_info['failed']}"
            )
            print(f"  - 소요시간: {batch_info['duration_seconds']:.2f}초")

    def print_final_summary(self) -> None:
        """최종 처리 결과 요약"""
        self.global_stats["end_time"] = datetime.now()
        total_duration = (
            self.global_stats["end_time"] - self.global_stats["start_time"]
        ).total_seconds()

        print("\n\n" + "=" * 70)
        print("배치 처리 완료 - 최종 결과")
        print("=" * 70)

        print(f"\n📊 처리 통계:")
        print(f"  - 총 배치 수: {self.batch_stats['batch_count']}")
        print(f"  - 빈 배치 수: {self.batch_stats['empty_batch_count']}")
        print(f"  - 총 수집 이벤트: {self.global_stats['total_consumed']}")
        print(f"  - 총 처리 이벤트: {self.batch_stats['total_processed']}")
        print(f"  - 총 소요 시간: {total_duration:.2f}초")
        if total_duration > 0:
            print(
                f"  - 평균 처리 속도: {self.global_stats['total_consumed']/total_duration:.1f} events/sec"
            )

        print(f"\n📧 이벤트 분류:")
        print(f"  - email.received: {self.global_stats['email_events']}")
        print(f"    └─ CHAIR: {self.global_stats['chair_events']}")
        print(f"    └─ MEMBER: {self.global_stats['member_events']}")
        print(f"    └─ UNKNOWN: {self.global_stats['unknown_sender_events']}")
        print(f"    └─ OTHER: {self.global_stats['other_sender_events']}")
        print(f"  - 기타 이벤트: {self.global_stats['other_events']}")

        print(f"\n✅ 처리 결과:")
        print(f"  - 성공: {self.global_stats['processed_success']}")
        print(f"  - 실패: {self.global_stats['processed_failed']}")

        if self.global_stats["errors"] and self.verbose:
            print(f"\n❌ 오류 상세 (최대 10개):")
            for error in self.global_stats["errors"][:10]:
                print(
                    f"  - [{error['category']}] {error['event_id']}: {error['error']}"
                )

        if self.dry_run:
            print(f"\n[DRY RUN 모드] 실제로 저장되지 않았습니다.")

        # 배치별 성능 통계
        if self.batch_stats["batches"] and self.verbose:
            print(f"\n📈 배치별 성능:")
            total_events = sum(
                b["events_collected"] for b in self.batch_stats["batches"]
            )
            total_time = sum(b["duration_seconds"] for b in self.batch_stats["batches"])
            avg_batch_size = (
                total_events / len(self.batch_stats["batches"])
                if self.batch_stats["batches"]
                else 0
            )
            avg_batch_time = (
                total_time / len(self.batch_stats["batches"])
                if self.batch_stats["batches"]
                else 0
            )

            print(f"  - 평균 배치 크기: {avg_batch_size:.1f} events")
            print(f"  - 평균 배치 처리 시간: {avg_batch_time:.2f}초")
            if avg_batch_time > 0:
                print(
                    f"  - 평균 배치 처리 속도: {avg_batch_size/avg_batch_time:.1f} events/sec"
                )

    def run(
        self,
        topic: str = "email.received",
        max_batches: Optional[int] = None,
        max_total: Optional[int] = None,
        from_beginning: bool = False,
        consumer_group: Optional[str] = None,
    ) -> bool:
        """배치 처리 실행"""
        try:
            print(f"배치 이벤트 수집 및 처리 시작")
            print(f"설정:")
            print(f"  - 토픽: {topic}")
            print(f"  - 배치 크기: {self.batch_size}")
            print(f"  - 최대 배치: {max_batches if max_batches else '제한 없음'}")
            print(f"  - 최대 이벤트: {max_total if max_total else '제한 없음'}")
            print(f"  - 드라이런: {self.dry_run}")
            print(f"  - 처음부터: {from_beginning}")
            print(f"  - 빈 배치 제한: {self.empty_batch_limit}")
            print()

            # 컨슈머 그룹 결정
            if consumer_group:
                final_consumer_group = consumer_group
            elif from_beginning:
                timestamp = int(time.time())
                final_consumer_group = f"{self.config.get_setting('KAFKA_CONSUMER_GROUP_ID', 'dashboard')}-batch-{timestamp}"
            else:
                final_consumer_group = f"{self.config.get_setting('KAFKA_CONSUMER_GROUP_ID', 'dashboard')}-batch"

            print(f"컨슈머 그룹: {final_consumer_group}\n")

            # 배치 처리 루프
            while True:
                # 종료 조건 확인
                if max_batches and self.batch_stats["batch_count"] >= max_batches:
                    print(f"\n최대 배치 수({max_batches})에 도달했습니다.")
                    break

                if max_total and self.global_stats["total_consumed"] >= max_total:
                    print(f"\n최대 이벤트 수({max_total})에 도달했습니다.")
                    break

                if (
                    self.batch_stats["consecutive_empty_batches"]
                    >= self.empty_batch_limit
                ):
                    print(
                        f"\n연속 {self.empty_batch_limit}개의 빈 배치 - 더 이상 이벤트가 없습니다."
                    )
                    break

                # 배치 처리
                result = self.process_batch(topic, final_consumer_group)

                if result["success"]:
                    self.print_batch_summary(result["batch_info"])

                    # 배치 간 대기
                    if result["collected"] > 0 and self.batch_delay > 0:
                        time.sleep(self.batch_delay)
                else:
                    self.logger.error(f"배치 처리 오류: {result.get('error')}")
                    break

            # 최종 결과 출력
            self.print_final_summary()

            return True

        except KeyboardInterrupt:
            print("\n\n⚠️  사용자에 의해 중단되었습니다.")
            self.print_final_summary()
            return False
        except Exception as e:
            self.logger.error(f"실행 실패: {str(e)}")
            return False


def reset_tables_only():
    """테이블만 초기화하는 함수"""
    print("\n테이블 초기화 중...")
    try:
        orchestrator = EmailDashboardOrchestrator()
        result = orchestrator.clear_all_data()

        if result.get("success"):
            print(
                f"✅ 테이블 초기화 완료: {result.get('total_deleted', 0)}개 레코드 삭제"
            )

            # 테이블별 결과 표시
            if "table_results" in result:
                print("\n테이블별 삭제 결과:")
                for table_result in result["table_results"]:
                    table_name = table_result.get("table", "unknown")
                    deleted_count = table_result.get("deleted_count", 0)
                    print(f"  - {table_name}: {deleted_count}개 삭제")
        else:
            print(f"❌ 테이블 초기화 실패: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ 테이블 초기화 중 오류: {str(e)}")


def show_interactive_menu():
    """대화형 메뉴를 표시하고 사용자 선택을 처리"""
    print("\n" + "=" * 70)
    print("Email Dashboard 이벤트 수집기")
    print("=" * 70)
    print("\n사용할 작업을 선택하세요:\n")

    print("  [Enter] 증분 처리 (기본) - 새 이벤트만 100개씩 처리")
    print("  [1] 모든 이벤트를 배치로 처리 (500개씩)")
    print("  [2] 대용량 빠른 처리 (1000개씩, 0.5초 대기)")
    print("  [3] 제한된 처리 - 최대 10개 배치만")
    print("  [4] 제한된 처리 - 총 5000개까지만")
    print("  [5] 증분 처리 - 200개씩")
    print("  [6] 전체 이벤트 수 확인 (드라이런)")
    print("  [7] 특정 컨슈머 그룹으로 처리")
    print("  [8] 상세 로그와 함께 처리")
    print("  [0] 테이블 초기화만 실행")
    print("  [q] 종료")

    choice = input("\n선택 [Enter/0-8/q]: ").strip().lower()

    if choice == "q":
        print("종료합니다.")
        sys.exit(0)

    if choice == "0":
        reset_tables_only()
        return None

    # 각 선택에 대한 설정
    configs = {
        "": {  # Enter key (기본)
            "args": ["--no-reset", "--batch-size", "100"],
            "description": "증분 처리 (새 이벤트만 100개씩)",
        },
        "1": {
            "args": ["--from-beginning", "--batch-size", "500"],
            "description": "모든 이벤트를 500개씩 배치로 처리",
        },
        "2": {
            "args": [
                "--batch-size",
                "1000",
                "--batch-delay",
                "0.5",
                "--from-beginning",
            ],
            "description": "대용량 빠른 처리 (1000개씩)",
        },
        "3": {
            "args": ["--batch-size", "100", "--max-batches", "10"],
            "description": "최대 10개 배치만 처리 (총 1000개)",
        },
        "4": {
            "args": ["--batch-size", "200", "--max-total", "5000"],
            "description": "총 5000개까지만 처리",
        },
        "5": {
            "args": ["--no-reset", "--batch-size", "200"],
            "description": "증분 처리 (200개씩)",
        },
        "6": {
            "args": ["--dry-run", "--from-beginning", "--verbose"],
            "description": "전체 이벤트 수 확인",
        },
        "7": {"description": "특정 컨슈머 그룹으로 처리", "interactive": True},
        "8": {
            "args": ["--verbose", "--batch-size", "50", "--from-beginning"],
            "description": "상세 로그와 함께 처리",
        },
    }

    if choice in configs:
        config = configs[choice]
        print(f"\n선택: {config['description']}")

        if config.get("interactive"):
            # 추가 입력이 필요한 경우
            if choice == "7":
                group_name = input("컨슈머 그룹 이름을 입력하세요: ").strip()
                if not group_name:
                    print("컨슈머 그룹 이름이 필요합니다.")
                    return None
                config["args"] = ["--consumer-group", group_name, "--from-beginning"]

        return config.get("args", [])
    else:
        print("잘못된 선택입니다.")
        return None


def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(
        description="Kafka에서 이벤트를 배치로 수집하여 Email Dashboard에 저장",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--topic", default="email.received", help="Kafka 토픽 (기본값: email.received)"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="배치당 처리할 메시지 수 (기본값: 100)",
    )

    parser.add_argument(
        "--max-batches",
        type=int,
        help="최대 배치 수 (기본값: 제한 없음)",
    )

    parser.add_argument(
        "--max-total",
        type=int,
        help="최대 총 메시지 수 (기본값: 제한 없음)",
    )

    parser.add_argument(
        "--batch-delay",
        type=float,
        default=1.0,
        help="배치 간 대기 시간(초) (기본값: 1)",
    )

    parser.add_argument(
        "--empty-batch-limit",
        type=int,
        default=3,
        help="연속 빈 배치 허용 횟수 (기본값: 3)",
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="실제 저장하지 않고 테스트만 실행"
    )

    parser.add_argument("--verbose", action="store_true", help="상세 로그 출력")

    parser.add_argument(
        "--from-beginning",
        action="store_true",
        help="처음부터 모든 이벤트 읽기",
    )

    parser.add_argument("--consumer-group", help="사용할 컨슈머 그룹 ID")

    parser.add_argument(
        "--no-reset", action="store_true", help="테이블 초기화 건너뛰기"
    )

    return parser.parse_args()


def main():
    """메인 함수"""
    # 명령행 인수가 없으면 대화형 메뉴 표시
    if len(sys.argv) == 1:
        selected_args = show_interactive_menu()
        if selected_args is None:
            return

        # 선택된 옵션으로 sys.argv 재구성
        sys.argv.extend(selected_args)

    args = parse_arguments()

    try:
        # 수집기 초기화
        collector = BatchEventCollector(
            dry_run=args.dry_run,
            verbose=args.verbose,
            reset_tables=not args.no_reset,
            batch_size=args.batch_size,
            batch_delay=args.batch_delay,
            empty_batch_limit=args.empty_batch_limit,
        )

        # 실행
        success = collector.run(
            topic=args.topic,
            max_batches=args.max_batches,
            max_total=args.max_total,
            from_beginning=args.from_beginning,
            consumer_group=args.consumer_group,
        )

        if success:
            print("\n✅ 배치 처리가 완료되었습니다!")
        else:
            print("\n❌ 배치 처리 실패")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
