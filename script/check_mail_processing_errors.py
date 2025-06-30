#!/usr/bin/env python3
"""
메일 처리 오류 확인 스크립트
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infra.core.database import get_database_manager
from datetime import datetime, timedelta

db = get_database_manager()

print("=== 메일 처리 오류 분석 ===\n")

# 1. 최근 24시간 내 처리 로그 확인
print("1. 최근 24시간 내 ERROR 로그:")
recent_errors = db.fetch_all("""
    SELECT pl.*, a.user_id
    FROM processing_logs pl
    LEFT JOIN accounts a ON pl.account_id = a.id
    WHERE pl.log_level = 'ERROR'
    AND pl.timestamp >= datetime('now', '-1 day')
    ORDER BY pl.timestamp DESC
    LIMIT 20
""")

if recent_errors:
    for error in recent_errors:
        print(f"\n[{error['timestamp']}] {error['user_id'] or 'SYSTEM'}")
        print(f"  메시지: {error['message']}")
else:
    print("  최근 오류 없음")

# 2. 중복 메일 확인
print("\n\n2. 중복 message_id 확인:")
duplicates = db.fetch_all("""
    SELECT message_id, COUNT(*) as count
    FROM mail_history
    GROUP BY message_id
    HAVING COUNT(*) > 1
""")

if duplicates:
    print(f"  중복된 message_id 발견: {len(duplicates)}개")
    for dup in duplicates[:5]:
        print(f"    - {dup['message_id']}: {dup['count']}번")
else:
    print("  중복 없음")

# 3. 실제 저장 시도와 성공 비교
print("\n\n3. 오늘 처리 통계:")

# 오늘 처리된 메일 수 (mail_history)
saved_today = db.fetch_one("""
    SELECT COUNT(*) as count
    FROM mail_history
    WHERE DATE(processed_at) = DATE('now')
""")

print(f"  - 오늘 저장된 메일: {saved_today['count'] if saved_today else 0}개")

# 계정별 상세
account_stats = db.fetch_all("""
    SELECT 
        a.user_id,
        COUNT(mh.id) as saved_count,
        MIN(mh.processed_at) as first_mail,
        MAX(mh.processed_at) as last_mail
    FROM accounts a
    LEFT JOIN mail_history mh ON a.id = mh.account_id 
        AND DATE(mh.processed_at) = DATE('now')
    WHERE a.user_id IN ('kimghw', 'krsdtp')
    GROUP BY a.user_id
""")

print("\n  계정별 오늘 저장 현황:")
for stat in account_stats:
    print(f"    - {stat['user_id']}: {stat['saved_count']}개")
    if stat['first_mail']:
        print(f"      첫 메일: {stat['first_mail']}")
        print(f"      마지막: {stat['last_mail']}")

# 4. 가장 최근 메일 처리 시각 확인
print("\n\n4. 최근 메일 처리 시각:")
recent_mails = db.fetch_all("""
    SELECT 
        a.user_id,
        mh.message_id,
        mh.subject,
        mh.processed_at
    FROM mail_history mh
    JOIN accounts a ON mh.account_id = a.id
    WHERE a.user_id IN ('kimghw', 'krsdtp')
    ORDER BY mh.processed_at DESC
    LIMIT 10
""")

for mail in recent_mails:
    # processed_at을 datetime으로 파싱
    try:
        processed_time = datetime.fromisoformat(mail['processed_at'].replace('Z', '+00:00'))
        time_ago = datetime.now() - processed_time.replace(tzinfo=None)
        hours_ago = time_ago.total_seconds() / 3600
        
        print(f"\n  [{mail['user_id']}] {hours_ago:.1f}시간 전")
        print(f"    ID: {mail['message_id'][:40]}...")
        print(f"    제목: {mail['subject'][:40]}...")
    except:
        print(f"\n  [{mail['user_id']}] {mail['processed_at']}")
        print(f"    ID: {mail['message_id'][:40]}...")

# 5. DB 저장 실패 원인 분석
print("\n\n5. DB 저장 실패 원인 분석:")
print("  가능한 원인:")
print("  1) message_id 중복 (UNIQUE 제약)")
print("  2) 이미 처리된 메일을 다시 처리 시도")
print("  3) 중복 체크 로직이 제대로 작동하지 않음")

# 테스트 제안
print("\n\n6. 해결 방법:")
print("  1) 중복 체크 로직 강화")
print("  2) 이미 처리된 메일은 스킵하도록 수정")
print("  3) 오류 발생 시 더 자세한 로깅 추가")
