#!/usr/bin/env python3
"""
새로운 메일만 처리하는 테스트
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime, timedelta
from modules.mail_query.mail_query_orchestrator import MailQueryOrchestrator
from modules.mail_query.mail_query_schema import MailQueryRequest, MailQueryFilters, PaginationOptions
from modules.mail_process.mail_processor_orchestrator import MailProcessorOrchestrator
from infra.core import get_database_manager, get_logger

logger = get_logger(__name__)
db = get_database_manager()

async def test_with_new_mails_only(user_id: str = "kimghw"):
    """새로운 메일만 처리"""
    
    print(f"\n=== {user_id}의 새 메일만 처리 테스트 ===\n")
    
    # 1. 마지막 처리 시간 확인
    last_processed = db.fetch_one("""
        SELECT MAX(mh.received_time) as last_time
        FROM mail_history mh
        JOIN accounts a ON mh.account_id = a.id
        WHERE a.user_id = ?
    """, (user_id,))
    
    if last_processed and last_processed['last_time']:
        # ISO 형식 문자열을 datetime으로 변환
        last_time_str = last_processed['last_time']
        if isinstance(last_time_str, str):
            # 다양한 형식 처리
            try:
                if 'T' in last_time_str:
                    last_time = datetime.fromisoformat(last_time_str.replace('Z', '+00:00'))
                else:
                    # 마이크로초가 포함된 경우 처리
                    if '.' in last_time_str:
                        last_time = datetime.strptime(last_time_str, '%Y-%m-%d %H:%M:%S.%f')
                    else:
                        last_time = datetime.strptime(last_time_str, '%Y-%m-%d %H:%M:%S')
            except ValueError as e:
                print(f"   날짜 파싱 오류: {last_time_str} - {e}")
                # 파싱 실패 시 30일 전부터 조회
                last_time = None
        else:
            last_time = last_time_str
            
        # timezone 정보 제거 (naive datetime으로 변환)
        if last_time and hasattr(last_time, 'replace'):
            last_time = last_time.replace(tzinfo=None)
        
        if last_time:
            print(f"1. 마지막 처리된 메일 시간: {last_time}")
            # 1초 더해서 중복 방지
            date_from = last_time + timedelta(seconds=1)
        else:
            # 파싱 실패 시 30일 전부터
            date_from = datetime.now() - timedelta(days=30)
            print(f"1. 날짜 파싱 실패. {date_from.date()}부터 조회")
    else:
        # 처리된 메일이 없으면 30일 전부터
        date_from = datetime.now() - timedelta(days=30)
        print(f"1. 처리된 메일이 없음. {date_from.date()}부터 조회")
    
    # 2. 이미 처리된 메일 ID 목록
    processed_ids = db.fetch_all("""
        SELECT message_id 
        FROM mail_history mh
        JOIN accounts a ON mh.account_id = a.id
        WHERE a.user_id = ?
    """, (user_id,))
    
    processed_id_set = {mail['message_id'] for mail in processed_ids}
    print(f"2. 이미 처리된 메일: {len(processed_id_set)}개")
    
    # 3. 새 메일 조회
    mail_query = MailQueryOrchestrator()
    mail_processor = MailProcessorOrchestrator()
    
    try:
        request = MailQueryRequest(
            user_id=user_id,
            filters=MailQueryFilters(
                date_from=date_from  # 마지막 처리 시간 이후
            ),
            pagination=PaginationOptions(
                top=10,  # 10개만 테스트
                max_pages=1
            ),
            select_fields=[
                "id", "subject", "from", "sender", 
                "receivedDateTime", "bodyPreview", "body"
            ]
        )
        
        print(f"3. 메일 조회 중... (from: {date_from})")
        
        async with mail_query as orchestrator:
            response = await orchestrator.mail_query_user_emails(request)
        
        print(f"   - 조회된 메일: {response.total_fetched}개")
        
        if response.total_fetched == 0:
            print("   - 새로운 메일이 없습니다.")
            return
        
        # 4. 중복 제거
        new_mails = []
        duplicates = []
        
        for mail in response.messages:
            if mail.id not in processed_id_set:
                new_mails.append(mail)
            else:
                duplicates.append(mail)
        
        print(f"4. 중복 확인:")
        print(f"   - 새 메일: {len(new_mails)}개")
        print(f"   - 이미 처리됨: {len(duplicates)}개")
        
        if duplicates:
            print("\n   중복 메일 예시:")
            for dup in duplicates[:3]:
                print(f"     - {dup.subject[:50]}...")
        
        if not new_mails:
            print("\n   모든 메일이 이미 처리되었습니다.")
            return
        
        # 5. 새 메일만 처리
        print(f"\n5. 새 메일 {len(new_mails)}개 처리 중...")
        
        # 처리
        stats = await mail_processor.process_mails(
            account_id=user_id,
            mails=[mail.model_dump() for mail in new_mails],
            publish_batch_event=False
        )
        
        print(f"\n6. 처리 결과:")
        print(f"   - 저장: {stats.get('saved_mails', 0)}개")
        print(f"   - 중복: {stats.get('duplicate_mails', 0)}개")
        print(f"   - 오류: {stats.get('db_errors', 0)}개")
        print(f"   - 이벤트: {stats.get('events_published', 0)}개")
        
    finally:
        await mail_query.close()
        await mail_processor.close()

async def main():
    """메인 함수"""
    # 각 계정에 대해 테스트
    for user_id in ["kimghw", "krsdtp"]:
        await test_with_new_mails_only(user_id)
        print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(main())
