"""
메일 처리 오케스트레이터 - 메일 처리 워크플로우 총괄
modules/mail_process/mail_processor_orchestrator.py
"""

import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from infra.core.logger import get_logger
from infra.core.database import get_database_manager
from .services.filtering_service import FilteringService
from .services.queue_service import MailQueueService
from .services.processing_service import ProcessingService
from .services.db_service import MailDatabaseService
from .services.persistence_service import PersistenceService
from .mail_processor_schema import (
    MailProcessingResult,
    ProcessedMailData,
    GraphMailItem,
    ProcessingStatus,
    SenderType,
    MailType,
    DecisionStatus,
    MailHistoryData,
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
        self.persistence_service = PersistenceService()

        # 백그라운드 태스크
        self._background_task: Optional[asyncio.Task] = None
        self._should_stop = False

        self.logger.info("오케스트레이터 초기화 완료")

    async def enqueue_mail_batch(
        self, account_id, mails: List[GraphMailItem]
    ) -> Dict[str, Any]:
        """
        외부에서 전달받은 메일 배치를 전처리하고 큐에 저장

        Args:
            account_id: 사용자 ID (문자열 또는 정수)
            mails: 메일 리스트 (GraphMailItem Pydantic 객체)

        Returns:
            큐 저장 결과
        """
        try:
            # account_id를 문자열로 변환
            account_id = str(account_id)

            self.logger.info(
                f"메일 배치 처리 시작 - account_id: {account_id}, 메일 수: {len(mails)}개"
            )

            enqueued = 0
            filtered = 0
            duplicates = 0
            errors = []

            for mail_item in mails:
                try:
                    # 외부에서 이미 GraphMailItem으로 변환된 상태로 전달받음
                    # mail_item은 GraphMailItem Pydantic 객체

                    # 1. 필터링 체크
                    filter_result = await self.filtering_service.filter_mail_single(
                        mail_item
                    )
                    if filter_result["filtered"]:
                        filtered += 1
                        self.logger.debug(
                            f"메일 필터링됨 - ID: {mail_item.id}, "
                            f"이유: {filter_result['reason']}"
                        )
                        continue

                    # 2. 중복 확인 후 DB 저장
                    saved, should_continue = self.db_service.check_and_save_graph_mail(
                        account_id, mail_item
                    )

                    if not should_continue:
                        # 중복이고 환경설정이 false인 경우만 스킵
                        duplicates += 1
                        self.logger.debug(
                            f"중복 메일로 큐 저장 스킵 - ID: {mail_item.id}"
                        )
                        continue

                    # 3. 텍스트 정제
                    cleaned_content = self.queue_service._clean_mail_content(mail_item)

                    # 4. 큐에 추가 (딕셔너리 형태로 변환하여 저장)
                    mail_dict = mail_item.model_dump()  # Pydantic → 딕셔너리 변환

                    # body content를 cleaned_content로 대체
                    if "body" in mail_dict and isinstance(mail_dict["body"], dict):
                        mail_dict["body"]["content"] = cleaned_content

                    # account_id는 Graph API 데이터에 없으므로 추가 (process_batch에서 필요)
                    mail_dict["_account_id"] = account_id  # _prefix로 구분

                    await self.queue_service.add_to_queue(mail_dict)
                    enqueued += 1

                except Exception as e:
                    # Pydantic 모델에서 ID 추출
                    mail_id = getattr(mail_item, "id", "unknown")
                    error_msg = f"메일 처리 실패 - ID: {mail_id}, error: {str(e)}"
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
        1. 큐에서 배치 가져오기 (기본 50개)
        2. IACS 파싱 수행
        3. OpenRouter로 배치 키워드 추출
        4. 이벤트 발행
        5. 재귀적으로 다음 배치 처리

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

            # 2. IACS 파싱 및 데이터 준비
            from modules.mail_process.utilities.iacs import IACSCodeParser

            iacs_parser = IACSCodeParser()

            enriched_items = []
            mail_info_list = []

            for mail in batch:
                iacs_info = iacs_parser.extract_all_patterns_from_mail(mail)
                mail_info = iacs_info.get("extracted_info", {})

                # OpenRouter 배치 처리를 위한 아이템 준비
                enriched_item = {
                    "subject": mail.get("subject", ""),
                    "content": (
                        mail.get("body", {}).get("content", "")
                        if isinstance(mail.get("body"), dict)
                        else ""
                    ),
                }
                enriched_items.append(enriched_item)

            # 3. OpenRouter 배치 키워드 추출
            from modules.keyword_extractor import KeywordExtractorOrchestrator
            from modules.keyword_extractor.keyword_extractor_schema import (
                BatchExtractionRequest,
            )

            keyword_orchestrator = KeywordExtractorOrchestrator()

            batch_request = BatchExtractionRequest(
                items=enriched_items, batch_size=50, concurrent_requests=1
            )

            async with keyword_orchestrator:
                batch_response = await keyword_orchestrator.extract_keywords_batch(
                    batch_request
                )

            # 4. 결과 처리 및 이벤트 발행
            results = []
            from infra.core.kafka_client import get_kafka_client

            kafka_client = get_kafka_client()

            for idx, (item, keywords) in enumerate(
                zip(enriched_items, batch_response.results)
            ):
                try:
                    # ProcessedMailData 생성
                    processed_data = ProcessedMailData(
                        mail_id=item["mail_id"],
                        account_id=item["account_id"],
                        subject=item["subject"],
                        body_preview=item["mail"].get("bodyPreview", ""),
                        sent_time=(
                            datetime.fromisoformat(
                                item["sent_time"].replace("Z", "+00:00")
                            )
                            if item.get("sent_time")
                            else datetime.now()
                        ),
                        sender_address=item["sender_address"],
                        sender_name=item["sender_name"],
                        sender_type=(
                            SenderType(item["iacs_info"].get("sender_type"))
                            if item["iacs_info"].get("sender_type")
                            else None
                        ),
                        sender_organization=item["iacs_info"].get(
                            "sender_organization"
                        ),
                        keywords=keywords,
                        processing_status=(
                            ProcessingStatus.SUCCESS
                            if keywords
                            else ProcessingStatus.FAILED
                        ),
                        # IACS 정보
                        agenda_code=item["iacs_info"]
                        .get("extracted_info", {})
                        .get("agenda_code"),
                        agenda_base=item["iacs_info"]
                        .get("extracted_info", {})
                        .get("agenda_base"),
                        agenda_version=item["iacs_info"]
                        .get("extracted_info", {})
                        .get("agenda_version"),
                        agenda_panel=item["iacs_info"]
                        .get("extracted_info", {})
                        .get("agenda_panel"),
                        response_org=item["iacs_info"].get("response_org"),
                        response_version=item["iacs_info"].get("response_version"),
                        clean_content=item["content"],
                        mail_type=MailType.OTHER,
                        decision_status=DecisionStatus.CREATED,
                        urgency=item["iacs_info"].get("urgency", "NORMAL"),
                        is_reply=item["iacs_info"].get("is_reply", False),
                        is_forward=item["iacs_info"].get("is_forward", False),
                    )

                    # DB 저장 및 다음 단계 진행 여부 결정
                    saved, should_continue = (
                        self.persistence_service.check_and_save_mail(processed_data)
                    )

                    if not should_continue:
                        # 중복이고 환경설정이 false인 경우 - 이벤트 발행 스킵
                        self.logger.debug(
                            f"중복 메일로 이벤트 발행 스킵 - ID: {item['mail_id']}"
                        )
                        continue

                    # 이벤트 발행
                    event_data = {
                        "event_type": "email_type",
                        "event_id": str(uuid.uuid4()),
                        "account_id": item["account_id"],
                        "occurred_at": datetime.now().isoformat(),
                        "mail_id": item["mail_id"],
                        "original_mail": item["mail"],
                        "iacs_info": item["iacs_info"],
                        "keywords": keywords,
                        "processed_at": datetime.now().isoformat(),
                    }

                    kafka_client.produce_event(
                        topic="email.processed",
                        event_data=event_data,
                        key=item["account_id"],
                    )

                    results.append(
                        MailProcessingResult(
                            success=True,
                            mail_id=item["mail_id"],
                            account_id=item["account_id"],
                            processed_data=processed_data,
                            keywords=keywords,
                        )
                    )

                except Exception as e:
                    self.logger.error(
                        f"메일 처리 실패 - ID: {item.get('mail_id')}: {str(e)}"
                    )
                    results.append(
                        MailProcessingResult(
                            success=False,
                            mail_id=item.get("mail_id", "unknown"),
                            account_id=item["account_id"],
                            error=str(e),
                        )
                    )

            # 5. 처리 결과 통계
            success_count = sum(1 for r in results if r.success)
            self.logger.info(
                f"배치 처리 완료 - "
                f"전체: {len(results)}, "
                f"성공: {success_count}, "
                f"실패: {len(results) - success_count}"
            )

            # 6. 큐에 데이터가 남아있는지 확인하고 재귀 처리
            queue_status = await self.queue_service.get_queue_status()
            if not queue_status["is_empty"]:
                self.logger.info(
                    f"큐에 {queue_status['queue_size']}개 아이템 남음. 다음 배치 처리 시작"
                )
                # 비동기 태스크로 다음 배치 처리 (블로킹 방지)
                asyncio.create_task(self.process_batch())

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
