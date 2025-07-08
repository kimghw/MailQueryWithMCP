"""
메일 큐 서비스 - 배치 처리를 위한 큐 관리
modules/mail_process/services/queue_service.py
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import deque
import os

from infra.core.logger import get_logger
from modules.mail_process.mail_processor_schema import GraphMailItem
from modules.mail_process.utilities.text_cleaner import TextCleaner


class MailQueueService:
    """메일 큐 서비스 - 배치 처리를 위한 큐 관리"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.text_cleaner = TextCleaner()

        # 큐 저장소 (실제 운영에서는 Redis 등 사용 권장)
        self._queue: deque = deque()
        self._lock = asyncio.Lock()

        # 배치 크기 설정
        self.batch_size = int(os.getenv("MAIL_BATCH_SIZE", "50"))

        self.logger.info(f"메일 큐 서비스 초기화 - 배치 크기: {self.batch_size}")

        # 통계
        self._stats = {
            "total_enqueued": 0,
            "total_dequeued": 0,
            "current_queue_size": 0,
        }

    async def add_to_queue(self, queue_item: Dict[str, Any]) -> None:
        """
        큐에 아이템 추가 (이미 전처리된 아이템)

        Args:
            queue_item: 큐에 추가할 아이템
        """
        async with self._lock:
            self._queue.append(queue_item)
            self._stats["total_enqueued"] += 1
            self._stats["current_queue_size"] = len(self._queue)

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

    async def get_queue_size(self) -> int:
        """현재 큐 크기 반환"""
        async with self._lock:
            return len(self._queue)

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
