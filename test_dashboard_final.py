#!/usr/bin/env python3
"""
Email Dashboard 최종 테스트
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import sqlite3
from pathlib import Path


def test_dashboard():
    """대시보드 테스트"""
    db_path = Path("./data/iacsgraph.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("🧪 Email Dashboard 최종 테스트")
    print("=" * 60)

    # 1. 테이블 상태 확인
    print("\n1️⃣ 테이블 상태 확인")
    print("-" * 40)

    tables = [
        "agenda_all",
        "agenda_chair",
        "agenda_responses_content",
        "agenda_responses_receivedtime",
        "agenda_pending",
    ]

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"{table}: {count}개 레코드")

    # 2. agenda_chair 상세 확인
    print("\n2️⃣ agenda_chair 테이블 상세")
    print("-" * 40)

    cursor.execute(
        """
        SELECT agenda_base_version, agenda_code, agenda_panel, 
               agenda_year, agenda_number, sender_organization
        FROM agenda_chair
        ORDER BY sent_time DESC
        LIMIT 10
    """
    )

    for row in cursor.fetchall():
        print(
            f"• {row['agenda_base_version']} | {row['agenda_code']} | "
            f"Panel: {row['agenda_panel']} | Year: {row['agenda_year']} | "
            f"Number: {row['agenda_number']} | From: {row['sender_organization']}"
        )

    # 3. 응답 상태 확인
    print("\n3️⃣ 응답 상태 확인")
    print("-" * 40)

    cursor.execute(
        """
        SELECT c.agenda_base_version, c.agenda_code,
               rc.ABS, rc.BV, rc.CCS, rc.CRS, rc.DNV, rc.IRS, 
               rc.KR, rc.LR, rc.NK, rc.PRS, rc.RINA, rc.IL, rc.TL
        FROM agenda_chair c
        LEFT JOIN agenda_responses_content rc ON c.agenda_base_version = rc.agenda_base_version
        ORDER BY c.sent_time DESC
        LIMIT 5
    """
    )

    for row in cursor.fetchall():
        print(f"\n📋 {row['agenda_base_version']} ({row['agenda_code']})")
        orgs = [
            "ABS",
            "BV",
            "CCS",
            "CRS",
            "DNV",
            "IRS",
            "KR",
            "LR",
            "NK",
            "PRS",
            "RINA",
            "IL",
            "TL",
        ]
        responded = []
        pending = []

        for org in orgs:
            if row[org]:
                responded.append(org)
            else:
                pending.append(org)

        print(f"  ✅ 응답: {', '.join(responded) if responded else '없음'}")
        print(f"  ⏳ 대기: {', '.join(pending) if pending else '없음'}")

    # 4. 미처리 이벤트 분석
    print("\n4️⃣ 미처리 이벤트 분석")
    print("-" * 40)

    cursor.execute(
        """
        SELECT error_reason, COUNT(*) as count
        FROM agenda_pending
        WHERE processed = 0
        GROUP BY error_reason
        ORDER BY count DESC
    """
    )

    for row in cursor.fetchall():
        print(f"• {row['error_reason']}: {row['count']}개")

    # 5. 특정 아젠다 검색 테스트
    print("\n5️⃣ 특정 아젠다 검색 테스트")
    print("-" * 40)

    test_agendas = ["PL24035", "PL25015", "PL24033"]

    for agenda in test_agendas:
        # agenda_chair에서 검색
        cursor.execute(
            """
            SELECT agenda_base_version, agenda_code 
            FROM agenda_chair 
            WHERE agenda_code = ? OR agenda_base_version LIKE ?
        """,
            (agenda, f"%{agenda}%"),
        )

        chair_results = cursor.fetchall()

        # agenda_all에서 검색
        cursor.execute(
            """
            SELECT COUNT(*) as count, sender_type
            FROM agenda_all 
            WHERE agenda_code = ? OR agenda_base_version LIKE ?
            GROUP BY sender_type
        """,
            (agenda, f"%{agenda}%"),
        )

        all_results = cursor.fetchall()

        print(f"\n🔍 {agenda}:")
        print(f"  • agenda_chair: {len(chair_results)}개")
        for row in chair_results:
            print(f"    - {row['agenda_base_version']}")

        print(f"  • agenda_all:")
        for row in all_results:
            print(f"    - {row['sender_type']}: {row['count']}개")

    # 6. 데이터 일관성 검사
    print("\n6️⃣ 데이터 일관성 검사")
    print("-" * 40)

    # agenda_chair에 있지만 응답 테이블에 없는 경우
    cursor.execute(
        """
        SELECT COUNT(*) as count
        FROM agenda_chair c
        LEFT JOIN agenda_responses_content rc ON c.agenda_base_version = rc.agenda_base_version
        WHERE rc.agenda_base_version IS NULL
    """
    )

    missing_response_tables = cursor.fetchone()["count"]
    print(f"• 응답 테이블 누락: {missing_response_tables}개")

    # 중복 event_id 확인
    cursor.execute(
        """
        SELECT event_id, COUNT(*) as count
        FROM agenda_all
        GROUP BY event_id
        HAVING count > 1
    """
    )

    duplicates = cursor.fetchall()
    print(f"• 중복 event_id: {len(duplicates)}개")

    conn.close()

    print("\n" + "=" * 60)
    print("✅ 테스트 완료!")


if __name__ == "__main__":
    test_dashboard()
