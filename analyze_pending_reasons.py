#!/usr/bin/env python3
"""
Pending 이벤트가 많은 이유 분석
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import sqlite3
from collections import defaultdict
from pathlib import Path


def analyze_pending():
    """Pending 이벤트 상세 분석"""
    db_path = Path("./data/iacsgraph.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("🔍 Pending 이벤트가 많은 이유 분석")
    print("=" * 60)

    # 1. 전체 pending 통계
    cursor.execute(
        """
        SELECT error_reason, COUNT(*) as count
        FROM agenda_pending
        WHERE processed = 0
        GROUP BY error_reason
        ORDER BY count DESC
    """
    )

    print("\n1️⃣ Pending 이유별 통계")
    print("-" * 40)

    total_pending = 0
    for row in cursor.fetchall():
        count = row["count"]
        total_pending += count
        print(f"• {row['error_reason']}: {count}개")

    print(f"\n총 Pending: {total_pending}개")

    # 2. agenda_not_found 상세 분석
    print("\n2️⃣ agenda_not_found 상세 분석")
    print("-" * 40)

    cursor.execute(
        """
        SELECT raw_event_data
        FROM agenda_pending
        WHERE error_reason = 'agenda_not_found'
        AND processed = 0
        LIMIT 10
    """
    )

    agenda_versions = defaultdict(int)

    for row in cursor.fetchall():
        try:
            data = json.loads(row["raw_event_data"])
            event_info = data.get("event_info", {})
            agenda_base_version = event_info.get("agenda_base_version", "Unknown")
            agenda_code = event_info.get("agenda_code", "Unknown")
            sender_org = event_info.get("sender_organization", "Unknown")

            agenda_versions[f"{agenda_code} ({agenda_base_version})"] += 1

        except:
            pass

    print("\n찾지 못한 아젠다들:")
    for agenda, count in sorted(
        agenda_versions.items(), key=lambda x: x[1], reverse=True
    )[:10]:
        print(f"• {agenda}: {count}개 응답")

    # 3. 실제 존재하는 아젠다와 비교
    print("\n3️⃣ 실제 agenda_chair 테이블과 비교")
    print("-" * 40)

    cursor.execute(
        """
        SELECT agenda_base_version, agenda_code
        FROM agenda_chair
        ORDER BY agenda_code
    """
    )

    existing_agendas = {}
    for row in cursor.fetchall():
        existing_agendas[row["agenda_code"]] = row["agenda_base_version"]

    print("\n존재하는 아젠다:")
    for code, version in existing_agendas.items():
        print(f"• {code}: {version}")

    # 4. 매칭 문제 분석
    print("\n4️⃣ 매칭 문제 분석")
    print("-" * 40)

    # 몇 개의 pending 이벤트 샘플 분석
    cursor.execute(
        """
        SELECT raw_event_data
        FROM agenda_pending
        WHERE error_reason = 'agenda_not_found'
        AND processed = 0
        LIMIT 5
    """
    )

    print("\n샘플 분석:")
    for i, row in enumerate(cursor.fetchall(), 1):
        try:
            data = json.loads(row["raw_event_data"])
            event_info = data.get("event_info", {})

            print(f"\n[샘플 {i}]")
            print(f"  agenda_code: {event_info.get('agenda_code')}")
            print(f"  agenda_base_version: {event_info.get('agenda_base_version')}")
            print(f"  sender_org: {event_info.get('sender_organization')}")
            print(f"  response_org: {event_info.get('response_org')}")

            # 매칭 시도
            agenda_code = event_info.get("agenda_code")
            if agenda_code in existing_agendas:
                print(f"  ⚠️ 매칭 실패: DB에는 '{existing_agendas[agenda_code]}' 있음")
            else:
                print(f"  ❌ agenda_code '{agenda_code}'가 DB에 없음")

        except Exception as e:
            print(f"  오류: {str(e)}")

    # 5. 중복 처리 시도 분석
    print("\n5️⃣ 중복 처리 시도 분석")
    print("-" * 40)

    cursor.execute(
        """
        SELECT event_id, COUNT(*) as count
        FROM agenda_pending
        GROUP BY event_id
        HAVING count > 1
    """
    )

    duplicates = cursor.fetchall()
    print(f"중복 event_id: {len(duplicates)}개")

    conn.close()


if __name__ == "__main__":
    analyze_pending()
