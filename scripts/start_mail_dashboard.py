#!/usr/bin/env python3
"""
Email Dashboard 모듈 시작 스크립트

이 스크립트는 Email Dashboard 모듈을 초기화하고 이벤트 구독을 시작합니다.
독립적으로 실행할 수 있는 서비스 형태로 구성되어 있습니다.
"""

import sys
import signal
import time
from pathlib import Path

# 프로젝트 루트 경로를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.mail_dashboard import (
    get_dashboard_service,
    initialize_dashboard_module,
    start_dashboard_event_subscription,
    stop_dashboard_event_subscription,
)
from infra.core import get_logger, get_config

logger = get_logger(__name__)
config = get_config()

# 전역 상태 관리
dashboard_service = None
shutdown_requested = False


def signal_handler(signum, frame):
    """시그널 핸들러 - Ctrl+C 등으로 종료 시 정리 작업"""
    global shutdown_requested
    logger.info(f"종료 시그널 수신: {signum}")
    shutdown_requested = True


def main():
    """메인 실행 함수"""
    global dashboard_service

    logger.info("=" * 60)
    logger.info("Email Dashboard 모듈 시작")
    logger.info("=" * 60)

    try:
        # 시그널 핸들러 등록
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # 종료 신호

        # 1. 모듈 초기화
        logger.info("1단계: 모듈 초기화")
        if not initialize_dashboard_module():
            logger.error("❌ 모듈 초기화 실패")
            return 1
        logger.info("✅ 모듈 초기화 완료")

        # 2. 서비스 인스턴스 가져오기
        dashboard_service = get_dashboard_service()

        # 3. 상태 확인
        logger.info("2단계: 모듈 상태 확인")
        health_status = dashboard_service.get_health_status()
        if health_status.get("success") and health_status.get("tables_ready"):
            logger.info("✅ 모듈 상태 정상")
            logger.info(
                f"   - 데이터베이스: {'연결됨' if health_status.get('database_connected') else '연결 실패'}"
            )
            logger.info(
                f"   - 테이블 준비: {'완료' if health_status.get('tables_ready') else '실패'}"
            )
            logger.info(f"   - 필요 테이블: {health_status.get('required_tables', [])}")
        else:
            logger.error("❌ 모듈 상태 비정상")
            logger.error(f"   - 오류: {health_status.get('error', '알 수 없음')}")
            return 1

        # 4. 이벤트 구독 시작
        logger.info("3단계: 이벤트 구독 시작")
        enable_events = config.get_setting(
            "ENABLE_DASHBOARD_EVENTS", "true"
        ).lower() in ("true", "1", "yes", "on")

        if enable_events:
            if start_dashboard_event_subscription():
                logger.info("✅ 이벤트 구독 시작됨")
                topic = config.get_setting(
                    "KAFKA_TOPIC_DASHBOARD_EVENTS", "email.api.response"
                )
                consumer_group = f"{config.kafka_consumer_group_id}-dashboard"
                logger.info(f"   - 토픽: {topic}")
                logger.info(f"   - 컨슈머 그룹: {consumer_group}")
            else:
                logger.error("❌ 이벤트 구독 시작 실패")
                return 1
        else:
            logger.info("⚠️  이벤트 구독 비활성화됨 (ENABLE_DASHBOARD_EVENTS=false)")

        # 5. 서비스 실행 상태 출력
        logger.info("=" * 60)
        logger.info("🚀 Email Dashboard 서비스 실행 중")
        logger.info("=" * 60)
        logger.info(f"환경: {config.environment}")
        logger.info(f"로그 레벨: {config.log_level}")
        logger.info(f"데이터베이스: {config.database_path}")
        if enable_events:
            logger.info(f"Kafka 서버: {config.kafka_bootstrap_servers}")
        logger.info("종료하려면 Ctrl+C를 누르세요")
        logger.info("=" * 60)

        # 6. 메인 루프 - 서비스 실행 유지
        while not shutdown_requested:
            try:
                time.sleep(1)  # 1초마다 상태 확인

                # 주기적으로 상태 체크 (5분마다)
                if int(time.time()) % 300 == 0:  # 5분 = 300초
                    status = dashboard_service.get_health_status()
                    if status.get("success"):
                        logger.debug("정기 상태 체크: 정상")
                    else:
                        logger.warning(
                            f"정기 상태 체크: 이상 감지 - {status.get('error')}"
                        )

            except KeyboardInterrupt:
                logger.info("사용자 중단 요청")
                break
            except Exception as e:
                logger.error(f"메인 루프 오류: {str(e)}")
                time.sleep(5)  # 5초 후 재시도

        return 0

    except Exception as e:
        logger.error(f"서비스 시작 실패: {str(e)}")
        return 1

    finally:
        # 정리 작업
        logger.info("=" * 60)
        logger.info("Email Dashboard 서비스 종료 중...")
        logger.info("=" * 60)

        try:
            if dashboard_service:
                # 이벤트 구독 중지
                logger.info("이벤트 구독 중지 중...")
                stop_dashboard_event_subscription()

                # 서비스 종료
                logger.info("서비스 종료 중...")
                dashboard_service.shutdown()

            logger.info("✅ 정리 작업 완료")

        except Exception as e:
            logger.error(f"정리 작업 중 오류: {str(e)}")

        logger.info("Email Dashboard 서비스 종료됨")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
