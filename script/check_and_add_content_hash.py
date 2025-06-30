#!/usr/bin/env python3
"""
DB 스키마 확인 및 content_hash 컬럼 추가 스크립트
"""

import sys
import os

# Python 경로에 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from infra.core.database import get_database_manager

def main():
    """DB 스키마 확인 및 content_hash 컬럼 추가"""
    
    db = get_database_manager()

    # mail_history 테이블 구조 확인
    table_info = db.get_table_info('mail_history')
    print("mail_history 테이블 컬럼:")
    for col in table_info:
        print(f"  - {col['name']}: {col['type']}")

    # content_hash 컬럼이 있는지 확인
    has_content_hash = any(col['name'] == 'content_hash' for col in table_info)
    print(f"\ncontent_hash 컬럼 존재: {has_content_hash}")

    # 없다면 추가
    if not has_content_hash:
        print("content_hash 컬럼을 추가합니다...")
        db.execute_query("ALTER TABLE mail_history ADD COLUMN content_hash TEXT")
        db.execute_query("CREATE INDEX idx_mail_history_content_hash ON mail_history (content_hash)")
        print("content_hash 컬럼 추가 완료")
    else:
        print("content_hash 컬럼이 이미 존재합니다.")

if __name__ == "__main__":
    main()
