"""
메일 큐 서비스 - 배치 처리를 위한 큐 관리
modules/mail_process/services/queue_service.py
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import deque
import os

from infra.core.logger import get_logger
from infra.core.database import get_database_manager
from modules.mail_process.mail_processor_schema import GraphMailItem
from modules.mail_process.utilities.text_cleaner import TextCleaner
from .db_service import MailDatabaseService


class MailQueueService:
    """메일 큐 서비스 - 배치 처리를 위한 큐 관리"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.db_service = MailDatabaseService()
        self.text_cleaner = TextCleaner()

        # 큐 저장소 (실제 운영에서는 Redis 등 사용 권장)
        self._queue: deque = deque()
        self._lock = asyncio.Lock()

        # 배치 크기 설정
        self.batch_size = int(os.getenv("MAIL_BATCH_SIZE", "50"))

        # 중복 허용 설정
        self.allow_duplicates = (
            os.getenv("MAIL_ALLOW_DUPLICATES", "false").lower() == "true"
        )

        self.logger.info(
            f"메일 큐 서비스 초기화 - 배치 크기: {self.batch_size}, "
            f"중복 허용: {self.allow_duplicates}"
        )

        # 통계
        self._stats = {
            "total_enqueued": 0,
            "total_dequeued": 0,
            "total_duplicates": 0,
            "total_processed": 0,
            "current_queue_size": 0,
        }

    async def enqueue_mails(self, account_id: str, mails: List[Dict]) -> Dict[str, Any]:
        """
        메일을 큐에 저장

        Args:
            account_id: 계정 ID
            mails: 메일 리스트

        Returns:
            큐 저장 결과
        """
        async with self._lock:
            enqueued_count = 0
            duplicate_count = 0

            for mail in mails:
                try:
                    # GraphMailItem으로 변환
                    mail_item = GraphMailItem(**mail)

                    # 1. 중복 검사 (message_id 기반)
                    is_duplicate = self.db_service.check_duplicate_by_id(mail_item.id)

                    if is_duplicate:
                        duplicate_count += 1
                        self.logger.debug(f"중복 메일 발견 - ID: {mail_item.id}")

                        # 중복 허용 설정 확인
                        if not self.allow_duplicates:
                            self.logger.debug(f"중복 메일 스킵 - ID: {mail_item.id}")
                            continue
                        else:
                            self.logger.debug(
                                f"중복 허용 - 큐에 추가 - ID: {mail_item.id}"
                            )

                    # 2. body content 정제
                    cleaned_content = self._clean_mail_content(mail_item)

                    # 3. 큐에 저장할 데이터 준비
                    queue_item = {
                        "account_id": account_id,
                        "mail": mail_item.model_dump(),
                        "cleaned_content": cleaned_content,
                        "enqueued_at": datetime.now().isoformat(),
                    }

                    # 4. 큐에 추가
                    self._queue.append(queue_item)
                    enqueued_count += 1

                except Exception as e:
                    self.logger.error(
                        f"메일 큐 저장 실패 - ID: {mail.get('id', 'unknown')}, "
                        f"error: {str(e)}"
                    )
                    continue

            # 통계 업데이트
            self._stats["total_enqueued"] += enqueued_count
            self._stats["total_duplicates"] += duplicate_count
            self._stats["current_queue_size"] = len(self._queue)

            self.logger.info(
                f"큐 저장 완료 - "
                f"계정: {account_id}, "
                f"저장: {enqueued_count}, "
                f"중복: {duplicate_count}, "
                f"현재 큐 크기: {len(self._queue)}"
            )

            return {
                "account_id": account_id,
                "enqueued": enqueued_count,
                "duplicates": duplicate_count,
                "queue_size": len(self._queue),
            }

    async def dequeue_batch(self) -> List[Dict[str, Any]]:
        """
        배치 크기만큼 큐에서 꺼내기

        Returns:
            배치 아이템 리스트
        """
        async with self._lock:
            batch = []

            # 설정된 배치 크기만큼 또는 큐에 있는 만큼 꺼내기
            items_to_dequeue = min(self.batch_size, len(self._queue))

            for _ in range(items_to_dequeue):
                if self._queue:
                    item = self._queue.popleft()
                    batch.append(item)

            # 통계 업데이트
            self._stats["total_dequeued"] += len(batch)
            self._stats["current_queue_size"] = len(self._queue)

            if batch:
                self.logger.info(
                    f"배치 디큐 - "
                    f"크기: {len(batch)}, "
                    f"남은 큐: {len(self._queue)}"
                )

            return batch

    async def get_queue_status(self) -> Dict[str, Any]:
        """큐 상태 조회"""
        async with self._lock:
            return {
                "queue_size": len(self._queue),
                "batch_size": self.batch_size,
                "statistics": self._stats.copy(),
                "is_empty": len(self._queue) == 0,
            }

    async def clear_queue(self) -> int:
        """큐 비우기 (테스트/관리용)"""
        async with self._lock:
            cleared_count = len(self._queue)
            self._queue.clear()
            self._stats["current_queue_size"] = 0

            self.logger.warning(f"큐 초기화됨 - 제거된 아이템: {cleared_count}개")
            return cleared_count

    def _clean_mail_content(self, mail: GraphMailItem) -> str:
        """
        메일 내용 정제

        Args:
            mail: GraphMailItem 객체

        Returns:
            정제된 내용
        """
        # 제목 추출
        subject = mail.subject or ""

        # 본문 추출
        body_content = ""
        if mail.body and isinstance(mail.body, dict):
            body_content = mail.body.get("content", "")

        # 본문이 없으면 미리보기 사용
        if not body_content:
            body_content = mail.body_preview or ""

        # 제목과 본문 결합 후 정제
        full_content = f"{subject}\n\n{body_content}"
        cleaned = self.text_cleaner.clean_text(full_content)

        return cleaned

    async def peek_queue(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        큐의 앞부분 확인 (디버깅용)

        Args:
            count: 확인할 아이템 수

        Returns:
            큐 아이템 리스트 (실제로 제거하지 않음)
        """
        async with self._lock:
            items = []
            for i, item in enumerate(self._queue):
                if i >= count:
                    break
                # 민감한 정보는 제외하고 요약 정보만
                summary = {
                    "account_id": item["account_id"],
                    "mail_id": item["mail"]["id"],
                    "subject": item["mail"].get("subject", "")[:50],
                    "enqueued_at": item["enqueued_at"],
                    "cleaned_content_length": len(item["cleaned_content"]),
                }
                items.append(summary)

            return items

    async def requeue_failed_items(self, failed_items: List[Dict[str, Any]]) -> int:
        """
        실패한 아이템 재큐잉

        Args:
            failed_items: 실패한 아이템 리스트

        Returns:
            재큐잉된 아이템 수
        """
        async with self._lock:
            requeued_count = 0

            for item in failed_items:
                # 재시도 횟수 증가
                if "retry_count" not in item:
                    item["retry_count"] = 0
                item["retry_count"] += 1

                # 최대 재시도 횟수 확인
                max_retries = int(os.getenv("MAIL_MAX_RETRIES", "3"))
                if item["retry_count"] <= max_retries:
                    item["requeued_at"] = datetime.now().isoformat()
                    self._queue.append(item)
                    requeued_count += 1
                else:
                    self.logger.warning(
                        f"최대 재시도 횟수 초과 - "
                        f"mail_id: {item['mail']['id']}, "
                        f"retries: {item['retry_count']}"
                    )

            self._stats["current_queue_size"] = len(self._queue)

            if requeued_count > 0:
                self.logger.info(f"실패 아이템 재큐잉 - {requeued_count}개")

            return requeued_count

    def get_batch_size(self) -> int:
        """현재 배치 크기 반환"""
        return self.batch_size

    def set_batch_size(self, size: int) -> None:
        """배치 크기 동적 변경"""
        if size < 1:
            raise ValueError("배치 크기는 1 이상이어야 합니다")

        old_size = self.batch_size
        self.batch_size = size
        self.logger.info(f"배치 크기 변경: {old_size} -> {size}")


# 싱글톤 인스턴스
_queue_service_instance: Optional[MailQueueService] = None


def get_queue_service() -> MailQueueService:
    """큐 서비스 싱글톤 인스턴스 반환"""
    global _queue_service_instance
    if _queue_service_instance is None:
        _queue_service_instance = MailQueueService()
    return _queue_service_instance
