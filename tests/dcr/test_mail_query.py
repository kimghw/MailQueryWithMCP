#!/usr/bin/env python3
"""메일 조회 상세 테스트"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from infra.core.database import get_database_manager
from modules.enrollment.account import AccountCryptoHelpers

def test_mail_query():
    """GraphAPI를 통한 메일 조회 테스트"""

    print("\n=== 메일 조회 상세 테스트 ===\n")

    # 토큰 가져오기
    db_manager = get_database_manager()
    crypto = AccountCryptoHelpers()

    user_id = os.getenv("AUTO_REGISTER_USER_ID", "kimghw")

    account = db_manager.fetch_one("""
        SELECT access_token, email
        FROM accounts
        WHERE user_id = ?
    """, (user_id,))

    if not account or not account[0]:
        print("❌ 토큰이 없습니다")
        return

    access_token = crypto.account_decrypt_sensitive_data(account[0])
    email = account[1]

    print(f"사용자: {email}")
    print("-" * 60)

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # 1. 받은 편지함 메일 개수
    print("\n📊 메일함 통계:")

    # 전체 메일 수
    count_response = requests.get(
        'https://graph.microsoft.com/v1.0/me/messages/$count',
        headers={**headers, 'ConsistencyLevel': 'eventual'}
    )

    if count_response.status_code == 200:
        print(f"  - 전체 메일: {count_response.text}개")

    # 읽지 않은 메일
    unread_response = requests.get(
        'https://graph.microsoft.com/v1.0/me/messages?$filter=isRead eq false&$count=true',
        headers={**headers, 'ConsistencyLevel': 'eventual'}
    )

    if unread_response.status_code == 200:
        unread_data = unread_response.json()
        print(f"  - 읽지 않은 메일: {unread_data.get('@odata.count', 'N/A')}개")

    # 2. 최근 메일 상세 조회
    print("\n📧 최근 메일 5개 상세:")
    print("-" * 60)

    mail_response = requests.get(
        'https://graph.microsoft.com/v1.0/me/messages?$top=5&$select=subject,from,toRecipients,receivedDateTime,bodyPreview,hasAttachments,importance,isRead',
        headers=headers
    )

    if mail_response.status_code == 200:
        mails = mail_response.json()
        mail_list = mails.get('value', [])

        for i, mail in enumerate(mail_list, 1):
            print(f"\n메일 {i}:")
            print(f"  제목: {mail.get('subject', 'N/A')}")
            print(f"  발신자: {mail.get('from', {}).get('emailAddress', {}).get('address', 'N/A')}")

            # 수신자 목록
            recipients = mail.get('toRecipients', [])
            if recipients:
                recipient_emails = [r.get('emailAddress', {}).get('address', 'N/A') for r in recipients[:3]]
                print(f"  수신자: {', '.join(recipient_emails)}")

            print(f"  날짜: {mail.get('receivedDateTime', 'N/A')[:19]}")
            print(f"  읽음: {'예' if mail.get('isRead') else '아니오'}")
            print(f"  중요도: {mail.get('importance', 'normal')}")
            print(f"  첨부파일: {'있음' if mail.get('hasAttachments') else '없음'}")

            # 본문 미리보기 (처음 100자)
            preview = mail.get('bodyPreview', '')[:100]
            if preview:
                print(f"  본문 미리보기: {preview}...")

    # 3. 특정 발신자 메일 검색
    print("\n\n🔍 특정 발신자 메일 검색 (block@krs.co.kr):")
    print("-" * 60)

    search_response = requests.get(
        "https://graph.microsoft.com/v1.0/me/messages?$filter=from/emailAddress/address eq 'block@krs.co.kr'&$top=3&$select=subject,receivedDateTime",
        headers=headers
    )

    if search_response.status_code == 200:
        search_results = search_response.json()
        search_list = search_results.get('value', [])

        if search_list:
            for mail in search_list:
                print(f"  - [{mail.get('receivedDateTime', 'N/A')[:10]}] {mail.get('subject', 'N/A')[:60]}")
        else:
            print("  해당 발신자의 메일이 없습니다")

    # 4. 폴더 목록
    print("\n\n📁 메일 폴더 목록:")
    print("-" * 60)

    folders_response = requests.get(
        'https://graph.microsoft.com/v1.0/me/mailFolders',
        headers=headers
    )

    if folders_response.status_code == 200:
        folders = folders_response.json()
        folder_list = folders.get('value', [])

        for folder in folder_list[:10]:  # 처음 10개만
            print(f"  - {folder.get('displayName')} ({folder.get('totalItemCount', 0)}개)")
            if folder.get('unreadItemCount', 0) > 0:
                print(f"    └─ 읽지 않음: {folder.get('unreadItemCount')}개")

    print("\n✅ 메일 조회 테스트 완료!")

if __name__ == "__main__":
    test_mail_query()