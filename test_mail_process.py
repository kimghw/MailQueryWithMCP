#!/usr/bin/env python3
"""
중복 체크 문제 디버깅 스크립트
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infra.core.database import get_database_manager
from infra.core.logger import get_logger
from modules.mail_query import (
    MailQueryOrchestrator,
    MailQueryRequest,
    MailQueryFilters,
    PaginationOptions,
)
from modules.mail_process.services.db_service import MailDatabaseService

logger = get_logger(__name__)


async def debug_duplicate_check(user_id: str):
    """중복 체크 문제 디버깅"""

    print(f"\n🔍 중복 체크 디버깅: {user_id}")
    print("=" * 80)

    db = get_database_manager()
    db_service = MailDatabaseService()

    # 1. 현재 mail_history 상태 확인
    print("\n1️⃣ 현재 mail_history 테이블 상태:")

    # 테이블 구조 확인
    table_info = db.get_table_info("mail_history")
    print(f"\n📊 mail_history 테이블 컬럼:")
    for col in table_info:
        print(f"  - {col['name']} ({col['type']})")

    # 저장된 메일 수 확인
    total_mails = db.fetch_one(
        """
        SELECT COUNT(*) as count FROM mail_history
    """
    )
    print(f"\n📧 전체 저장된 메일: {total_mails['count']}개")

    # 계정별 메일 수 확인
    account_mails = db.fetch_one(
        """
        SELECT COUNT(*) as count 
        FROM mail_history mh
        JOIN accounts a ON mh.account_id = a.id
        WHERE a.user_id = ?
    """,
        (user_id,),
    )
    print(f"📧 {user_id} 계정의 메일: {account_mails['count']}개")

    # 2. 최근 메일 조회
    print("\n2️⃣ Graph API에서 메일 조회:")

    async with MailQueryOrchestrator() as mail_query:
        request = MailQueryRequest(
            user_id=user_id,
            filters=MailQueryFilters(date_from=datetime.now() - timedelta(days=30)),
            pagination=PaginationOptions(top=10, max_pages=1),
        )

        response = await mail_query.mail_query_user_emails(request)

        print(f"\n조회된 메일: {response.total_fetched}개")

        # 3. 각 메일의 중복 체크 테스트
        print("\n3️⃣ 각 메일의 중복 체크 결과:")
        print("-" * 80)

        for i, mail in enumerate(response.messages[:5], 1):  # 처음 5개만
            print(f"\n[메일 {i}]")
            print(f"  ID: {mail.id}")
            print(f"  제목: {mail.subject[:50]}...")
            print(f"  수신: {mail.received_date_time}")

            # 메시지 ID로 중복 체크
            is_duplicate_by_id = db_service.check_duplicate_by_id(mail.id)
            print(f"  message_id 중복 체크: {'중복' if is_duplicate_by_id else '신규'}")

            # 실제 DB에 있는지 확인
            existing = db.fetch_one(
                """
                SELECT id, message_id, subject, processed_at
                FROM mail_history
                WHERE message_id = ?
            """,
                (mail.id,),
            )

            if existing:
                print(f"  DB에 존재: YES (저장 시간: {existing['processed_at']})")
            else:
                print(f"  DB에 존재: NO")

            # content_hash 체크 (컬럼이 있다면)
            if "content_hash" in [col["name"] for col in table_info]:
                # 간단한 내용으로 해시 체크
                content = f"{mail.subject}\n\n{mail.body_preview or ''}"
                is_dup_by_hash, existing_keywords = (
                    db_service.check_duplicate_by_content_hash(mail.id, content)
                )
                print(
                    f"  content_hash 중복 체크: {'중복' if is_dup_by_hash else '신규'}"
                )
                if is_dup_by_hash and existing_keywords:
                    print(f"  기존 키워드: {existing_keywords}")

    # 4. 중복 메일 상세 분석
    print("\n4️⃣ 중복 메일 상세 분석:")

    # 중복된 message_id 찾기
    duplicates = db.fetch_all(
        """
        SELECT message_id, COUNT(*) as count
        FROM mail_history
        GROUP BY message_id
        HAVING COUNT(*) > 1
        ORDER BY count DESC
        LIMIT 10
    """
    )

    if duplicates:
        print(f"\n⚠️  중복된 message_id 발견: {len(duplicates)}개")
        for dup in duplicates:
            print(f"  - {dup['message_id']}: {dup['count']}번 중복")
    else:
        print("\n✅ 중복된 message_id 없음")

    # 5. 환경 변수 확인
    print("\n5️⃣ 환경 변수 설정:")
    print(
        f"  - ENABLE_MAIL_DUPLICATE_CHECK: {os.getenv('ENABLE_MAIL_DUPLICATE_CHECK', 'true')}"
    )
    print(f"  - MAIL_ALLOW_DUPLICATES: {os.getenv('MAIL_ALLOW_DUPLICATES', 'false')}")

    # 6. 최근 처리 로그 확인
    print("\n6️⃣ 최근 처리 로그:")
    recent_logs = db.fetch_all(
        """
        SELECT 
            processed_at,
            COUNT(*) as count
        FROM mail_history
        WHERE processed_at >= datetime('now', '-1 day')
        GROUP BY DATE(processed_at), strftime('%H', processed_at)
        ORDER BY processed_at DESC
        LIMIT 5
    """
    )

    if recent_logs:
        print("\n시간대별 처리 현황:")
        for log in recent_logs:
            print(f"  - {log['processed_at']}: {log['count']}개")


async def test_direct_duplicate_check():
    """직접 중복 체크 테스트"""

    print("\n🧪 직접 중복 체크 테스트")
    print("=" * 80)

    db_service = MailDatabaseService()

    # 테스트용 메시지 ID
    test_message_ids = [
        "test_message_001",
        "test_message_002",
        "test_message_001",  # 일부러 중복
    ]

    for msg_id in test_message_ids:
        is_duplicate = db_service.check_duplicate_by_id(msg_id)
        print(f"메시지 ID '{msg_id}': {'중복' if is_duplicate else '신규'}")


async def main():
    """메인 함수"""
    print("\n🔍 메일 중복 체크 디버깅 도구")
    print("=" * 80)

    print("\n테스트 모드 선택:")
    print("1. 특정 계정 중복 체크 분석")
    print("2. 직접 중복 체크 테스트")
    print("3. mail_history 테이블 초기화")

    choice = input("\n선택 (1-3): ").strip()

    if choice == "1":
        user_id = input("계정 ID 입력: ").strip()
        await debug_duplicate_check(user_id)

    elif choice == "2":
        await test_direct_duplicate_check()

    elif choice == "3":
        confirm = input("⚠️  정말 mail_history를 초기화하시겠습니까? (yes/no): ")
        if confirm.lower() == "yes":
            db = get_database_manager()
            db.execute_query("DELETE FROM mail_history")
            print("✅ mail_history 테이블이 초기화되었습니다.")

    else:
        print("❌ 잘못된 선택입니다.")


if __name__ == "__main__":
    asyncio.run(main())
