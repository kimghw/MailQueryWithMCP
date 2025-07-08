"""
데이터 병합 서비스 - IACS와 OpenRouter 결과 병합
modules/mail_process/services/data_merger.py
"""

from datetime import datetime
from typing import Dict, Any, Optional

from ..mail_processor_schema import MailType, DecisionStatus, ProcessingStatus


class MailTransformationRules:
    """메일 변환 규칙"""

    @staticmethod
    def to_event_format(mail: Dict[str, Any]) -> Dict[str, Any]:
        """이벤트용 포맷으로 변환 - 필요한 필드만 선택"""
        # 필요한 필드만 선택하여 새 딕셔너리 생성
        event_data = {
            # 기본 필드
            "id": mail.get("id"),
            "subject": mail.get("subject"),
            "from": mail.get("from_address") or mail.get("from"),
            "receivedDateTime": mail.get("receivedDateTime") or mail.get("sent_time"),
            "bodyPreview": mail.get("bodyPreview") or mail.get("body_preview"),
            "body": mail.get("body", {}),
            # 발신자 정보
            "sender_organization": mail.get("sender_organization"),
            "sender_type": mail.get("sender_type"),
            # IACS 정보 - 통일된 네이밍
            "agenda_code": mail.get("agenda_code"),
            "agenda_base": mail.get("agenda_base"),
            "agenda_panel": mail.get("agenda_panel"),  # agenda_org에서 변경
            "response_org": mail.get("response_org")
            or mail.get(
                "agenda_organization"
            ),  # agenda_organization을 response_org로 매핑
            "response_version": mail.get("response_version"),
                        "agenda_version": mail.get("agenda_version"),
            # 추가 정보
            "extracted_keywords": mail.get("keywords", []),
            "urgency": mail.get("urgency", "NORMAL"),
            "is_reply": mail.get("is_reply", False),
            "is_forward": mail.get("is_forward", False),
            "mail_type": mail.get("mail_type", "OTHER"),
            "decision_status": mail.get("decision_status", "created"),
            "has_deadline": mail.get("has_deadline", False),
            "deadline": mail.get("deadline"),
            "summary": mail.get("summary"),
        }


        return event_data

    @staticmethod
    def merge_extractions(
        iacs_result: Optional[Dict], openrouter_result: Optional[Dict]
    ) -> Dict[str, Any]:
        """IACS와 OpenRouter 결과를 명확한 우선순위로 병합"""
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

        # 1. IACS 파서 결과 병합 (우선순위 높음)
        if iacs_result:
            if iacs_result.get("extracted_info"):
                info = iacs_result["extracted_info"]
                base_no = info.get("base_agenda_no", "")
                version = info.get("agenda_version", "")

                merged.update(
                    {
                        "agenda_code": f"{base_no}{version}" if base_no else None,
                        "agenda_base": base_no,
                        "agenda_version": version,
                        "agenda_panel": info.get("panel"),  # 패널 정보
                        "response_org": info.get("organization"),  # 응답 조직
                        "response_version": info.get("response_version"),
                        "agenda_version": mail.get("agenda_version"),
                        "agenda_version": version,
                    }
                )

            # IACS 메타 정보
            merged.update(
                {
                    "urgency": iacs_result.get("urgency", "NORMAL"),
                    "is_reply": iacs_result.get("is_reply", False),
                    "reply_depth": iacs_result.get("reply_depth"),
                    "is_forward": iacs_result.get("is_forward", False),
                    "additional_agenda_references": iacs_result.get(
                        "additional_agenda_references", []
                    ),
                    "sender_address": iacs_result.get("sender_address"),
                    "sender_name": iacs_result.get("sender_name"),
                    "sender_type": iacs_result.get("sender_type"),
                    "sender_organization": iacs_result.get("sender_organization"),
                    "sent_time": iacs_result.get("sent_time"),
                    "clean_content": iacs_result.get("clean_content"),
                }
            )

        # 2. OpenRouter 결과 병합 (IACS에 없는 정보만)
        if openrouter_result:
            # 항상 OpenRouter에서 가져오는 정보
            merged["keywords"] = openrouter_result.get("keywords", [])
            merged["summary"] = openrouter_result.get("summary", "")

            # IACS에서 못 찾은 정보만 보충
            # mail_type은 항상 OpenRouter 값 사용
            if "mail_type" in openrouter_result:
                merged["mail_type"] = openrouter_result["mail_type"]
            
            # 나머지는 IACS에 없는 경우만
            for key in ["decision_status", "has_deadline", "deadline"]:
                if key in openrouter_result:
                    merged[key] = openrouter_result[key]

            # 발신자 정보 보충
            if not merged.get("sender_type") and openrouter_result.get("sender_type"):
                merged["sender_type"] = openrouter_result["sender_type"]
            if not merged.get("sender_organization") and openrouter_result.get(
                "sender_organization"
            ):
                merged["sender_organization"] = openrouter_result["sender_organization"]

            # agenda 정보 보충
            if not merged.get("agenda_code") and openrouter_result.get("agenda_no"):
                merged["agenda_code"] = openrouter_result["agenda_no"]
                merged["agenda_base"] = openrouter_result["agenda_no"]

        return merged

    @staticmethod
    def format_datetime(dt: Any) -> str:
        """datetime 객체를 문자열로 포맷"""
        if isinstance(dt, datetime):
            return dt.isoformat()
        else:
            return str(dt)
