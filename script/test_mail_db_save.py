#!/usr/bin/env python3
"""
메일 DB 저장 테스트 스크립트
DB 저장 실패 원인을 파악하기 위한 테스트
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from infra.core.database import get_database_manager
from infra.core.logger import get_logger, update_all_loggers_level
from modules.mail_process.services.db_service import MailDatabaseService
from modules.mail_process.mail_processor_schema import ProcessedMailData, ProcessingStatus

# 로그 레벨 설정
update_all_loggers_level("DEBUG")
logger = get_logger(__name__)

def test_direct_save():
    """직접 DB 저장 테스트"""
    print("\n=== 직접 DB 저장 테스트 ===\n")
    
    db = get_database_manager()
    db_service = MailDatabaseService()
    
    # 1. 계정 정보 확인
    print("1. 계정 정보 확인:")
    accounts = db.fetch_all("SELECT id, user_id, user_name FROM accounts WHERE user_id IN ('kimghw', 'krsdtp')")
    for account in accounts:
        print(f"   - ID: {account['id']}, user_id: {account['user_id']}, user_name: {account['user_name']}")
    
    if not accounts:
        print("   ❌ 계정이 없습니다!")
        return
    
    # 2. 테스트 메일 데이터 생성
    print("\n2. 테스트 메일 저장 시도:")
    
    test_mail = ProcessedMailData(
        mail_id=f"test_mail_{datetime.now().timestamp()}",
        account_id="kimghw",  # user_id 사용
        sender_address="test@example.com",
        subject="테스트 메일 제목",
        body_preview="테스트 메일 내용입니다.",
        sent_time=datetime.now(),
        keywords=["테스트", "키워드", "DB"],
        processing_status=ProcessingStatus.SUCCESS
    )
    
    try:
        # 저장 시도
        result = db_service.save_mail_with_hash(test_mail, "테스트 정제된 내용")
        print(f"   ✅ 저장 성공: {result}")
        
        # 저장된 데이터 확인
        saved = db.fetch_one(
            "SELECT * FROM mail_history WHERE message_id = ?", 
            (test_mail.mail_id,)
        )
        
        if saved:
            print(f"\n3. 저장된 데이터:")
            print(f"   - ID: {saved['id']}")
            print(f"   - Account ID: {saved['account_id']}")
            print(f"   - Message ID: {saved['message_id']}")
            print(f"   - Subject: {saved['subject']}")
            print(f"   - Keywords: {saved['keywords']}")
            print(f"   - Content Hash: {saved['content_hash'][:16]}...")
        
    except Exception as e:
        print(f"   ❌ 저장 실패!")
        print(f"   - 에러 타입: {type(e).__name__}")
        print(f"   - 에러 메시지: {str(e)}")
        
        # 상세 에러 정보
        import traceback
        print(f"\n   상세 에러:")
        traceback.print_exc()
        
        # account_id 문제인지 확인
        if "account_id" in str(e).lower() or "foreign key" in str(e).lower():
            print(f"\n   💡 account_id 관련 문제일 가능성이 높습니다.")
            print(f"   💡 _get_actual_account_id() 메서드를 확인해보세요.")

def test_duplicate_detection():
    """중복 감지 테스트"""
    print("\n\n=== 중복 감지 테스트 ===\n")
    
    db_service = MailDatabaseService()
    
    # 이미 저장된 메일이 있는지 확인
    test_mail_id = "existing_mail_001"
    test_content = "이미 존재하는 메일 내용"
    
    is_duplicate, keywords = db_service.check_duplicate_by_content_hash(
        test_mail_id, 
        test_content
    )
    
    print(f"1. 중복 체크 결과:")
    print(f"   - 중복 여부: {is_duplicate}")
    print(f"   - 기존 키워드: {keywords}")

def check_mail_history_stats():
    """mail_history 테이블 통계"""
    print("\n\n=== mail_history 테이블 통계 ===\n")
    
    db = get_database_manager()
    
    # 전체 레코드 수
    total = db.fetch_one("SELECT COUNT(*) as count FROM mail_history")
    print(f"1. 전체 메일 수: {total['count'] if total else 0}개")
    
    # 계정별 메일 수
    by_account = db.fetch_all("""
        SELECT a.user_id, COUNT(mh.id) as count 
        FROM accounts a
        LEFT JOIN mail_history mh ON a.id = mh.account_id
        GROUP BY a.user_id
    """)
    
    print(f"\n2. 계정별 메일 수:")
    for row in by_account:
        print(f"   - {row['user_id']}: {row['count']}개")
    
    # 최근 저장된 메일
    recent = db.fetch_all("""
        SELECT mh.message_id, mh.subject, mh.processed_at, a.user_id
        FROM mail_history mh
        JOIN accounts a ON mh.account_id = a.id
        ORDER BY mh.processed_at DESC
        LIMIT 5
    """)
    
    print(f"\n3. 최근 저장된 메일 (최대 5개):")
    if recent:
        for mail in recent:
            print(f"   - [{mail['user_id']}] {mail['subject'][:30]}... ({mail['processed_at']})")
    else:
        print("   - 저장된 메일이 없습니다.")

def test_account_id_conversion():
    """account_id 변환 테스트"""
    print("\n\n=== Account ID 변환 테스트 ===\n")
    
    db = get_database_manager()
    db_service = MailDatabaseService()
    
    # user_id를 실제 ID로 변환 테스트
    test_user_ids = ["kimghw", "krsdtp", "nonexistent"]
    
    for user_id in test_user_ids:
        try:
            # _get_actual_account_id 메서드 직접 호출
            actual_id = db_service._get_actual_account_id(user_id)
            print(f"✅ {user_id} -> {actual_id}")
        except Exception as e:
            print(f"❌ {user_id} -> 에러: {str(e)}")

if __name__ == "__main__":
    print("메일 DB 저장 테스트 시작")
    print("=" * 50)
    
    # 각 테스트 실행
    test_direct_save()
    test_duplicate_detection()
    check_mail_history_stats()
    test_account_id_conversion()
    
    print("\n" + "=" * 50)
    print("테스트 완료")
