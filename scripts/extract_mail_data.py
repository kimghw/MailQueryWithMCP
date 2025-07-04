#!/usr/bin/env python3
"""
mail_history 테이블에서 subject, sender, keywords 데이터를 txt 파일로 추출하는 스크립트
"""

import sqlite3
import os
import json
from datetime import datetime
from pathlib import Path


def extract_mail_data_to_txt():
    """mail_history에서 subject, sender, keywords를 추출하여 txt 파일로 저장"""

    # 데이터베이스 경로
    db_path = "data/iacsgraph.db"

    if not os.path.exists(db_path):
        print(f"데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return

    # 출력 디렉토리 생성
    output_dir = Path("data/extracted")
    output_dir.mkdir(exist_ok=True)

    # 현재 시간을 파일명에 포함
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        # 데이터베이스 연결
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # mail_history 테이블에서 데이터 추출
        query = """
        SELECT 
            id,
            subject,
            sender,
            keywords,
            received_time
        FROM mail_history 
        ORDER BY received_time DESC
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        if not rows:
            print("mail_history 테이블에 데이터가 없습니다.")
            return

        # 전체 데이터를 하나의 파일로 저장
        output_file = output_dir / f"mail_data_all_{timestamp}.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"MAIL HISTORY 데이터 추출 결과\n")
            f.write(f"추출 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"총 {len(rows)}개의 메일 데이터\n")
            f.write("=" * 80 + "\n\n")

            for i, (mail_id, subject, sender, keywords, received_time) in enumerate(
                rows, 1
            ):
                f.write(f"[{i:04d}] ID: {mail_id}\n")
                f.write(f"수신일시: {received_time}\n")
                f.write(f"발신자: {sender or 'N/A'}\n")
                f.write(f"제목: {subject or 'N/A'}\n")

                # keywords JSON 파싱
                if keywords:
                    try:
                        keyword_list = json.loads(keywords)
                        if isinstance(keyword_list, list):
                            f.write(f"키워드: {', '.join(keyword_list)}\n")
                        else:
                            f.write(f"키워드: {keywords}\n")
                    except json.JSONDecodeError:
                        f.write(f"키워드: {keywords}\n")
                else:
                    f.write(f"키워드: N/A\n")

                f.write("-" * 60 + "\n\n")

        # Subject만 추출
        subject_file = output_dir / f"mail_subjects_{timestamp}.txt"
        with open(subject_file, "w", encoding="utf-8") as f:
            f.write("메일 제목 목록\n")
            f.write("=" * 50 + "\n")
            for i, (_, subject, _, _, _) in enumerate(rows, 1):
                if subject:
                    f.write(f"{i:04d}. {subject}\n")

        # Sender만 추출 (고유값)
        sender_file = output_dir / f"mail_senders_{timestamp}.txt"
        with open(sender_file, "w", encoding="utf-8") as f:
            f.write("메일 발신자 목록 (고유값)\n")
            f.write("=" * 50 + "\n")
            senders = set()
            for _, _, sender, _, _ in rows:
                if sender:
                    senders.add(sender)

            for i, sender in enumerate(sorted(senders), 1):
                f.write(f"{i:04d}. {sender}\n")

        # 발신자별 메일 수 통계
        sender_stats_file = output_dir / f"mail_sender_stats_{timestamp}.txt"
        with open(sender_stats_file, "w", encoding="utf-8") as f:
            f.write("발신자별 메일 수 통계\n")
            f.write("=" * 50 + "\n")
            sender_count = {}
            for _, _, sender, _, _ in rows:
                if sender:
                    sender_count[sender] = sender_count.get(sender, 0) + 1

            # 메일 수 기준으로 정렬
            sorted_senders = sorted(
                sender_count.items(), key=lambda x: x[1], reverse=True
            )
            for i, (sender, count) in enumerate(sorted_senders, 1):
                f.write(f"{i:04d}. {sender} ({count}개)\n")

        # Keywords만 추출
        keywords_file = output_dir / f"mail_keywords_{timestamp}.txt"
        with open(keywords_file, "w", encoding="utf-8") as f:
            f.write("메일 키워드 목록 (고유값)\n")
            f.write("=" * 50 + "\n")
            all_keywords = set()
            for _, _, _, keywords, _ in rows:
                if keywords:
                    try:
                        keyword_list = json.loads(keywords)
                        if isinstance(keyword_list, list):
                            all_keywords.update(keyword_list)
                        else:
                            # JSON이 아닌 경우 쉼표로 분리 시도
                            keyword_list = [
                                k.strip() for k in str(keywords).split(",") if k.strip()
                            ]
                            all_keywords.update(keyword_list)
                    except json.JSONDecodeError:
                        # JSON 파싱 실패시 쉼표로 분리
                        keyword_list = [
                            k.strip() for k in str(keywords).split(",") if k.strip()
                        ]
                        all_keywords.update(keyword_list)

            for i, keyword in enumerate(sorted(all_keywords), 1):
                f.write(f"{i:04d}. {keyword}\n")

        # 키워드별 빈도 통계
        keyword_stats_file = output_dir / f"mail_keyword_stats_{timestamp}.txt"
        with open(keyword_stats_file, "w", encoding="utf-8") as f:
            f.write("키워드별 빈도 통계\n")
            f.write("=" * 50 + "\n")
            keyword_count = {}
            for _, _, _, keywords, _ in rows:
                if keywords:
                    try:
                        keyword_list = json.loads(keywords)
                        if isinstance(keyword_list, list):
                            for keyword in keyword_list:
                                keyword_count[keyword] = (
                                    keyword_count.get(keyword, 0) + 1
                                )
                        else:
                            keyword_list = [
                                k.strip() for k in str(keywords).split(",") if k.strip()
                            ]
                            for keyword in keyword_list:
                                keyword_count[keyword] = (
                                    keyword_count.get(keyword, 0) + 1
                                )
                    except json.JSONDecodeError:
                        keyword_list = [
                            k.strip() for k in str(keywords).split(",") if k.strip()
                        ]
                        for keyword in keyword_list:
                            keyword_count[keyword] = keyword_count.get(keyword, 0) + 1

            # 빈도 기준으로 정렬
            sorted_keywords = sorted(
                keyword_count.items(), key=lambda x: x[1], reverse=True
            )
            for i, (keyword, count) in enumerate(sorted_keywords, 1):
                f.write(f"{i:04d}. {keyword} ({count}회)\n")

        # 통계 정보
        stats_file = output_dir / f"mail_statistics_{timestamp}.txt"
        with open(stats_file, "w", encoding="utf-8") as f:
            f.write("메일 데이터 통계\n")
            f.write("=" * 50 + "\n")
            f.write(f"총 메일 수: {len(rows)}\n")
            f.write(
                f"제목이 있는 메일: {sum(1 for _, subject, _, _, _ in rows if subject)}\n"
            )
            f.write(
                f"발신자가 있는 메일: {sum(1 for _, _, sender, _, _ in rows if sender)}\n"
            )
            f.write(
                f"키워드가 있는 메일: {sum(1 for _, _, _, keywords, _ in rows if keywords)}\n"
            )
            f.write(
                f"고유 발신자 수: {len(set(sender for _, _, sender, _, _ in rows if sender))}\n"
            )

            # 키워드 통계
            all_keywords = []
            for _, _, _, keywords, _ in rows:
                if keywords:
                    try:
                        keyword_list = json.loads(keywords)
                        if isinstance(keyword_list, list):
                            all_keywords.extend(keyword_list)
                        else:
                            keyword_list = [
                                k.strip() for k in str(keywords).split(",") if k.strip()
                            ]
                            all_keywords.extend(keyword_list)
                    except json.JSONDecodeError:
                        keyword_list = [
                            k.strip() for k in str(keywords).split(",") if k.strip()
                        ]
                        all_keywords.extend(keyword_list)

            f.write(f"총 키워드 수: {len(all_keywords)}\n")
            f.write(f"고유 키워드 수: {len(set(all_keywords))}\n")

            # 날짜 범위
            dates = [
                received_time for _, _, _, _, received_time in rows if received_time
            ]
            if dates:
                f.write(f"메일 수신 기간: {min(dates)} ~ {max(dates)}\n")

        print(f"데이터 추출 완료!")
        print(f"출력 디렉토리: {output_dir}")
        print(f"생성된 파일들:")
        print(f"  - 전체 데이터: {output_file}")
        print(f"  - 제목 목록: {subject_file}")
        print(f"  - 발신자 목록: {sender_file}")
        print(f"  - 발신자 통계: {sender_stats_file}")
        print(f"  - 키워드 목록: {keywords_file}")
        print(f"  - 키워드 통계: {keyword_stats_file}")
        print(f"  - 통계 정보: {stats_file}")

    except sqlite3.Error as e:
        print(f"데이터베이스 오류: {e}")
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    extract_mail_data_to_txt()
