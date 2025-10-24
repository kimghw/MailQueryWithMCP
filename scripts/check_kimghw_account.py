#!/usr/bin/env python3
"""kimghw 계정 정보 확인"""

import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# DB 경로
db_path = PROJECT_ROOT / "data" / "accounts.db"

if not db_path.exists():
    print(f"❌ DB 파일 없음: {db_path}")
    sys.exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 테이블 목록
print("=" * 60)
print("📋 테이블 목록")
print("=" * 60)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for table in tables:
    print(f"  • {table[0]}")

# kimghw 계정 조회
print("\n" + "=" * 60)
print("👤 kimghw 계정 조회")
print("=" * 60)

cursor.execute("""
    SELECT user_id, user_email, created_at, updated_at
    FROM accounts
    WHERE user_email LIKE '%kimghw%' OR user_id LIKE '%kimghw%'
    LIMIT 10
""")
accounts = cursor.fetchall()

if accounts:
    for acc in accounts:
        user_id, email, created, updated = acc
        print(f"\nuser_id: {user_id}")
        print(f"email: {email}")
        print(f"created: {created}")
        print(f"updated: {updated}")
else:
    print("\n⚠️  kimghw 계정을 찾을 수 없습니다")

    # 전체 계정 수 확인
    cursor.execute("SELECT COUNT(*) FROM accounts")
    count = cursor.fetchone()[0]
    print(f"\n전체 계정 수: {count}")

    if count > 0:
        print("\n처음 5개 계정:")
        cursor.execute("SELECT user_id, user_email FROM accounts LIMIT 5")
        for row in cursor.fetchall():
            print(f"  • {row[1]} (ID: {row[0]})")

# 토큰 확인 (accounts 테이블에 토큰이 있는지)
print("\n" + "=" * 60)
print("🔑 토큰 정보")
print("=" * 60)

cursor.execute("PRAGMA table_info(accounts)")
columns = cursor.fetchall()
token_columns = [col[1] for col in columns if 'token' in col[1].lower() or 'access' in col[1].lower()]

if token_columns:
    print(f"토큰 관련 컬럼: {', '.join(token_columns)}")
else:
    print("⚠️  accounts 테이블에 토큰 컬럼 없음")

conn.close()
