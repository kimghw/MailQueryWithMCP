"""
Email Dashboard Event Processor

이메일 관련 이벤트를 처리하여 데이터베이스에 저장합니다.
조건에 맞지 않는 이벤트도 별도 테이블에 저장합니다.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from infra.core import get_logger
from infra.core.exceptions import BusinessLogicError, ValidationError

from .repository import EmailDashboardRepository
from .schema import ORGANIZATIONS, EmailDashboardEvent


class EmailDashboardEventProcessor:
    """이메일 대시보드 이벤트 처리기"""

    def __init__(self):
        self.repository = EmailDashboardRepository()
        self.logger = get_logger(__name__)

    def email_dashboard_process_event(
        self, event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        이메일 대시보드 이벤트 처리

        Args:
            event_data: 이벤트 데이터

        Returns:
            처리 결과
        """
        try:
            # 이벤트 데이터 검증 및 파싱
            event = self._email_dashboard_validate_and_parse_event(event_data)

            # 추출 성공 여부 확인
            if not event.data.extraction_metadata.success:
                # 추출 실패한 이벤트도 저장
                self._save_unprocessed_event(
                    event, "extraction_failed", "키워드 추출 실패"
                )
                self.logger.warning(
                    f"추출 실패한 이벤트 저장: {event.event_id}, "
                    f"mail_id={event.data.mail_id}"
                )
                return {
                    "success": True,
                    "action": "saved_as_unprocessed",
                    "reason": "extraction_failed",
                    "message": "추출 실패한 이벤트를 미처리 테이블에 저장",
                }

            extraction_result = event.data.extraction_result

            # 대시보드 처리 가능 여부 확인
            is_worthy, reason = self._check_dashboard_worthiness(extraction_result)

            if not is_worthy:
                # 조건에 맞지 않는 이벤트 저장
                self._save_unprocessed_event(
                    event, reason, self._get_reason_description(reason)
                )
                self.logger.info(
                    f"미처리 이벤트 저장: event_id={event.event_id}, "
                    f"reason={reason}, org={extraction_result.sender_organization}"
                )
                return {
                    "success": True,
                    "action": "saved_as_unprocessed",
                    "reason": reason,
                    "message": f"조건 불충족 이벤트를 미처리 테이블에 저장: {reason}",
                }

            # 발신자 타입에 따른 처리 분기
            if extraction_result.sender_type == "CHAIR":
                return self._email_dashboard_process_chair_mail(event)
            elif extraction_result.sender_type == "MEMBER":
                return self._email_dashboard_process_member_mail(event)
            else:
                # 알 수 없는 발신자 타입도 저장
                self._save_unprocessed_event(
                    event,
                    "unknown_sender_type",
                    f"알 수 없는 발신자 타입: {extraction_result.sender_type}",
                )
                self.logger.warning(
                    f"알 수 없는 발신자 타입: {extraction_result.sender_type}, "
                    f"event_id={event.event_id}"
                )
                return {
                    "success": True,
                    "action": "saved_as_unprocessed",
                    "reason": "unknown_sender_type",
                    "message": f"알 수 없는 발신자 타입: {extraction_result.sender_type}",
                }

        except ValidationError as e:
            self.logger.error(f"이벤트 검증 실패: {str(e)}")
            # 검증 실패 이벤트도 원본 데이터와 함께 저장 시도
            try:
                self._save_raw_unprocessed_event(event_data, "validation_error", str(e))
            except Exception as save_error:
                self.logger.error(f"미처리 이벤트 저장 실패: {str(save_error)}")
            return {"success": False, "error": "validation_error", "message": str(e)}
        except Exception as e:
            self.logger.error(f"이벤트 처리 중 예상치 못한 오류: {str(e)}")
            # 예외 발생 이벤트도 저장 시도
            try:
                self._save_raw_unprocessed_event(event_data, "other", str(e))
            except Exception as save_error:
                self.logger.error(f"미처리 이벤트 저장 실패: {str(save_error)}")
            return {
                "success": False,
                "error": "processing_error",
                "message": f"이벤트 처리 실패: {str(e)}",
            }

    def _check_dashboard_worthiness(self, extraction_result) -> tuple[bool, str]:
        """
        대시보드 처리 가능 여부 확인

        Returns:
            (처리 가능 여부, 불가능한 경우 사유)
        """
        # 조건 1: 아젠다 번호 확인
        if not extraction_result.agenda_no:
            return False, "no_agenda_number"

        # 조건 2: 발신자 조직 확인
        sender_org = extraction_result.sender_organization
        if not sender_org:
            return False, "invalid_organization"

        # 조건 3: IACS 멤버 확인
        if sender_org not in ORGANIZATIONS:
            return False, "not_iacs_member"

        return True, ""

    def _get_reason_description(self, reason: str) -> str:
        """미처리 사유에 대한 설명"""
        descriptions = {
            "no_agenda_number": "아젠다 번호 없음",
            "invalid_organization": "발신 기관 정보 없음",
            "not_iacs_member": "IACS 멤버가 아닌 기관",
            "unknown_sender_type": "알 수 없는 발신자 타입",
            "extraction_failed": "키워드 추출 실패",
            "validation_error": "이벤트 데이터 검증 실패",
            "other": "기타 오류",
        }
        return descriptions.get(reason, reason)

    def _save_unprocessed_event(
        self, event: EmailDashboardEvent, reason: str, description: str
    ):
        """미처리 이벤트 저장"""
        try:
            extraction = event.data.extraction_result

            # 날짜 파싱
            send_time = None
            if extraction.send_time:
                try:
                    send_time = datetime.fromisoformat(
                        extraction.send_time.replace(" ", "T")
                    )
                    if send_time.tzinfo is None:
                        send_time = send_time.replace(tzinfo=timezone.utc)
                except Exception:
                    pass

            deadline = None
            if extraction.deadline:
                try:
                    deadline = datetime.fromisoformat(
                        extraction.deadline.replace(" ", "T")
                    )
                    if deadline.tzinfo is None:
                        deadline = deadline.replace(tzinfo=timezone.utc)
                except Exception:
                    pass

            # 이벤트 전체 데이터를 JSON으로 저장
            raw_event_data = json.dumps(event.model_dump(), ensure_ascii=False)

            # 데이터베이스에 저장
            self.repository.email_dashboard_save_unprocessed_event(
                event_id=event.event_id,
                event_type=event.event_type,
                mail_id=event.data.mail_id,
                sender_type=extraction.sender_type,
                sender_organization=extraction.sender_organization,
                agenda_no=extraction.agenda_no,
                send_time=send_time,
                subject=None,  # 현재 스키마에는 subject가 없음
                summary=extraction.summary,
                keywords=extraction.keywords,
                mail_type=extraction.mail_type,
                decision_status=extraction.decision_status,
                has_deadline=extraction.has_deadline,
                deadline=deadline,
                unprocessed_reason=reason,
                raw_event_data=raw_event_data,
            )

        except Exception as e:
            self.logger.error(f"미처리 이벤트 저장 실패: {str(e)}")

    def _save_raw_unprocessed_event(
        self, event_data: Dict[str, Any], reason: str, description: str
    ):
        """원본 이벤트 데이터를 미처리 테이블에 저장 (파싱 실패 시)"""
        try:
            # 최소한의 정보 추출 시도
            event_id = event_data.get(
                "event_id", f"unknown_{datetime.now().timestamp()}"
            )
            event_type = event_data.get("event_type", "unknown")

            # 전체 데이터를 JSON으로 저장
            raw_event_data = json.dumps(event_data, ensure_ascii=False)

            self.repository.email_dashboard_save_unprocessed_event(
                event_id=event_id,
                event_type=event_type,
                mail_id=None,
                sender_type=None,
                sender_organization=None,
                agenda_no=None,
                send_time=None,
                subject=None,
                summary=description,
                keywords=[],
                mail_type=None,
                decision_status=None,
                has_deadline=False,
                deadline=None,
                unprocessed_reason=reason,
                raw_event_data=raw_event_data,
            )
        except Exception as e:
            self.logger.error(f"원본 미처리 이벤트 저장 실패: {str(e)}")

    def _email_dashboard_validate_and_parse_event(
        self, event_data: Dict[str, Any]
    ) -> EmailDashboardEvent:
        """이벤트 데이터 검증 및 파싱"""
        try:
            return EmailDashboardEvent(**event_data)
        except Exception as e:
            raise ValidationError(
                f"이벤트 데이터 형식 오류: {str(e)}",
                field="event_data",
                value=str(event_data)[:200],
            ) from e

    def _email_dashboard_process_chair_mail(
        self, event: EmailDashboardEvent
    ) -> Dict[str, Any]:
        """
        의장 발송 메일 처리

        Args:
            event: 이메일 대시보드 이벤트

        Returns:
            처리 결과
        """
        try:
            extraction = event.data.extraction_result

            # 아젠다 번호 결정
            agenda_no = self._email_dashboard_determine_agenda_no(extraction)
            if not agenda_no:
                self.logger.warning(
                    f"아젠다 번호를 결정할 수 없음: event_id={event.event_id}, "
                    f"mail_id={event.data.mail_id}"
                )
                return {
                    "success": True,
                    "action": "ignored",
                    "reason": "no_agenda_number",
                    "message": "아젠다 번호를 결정할 수 없어 처리하지 않음",
                }

            # 패널 ID 결정
            panel_id = self._email_dashboard_determine_panel_id(extraction)

            # 발송 시간 파싱
            send_time = datetime.fromisoformat(extraction.send_time.replace(" ", "T"))
            if send_time.tzinfo is None:
                send_time = send_time.replace(tzinfo=timezone.utc)

            # 마감 시간 파싱
            deadline = None
            if extraction.has_deadline and extraction.deadline:
                try:
                    deadline = datetime.fromisoformat(
                        extraction.deadline.replace(" ", "T")
                    )
                    if deadline.tzinfo is None:
                        deadline = deadline.replace(tzinfo=timezone.utc)
                except ValueError as e:
                    self.logger.warning(
                        f"마감 시간 파싱 실패: {extraction.deadline}, error={str(e)}"
                    )

            # 회차 번호 및 버전 추출
            round_no = None
            agenda_version = None

            if extraction.agenda_info:
                if extraction.agenda_info.round_no:
                    round_no = extraction.agenda_info.round_no
                if extraction.agenda_info.agenda_version:
                    agenda_version = extraction.agenda_info.agenda_version

            # 아젠다 생성/업데이트
            success = self.repository.email_dashboard_create_or_update_agenda(
                panel_id=panel_id,
                agenda_no=agenda_no,
                send_time=send_time,
                deadline=deadline,
                mail_type=extraction.mail_type,
                decision_status=extraction.decision_status,
                summary=extraction.summary,
                round_no=round_no,
                agenda_version=agenda_version,
            )

            if success:
                self.logger.info(
                    f"의장 메일 처리 완료: agenda_no={agenda_no}, "
                    f"event_id={event.event_id}"
                )
                return {
                    "success": True,
                    "action": "chair_mail_processed",
                    "agenda_no": agenda_no,
                    "message": f"의장 메일 처리 완료: {agenda_no}",
                }
            else:
                raise BusinessLogicError(
                    f"의장 메일 처리 실패: {agenda_no}", operation="process_chair_mail"
                )

        except Exception as e:
            self.logger.error(
                f"의장 메일 처리 실패: event_id={event.event_id}, error={str(e)}"
            )
            return {
                "success": False,
                "error": "chair_mail_processing_error",
                "message": f"의장 메일 처리 실패: {str(e)}",
            }

    def _email_dashboard_process_member_mail(
        self, event: EmailDashboardEvent
    ) -> Dict[str, Any]:
        """
        멤버 기관 응답 메일 처리

        Args:
            event: 이메일 대시보드 이벤트

        Returns:
            처리 결과
        """
        try:
            extraction = event.data.extraction_result

            # 발신 기관 확인
            if not extraction.sender_organization:
                self.logger.warning(
                    f"발신 기관 정보 없음: event_id={event.event_id}, "
                    f"mail_id={event.data.mail_id}"
                )
                return {
                    "success": True,
                    "action": "ignored",
                    "reason": "no_sender_organization",
                    "message": "발신 기관 정보가 없어 처리하지 않음",
                }

            # 기관 코드 유효성 검사
            if extraction.sender_organization not in ORGANIZATIONS:
                self.logger.warning(
                    f"유효하지 않은 기관 코드: {extraction.sender_organization}, "
                    f"event_id={event.event_id}"
                )
                return {
                    "success": True,
                    "action": "ignored",
                    "reason": "invalid_organization",
                    "message": f"유효하지 않은 기관 코드: {extraction.sender_organization}",
                }

            # 아젠다 번호 확인
            agenda_no = extraction.agenda_no
            if not agenda_no:
                self.logger.warning(
                    f"멤버 응답에 아젠다 번호 없음: event_id={event.event_id}, "
                    f"org={extraction.sender_organization}"
                )
                return {
                    "success": True,
                    "action": "ignored",
                    "reason": "no_agenda_number",
                    "message": "멤버 응답에 아젠다 번호가 없어 처리하지 않음",
                }

            # 응답 시간 파싱
            response_time = datetime.fromisoformat(
                extraction.send_time.replace(" ", "T")
            )
            if response_time.tzinfo is None:
                response_time = response_time.replace(tzinfo=timezone.utc)

            # 아젠다 존재 확인 및 자동 생성
            if not self.repository.email_dashboard_agenda_exists(agenda_no):
                self.logger.info(
                    f"아젠다가 없어 기본 아젠다 생성: {agenda_no}, "
                    f"org={extraction.sender_organization}"
                )
                self._email_dashboard_create_missing_agenda(extraction, agenda_no)

            # 멤버 응답 업데이트
            success = self.repository.email_dashboard_update_member_response(
                agenda_no=agenda_no,
                organization=extraction.sender_organization,
                response_content=extraction.summary,
                response_time=response_time,
            )

            if success:
                self.logger.info(
                    f"멤버 응답 처리 완료: agenda_no={agenda_no}, "
                    f"org={extraction.sender_organization}, event_id={event.event_id}"
                )
                return {
                    "success": True,
                    "action": "member_response_processed",
                    "agenda_no": agenda_no,
                    "organization": extraction.sender_organization,
                    "message": f"멤버 응답 처리 완료: {extraction.sender_organization} -> {agenda_no}",
                }
            else:
                raise BusinessLogicError(
                    f"멤버 응답 처리 실패: {agenda_no}, org={extraction.sender_organization}",
                    operation="process_member_mail",
                )

        except Exception as e:
            self.logger.error(
                f"멤버 응답 처리 실패: event_id={event.event_id}, error={str(e)}"
            )
            return {
                "success": False,
                "error": "member_response_processing_error",
                "message": f"멤버 응답 처리 실패: {str(e)}",
            }

    def _email_dashboard_determine_agenda_no(self, extraction) -> Optional[str]:
        """아젠다 번호 결정"""
        # 1. 직접 추출된 아젠다 번호 사용
        if extraction.agenda_no:
            return extraction.agenda_no

        # 2. agenda_info에서 패턴 기반 생성
        if extraction.agenda_info and extraction.agenda_info.full_pattern:
            return extraction.agenda_info.full_pattern

        # 3. 개별 정보로 구성
        if extraction.agenda_info:
            info = extraction.agenda_info
            if info.panel_name and info.round_no:
                # agenda_version이 있으면 포함
                if info.agenda_version:
                    return f"{info.panel_name}{info.year}{info.round_no}{info.agenda_version}"
                else:
                    return f"{info.panel_name}{info.year}{info.round_no}"

        return None

    def _email_dashboard_determine_panel_id(self, extraction) -> str:
        """패널 ID 결정"""
        if extraction.agenda_info and extraction.agenda_info.panel_name:
            return extraction.agenda_info.panel_name

        # 기본값 반환
        return "UNKNOWN_PANEL"

    def _email_dashboard_create_missing_agenda(
        self, extraction, agenda_no: str
    ) -> None:
        """
        누락된 아젠다 자동 생성

        멤버 응답이 있는데 해당 아젠다가 없는 경우 기본값으로 생성
        """
        try:
            panel_id = self._email_dashboard_determine_panel_id(extraction)

            # 응답 시간을 발송 시간으로 사용 (실제 발송 시간은 알 수 없음)
            send_time = datetime.fromisoformat(extraction.send_time.replace(" ", "T"))
            if send_time.tzinfo is None:
                send_time = send_time.replace(tzinfo=timezone.utc)

            # 기본 마감일 설정 (응답 시간 + 7일)
            deadline = None
            if extraction.has_deadline and extraction.deadline:
                try:
                    deadline = datetime.fromisoformat(
                        extraction.deadline.replace(" ", "T")
                    )
                    if deadline.tzinfo is None:
                        deadline = deadline.replace(tzinfo=timezone.utc)
                except ValueError:
                    # 파싱 실패 시 응답 시간 + 7일로 설정
                    from datetime import timedelta

                    deadline = send_time + timedelta(days=7)

            round_no = None
            agenda_version = None

            if extraction.agenda_info:
                if extraction.agenda_info.round_no:
                    round_no = extraction.agenda_info.round_no
                if extraction.agenda_info.agenda_version:
                    agenda_version = extraction.agenda_info.agenda_version

            self.repository.email_dashboard_create_or_update_agenda(
                panel_id=panel_id,
                agenda_no=agenda_no,
                send_time=send_time,
                deadline=deadline,
                mail_type="REQUEST",  # 기본값
                decision_status="comment",  # 이미 응답이 있으므로 comment 상태
                summary=f"자동 생성된 아젠다 (응답 기반): {agenda_no}",
                round_no=round_no,
                agenda_version=agenda_version,
            )

            self.logger.info(f"누락된 아젠다 자동 생성 완료: {agenda_no}")

        except Exception as e:
            self.logger.error(f"누락된 아젠다 생성 실패: {agenda_no}, error={str(e)}")
            # 생성 실패해도 예외를 던지지 않음 (응답 처리는 계속 진행)

    # =========================================================================
    # 배치 처리 메서드
    # =========================================================================

    def email_dashboard_process_batch_events(
        self, events: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        여러 이벤트 배치 처리

        Args:
            events: 이벤트 목록

        Returns:
            배치 처리 결과
        """
        try:
            results = []
            success_count = 0
            error_count = 0
            unprocessed_count = 0

            for i, event_data in enumerate(events):
                try:
                    result = self.email_dashboard_process_event(event_data)
                    results.append(
                        {
                            "index": i,
                            "event_id": event_data.get("event_id", "unknown"),
                            "result": result,
                        }
                    )

                    if result["success"]:
                        if result.get("action") == "saved_as_unprocessed":
                            unprocessed_count += 1
                        else:
                            success_count += 1
                    else:
                        error_count += 1

                except Exception as e:
                    error_result = {
                        "success": False,
                        "error": "batch_processing_error",
                        "message": f"배치 처리 중 오류: {str(e)}",
                    }
                    results.append(
                        {
                            "index": i,
                            "event_id": event_data.get("event_id", "unknown"),
                            "result": error_result,
                        }
                    )
                    error_count += 1

                    self.logger.error(
                        f"배치 이벤트 처리 실패: index={i}, error={str(e)}"
                    )

            self.logger.info(
                f"배치 처리 완료: 총 {len(events)}개, "
                f"성공 {success_count}개, 미처리 {unprocessed_count}개, 실패 {error_count}개"
            )

            return {
                "success": True,
                "total_events": len(events),
                "success_count": success_count,
                "unprocessed_count": unprocessed_count,
                "error_count": error_count,
                "results": results,
                "message": f"배치 처리 완료: {success_count}/{len(events)} 성공, {unprocessed_count} 미처리",
            }

        except Exception as e:
            self.logger.error(f"배치 처리 전체 실패: {str(e)}")
            return {
                "success": False,
                "error": "batch_processing_failure",
                "message": f"배치 처리 전체 실패: {str(e)}",
            }

    def email_dashboard_reprocess_unprocessed_events(
        self, filter_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        미처리 이벤트 재처리

        Args:
            filter_params: 필터 조건

        Returns:
            재처리 결과
        """
        try:
            # 미처리 이벤트 조회
            unprocessed_events = self.repository.email_dashboard_get_unprocessed_events(
                filter_params
            )

            if not unprocessed_events:
                return {
                    "success": True,
                    "message": "재처리할 미처리 이벤트가 없습니다",
                    "processed_count": 0,
                }

            processed_count = 0
            success_count = 0

            for event in unprocessed_events:
                try:
                    # 원본 이벤트 데이터 파싱
                    raw_event = json.loads(event.raw_event_data)

                    # 재처리
                    result = self.email_dashboard_process_event(raw_event)

                    if (
                        result.get("success")
                        and result.get("action") != "saved_as_unprocessed"
                    ):
                        # 성공적으로 처리된 경우 processed 플래그 업데이트
                        self.repository.email_dashboard_mark_event_processed(
                            event.event_id
                        )
                        success_count += 1

                    processed_count += 1

                except Exception as e:
                    self.logger.error(
                        f"미처리 이벤트 재처리 실패: event_id={event.event_id}, error={str(e)}"
                    )

            return {
                "success": True,
                "total_events": len(unprocessed_events),
                "processed_count": processed_count,
                "success_count": success_count,
                "message": f"{success_count}/{len(unprocessed_events)}개 이벤트 재처리 성공",
            }

        except Exception as e:
            self.logger.error(f"미처리 이벤트 재처리 실패: {str(e)}")
            return {
                "success": False,
                "error": "reprocess_failure",
                "message": f"미처리 이벤트 재처리 실패: {str(e)}",
            }
