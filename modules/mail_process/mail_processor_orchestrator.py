"""메일 처리 오케스트레이터 - 통합 IACS Parser 사용

modules/mail_process/mail_processor_orchestrator.py
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from infra.core.logger import get_logger

from .mail_processor_schema import ProcessingStatus
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

        # 서비스 초기화 (의존성 주입 지원)
        self.filtering_service = filtering_service or FilteringService()
        self.processing_service = processing_service or ProcessingService()
        self.persistence_service = persistence_service or PersistenceService()
        self.statistics_service = statistics_service or StatisticsService()

        # 통합 IACS 파서 초기화
        self.iacs_parser = IACSCodeParser()

        self.logger.info("메일 처리 오케스트레이터 초기화 완료 (통합 IACS 파서)")

    async def __aenter__(self):
        """컨텍스트 매니저 진입"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료 - 자동 리소스 정리"""
        await self.close()

    async def process_mails(
        self, account_id: str, mails: List[Dict], publish_batch_event: bool = True
    ) -> Dict[str, Any]:
        """
        메일 처리 메인 플로우 (중복 체크 우선 처리)

        Args:
            account_id: 계정 ID
            mails: 메일 리스트
            publish_batch_event: 배치 이벤트 발행 여부

        Returns:
            처리 통계
        """
        self.logger.info(f"메일 처리 시작: account_id={account_id}, count={len(mails)}")

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
            statistics = await self._phase5_statistics(
                account_id,
                len(mails),
                len(filtered_mails),
                len(new_mails),
                len(duplicate_mails),
                saved_results,
                publish_batch_event,
                processed_mails,
            )

            self.logger.info(f"메일 처리 완료: {statistics}")
            return statistics

        except Exception as e:
            self.logger.error(f"메일 처리 중 예외 발생: {str(e)}", exc_info=True)
            # 부분 실패 허용 - 현재까지 처리된 통계 반환
            return self.statistics_service.get_current_statistics()
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
            f"Phase 2 완료: 전체 {len(mails)}개 중 신규 {len(new_mails)}개, 중복 {len(duplicate_mails)}개"
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
        processed_mails = await self.processing_service.process_mails(mails)

        # 처리 통계 로깅
        total_keywords = 0
        iacs_parsed_count = 0

        for mail in processed_mails:
            if "_processed" in mail and "keywords" in mail["_processed"]:
                keywords = mail["_processed"]["keywords"]
                total_keywords += len(keywords)
                if keywords:
                    self.logger.debug(
                        f"메일 {mail.get('id', 'unknown')}: 키워드 {len(keywords)}개 - {keywords}"
                    )

            if "_iacs_parsed" in mail:
                iacs_parsed_count += 1

        self.logger.info(
            f"Phase 3 완료: {len(processed_mails)}개 메일 처리, "
            f"IACS 파싱={iacs_parsed_count}, "
            f"총 키워드={total_keywords}개"
        )

        return processed_mails

    def _extract_iacs_patterns(self, mails: List[Dict]):
        """각 메일에서 IACS 코드 및 메타정보 추출 (발신자 정보 포함)"""
        for mail in mails:
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
                    f"발신자 타입: {patterns.get('sender_type', 'N/A')}"
                )

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
            event_mail = mail.copy()

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
            ]
            for field in fields_to_remove:
                if field in event_mail:
                    del event_mail[field]

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
        merged = {}

        # 1. IACS 파서 결과 (최우선)
        if "_iacs_parsed" in mail:
            iacs_data = mail["_iacs_parsed"]

            # IACS 코드 정보가 있는 경우
            if "extracted_info" in iacs_data:
                iacs_info = iacs_data["extracted_info"]

                # 아젠다 번호
                if iacs_info.get("base_agenda_no"):
                    merged["agenda_no"] = iacs_info["base_agenda_no"]

                # 아젠다 상세 정보
                merged["agenda_info"] = {
                    "full_pattern": iacs_info.get("full_code"),
                    "panel_name": iacs_info.get("panel"),
                    "year": iacs_info.get("year"),
                    "round_no": iacs_info.get("number"),
                    "agenda_version": iacs_info.get("agenda_version"),
                    "document_type": iacs_info.get("document_type"),
                    "is_response": iacs_info.get("is_response", False),
                }

                # 응답인 경우 추가 정보
                if iacs_info.get("is_response") and iacs_info.get("organization"):
                    merged["sender_organization"] = iacs_info["organization"]
                    merged["response_version"] = iacs_info.get("response_version")
                    # agenda_response_id 추가 (대시보드에서 활용)
                    merged["agenda_response_id"] = (
                        f"{iacs_info['organization']}{iacs_info.get('response_version', '')}"
                    )

            # 메타 정보 (IACS 파서에서 추출)
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

            # 발신자 정보 (IACS 파서 우선)
            if iacs_data.get("sender_address"):
                merged["sender_address"] = iacs_data["sender_address"]
            if iacs_data.get("sender_name"):
                merged["sender_name"] = iacs_data["sender_name"]
            if iacs_data.get("sender_type"):
                merged["sender_type"] = iacs_data["sender_type"]

            # 시간 정보 (IACS 파서 우선)
            if iacs_data.get("sent_time"):
                merged["sent_time"] = iacs_data["sent_time"]

            # 정제된 내용 (IACS 파서 우선)
            if iacs_data.get("clean_content"):
                merged["clean_content"] = iacs_data["clean_content"]

        # 2. OpenRouter 결과 (의미 분석)
        if "_processed" in mail:
            processed_info = mail["_processed"]

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
            if not merged.get("agenda_no") and processed_info.get("agenda_no"):
                merged["agenda_no"] = processed_info["agenda_no"]

        # 3. 기본값 설정
        merged.setdefault("mail_type", "OTHER")
        merged.setdefault("decision_status", "created")
        merged.setdefault("has_deadline", False)
        merged.setdefault("keywords", [])
        merged.setdefault("summary", "")
        merged.setdefault("processing_status", "SUCCESS")
        merged.setdefault("urgency", "NORMAL")

        # 4. send_time 형식 보정 (대시보드 이벤트용)
        if merged.get("sent_time"):
            if hasattr(merged["sent_time"], "isoformat"):
                merged["send_time"] = merged["sent_time"].isoformat()
            else:
                merged["send_time"] = str(merged["sent_time"])

        # 5. 추출 메타데이터
        merged["extraction_metadata"] = {
            "iacs_parsed": "_iacs_parsed" in mail,
            "openrouter_parsed": "_processed" in mail,
            "extraction_timestamp": datetime.now().isoformat(),
        }

        return merged

    async def _phase5_statistics(
        self,
        account_id: str,
        total_count: int,
        filtered_count: int,
        new_count: int,
        duplicate_count: int,
        saved_results: Dict,
        publish_batch_event: bool,
        processed_mails: List[Dict] = None,
    ) -> Dict:
        """Phase 5: 통계 기록 (중복 정보 포함)"""
        self.logger.debug("Phase 5 시작: 통계")

        # 통계 서비스에 전달할 파라미터 구성
        statistics_params = {
            "account_id": account_id,
            "total_count": total_count,
            "filtered_count": filtered_count,
            "new_count": new_count,
            "duplicate_count": duplicate_count,
            "saved_results": saved_results,
            "publish_batch_event": publish_batch_event,
            "processed_mails": processed_mails,
        }

        return await self.statistics_service.record_statistics(**statistics_params)

    async def _cleanup_resources(self):
        """리소스 정리"""
        try:
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
