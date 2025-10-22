#!/usr/bin/env python3
"""
OAuth 토큰 정리 스크립트

사용된 auth_code, 만료된 토큰, 오래된 client를 자동으로 정리합니다.
"""

import sqlite3
import sys
from pathlib import Path

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "graphapi.db"

def cleanup_oauth_tokens(keep_clients: int = 3, keep_auth_codes: int = 5):
    """
    OAuth 토큰 정리

    Args:
        keep_clients: 유지할 최근 client 개수
        keep_auth_codes: 유지할 최근 auth_code 개수 (미사용 것만)
    """
    if not DB_PATH.exists():
        print(f"❌ 데이터베이스를 찾을 수 없습니다: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("🧹 OAuth 토큰 정리 시작...")
    print()

    # 정리 전 상태
    cursor.execute("SELECT COUNT(*) FROM dcr_oauth")
    total_before = cursor.fetchone()[0]
    print(f"정리 전 전체 토큰: {total_before}개")

    try:
        # 1. 사용된 auth_code 삭제
        cursor.execute(
            'DELETE FROM dcr_oauth WHERE token_type = "auth_code" AND used_at IS NOT NULL'
        )
        deleted_used_auth = cursor.rowcount
        if deleted_used_auth > 0:
            print(f"✅ 사용된 auth_code {deleted_used_auth}개 삭제")

        # 2. 만료된 토큰 삭제
        cursor.execute('DELETE FROM dcr_oauth WHERE expires_at < datetime("now")')
        deleted_expired = cursor.rowcount
        if deleted_expired > 0:
            print(f"✅ 만료된 토큰 {deleted_expired}개 삭제")

        # 3. 무효화된 토큰 삭제
        cursor.execute('DELETE FROM dcr_oauth WHERE revoked_at IS NOT NULL')
        deleted_revoked = cursor.rowcount
        if deleted_revoked > 0:
            print(f"✅ 무효화된 토큰 {deleted_revoked}개 삭제")

        # 4. Azure Client ID별 중복 client 삭제 (최신 1개만 유지)
        cursor.execute(
            """
            DELETE FROM dcr_oauth
            WHERE token_type = 'client'
            AND id NOT IN (
                SELECT MAX(id)
                FROM dcr_oauth
                WHERE token_type = 'client'
                GROUP BY azure_client_id
            )
            """
        )
        deleted_dup_clients = cursor.rowcount
        if deleted_dup_clients > 0:
            print(f"✅ 중복 client {deleted_dup_clients}개 삭제 (사용자별 최신 1개만 유지)")

        # 5. 고아 토큰 삭제 (존재하지 않는 client의 토큰)
        cursor.execute(
            """
            DELETE FROM dcr_oauth
            WHERE client_id NOT IN (
                SELECT DISTINCT token_value
                FROM dcr_oauth
                WHERE token_type = 'client'
            )
            AND token_type != 'client'
            """
        )
        deleted_orphans = cursor.rowcount
        if deleted_orphans > 0:
            print(f"✅ 고아 토큰 {deleted_orphans}개 삭제")

        # 6. 오래된 client 삭제 (최근 N개만 유지)
        cursor.execute(
            f"""
            DELETE FROM dcr_oauth
            WHERE token_type = 'client'
            AND id NOT IN (
                SELECT id FROM dcr_oauth
                WHERE token_type = 'client'
                ORDER BY created_at DESC
                LIMIT {keep_clients}
            )
            """
        )
        deleted_old_clients = cursor.rowcount
        if deleted_old_clients > 0:
            print(f"✅ 오래된 client {deleted_old_clients}개 삭제 (최근 {keep_clients}개 유지)")

        # 7. 오래된 auth_code 삭제 (미사용 것 중 최근 N개만 유지)
        cursor.execute(
            f"""
            DELETE FROM dcr_oauth
            WHERE token_type = 'auth_code'
            AND used_at IS NULL
            AND id NOT IN (
                SELECT id FROM dcr_oauth
                WHERE token_type = 'auth_code'
                AND used_at IS NULL
                ORDER BY created_at DESC
                LIMIT {keep_auth_codes}
            )
            """
        )
        deleted_auth_codes = cursor.rowcount
        if deleted_auth_codes > 0:
            print(
                f"✅ 오래된 auth_code {deleted_auth_codes}개 삭제 (최근 {keep_auth_codes}개 유지)"
            )

        conn.commit()

        # 정리 후 상태
        print()
        cursor.execute(
            "SELECT token_type, COUNT(*) FROM dcr_oauth GROUP BY token_type ORDER BY token_type"
        )
        print("정리 후 토큰 개수:")
        for row in cursor.fetchall():
            print(f"  {row[0]:15}: {row[1]:2}개")

        cursor.execute("SELECT COUNT(*) FROM dcr_oauth")
        total_after = cursor.fetchone()[0]
        print()
        print(f"전체: {total_before}개 → {total_after}개 (삭제: {total_before - total_after}개)")
        print()
        print("✅ 정리 완료!")

    except Exception as e:
        conn.rollback()
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="OAuth 토큰 정리")
    parser.add_argument(
        "--keep-clients",
        type=int,
        default=3,
        help="유지할 최근 client 개수 (기본값: 3)",
    )
    parser.add_argument(
        "--keep-auth-codes",
        type=int,
        default=5,
        help="유지할 최근 auth_code 개수 (기본값: 5)",
    )

    args = parser.parse_args()

    cleanup_oauth_tokens(
        keep_clients=args.keep_clients, keep_auth_codes=args.keep_auth_codes
    )
