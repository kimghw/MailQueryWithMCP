#!/usr/bin/env python3
"""
Email Dashboard 모듈 시작 스크립트 (주기적 처리 방식)

백그라운드 이벤트 구독 대신 5분마다 주기적으로 대기 중인 이벤트를 처리합니다.
더 안정적이고 리소스 효율적인 방식입니다.

실행 방법:
    python scripts/start_mail_dashboard.py

중단:
    Ctrl+C
"""

import os
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# ============================================================
# 환경변수 설정 (스크립트 실행 시 자동 적용)
# ============================================================
os.environ.setdefault(
    "ENABLE_DASHBOARD_EVENTS", "false"
)  # 백그라운드 이벤트 구독 비활성화
os.environ.setdefault("DASHBOARD_PROCESSING_INTERVAL", "300")  # 처리 간격 (초) - 5분
os.environ.setdefault("DASHBOARD_MAX_MESSAGES_PER_BATCH", "100")  # 배치 크기
os.environ.setdefault("DASHBOARD_PROCESSING_TIMEOUT", "30")  # 처리 타임아웃 (초)
os.environ.setdefault("LOG_LEVEL", "INFO")  # 로그 레벨

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.mail_dashboard import (
    get_dashboard_service,
    initialize_dashboard_module,
)
from infra.core import get_logger, get_config, get_kafka_client

logger = get_logger(__name__)
config = get_config()

# 전역 상태 관리
service_instance = None
is_running = False
processing_thread = None


def signal_handler(signum, frame):
    """시그널 핸들러 (Ctrl+C 등)"""
    global is_running
    print("\n⚠️  종료 신호 수신됨...")
    is_running = False


def check_kafka_connection():
    """Kafka 연결 상태 확인"""
    try:
        kafka_client = get_kafka_client()

        # Kafka 브로커 연결 확인
        print("🔍 Kafka 서버 연결 확인 중...")

        # 간단한 이벤트 발행으로 연결 테스트
        test_event = {
            "event_type": "connection_test",
            "timestamp": datetime.utcnow().isoformat(),
            "test": True,
        }

        # produce_event 메서드로 연결 테스트
        try:
            kafka_client.produce_event(
                topic="test-connection", event_data=test_event, key="test"
            )
            print("✅ Kafka 서버 연결 성공")
            return True
        except Exception as produce_error:
            # produce_event가 실패해도 연결은 될 수 있음
            if "NoBrokersAvailable" in str(produce_error):
                print("❌ Kafka 브로커에 연결할 수 없습니다")
                return False
            else:
                # 다른 오류는 연결은 되었지만 권한 등의 문제일 수 있음
                print(
                    f"⚠️  Kafka 연결은 되었지만 테스트 이벤트 발행 실패: {str(produce_error)}"
                )
                return True

    except Exception as e:
        print(f"❌ Kafka 서버 연결 실패: {str(e)}")
        print("\n💡 Kafka 서버가 실행 중인지 확인하세요:")
        print(
            "   - Kafka 브로커 주소: "
            + config.get_setting("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        )
        print("   - docker-compose up -d kafka 명령으로 Kafka 시작")
        return False


def verify_kafka_topics():
    """필요한 Kafka 토픽 확인"""
    try:
        kafka_client = get_kafka_client()
        required_topics = [
            config.get_setting("KAFKA_TOPIC_DASHBOARD_EVENTS", "email.api.response"),
            config.get_setting("KAFKA_TOPIC_EMAIL_EVENTS", "email-events"),
        ]

        print(f"\n🔍 Kafka 토픽 확인 중...")
        print(f"   필요한 토픽: {required_topics}")

        # 토픽 존재 여부 확인 (실제로는 consumer를 생성해봐야 알 수 있음)
        # 여기서는 간단히 설정값만 확인
        for topic in required_topics:
            print(f"   - {topic}: 설정됨")

        print("✅ Kafka 토픽 설정 확인 완료")
        return True

    except Exception as e:
        print(f"⚠️  Kafka 토픽 확인 중 오류: {str(e)}")
        return False


def simple_event_processor(service, max_messages, timeout_seconds):
    """간단한 이벤트 처리 함수"""
    try:
        kafka_client = get_kafka_client()

        dashboard_topic = config.get_setting(
            "KAFKA_TOPIC_DASHBOARD_EVENTS", "email.api.response"
        )
        topics = [dashboard_topic]
        consumer_group_id = f"{config.kafka_consumer_group_id}-dashboard"

        processed_count = 0
        error_count = 0

        def message_handler(topic: str, message: dict):
            nonlocal processed_count, error_count
            try:
                event_type = message.get("event_type")
                if event_type == "email-dashboard":
                    result = service.orchestrator.email_dashboard_handle_email_event(
                        message
                    )
                    if result.get("success"):
                        logger.debug(f"이벤트 처리 성공: {result.get('action')}")
                        processed_count += 1
                    else:
                        logger.warning(f"이벤트 처리 실패: {result.get('message')}")
                        error_count += 1
                else:
                    logger.debug(f"처리하지 않는 이벤트 타입: {event_type}")
            except Exception as e:
                logger.error(f"메시지 처리 중 오류: {str(e)}")
                error_count += 1

        # 간단한 이벤트 소비
        try:
            kafka_client.consume_events(
                topics=topics,
                message_handler=message_handler,
                consumer_group_id=consumer_group_id,
                max_messages=max_messages,
            )
        except Exception as e:
            logger.error(f"이벤트 소비 실패: {str(e)}")
            error_count += 1

        return {
            "success": True,
            "processed_count": processed_count,
            "success_count": processed_count,
            "error_count": error_count,
            "message": f"{processed_count}개 이벤트 처리 완료",
        }

    except Exception as e:
        logger.error(f"간단한 이벤트 처리 실패: {str(e)}")
        return {
            "success": False,
            "processed_count": 0,
            "error": str(e),
            "message": f"이벤트 처리 중 오류: {str(e)}",
        }


def periodic_event_processor():
    """주기적 이벤트 처리 워커"""
    global is_running, service_instance

    # 처리 간격 (초) - 기본 5분
    processing_interval = int(
        config.get_setting("DASHBOARD_PROCESSING_INTERVAL", "300")
    )  # 5분 = 300초
    max_messages_per_batch = int(
        config.get_setting("DASHBOARD_MAX_MESSAGES_PER_BATCH", "100")
    )
    processing_timeout = int(config.get_setting("DASHBOARD_PROCESSING_TIMEOUT", "30"))

    logger.info(
        f"📋 주기적 처리 설정: {processing_interval}초 간격, 최대 {max_messages_per_batch}개 메시지"
    )

    # 즉시 첫 번째 처리를 위해 next_processing_time을 현재 시간으로 설정
    next_processing_time = time.time()  # 변경: 즉시 처리 시작
    kafka_error_count = 0
    max_kafka_errors = 3

    while is_running:
        try:
            current_time = time.time()

            # 처리 시간이 되었는지 확인
            if current_time >= next_processing_time:
                logger.info("🔄 주기적 이벤트 처리 시작...")

                # 이벤트 처리 실행
                try:
                    # 간단한 처리 함수 사용
                    result = simple_event_processor(
                        service_instance, max_messages_per_batch, processing_timeout
                    )

                    # Kafka 연결 성공 시 에러 카운트 리셋
                    kafka_error_count = 0

                except Exception as e:
                    logger.error(f"이벤트 처리 중 오류: {str(e)}")
                    result = {"success": False, "message": str(e)}

                    # Kafka 관련 오류인 경우 카운트 증가
                    if "kafka" in str(e).lower() or "broker" in str(e).lower():
                        kafka_error_count += 1
                        if kafka_error_count >= max_kafka_errors:
                            logger.error(
                                f"❌ Kafka 연결 오류가 {max_kafka_errors}회 이상 발생했습니다. 프로그램을 종료합니다."
                            )
                            is_running = False
                            break

                if result["success"]:
                    processed = result["processed_count"]
                    success_count = result.get("success_count", 0)
                    error_count = result.get("error_count", 0)

                    if processed > 0:
                        logger.info(
                            f"✅ 이벤트 처리 완료: 총 {processed}개 처리 "
                            f"(성공 {success_count}개, 실패 {error_count}개)"
                        )
                    else:
                        logger.debug("💡 처리할 이벤트가 없습니다")
                else:
                    logger.error(f"❌ 이벤트 처리 실패: {result.get('message')}")

                # 다음 처리 시간 설정
                next_processing_time = current_time + processing_interval

                # 다음 처리까지 남은 시간 표시
                next_time_str = datetime.fromtimestamp(next_processing_time).strftime(
                    "%H:%M:%S"
                )
                logger.info(f"⏰ 다음 처리 예정 시간: {next_time_str}")

            # 1초 대기 (CPU 사용량 절약)
            time.sleep(1)

        except Exception as e:
            logger.error(f"주기적 처리 중 오류: {str(e)}")
            # 오류가 발생해도 계속 실행
            time.sleep(10)  # 10초 후 재시도

    logger.info("주기적 이벤트 처리 워커 종료")


def main():
    global service_instance, is_running, processing_thread

    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        print("=" * 60)
        print("Email Dashboard 모듈 시작 (주기적 처리 방식)")
        print("=" * 60)

        # 0단계: Kafka 연결 확인
        print("\n0단계: 이벤트 서버(Kafka) 연결 확인")

        # 환경변수로 Kafka 확인 건너뛰기 옵션
        skip_kafka_check = os.getenv("SKIP_KAFKA_CHECK", "false").lower() == "true"

        if skip_kafka_check:
            print("⚠️  SKIP_KAFKA_CHECK=true 설정으로 Kafka 연결 확인을 건너뜁니다")
        else:
            if not check_kafka_connection():
                print("\n❌ Kafka 서버에 연결할 수 없습니다.")
                print("   Email Dashboard를 시작하려면 Kafka 서버가 필요합니다.")
                print(
                    "\n💡 Kafka 확인을 건너뛰려면 SKIP_KAFKA_CHECK=true 환경변수를 설정하세요"
                )
                return 1

        # Kafka 토픽 확인
        verify_kafka_topics()

        # 1단계: 모듈 초기화
        print("\n1단계: 모듈 초기화")
        if not initialize_dashboard_module():
            print("❌ 모듈 초기화 실패")
            return 1

        print("✅ 모듈 초기화 성공")

        # 2단계: 서비스 초기화
        print("\n2단계: 서비스 초기화")
        service_instance = get_dashboard_service()

        # 백그라운드 이벤트 구독 비활성화 (주기적 처리 방식 사용)
        try:
            service_instance.stop_event_subscription()
        except Exception as e:
            logger.debug(f"이벤트 구독 중지 시도: {str(e)}")

        print("✅ 서비스 초기화 완료")

        # 3단계: 상태 확인
        print("\n3단계: 상태 확인")
        health_status = service_instance.get_health_status()

        if health_status.get("success"):
            print("✅ 모듈 상태 정상")
            if health_status.get("tables_ready"):
                print("✅ 데이터베이스 테이블 준비 완료")
        else:
            print("⚠️ 모듈 상태 확인 실패")
            print(f"   오류: {health_status.get('error', 'Unknown')}")

        # 4단계: 주기적 처리 시작
        print("\n4단계: 주기적 이벤트 처리 시작")
        is_running = True

        # 처리 설정 정보 출력
        processing_interval = int(
            config.get_setting("DASHBOARD_PROCESSING_INTERVAL", "300")
        )
        max_messages = int(
            config.get_setting("DASHBOARD_MAX_MESSAGES_PER_BATCH", "100")
        )

        print(f"📋 처리 설정:")
        print(
            f"   - Kafka 브로커: {config.get_setting('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')}"
        )
        print(
            f"   - 대시보드 토픽: {config.get_setting('KAFKA_TOPIC_DASHBOARD_EVENTS', 'email.api.response')}"
        )
        print(f"   - 처리 간격: {processing_interval}초 ({processing_interval//60}분)")
        print(f"   - 배치 크기: 최대 {max_messages}개 메시지")
        print(f"   - 처리 타임아웃: 30초")

        # 주기적 처리 스레드 시작
        processing_thread = threading.Thread(
            target=periodic_event_processor, daemon=True
        )
        processing_thread.start()

        print("\n✅ 주기적 처리 시작됨")
        print("🚀 즉시 첫 번째 이벤트 처리를 시작합니다...")  # 추가: 즉시 처리 안내
        print("\n" + "=" * 60)
        print("Email Dashboard가 실행 중입니다.")
        print("종료하려면 Ctrl+C를 누르세요.")
        print("=" * 60)

        # 메인 루프 - 사용자 입력 대기
        try:
            while is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⚠️  종료 신호 수신됨...")
            is_running = False

        # 5단계: 정리 작업
        print("\n" + "=" * 60)
        print("Email Dashboard 서비스 종료 중...")
        print("=" * 60)

        # 처리 스레드 종료 대기
        if processing_thread and processing_thread.is_alive():
            print("주기적 처리 스레드 종료 대기 중...")
            processing_thread.join(timeout=10)

        # 서비스 종료
        if service_instance:
            service_instance.shutdown()

        print("✅ 정리 작업 완료")
        print("Email Dashboard 서비스 종료됨")

        return 0

    except Exception as e:
        logger.error(f"Email Dashboard 실행 중 오류: {str(e)}", exc_info=True)
        print(f"\n❌ 오류 발생: {str(e)}")
        return 1

    finally:
        is_running = False


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
