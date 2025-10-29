"""
Teams DB Manager
Teams 채팅 정보의 데이터베이스 관리
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from infra.core.logger import get_logger
from infra.core.database import get_database_manager

logger = get_logger(__name__)


class TeamsDBManager:
    """Teams 채팅 DB 관리"""

    def __init__(self):
        self.db = get_database_manager()

    async def find_chat_by_name(self, user_id: str, recipient_name: str) -> Optional[str]:
        """
        사용자 이름으로 chat_id 검색

        Args:
            user_id: 사용자 ID
            recipient_name: 검색할 상대방 이름

        Returns:
            chat_id 또는 None
        """
        try:
            # DB에서 이름으로 검색 (대소문자 무시)
            result = self.db.execute_query(
                """
                SELECT chat_id FROM teams_chats
                WHERE user_id = ?
                AND is_active = TRUE
                AND (
                    LOWER(peer_user_name) LIKE LOWER(?)
                    OR LOWER(topic) LIKE LOWER(?)
                )
                ORDER BY last_message_time DESC
                LIMIT 1
                """,
                (user_id, f"%{recipient_name}%", f"%{recipient_name}%"),
                fetch_result=True
            )

            if result and len(result) > 0:
                chat_id = result[0][0]
                logger.info(f"✅ 사용자 '{recipient_name}' 채팅 찾음: {chat_id}")
                return chat_id
            else:
                logger.warning(f"⚠️ 사용자 '{recipient_name}' 채팅을 찾을 수 없습니다")
                return None

        except Exception as e:
            logger.error(f"❌ 채팅 검색 오류: {str(e)}", exc_info=True)
            return None

    async def get_recent_chat_id(self, user_id: str) -> Optional[str]:
        """
        최근 대화한 chat_id 조회

        Args:
            user_id: 사용자 ID

        Returns:
            chat_id 또는 None
        """
        try:
            result = self.db.execute_query(
                """
                SELECT chat_id FROM teams_chats
                WHERE user_id = ? AND is_active = TRUE
                ORDER BY
                    CASE
                        WHEN last_sent_at IS NOT NULL THEN last_sent_at
                        WHEN last_received_at IS NOT NULL THEN last_received_at
                        WHEN last_message_time IS NOT NULL THEN last_message_time
                        ELSE created_at
                    END DESC
                LIMIT 1
                """,
                (user_id,),
                fetch_result=True
            )

            if result and len(result) > 0:
                chat_id = result[0][0]
                logger.info(f"✅ 최근 채팅 찾음: {chat_id}")
                return chat_id
            else:
                logger.warning("⚠️ 최근 채팅을 찾을 수 없습니다")
                return None

        except Exception as e:
            logger.error(f"❌ 최근 채팅 조회 오류: {str(e)}", exc_info=True)
            return None

    async def sync_chats_to_db(self, user_id: str, chats: List[Dict[str, Any]]) -> None:
        """
        채팅 목록을 DB에 동기화

        Args:
            user_id: 사용자 ID
            chats: Graph API에서 조회한 채팅 목록
        """
        try:
            # 현재 조회된 chat_id들
            current_chat_ids = {chat.get("id") for chat in chats}

            # 기존 DB의 활성 chat_id들 조회
            existing_chats = self.db.execute_query(
                "SELECT chat_id FROM teams_chats WHERE user_id = ? AND is_active = TRUE",
                (user_id,),
                fetch_result=True
            )
            existing_chat_ids = {row[0] for row in existing_chats}

            # 삭제된 채팅 비활성화 (Graph API에는 없지만 DB에는 있는 것)
            deleted_chat_ids = existing_chat_ids - current_chat_ids
            for chat_id in deleted_chat_ids:
                self.db.execute_query(
                    "UPDATE teams_chats SET is_active = FALSE, updated_at = ? WHERE user_id = ? AND chat_id = ?",
                    (datetime.utcnow().isoformat(), user_id, chat_id)
                )
                logger.info(f"🗑️ 채팅 비활성화: {chat_id}")

            # 각 채팅 정보를 DB에 UPSERT
            for chat in chats:
                chat_id = chat.get("id")
                chat_type = chat.get("chatType", "unknown")
                topic = chat.get("topic", "")

                # 멤버 정보 추출
                members = chat.get("members", [])
                member_count = len(members)
                members_json = json.dumps(members, ensure_ascii=False)

                # 1:1 채팅인 경우 상대방 정보 추출
                peer_user_name = None
                peer_user_email = None
                if chat_type == "oneOnOne" and len(members) >= 2:
                    # 두 번째 멤버를 상대방으로 간주 (첫 번째는 보통 본인)
                    # 더 정확하게는 user_id와 비교해야 하지만, 간단히 두 번째 선택
                    peer_member = members[1] if len(members) > 1 else members[0]
                    peer_user_name = peer_member.get("displayName", "")
                    peer_user_email = peer_member.get("email", "")

                # 마지막 메시지 정보
                last_message_preview = chat.get("lastMessagePreview", {}).get("body", {}).get("content", "")
                last_message_time = chat.get("lastUpdatedDateTime", "")

                # DB에 UPSERT
                self.db.execute_query(
                    """
                    INSERT INTO teams_chats (
                        user_id, chat_id, chat_type, topic,
                        member_count, members_json, peer_user_name, peer_user_email,
                        last_message_preview, last_message_time,
                        created_at, updated_at, last_sync_at, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE)
                    ON CONFLICT(user_id, chat_id) DO UPDATE SET
                        chat_type = excluded.chat_type,
                        topic = excluded.topic,
                        member_count = excluded.member_count,
                        members_json = excluded.members_json,
                        peer_user_name = excluded.peer_user_name,
                        peer_user_email = excluded.peer_user_email,
                        last_message_preview = excluded.last_message_preview,
                        last_message_time = excluded.last_message_time,
                        updated_at = excluded.updated_at,
                        last_sync_at = excluded.last_sync_at,
                        is_active = TRUE
                    """,
                    (
                        user_id, chat_id, chat_type, topic,
                        member_count, members_json, peer_user_name, peer_user_email,
                        last_message_preview, last_message_time,
                        datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), datetime.utcnow().isoformat()
                    )
                )

            logger.info(f"✅ DB 동기화 완료: {len(chats)}개 채팅, {len(deleted_chat_ids)}개 비활성화")

        except Exception as e:
            logger.error(f"❌ DB 동기화 오류: {str(e)}", exc_info=True)

    async def update_last_sent_at(self, user_id: str, chat_id: str) -> None:
        """
        메시지 전송 시간 업데이트

        Args:
            user_id: 사용자 ID
            chat_id: 채팅 ID
        """
        try:
            self.db.execute_query(
                "UPDATE teams_chats SET last_sent_at = ?, updated_at = ? WHERE user_id = ? AND chat_id = ?",
                (datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), user_id, chat_id)
            )
        except Exception as e:
            logger.warning(f"⚠️ DB 업데이트 실패 (무시): {str(e)}")
