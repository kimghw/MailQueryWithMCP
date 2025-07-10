#!/usr/bin/env python3
"""
Dashboard 최종 상태 확인
"""

import sys
sys.path.insert(0, "/home/kimghw/IACSGRAPH")

from infra.core import get_database_manager, get_logger

logger = get_logger(__name__)


def check_final_status():
    """최종 상태 확인"""
    db = get_database_manager()
    
    print("=" * 60)
    print("📊 Email Dashboard 최종 상태")
    print("=" * 60)
    
    # 1. 전체 통계
    print("\n1️⃣ 전체 통계:")
    
    # agenda_all 테이블
    all_count = db.fetch_one("SELECT COUNT(*) as count FROM agenda_all")
    print(f"  • 전체 이벤트 (agenda_all): {all_count['count']}개")
    
    # agenda_chair 테이블
    chair_count = db.fetch_one("SELECT COUNT(*) as count FROM agenda_chair")
    placeholder_count = db.fetch_one(
        "SELECT COUNT(*) as count FROM agenda_chair WHERE parsing_method = 'placeholder'"
    )
    print(f"  • 의장 아젠다 (agenda_chair): {chair_count['count']}개")
    print(f"    - 임시 레코드: {placeholder_count['count']}개")
    
    # pending 테이블
    pending_total = db.fetch_one("SELECT COUNT(*) as count FROM agenda_pending")
    pending_unprocessed = db.fetch_one(
        "SELECT COUNT(*) as count FROM agenda_pending WHERE processed = 0"
    )
    print(f"  • Pending 이벤트: {pending_total['count']}개")
    print(f"    - 미처리: {pending_unprocessed['count']}개")
    print(f"    - 처리됨: {pending_total['count'] - pending_unprocessed['count']}개")
    
    # 2. 미처리 이벤트 분석
    print("\n2️⃣ 미처리 이벤트 분석:")
    
    error_reasons = db.fetch_all("""
        SELECT error_reason, COUNT(*) as count
        FROM agenda_pending
        WHERE processed = 0
        GROUP BY error_reason
        ORDER BY count DESC
    """)
    
    for reason in error_reasons:
        print(f"  • {reason['error_reason']}: {reason['count']}개")
    
    # 3. 응답 현황
    print("\n3️⃣ 응답 현황:")
    
    # 각 아젠다별 응답 수
    response_stats = db.fetch_all("""
        SELECT 
            c.agenda_base_version,
            c.agenda_code,
            c.decision_status,
            (
                SELECT COUNT(*)
                FROM (
                    SELECT 1 FROM agenda_responses_content r
                    WHERE r.agenda_base_version = c.agenda_base_version
                    AND (r.ABS IS NOT NULL OR r.BV IS NOT NULL OR r.CCS IS NOT NULL 
                         OR r.CRS IS NOT NULL OR r.DNV IS NOT NULL OR r.IRS IS NOT NULL 
                         OR r.KR IS NOT NULL OR r.NK IS NOT NULL OR r.PRS IS NOT NULL 
                         OR r.RINA IS NOT NULL OR r.IL IS NOT NULL OR r.TL IS NOT NULL)
                )
            ) as response_count
        FROM agenda_chair c
        ORDER BY c.sent_time DESC
        LIMIT 10
    """)
    
    print("  최근 10개 아젠다:")
    for stat in response_stats:
