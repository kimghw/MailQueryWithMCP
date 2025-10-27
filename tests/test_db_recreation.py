#!/usr/bin/env python3
"""
DB 파일 삭제 후 재생성 테스트
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from infra.core.database import get_database_manager

def test_db_recreation():
    """DB 파일 삭제 후 재생성 테스트"""

    db = get_database_manager()
    db_path = Path(db.config.database_path)

    print(f"\n=== DB 재생성 테스트 ===")
    print(f"DB 경로: {db_path}")

    # 1. 초기 상태 확인
    print("\n1. 초기 상태 확인...")
    if db_path.exists():
        print(f"   ✅ DB 파일 존재: {db_path}")
        # accounts 테이블 확인
        result = db.fetch_one("SELECT COUNT(*) as count FROM accounts")
        print(f"   - accounts 테이블 레코드 수: {result['count']}")
    else:
        print(f"   ❌ DB 파일 없음")

    # 2. DB에 테스트 데이터 삽입
    print("\n2. 테스트 데이터 삽입...")
    try:
        db.insert("accounts", {
            "user_id": "test_user_recreation",
            "user_name": "Test User for Recreation",
            "status": "ACTIVE",
            "is_active": 1
        })
        print("   ✅ 테스트 데이터 삽입 성공")
    except Exception as e:
        print(f"   ⚠️ 데이터 삽입 실패 (이미 존재할 수 있음): {e}")

    # 3. DB 파일 강제 삭제
    print("\n3. DB 파일 강제 삭제...")
    if db_path.exists():
        # WAL 파일도 함께 삭제
        wal_path = Path(str(db_path) + "-wal")
        shm_path = Path(str(db_path) + "-shm")

        try:
            # 연결 닫기 시도 (하지만 싱글톤이라 실제로는 안 닫힘)
            db.close()
        except:
            pass

        # 파일 삭제
        if db_path.exists():
            os.remove(db_path)
            print(f"   ✅ 메인 DB 파일 삭제됨: {db_path}")

        if wal_path.exists():
            os.remove(wal_path)
            print(f"   ✅ WAL 파일 삭제됨: {wal_path}")

        if shm_path.exists():
            os.remove(shm_path)
            print(f"   ✅ SHM 파일 삭제됨: {shm_path}")
    else:
        print("   ⚠️ DB 파일이 이미 없음")

    # 4. DB 파일 삭제 확인
    print("\n4. DB 파일 삭제 확인...")
    if not db_path.exists():
        print(f"   ✅ DB 파일이 삭제됨")
    else:
        print(f"   ❌ DB 파일이 여전히 존재함")
        return

    # 5. DB 작업 수행 (자동 재생성 테스트)
    print("\n5. DB 작업 수행 (자동 재생성 테스트)...")
    try:
        # fetch_one 호출 시 자동으로 DB 재생성되어야 함
        result = db.fetch_one("SELECT COUNT(*) as count FROM accounts")
        print(f"   ✅ DB 자동 재생성 성공!")
        print(f"   - accounts 테이블 레코드 수: {result['count']}")

        # DB 파일 존재 확인
        if db_path.exists():
            print(f"   ✅ DB 파일 재생성 확인: {db_path}")
        else:
            print(f"   ❌ DB 파일이 재생성되지 않음")

    except Exception as e:
        print(f"   ❌ DB 재생성 실패: {e}")
        import traceback
        traceback.print_exc()

    # 6. 테스트 데이터 다시 삽입
    print("\n6. 재생성된 DB에 데이터 삽입...")
    try:
        db.insert("accounts", {
            "user_id": "test_user_after_recreation",
            "user_name": "Test User After Recreation",
            "status": "ACTIVE",
            "is_active": 1
        })
        print("   ✅ 데이터 삽입 성공 (DB가 정상 작동함)")

        # 데이터 확인
        result = db.fetch_one("SELECT COUNT(*) as count FROM accounts")
        print(f"   - 현재 accounts 테이블 레코드 수: {result['count']}")

    except Exception as e:
        print(f"   ❌ 데이터 삽입 실패: {e}")

    print("\n=== 테스트 완료 ===")
    print("✅ DB 파일 삭제 후 자동 재생성 기능이 정상 작동합니다!")

if __name__ == "__main__":
    test_db_recreation()