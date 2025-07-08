"""
메일 처리 오케스트레이터 - 메일 처리 워크플로우 총괄
modules/mail_process/mail_processor_orchestrator.py
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

from infra.core.logger import get_logger
from infra.core.database import get_database_manager
from .services.filtering_service import FilteringService
from .services.queue_service import MailQueueService
from .services.processing_service import ProcessingService
from .services.db_service import MailDatabaseService
from .mail_processor_schema import (
    MailProcessingResult,
    ProcessedMailData,
    GraphMailItem,
)


class MailProcessorOrchestrator:
    """메일 처리 오케스트레이터 - 순수 비즈니스 로직만 포함"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.db_manager = get_database_manager()

        # 서비스 초기화
        self.filtering_service = FilteringService()
        self.queue_service = MailQueueService()
        self.processing_service = ProcessingService()
        self.db_service = MailDatabaseService()

        # 백그라운드 태스크
        self._background_task: Optional[asyncio.Task] = None
        self._should_stop = False

        self.logger.info("오케스트레이터 초기화 완료")

    async def enqueue_mail_batch(
        self, account_id: str, mails: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        외부에서 전달받은 메일 배치를 전처리하고 큐에 저장

        Args:
            account_id: 사용자 ID
            mails: 메일 리스트 (딕셔너리 형태)

        Returns:
            큐 저장 결과
        """
        try:
            self.logger.info(
                f"메일 배치 처리 시작 - account_id: {account_id}, 메일 수: {len(mails)}개"
            )

            enqueued = 0
            filtered = 0
            duplicates = 0
            errors = []

            for mail in mails:
                try:
                    # GraphMailItem으로 변환 (검증)
                    mail_item = GraphMailItem(**mail)

                    # 1. 필터링 체크
                    if self.filtering_service.is_enabled():
                        filter_result = await self.filtering_service.filter_mail(
                            {
                                "mail": mail,
                                "cleaned_content": "",  # 필터링 시점에는 아직 정제 전
                            }
                        )

                        if filter_result["filtered"]:
                            filtered += 1
                            self.logger.debug(
                                f"메일 필터링됨 - ID: {mail_item.id}, "
                                f"이유: {filter_result['reason']}"
                            )
                            continue

                    # 2. DB 중복 확인
                    if self.db_service.check_duplicate_by_id(mail_item.id):
                        duplicates += 1
                        self.logger.debug(f"중복 메일 발견 - ID: {mail_item.id}")
                        continue

                    # 3. 텍스트 정제
                    cleaned_content = self.queue_service._clean_mail_content(mail_item)

                    # 4. 큐에 추가
                    queue_item = {
                        "account_id": account_id,
                        "mail": mail,
                        "cleaned_content": cleaned_content,
                        "enqueued_at": datetime.now().isoformat(),
                    }

                    await self.queue_service.add_to_queue(queue_item)
                    enqueued += 1

                except Exception as e:
                    error_msg = f"메일 처리 실패 - ID: {mail.get('id', 'unknown')}, error: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)

            # 결과 요약
            result = {
                "account_id": account_id,
                "total": len(mails),
                "enqueued": enqueued,
                "filtered": filtered,
                "duplicates": duplicates,
                "errors": len(errors),
                "queue_size": await self.queue_service.get_queue_size(),
                "success": len(errors) == 0,
            }

            self.logger.info(
                f"메일 배치 처리 완료 - "
                f"총: {result['total']}, "
                f"큐 저장: {result['enqueued']}, "
                f"필터링: {result['filtered']}, "
                f"중복: {result['duplicates']}, "
                f"오류: {result['errors']}"
            )

            return result

        except Exception as e:
            self.logger.error(f"메일 배치 처리 중 오류 발생: {str(e)}")
            raise

    async def process_batch(self) -> List[MailProcessingResult]:
        """
        큐에서 배치를 가져와 처리

        Returns:
            처리 결과 리스트
        """
        try:
            # 1. 큐에서 배치 가져오기
            batch = await self.queue_service.dequeue_batch()

            if not batch:
                self.logger.debug("처리할 배치가 없음")
                return []

            self.logger.info(f"배치 처리 시작 - 크기: {len(batch)}")

            # 2. 배치 내 각 메일 처리
            results = []
            for item in batch:
                try:
                    # 메일 처리 (키워드 추출 등)
                    result = await self.processing_service.process_mail(
                        account_id=item["account_id"],
                        mail_data=item["mail"],
                        cleaned_content=item["cleaned_content"],
                    )

                    # DB 저장
                    if result.success and result.processed_data:
                        await self.db_service.save_processed_mail(result.processed_data)

                    results.append(result)

                except Exception as e:
                    self.logger.error(f"메일 처리 실패: {str(e)}")
                    # 실패한 메일도 결과에 포함
                    results.append(
                        MailProcessingResult(
                            success=False,
                            mail_id=item["mail"].get("id", "unknown"),
                            account_id=item["account_id"],
                            error=str(e),
                        )
                    )

            # 3. 처리 결과 통계
            success_count = sum(1 for r in results if r.success)
            self.logger.info(
                f"배치 처리 완료 - "
                f"전체: {len(results)}, "
                f"성공: {success_count}, "
                f"실패: {len(results) - success_count}"
            )

            return results

        except Exception as e:
            self.logger.error(f"배치 처리 중 오류 발생: {str(e)}")
            raise

    async def start_background_processor(self):
        """백그라운드 큐 처리 시작"""
        if self._background_task and not self._background_task.done():
            self.logger.warning("백그라운드 프로세서가 이미 실행 중")
            return

        self._should_stop = False
        self._background_task = asyncio.create_task(self._background_processor())
        self.logger.info("백그라운드 큐 프로세서 시작됨")

    async def stop_background_processor(self):
        """백그라운드 큐 처리 중지"""
        if not self._background_task:
            return

        self._should_stop = True

        try:
            await asyncio.wait_for(self._background_task, timeout=10.0)
        except asyncio.TimeoutError:
            self.logger.warning("백그라운드 프로세서 종료 타임아웃")
            self._background_task.cancel()

        self._background_task = None
        self.logger.info("백그라운드 큐 프로세서 중지됨")

    async def _background_processor(self):
        """백그라운드 큐 처리 루프"""
        self.logger.info("큐 프로세서 시작")
        consecutive_empty_count = 0
        max_empty_count = 3  # 3번 연속으로 큐가 비어있으면 종료

        while not self._should_stop:
            try:
                # 큐 상태 확인
                status = await self.queue_service.get_queue_status()

                if status["is_empty"]:
                    consecutive_empty_count += 1
                    if consecutive_empty_count >= max_empty_count:
                        self.logger.info(
                            f"큐가 {max_empty_count}번 연속 비어있음. 프로세서 종료"
                        )
                        break

                    # 큐가 비어있으면 잠시 대기
                    await asyncio.sleep(5)
                    continue

                # 큐에 데이터가 있으면 카운터 리셋
                consecutive_empty_count = 0

                # 배치 처리
                await self.process_batch()

                # 처리 간격
                await asyncio.sleep(1)

            except Exception as e:
                self.logger.error(f"백그라운드 처리 중 오류: {str(e)}")
                await asyncio.sleep(5)

        self.logger.info("큐 프로세서 종료")
        self._background_task = None  # 자동 종료 시 태스크 정리

    async def get_processing_stats(self) -> Dict[str, Any]:
        """처리 통계 조회"""
        queue_status = await self.queue_service.get_queue_status()
        db_stats = await self.db_service.get_statistics()

        return {
            "queue": queue_status,
            "database": db_stats,
            "background_processor": {
                "running": self._background_task is not None
                and not self._background_task.done()
            },
        }

    async def cleanup(self):
        """리소스 정리"""
        await self.stop_background_processor()
        self.logger.info("리소스 정리 완료")

    async def __aenter__(self):
        """컨텍스트 매니저 진입"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        await self.cleanup()
