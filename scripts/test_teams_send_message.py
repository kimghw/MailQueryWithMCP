#!/usr/bin/env python3
"""
Teams Chat 메시지 전송 테스트
TeamsHandler를 직접 호출하여 메시지 전송
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.teams_mcp.teams_handler import TeamsHandler
from infra.core.logger import get_logger

logger = get_logger(__name__)


async def send_teams_message(user_id: str, chat_id: str, message: str):
    """
    Teams 채팅에 메시지 전송

    Args:
        user_id: 사용자 ID (이메일)
        chat_id: 채팅 ID
        message: 보낼 메시지
    """
    logger.info(f"🚀 Teams 메시지 전송 시작")
    logger.info(f"  • 사용자: {user_id}")
    logger.info(f"  • 채팅 ID: {chat_id}")
    logger.info(f"  • 메시지: {message}")

    # TeamsHandler 인스턴스 생성
    handler = TeamsHandler()

    # 메시지 전송
    result = await handler.send_chat_message(user_id, chat_id, message)

    # 결과 출력
    if result.get("success"):
        logger.info(f"✅ 메시지 전송 성공!")
        logger.info(f"  • Message ID: {result.get('message_id')}")
        print(f"\n✅ 메시지 전송 성공!")
        print(f"Message ID: {result.get('message_id')}")
    else:
        logger.error(f"❌ 메시지 전송 실패: {result.get('message')}")
        print(f"\n❌ 메시지 전송 실패")
        print(f"오류: {result.get('message')}")

    return result


async def list_chats(user_id: str):
    """
    채팅 목록 조회

    Args:
        user_id: 사용자 ID (이메일)
    """
    logger.info(f"📋 채팅 목록 조회 시작")
    logger.info(f"  • 사용자: {user_id}")

    handler = TeamsHandler()
    result = await handler.list_chats(user_id)

    if result.get("success"):
        chats = result.get("chats", [])
        logger.info(f"✅ 채팅 {len(chats)}개 조회 성공")

        print(f"\n💬 총 {len(chats)}개 채팅 조회됨\n")
        for idx, chat in enumerate(chats, 1):
            chat_type = chat.get("chatType", "unknown")
            chat_id = chat.get("id")
            topic = chat.get("topic", "(제목 없음)")

            if chat_type == "oneOnOne":
                print(f"{idx}. [1:1] {topic}")
            elif chat_type == "group":
                print(f"{idx}. [그룹] {topic}")
            else:
                print(f"{idx}. [{chat_type}] {topic}")

            print(f"   ID: {chat_id}\n")
    else:
        logger.error(f"❌ 채팅 목록 조회 실패: {result.get('message')}")
        print(f"\n❌ 채팅 목록 조회 실패")
        print(f"오류: {result.get('message')}")

    return result


async def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="Teams 채팅 메시지 전송 테스트")
    parser.add_argument("--user-id", required=True, help="사용자 ID (이메일)")
    parser.add_argument("--list-chats", action="store_true", help="채팅 목록 조회")
    parser.add_argument("--chat-id", help="채팅 ID")
    parser.add_argument("--message", help="보낼 메시지")

    args = parser.parse_args()

    # 채팅 목록 조회
    if args.list_chats:
        await list_chats(args.user_id)
        return

    # 메시지 전송
    if not args.chat_id or not args.message:
        print("❌ --chat-id와 --message가 필요합니다")
        print("\n사용법:")
        print(f"  # 채팅 목록 조회")
        print(f"  python3 {sys.argv[0]} --user-id kimghw@example.com --list-chats")
        print(f"\n  # 메시지 전송")
        print(f"  python3 {sys.argv[0]} --user-id kimghw@example.com --chat-id 19:xxx... --message '안녕'")
        return

    await send_teams_message(args.user_id, args.chat_id, args.message)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}", exc_info=True)
        print(f"\n❌ 오류 발생: {e}")
        sys.exit(1)
