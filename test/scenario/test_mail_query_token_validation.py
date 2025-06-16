#!/usr/bin/env python3
"""
Mail Query 모듈의 토큰 검증 및 갱신 기능 테스트
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.mail_query import MailQueryRequest, MailQueryFilters, PaginationOptions
from modules.mail_query import get_mail_query_orchestrator
from infra.core import get_logger, get_token_service
from datetime import datetime, timedelta

logger = get_logger(__name__)


async def test_mail_query_with_token_validation():
    """메일 조회 시 토큰 검증 및 갱신 테스트"""
    
    # 테스트 사용자 ID
    test_user_id = "kimghw"
    
    logger.info("=" * 60)
    logger.info("Mail Query 토큰 검증 테스트 시작")
    logger.info("=" * 60)
    
    # 1. 토큰 서비스로 현재 토큰 상태 확인
    token_service = get_token_service()
    
    logger.info("\n1. 현재 토큰 상태 확인")
    auth_status = await token_service.check_authentication_status(test_user_id)
    logger.info(f"인증 상태: {auth_status['status']}")
    logger.info(f"재인증 필요: {auth_status['requires_reauth']}")
    logger.info(f"메시지: {auth_status['message']}")
    
    if auth_status['requires_reauth']:
        logger.error("재인증이 필요합니다. 먼저 인증을 완료해주세요.")
        return
    
    # 2. Mail Query 오케스트레이터 생성
    orchestrator = get_mail_query_orchestrator()
    
    # 3. 간단한 메일 조회 요청 생성
    logger.info("\n2. 메일 조회 요청 생성")
    request = MailQueryRequest(
        user_id=test_user_id,
        filters=MailQueryFilters(
            date_from=datetime.now() - timedelta(days=1),  # 최근 1일
            is_read=False  # 읽지 않은 메일만
        ),
        pagination=PaginationOptions(top=5, max_pages=1),
        select_fields=["id", "subject", "from", "receivedDateTime", "isRead"]
    )
    
    try:
        # 4. 메일 조회 실행 (토큰 검증 및 갱신 포함)
        logger.info("\n3. 메일 조회 실행 (토큰 자동 검증/갱신)")
        response = await orchestrator.mail_query_user_emails(request)
        
        logger.info(f"\n✅ 메일 조회 성공!")
        logger.info(f"조회된 메일 수: {response.total_fetched}")
        logger.info(f"실행 시간: {response.execution_time_ms}ms")
        logger.info(f"쿼리 정보: {response.query_info}")
        
        # 조회된 메일 목록 출력
        if response.messages:
            logger.info("\n조회된 메일 목록:")
            for idx, msg in enumerate(response.messages[:5], 1):
                logger.info(f"{idx}. {msg.subject} (from: {msg.from_address})")
        
        # 5. 토큰 상태 재확인
        logger.info("\n4. 토큰 상태 재확인")
        token_status = await token_service.validate_and_refresh_token(test_user_id)
        logger.info(f"토큰 상태: {token_status['status']}")
        
        if token_status['status'] == 'refreshed':
            logger.info("✅ 토큰이 자동으로 갱신되었습니다!")
        elif token_status['status'] == 'valid':
            logger.info("✅ 토큰이 여전히 유효합니다.")
        
    except Exception as e:
        logger.error(f"\n❌ 메일 조회 실패: {str(e)}")
        logger.error(f"에러 타입: {type(e).__name__}")
        
        # 토큰 관련 에러인 경우 상세 정보 출력
        if hasattr(e, 'details'):
            logger.error(f"상세 정보: {e.details}")


async def test_search_with_token_validation():
    """메일 검색 시 토큰 검증 테스트"""
    
    test_user_id = "kimghw"
    
    logger.info("\n" + "=" * 60)
    logger.info("Mail Search 토큰 검증 테스트")
    logger.info("=" * 60)
    
    orchestrator = get_mail_query_orchestrator()
    
    try:
        # 메일 검색 실행
        logger.info("\n메일 검색 실행 (토큰 자동 검증/갱신)")
        response = await orchestrator.mail_query_search_messages(
            user_id=test_user_id,
            search_term="회의",
            select_fields=["id", "subject", "from", "receivedDateTime"],
            top=10
        )
        
        logger.info(f"\n✅ 메일 검색 성공!")
        logger.info(f"검색 결과: {response.total_fetched}개")
        logger.info(f"실행 시간: {response.execution_time_ms}ms")
        
    except Exception as e:
        logger.error(f"\n❌ 메일 검색 실패: {str(e)}")


async def test_mailbox_info_with_token_validation():
    """메일박스 정보 조회 시 토큰 검증 테스트"""
    
    test_user_id = "kimghw"
    
    logger.info("\n" + "=" * 60)
    logger.info("Mailbox Info 토큰 검증 테스트")
    logger.info("=" * 60)
    
    orchestrator = get_mail_query_orchestrator()
    
    try:
        # 메일박스 정보 조회
        logger.info("\n메일박스 정보 조회 (토큰 자동 검증/갱신)")
        mailbox_info = await orchestrator.mail_query_get_mailbox_info(test_user_id)
        
        logger.info(f"\n✅ 메일박스 정보 조회 성공!")
        logger.info(f"표시 이름: {mailbox_info.display_name}")
        logger.info(f"시간대: {mailbox_info.time_zone}")
        logger.info(f"언어: {mailbox_info.language}")
        
    except Exception as e:
        logger.error(f"\n❌ 메일박스 정보 조회 실패: {str(e)}")


async def main():
    """메인 테스트 함수"""
    
    try:
        # 1. 메일 조회 테스트
        await test_mail_query_with_token_validation()
        
        # 2. 메일 검색 테스트
        await test_search_with_token_validation()
        
        # 3. 메일박스 정보 조회 테스트
        await test_mailbox_info_with_token_validation()
        
        logger.info("\n" + "=" * 60)
        logger.info("모든 테스트 완료!")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("\n테스트가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"\n예상치 못한 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
