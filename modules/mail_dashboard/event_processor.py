"""
Email Dashboard Event Processor

이메일 관련 이벤트를 처리하여 데이터베이스에 저장합니다.
"""

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
                self.logger.warning(
                    f"추출 실패한 이벤트 무시: {event.event_id}, "
                    f"mail_id={event.data.mail_id}"
                )
                return {
                    "success": True,
                    "action": "ignored",
                    "reason": "extraction_failed",
                    "message": "추출 실패한 이벤트는 처리하지 않음",
                }

            extraction_result = event.data.extraction_result

            # 발신자 타입에 따른 처리 분기
            if extraction_result.sender_type == "CHAIR":
                return self._email_dashboard_process_chair_mail(event)
            elif extraction_result.sender_type == "MEMBER":
                return self._email_dashboard_process_member_mail(event)
            else:
                self.logger.warning(
                    f"알 수 없는 발신자 타입: {extraction_result.sender_type}, "
                    f"event_id={event.event_id}"
                )
                return {
                    "success": True,
                    "action": "ignored",
                    "reason": "unknown_sender_type",
                    "message": f"알 수 없는 발신자 타입: {extraction_result.sender_type}",
                }

        except ValidationError as e:
            self.logger.error(f"이벤트 검증 실패: {str(e)}")
            return {"success": False, "error": "validation_error", "message": str(e)}
        except Exception as e:
            self.logger.error(f"이벤트 처리 중 예상치 못한 오류: {str(e)}")
            return {
                "success": False,
                "error": "processing_error",
                "message": f"이벤트 처리 실패: {str(e)}",
            }

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

            # 회차 번호 추출
            round_no = None
            if extraction.agenda_info and extraction.agenda_info.round_no:
                round_no = extraction.agenda_info.round_no

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
            if info.panel_name and info.round_no and info.sequence:
                return f"{info.panel_name}-{info.round_no}-{info.sequence}"

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
            if extraction.agenda_info and extraction.agenda_info.round_no:
                round_no = extraction.agenda_info.round_no

            self.repository.email_dashboard_create_or_update_agenda(
                panel_id=panel_id,
                agenda_no=agenda_no,
                send_time=send_time,
                deadline=deadline,
                mail_type="REQUEST",  # 기본값
                decision_status="comment",  # 이미 응답이 있으므로 comment 상태
                summary=f"자동 생성된 아젠다 (응답 기반): {agenda_no}",
                round_no=round_no,
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
                f"배치 처리 완료: 총 {len(events)}개, 성공 {success_count}개, 실패 {error_count}개"
            )

            return {
                "success": True,
                "total_events": len(events),
                "success_count": success_count,
                "error_count": error_count,
                "results": results,
                "message": f"배치 처리 완료: {success_count}/{len(events)} 성공",
            }

        except Exception as e:
            self.logger.error(f"배치 처리 전체 실패: {str(e)}")
            return {
                "success": False,
                "error": "batch_processing_failure",
                "message": f"배치 처리 전체 실패: {str(e)}",
            }
