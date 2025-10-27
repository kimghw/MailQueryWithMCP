#!/usr/bin/env python3
"""
graphapi.db 데이터베이스 생성 및 스키마 적용 스크립트
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from infra.core.logger import get_logger

logger = get_logger(__name__)

def create_database():
    """graphapi.db를 생성하고 초기 스키마를 적용합니다"""

    # 데이터 디렉토리 확인/생성
    data_dir = Path("data")
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Created data directory: {data_dir}")

    # 데이터베이스 경로
    db_path = data_dir / "graphapi.db"
    schema_path = Path("infra/migrations/initial_schema.sql")

    # 데이터베이스 연결
    logger.info(f"🗄️ Creating/connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 스키마 파일 읽기
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                schema_sql = f.read()

            # 스키마 적용
            logger.info(f"📋 Applying schema from: {schema_path}")
            cursor.executescript(schema_sql)
            conn.commit()
            logger.info("✅ Schema applied successfully")
        else:
            logger.error(f"❌ Schema file not found: {schema_path}")
            return False

        # 생성된 테이블 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        logger.info("\n📊 Created tables:")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            logger.info(f"  ✅ {table_name} (rows: {count})")

        # accounts 테이블 구조 확인
        logger.info("\n🔍 Accounts table structure:")
        cursor.execute("PRAGMA table_info(accounts)")
        columns = cursor.fetchall()
        for col in columns:
            logger.info(f"  - {col[1]} ({col[2]})")

        return True

    except Exception as e:
        logger.error(f"❌ Error creating database: {e}")
        return False
    finally:
        conn.close()

def check_existing_data():
    """기존 데이터 확인"""
    db_path = Path("data/graphapi.db")

    if not db_path.exists():
        logger.info("❌ Database does not exist yet")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # accounts 테이블 데이터 확인
        cursor.execute("SELECT COUNT(*) FROM accounts")
        count = cursor.fetchone()[0]
        logger.info(f"\n📊 Existing accounts: {count}")

        if count > 0:
            cursor.execute("""
                SELECT user_id, email, status, auth_type, created_at
                FROM accounts
                ORDER BY created_at DESC
                LIMIT 5
            """)
            rows = cursor.fetchall()
            logger.info("Recent accounts:")
            for row in rows:
                logger.info(f"  - {row[0]}: {row[1]} ({row[2]}, {row[3]}) - {row[4]}")

    except sqlite3.OperationalError as e:
        logger.error(f"❌ Error reading database: {e}")
    finally:
        conn.close()

def main():
    """메인 실행 함수"""
    logger.info("=" * 60)
    logger.info("🚀 GraphAPI Database Creation Script")
    logger.info("=" * 60)

    # 기존 데이터 확인
    db_path = Path("data/graphapi.db")
    if db_path.exists():
        logger.warning(f"⚠️ Database already exists: {db_path}")
        check_existing_data()

        response = input("\n❓ Do you want to recreate the database? (y/n): ").lower()
        if response != 'y':
            logger.info("❌ Database creation cancelled")
            return

        # 백업 생성
        backup_path = db_path.with_suffix(f".db.backup_{Path(db_path).stat().st_mtime:.0f}")
        logger.info(f"📦 Creating backup: {backup_path}")
        import shutil
        shutil.copy2(db_path, backup_path)
        logger.info("✅ Backup created")

    # 데이터베이스 생성
    if create_database():
        logger.info("\n✅ Database created successfully!")
        check_existing_data()
    else:
        logger.error("\n❌ Failed to create database")
        sys.exit(1)

if __name__ == "__main__":
    main()