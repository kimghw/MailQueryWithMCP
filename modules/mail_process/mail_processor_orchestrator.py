"""메일 처리 오케스트레이터 - 통합 IACS Parser 사용

modules/mail_process/mail_processor_orchestrator.py
"""

import os
import json
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from infra.core.logger import get_logger
from infra.core.config import get_config

from .mail_processor_schema import (
    ProcessingStatus,
    MailProcessingResult,
    SenderType,
    MailType,
    DecisionStatus,
)
from .services.filtering_service import FilteringService
from .services.persistence_service import PersistenceService
from .services.processing_service import ProcessingService
from .services.statistics_service import StatisticsService
from .utilities.iacs_code_parser import IACSCodeParser, ParsedCode

logger = get_logger(__name__)


class MailProcessorOrchestrator:
    """메일 처리 흐름 관리 오케스트레이터 - 2단계 추출 (IACS + OpenRouter)"""

    def __init__(
        self,
        filtering_service: Optional[FilteringService] = None,
        processing_service: Optional[ProcessingService] = None,
        persistence_service: Optional[PersistenceService] = None,
        statistics_service: Optional[StatisticsService] = None,
    ):
        """
        의존성 주입을 지원하는 초기화

        Args:
            filtering_service: 필터링 서비스 (테스트 시 모킹 가능)
            processing_service: 처리 서비스 (테스트 시 모킹 가능)
            persistence_service: 저장 서비스 (테스트 시 모킹 가능)
            statistics_service: 통계 서비스 (테스트 시 모킹 가능)
        """
        self.logger = get_logger(__name__)
        self.config = get_config()

        # 환경변수 검증
        self._validate_configuration()

        # 서비스 초기화 (의존성 주입 지원)
        self.filtering_service = filtering_service or FilteringService()
        self.processing_service = processing_service or ProcessingService()
        self.persistence_service = persistence_service or PersistenceService()
        self.statistics_service = statistics_service or StatisticsService()

        # 통합 IACS 파서 초기화
        self.iacs_parser = IACSCodeParser()

        # 설정값 로드
        self.max_mails_per_account = int(os.getenv("MAX_MAILS_PER_ACCOUNT", "200"))
        self.enable_dashboard_events = (
            os.getenv("ENABLE_DASHBOARD_EVENTS", "true").lower() == "true"
        )

        self.logger.info(
            f"메일 처리 오케스트레이터 초기화 완료 "
            f"(통합 IACS 파서, 최대 처리: {self.max_mails_per_account})"
        )

    def _validate_configuration(self):
        """환경설정 검증"""
        required_configs = [
            ("ENABLE_MAIL_FILTERING", "true"),
            ("ENABLE_MAIL_DUPLICATE_CHECK", "true"),
            ("ENABLE_BATCH_KEYWORD_EXTRACTION", "true"),
            ("ENABLE_MAIL_HISTORY", "true"),
            ("MAX_KEYWORDS_PER_MAIL", "5"),
            ("MIN_MAIL_CONTENT_LENGTH", "10"),
        ]

        for config_name, default_value in required_configs:
            value = os.getenv(config_name)
            if value is None:
                self.logger.warning(
                    f"환경변수 누락: {config_name}, 기본값 사용: {default_value}"
                )
                os.environ[config_name] = default_value

    async def __aenter__(self):
        """컨텍스트 매니저 진입"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료 - 자동 리소스 정리"""
        await self.close()

    async def process_mails(
        self, account_id: str, mails: List[Dict], publish_batch_event: bool = True
    ) -> MailProcessingResult:
        """
        메일 처리 메인 플로우 (중복 체크 우선 처리)

        Args:
            account_id: 계정 ID
            mails: 메일 리스트
            publish_batch_event: 배치 이벤트 발행 여부

        Returns:
            처리 결과 (MailProcessingResult)
        """
        start_time = datetime.now()
        self.logger.info(f"메일 처리 시작: account_id={account_id}, count={len(mails)}")

        # 처리 제한
        if len(mails) > self.max_mails_per_account:
            self.logger.warning(
                f"처리 제한 적용: {len(mails)} -> {self.max_mails_per_account}"
            )
            mails = mails[: self.max_mails_per_account]

        try:
            # Phase 1: 초기화 및 필터링
            filtered_mails = await self._phase1_filter(account_id, mails)

            # Phase 2: 중복 체크 (간단한 체크만)
            new_mails, duplicate_mails = await self._phase2_duplicate_check(
                account_id, filtered_mails
            )

            # Phase 3: 신규 메일만 정제 및 키워드 추출 (2단계 추출)
            processed_mails = await self._phase3_process_new_mails(
                account_id, new_mails
            )

            # Phase 4: 저장 및 이벤트 발행 (2가지 결과 병합)
            saved_results = await self._phase4_persist(account_id, processed_mails)

            # Phase 5: 통계 기록
            execution_time_ms = int(
                (datetime.now() - start_time).total_seconds() * 1000
            )

            result = await self._phase5_create_result(
                account_id=account_id,
                total_count=len(mails),
                filtered_count=len(filtered_mails),
                new_count=len(new_mails),
                duplicate_count=len(duplicate_mails),
                saved_results=saved_results,
                execution_time_ms=execution_time_ms,
                publish_batch_event=publish_batch_event,
                processed_mails=processed_mails,
            )

            self.logger.info(
                f"메일 처리 완료: account={account_id}, "
                f"성공률={result.success_rate}%, "
                f"중복률={result.duplication_rate}%, "
                f"실행시간={result.execution_time_ms}ms"
            )

            return result

        except Exception as e:
            self.logger.error(f"메일 처리 중 예외 발생: {str(e)}", exc_info=True)

            # 부분 실패 결과 반환
            execution_time_ms = int(
                (datetime.now() - start_time).total_seconds() * 1000
            )
            return MailProcessingResult(
                account_id=account_id,
                total_fetched=len(mails),
                filtered_count=0,
                new_count=0,
                duplicate_count=0,
                processed_count=0,
                saved_count=0,
                failed_count=len(mails),
                skipped_count=0,
                events_published=0,
                last_sync_time=datetime.now(),
                execution_time_ms=execution_time_ms,
                success_rate=0.0,
                duplication_rate=0.0,
                processing_efficiency=0.0,
                errors=[str(e)],
                warnings=[],
            )
        finally:
            # 리소스 정리는 항상 수행
            await self._cleanup_resources()

    async def _phase1_filter(self, account_id: str, mails: List[Dict]) -> List[Dict]:
        """Phase 1: 초기화 및 필터링"""
        self.logger.debug(f"Phase 1 시작: 필터링 ({len(mails)}개)")
        return await self.filtering_service.filter_mails(mails)

    async def _phase2_duplicate_check(
        self, account_id: str, mails: List[Dict]
    ) -> Tuple[List[Dict], List[Dict]]:
        """Phase 2: 중복 체크 (처리 전)"""
        self.logger.debug(f"Phase 2 시작: 중복 체크 ({len(mails)}개)")

        # 중복 체크가 비활성화된 경우 모든 메일을 신규로 처리
        if not self.persistence_service.duplicate_check_enabled:
            self.logger.debug("중복 체크 비활성화 - 모든 메일을 신규로 처리")
            return mails, []

        # 배치 중복 체크 수행
        mail_ids = [mail.get("id", "") for mail in mails if mail.get("id")]
        existing_ids = self.persistence_service.get_existing_mail_ids(mail_ids)
        existing_ids_set = set(existing_ids)

        new_mails = []
        duplicate_mails = []

        for mail in mails:
            mail_id = mail.get("id", "")
            if mail_id and mail_id in existing_ids_set:
                duplicate_mails.append(mail)
                self.logger.debug(f"중복 메일 발견: {mail_id}")
            else:
                new_mails.append(mail)

        self.logger.info(
            f"Phase 2 완료: 전체 {len(mails)}개 중 "
            f"신규 {len(new_mails)}개, 중복 {len(duplicate_mails)}개"
        )
        return new_mails, duplicate_mails

    async def _phase3_process_new_mails(
        self, account_id: str, mails: List[Dict]
    ) -> List[Dict]:
        """
        Phase 3: 신규 메일 처리 (IACS + OpenRouter)
        """
        if not mails:
            self.logger.debug("Phase 3 스킵: 처리할 신규 메일이 없습니다.")
            return []

        self.logger.debug(f"Phase 3 시작: 신규 메일 처리 ({len(mails)}개)")

        # Step 1: IACS 코드 및 메타정보 추출 (제목과 본문에서, 동기)
        self._extract_iacs_patterns(mails)

        # Step 2: OpenRouter 처리 (비동기, 배치)
        try:
            processed_mails = await self.processing_service.process_mails(mails)
        except Exception as e:
            self.logger.error(f"OpenRouter 처리 중 오류: {str(e)}", exc_info=True)
            # OpenRouter 실패 시에도 IACS 파싱 결과는 보존
            processed_mails = mails

        # 처리 통계 로깅
        self._log_processing_statistics(processed_mails)

        return processed_mails

    def _extract_iacs_patterns(self, mails: List[Dict]):
        """각 메일에서 IACS 코드 및 메타정보 추출 (발신자 정보 포함)"""
        for mail in mails:
            try:
                subject = mail.get("subject", "")

                # 정제된 내용이 있으면 사용, 없으면 원본 사용
                if "_processed" in mail:
                    body = mail["_processed"].get("clean_content", "")
                else:
                    body = mail.get("body", {}).get("content", "")

                if not subject:
                    continue

                # 통합 IACS 파서로 모든 패턴 추출 (메일 객체 전달)
                patterns = self.iacs_parser.extract_all_patterns(subject, body, mail)

                if patterns:
                    # 파싱 결과를 메일에 저장
                    mail["_iacs_parsed"] = patterns

                    self.logger.debug(
                        f"IACS 패턴 추출: {mail.get('id')} - "
                        f"코드: {patterns.get('extracted_info', {}).get('full_code', 'N/A')}, "
                        f"긴급도: {patterns.get('urgency', 'NORMAL')}, "
                        f"회신: {patterns.get('is_reply', False)}, "
                        f"발신자 타입: {patterns.get('sender_type', 'N/A')}, "
                        f"발신자 조직: {patterns.get('sender_organization', 'N/A')}, "
                        f"아젠다 조직: {patterns.get('agenda_organization', 'N/A')}, "
                        f"아젠다 라운드: {patterns.get('agenda_organization_round', 'N/A')}"
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
            "with_agenda_org": sum(
                1
                for m in processed_mails
                if m.get("_iacs_parsed", {}).get("agenda_organization")
            ),
        }

        self.logger.info(f"Phase 3 처리 통계: {json.dumps(stats, ensure_ascii=False)}")

    async def _phase4_persist(self, account_id: str, mails: List[Dict]) -> Dict:
        """
        Phase 4: 저장 및 이벤트 발행 (2가지 추출 결과 병합)
        """
        if not mails:
            self.logger.debug("Phase 4 스킵: 저장할 메일이 없습니다.")
            return {"saved": 0, "duplicates": 0, "failed": 0, "events_published": 0}

        self.logger.debug(f"Phase 4 시작: 저장 ({len(mails)}개)")

        # 이벤트 발행용 메일 데이터 준비
        mails_for_events = []

        for mail in mails:
            # 2가지 추출 결과 병합
            merged_data = self._merge_extraction_results(mail)

            # 병합된 데이터를 메일에 추가
            for key, value in merged_data.items():
                mail[key] = value

            # _processed 정보도 업데이트 (기존 로직 호환)
            if "_processed" in mail:
                mail["_processed"].update(merged_data)

            # 이벤트용 메일 복사본 생성
            event_mail = self._prepare_mail_for_event(mail)
            mails_for_events.append(event_mail)

        # 수정된 persist_mails 호출 (이벤트용 데이터 전달)
        return await self.persistence_service.persist_mails(
            account_id, mails, mails_for_events
        )

    def _merge_extraction_results(self, mail: Dict) -> Dict:
        """
        2가지 추출 결과를 지능적으로 병합
        우선순위: IACSCodeParser > OpenRouter
        """
        # 기본값 설정
        merged = {
            "mail_type": MailType.OTHER.value,
            "decision_status": DecisionStatus.CREATED.value,
            "has_deadline": False,
            "keywords": [],
            "summary": "",
            "processing_status": ProcessingStatus.SUCCESS.value,
            "urgency": "NORMAL",
            "is_reply": False,
            "is_forward": False,
        }

        # 1. IACS 파서 결과 병합
        if "_iacs_parsed" in mail:
            self._merge_iacs_results(merged, mail["_iacs_parsed"])

        # 2. OpenRouter 결과 병합
        if "_processed" in mail:
            self._merge_openrouter_results(merged, mail["_processed"])

        # 3. 타임스탬프 및 메타데이터 추가
        merged["extraction_metadata"] = {
            "iacs_parsed": "_iacs_parsed" in mail,
            "openrouter_parsed": "_processed" in mail,
            "extraction_timestamp": datetime.now().isoformat(),
            "orchestrator_version": "2.0",
        }

        # 4. 대시보드 이벤트용 send_time 형식 보정
        if merged.get("sent_time"):
            merged["send_time"] = self._format_datetime(merged["sent_time"])

        return merged

    def _merge_iacs_results(self, merged: Dict, iacs_data: Dict):
        """IACS 파서 결과 병합"""
        # IACS 코드 정보
        if "extracted_info" in iacs_data:
            iacs_info = iacs_data["extracted_info"]

            # 아젠다 번호와 버전을 결합한 agenda_code 생성
            if iacs_info.get("base_agenda_no"):
                base_no = iacs_info["base_agenda_no"]
                agenda_version = iacs_info.get("agenda_version", "")
                # agenda_code = base_agenda_no + agenda_version
                merged["agenda_code"] = (
                    f"{base_no}{agenda_version}" if agenda_version else base_no
                )
                # 원본 agenda_no도 유지 (호환성)
                merged["agenda_no"] = base_no

            # 아젠다 상세 정보
            merged["agenda_info"] = {
                "full_pattern": iacs_info.get("full_code"),
                "panel_name": iacs_info.get("panel"),
                "year": iacs_info.get("year"),
                "round_no": iacs_info.get("number"),
                "agenda_version": iacs_info.get("agenda_version"),
                "document_type": iacs_info.get("document_type"),
                "is_response": iacs_info.get("is_response", False),
                "parsing_method": iacs_info.get("parsing_method"),
            }

            # 응답인 경우 추가 정보
            if iacs_info.get("is_response") and iacs_info.get("organization"):
                merged["response_version"] = iacs_info.get("response_version")

        # agenda_organization 처리
        if iacs_data.get("agenda_organization"):
            merged["agenda_organization"] = iacs_data["agenda_organization"]

        # agenda_organization_round는 제거 (요청사항에 따라)

        # 메타 정보
        if iacs_data.get("urgency"):
            merged["urgency"] = iacs_data["urgency"]
        if iacs_data.get("is_reply") is not None:
            merged["is_reply"] = iacs_data["is_reply"]
            if iacs_data.get("reply_depth"):
                merged["reply_depth"] = iacs_data["reply_depth"]
        if iacs_data.get("is_forward") is not None:
            merged["is_forward"] = iacs_data["is_forward"]
        if iacs_data.get("additional_agenda_references"):
            merged["additional_agenda_references"] = iacs_data[
                "additional_agenda_references"
            ]

        # 발신자 정보 (IACS 파서에서 추출된 것 사용)
        if iacs_data.get("sender_address"):
            merged["sender_address"] = iacs_data["sender_address"]
        if iacs_data.get("sender_name"):
            merged["sender_name"] = iacs_data["sender_name"]
        if iacs_data.get("sender_type"):
            merged["sender_type"] = iacs_data["sender_type"]
        if iacs_data.get("sender_organization"):
            merged["sender_organization"] = iacs_data["sender_organization"]

        # 시간 정보 (IACS 파서 우선)
        if iacs_data.get("sent_time"):
            merged["sent_time"] = iacs_data["sent_time"]

        # 정제된 내용 (IACS 파서 우선)
        if iacs_data.get("clean_content"):
            merged["clean_content"] = iacs_data["clean_content"]

    def _merge_openrouter_results(self, merged: Dict, processed_info: Dict):
        """OpenRouter 결과 병합"""
        # 항상 OpenRouter에서 가져오는 정보
        merged["keywords"] = processed_info.get("keywords", [])
        merged["summary"] = processed_info.get("summary", "")

        # IACS 파서에서 못 찾은 정보만 보충
        if not merged.get("clean_content"):
            merged["clean_content"] = processed_info.get("clean_content", "")
        if not merged.get("sent_time"):
            merged["sent_time"] = processed_info.get("sent_time")
        if not merged.get("sender_address"):
            merged["sender_address"] = processed_info.get("sender_address", "")
        if not merged.get("sender_name"):
            merged["sender_name"] = processed_info.get("sender_name", "")

        # OpenRouter의 의미 분석 결과
        for key in [
            "mail_type",
            "decision_status",
            "has_deadline",
            "deadline",
        ]:
            if key in processed_info:
                merged[key] = processed_info[key]

        # sender_type은 IACS가 우선, 없으면 OpenRouter
        if not merged.get("sender_type") and processed_info.get("sender_type"):
            merged["sender_type"] = processed_info["sender_type"]

        # sender_organization도 IACS가 우선, 없으면 OpenRouter
        if not merged.get("sender_organization") and processed_info.get(
            "sender_organization"
        ):
            merged["sender_organization"] = processed_info["sender_organization"]

        # 다른 파서에서 못 찾은 정보 보충
        if not merged.get("agenda_code") and processed_info.get("agenda_no"):
            merged["agenda_code"] = processed_info["agenda_no"]
            merged["agenda_no"] = processed_info["agenda_no"]

        # OpenRouter에서 agenda_organization 관련 정보가 있으면 보충
        if not merged.get("agenda_organization") and processed_info.get(
            "agenda_organization"
        ):
            merged["agenda_organization"] = processed_info["agenda_organization"]

    def _format_datetime(self, dt: Any) -> str:
        """datetime 객체를 문자열로 포맷"""
        if hasattr(dt, "isoformat"):
            return dt.isoformat()
        else:
            return str(dt)

    def _prepare_mail_for_event(self, mail: Dict) -> Dict:
        """이벤트 발행용 메일 데이터 준비 (수정된 필드 매핑 적용)"""
        event_mail = mail.copy()

        # sender_organization과 sender_type은 그대로 유지
        # (event_service에서 처리하지 않고 그대로 전달)

        # agenda 정보 재구성
        if "_iacs_parsed" in mail and "extracted_info" in mail["_iacs_parsed"]:
            iacs_info = mail["_iacs_parsed"]["extracted_info"]

            # agenda 객체 생성
            event_mail["agenda"] = {
                "fullCode": iacs_info.get("full_code"),
                "documentType": iacs_info.get("document_type"),
                "panel": iacs_info.get("panel"),
                "year": iacs_info.get("year"),
                "number": iacs_info.get("number"),
                "version": iacs_info.get("agenda_version"),
                "organization": iacs_info.get("organization"),
                "responseVersion": iacs_info.get("response_version"),
                # orgRound 제거 (요청사항에 따라)
            }

            # agenda_org는 별도 필드로
            if "agenda_organization" in mail:
                event_mail["agenda_org"] = mail["agenda_organization"]

        # agenda_code 추가 (agenda_no 대체)
        if "agenda_code" in mail:
            event_mail["agenda_code"] = mail["agenda_code"]

        # _processed 정보는 제거 (이벤트에 불필요)
        if "_processed" in event_mail:
            del event_mail["_processed"]

        # 내부 처리 데이터 제거
        fields_to_remove = [
            "_iacs_parsed",
            "keywords",
            "clean_content",
            "sent_time",
            "processing_status",
            "sender_address",
            "sender_name",
            "extraction_metadata",
            "agenda_info",
            "agenda_organization",
            "agenda_organization_round",
            "response_version",
            "agenda_no",  # agenda_code로 대체되므로 제거
        ]

        for field in fields_to_remove:
            if field in event_mail:
                del event_mail[field]

        return event_mail

    async def _phase5_create_result(
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
        """Phase 5: 결과 생성 및 통계 기록"""
        self.logger.debug("Phase 5 시작: 결과 생성")

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
        if self.statistics_service:
            await self.statistics_service.record_statistics(
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

        return result

    async def _cleanup_resources(self):
        """리소스 정리"""
        try:
            if self.processing_service:
                await self.processing_service.close()
        except Exception as e:
            self.logger.error(f"리소스 정리 중 오류: {str(e)}")

    async def close(self):
        """명시적 리소스 정리"""
        await self._cleanup_resources()

    def set_chair_emails(self, emails: List[str]):
        """Chair 이메일 주소 설정"""
        self.iacs_parser.set_chair_emails(emails)
        self.logger.info(f"Chair 이메일 {len(emails)}개 설정됨")

    def set_member_emails(self, organization: str, emails: List[str]):
        """특정 조직의 멤버 이메일 주소 설정"""
        self.iacs_parser.set_member_emails(organization, emails)
        self.logger.info(f"{organization} 멤버 이메일 {len(emails)}개 설정됨")

    def get_processing_statistics(self) -> Dict[str, Any]:
        """현재 처리 통계 반환"""
        return {
            "filtering_stats": self.filtering_service.get_filter_stats(),
            "duplicate_check_enabled": self.persistence_service.get_duplicate_check_status(),
            "max_mails_per_account": self.max_mails_per_account,
            "dashboard_events_enabled": self.enable_dashboard_events,
        }
