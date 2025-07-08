"""
메일 처리 단계별 프로세서
modules/mail_process/services/phase_processor.py
"""

import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Protocol

from infra.core.logger import get_logger
from ..mail_processor_schema import MailProcessingResult
from .data_merger import DataMerger


class OrchestratorInterface(Protocol):
    """오케스트레이터 인터페이스 - 순환 참조 방지"""

    @property
    def filtering_service(self): ...

    @property
    def persistence_service(self): ...

    @property
    def processing_service(self): ...

    @property
    def statistics_service(self): ...

    @property
    def iacs_parser(self): ...


class PhaseProcessor:
    """메일 처리 단계별 프로세서"""

    def __init__(self, orchestrator: OrchestratorInterface):
        """
        Args:
            orchestrator: 메인 오케스트레이터 인터페이스
        """
        self.orchestrator = orchestrator
        self.logger = get_logger(__name__)
        self.data_merger = DataMerger()

    async def filter_mails(self, mails: List[Dict]) -> List[Dict]:
        """Phase 1: 필터링"""
        self.logger.debug(f"Phase 1 시작: 필터링 ({len(mails)}개)")
        return await self.orchestrator.filtering_service.filter_mails(mails)

    async def check_duplicates(
        self, account_id: str, mails: List[Dict]
    ) -> Tuple[List[Dict], List[Dict]]:
        """Phase 2: 중복 체크"""
        self.logger.debug(f"Phase 2 시작: 중복 체크 ({len(mails)}개)")

        if not self.orchestrator.persistence_service.duplicate_check_enabled:
            self.logger.debug("중복 체크 비활성화 - 모든 메일을 신규로 처리")
            return mails, []

        # 배치 중복 체크
        mail_ids = [mail.get("id", "") for mail in mails if mail.get("id")]
        existing_ids = self.orchestrator.persistence_service.get_existing_mail_ids(
            mail_ids
        )
        existing_ids_set = set(existing_ids)

        new_mails = []
        duplicate_mails = []

        for mail in mails:
            mail_id = mail.get("id", "")
            if mail_id and mail_id in existing_ids_set:
                duplicate_mails.append(mail)
            else:
                new_mails.append(mail)

        self.logger.info(
            f"Phase 2 완료: 전체 {len(mails)}개 중 "
            f"신규 {len(new_mails)}개, 중복 {len(duplicate_mails)}개"
        )
        return new_mails, duplicate_mails

    async def enrich_mails(self, account_id: str, mails: List[Dict]) -> List[Dict]:
        """Phase 3: 데이터 추출 (IACS + OpenRouter)"""
        if not mails:
            self.logger.debug("Phase 3 스킵: 처리할 신규 메일이 없습니다.")
            return []

        self.logger.debug(f"Phase 3 시작: 신규 메일 처리 ({len(mails)}개)")

        # Step 1: IACS 코드 및 메타정보 추출 (동기)
        self._extract_iacs_patterns(mails)

        # Step 2: OpenRouter 처리 (비동기, 배치)
        try:
            processed_mails = await self.orchestrator.processing_service.process_mails(
                mails
            )
        except Exception as e:
            self.logger.error(f"OpenRouter 처리 중 오류: {str(e)}", exc_info=True)
            processed_mails = mails

        # 처리 통계 로깅
        self._log_processing_statistics(processed_mails)

        return processed_mails

    async def persist_and_publish(self, account_id: str, mails: List[Dict]) -> Dict:
        """Phase 4: 저장 및 이벤트 발행"""
        if not mails:
            self.logger.debug("Phase 4 스킵: 저장할 메일이 없습니다.")
            return {"saved": 0, "duplicates": 0, "failed": 0, "events_published": 0}

        self.logger.debug(f"Phase 4 시작: 저장 ({len(mails)}개)")

        # 이벤트 발행용 메일 데이터 준비
        mails_for_events = []

        for mail in mails:
            # 2가지 추출 결과 병합
            merged_data = self.data_merger.merge_extractions(
                mail.get("_iacs_parsed"), mail.get("_processed")
            )

            # 병합된 데이터를 메일에 추가
            for key, value in merged_data.items():
                mail[key] = value

            # _processed 정보도 업데이트
            if "_processed" in mail:
                mail["_processed"].update(merged_data)

            # 원본 메일 정보 가져오기
            raw_mail = {
                "from": mail.get("from"),
                "body": mail.get("body", {}),
            }

            # 이벤트용 메일 생성 (필요한 필드만 선택)
            event_mail = self.data_merger.to_event_format(merged_data, mail, raw_mail)
            mails_for_events.append(event_mail)

        # 저장 및 이벤트 발행
        return await self.orchestrator.persistence_service.persist_mails(
            account_id, mails, mails_for_events
        )

    def _extract_iacs_patterns(self, mails: List[Dict]):
        """각 메일에서 IACS 코드 및 메타정보 추출"""
        for mail in mails:
            try:
                subject = mail.get("subject", "")
                body = mail.get("_processed", {}).get("clean_content", "") or mail.get(
                    "body", {}
                ).get("content", "")

                if not subject:
                    continue

                # 통합 IACS 파서로 모든 패턴 추출
                patterns = self.orchestrator.iacs_parser.extract_all_patterns(
                    subject, body, mail
                )

                if patterns:
                    mail["_iacs_parsed"] = patterns

                    self.logger.debug(
                        f"IACS 패턴 추출: {mail.get('id')} - "
                        f"코드: {patterns.get('extracted_info', {}).get('full_code', 'N/A')}, "
                        f"긴급도: {patterns.get('urgency', 'NORMAL')}, "
                        f"회신: {patterns.get('is_reply', False)}, "
                        f"발신자 타입: {patterns.get('sender_type', 'N/A')}, "
                        f"발신자 조직: {patterns.get('sender_organization', 'N/A')}"
                    )
            except Exception as e:
                self.logger.error(
                    f"IACS 패턴 추출 중 오류 - 메일 ID: {mail.get('id')}, "
                    f"오류: {str(e)}"
                )

    def _log_processing_statistics(self, processed_mails: List[Dict]):
        """처리 통계 구조화 로깅"""
        stats = {
            "total": len(processed_mails),
            "iacs_parsed": sum(1 for m in processed_mails if "_iacs_parsed" in m),
            "keywords_extracted": sum(
                1 for m in processed_mails if m.get("_processed", {}).get("keywords")
            ),
            "agenda_identified": sum(
                1
                for m in processed_mails
                if m.get("_iacs_parsed", {})
                .get("extracted_info", {})
                .get("base_agenda_no")
            ),
            "urgent": sum(
                1
                for m in processed_mails
                if m.get("_iacs_parsed", {}).get("urgency") == "HIGH"
            ),
            "responses": sum(
                1
                for m in processed_mails
                if m.get("_iacs_parsed", {})
                .get("extracted_info", {})
                .get("is_response")
            ),
        }

        self.logger.info(f"Phase 3 처리 통계: {json.dumps(stats, ensure_ascii=False)}")

    async def create_result(
        self,
        account_id: str,
        total_count: int,
        filtered_count: int,
        new_count: int,
        duplicate_count: int,
        saved_results: Dict,
        execution_time_ms: int,
        publish_batch_event: bool,
        processed_mails: List[Dict] = None,
    ) -> MailProcessingResult:
        """결과 생성"""
        # 성공률 계산
        success_rate = 0.0
        if new_count > 0:
            success_rate = (saved_results.get("saved", 0) / new_count) * 100

        # 중복률 계산
        duplication_rate = 0.0
        if filtered_count > 0:
            duplication_rate = (duplicate_count / filtered_count) * 100

        # 처리 효율성 계산
        processing_efficiency = 0.0
        if new_count + duplicate_count > 0:
            saved_processing = duplicate_count
            total_potential = new_count + duplicate_count
            processing_efficiency = (saved_processing / total_potential) * 100

        # 결과 객체 생성
        result = MailProcessingResult(
            account_id=account_id,
            total_fetched=total_count,
            filtered_count=filtered_count,
            new_count=new_count,
            duplicate_count=duplicate_count,
            processed_count=len(processed_mails) if processed_mails else 0,
            saved_count=saved_results.get("saved", 0),
            failed_count=saved_results.get("failed", 0),
            skipped_count=total_count - filtered_count,
            events_published=saved_results.get("events_published", 0),
            last_sync_time=datetime.now(),
            execution_time_ms=execution_time_ms,
            success_rate=round(success_rate, 2),
            duplication_rate=round(duplication_rate, 2),
            processing_efficiency=round(processing_efficiency, 2),
            errors=[],
            warnings=[],
        )

        # 통계 기록
        if self.orchestrator.statistics_service:
            import asyncio

            asyncio.create_task(
                self.orchestrator.statistics_service.record_statistics(
                    account_id=account_id,
                    total_count=total_count,
                    filtered_count=filtered_count,
                    new_count=new_count,
                    duplicate_count=duplicate_count,
                    saved_results=saved_results,
                    publish_batch_event=publish_batch_event,
                    processed_mails=processed_mails,
                    result=result,
                )
            )

        return result
