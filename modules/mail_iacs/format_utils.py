"""
IACS 메일 조회 결과 포맷팅 유틸리티
mail_query_without_db와 동일한 포맷으로 출력
"""

import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional


class IACSResultFormatter:
    """IACS 메일 조회 결과 포맷터"""

    def __init__(self):
        """KST 타임존 설정"""
        self.KST = timezone(timedelta(hours=9))

    def format_search_results(
        self,
        mails: List[Dict[str, Any]],
        user_id: str,
        panel_name: str,
        chair_address: str,
        start_date: datetime,
        end_date: datetime,
        mail_type: str = "agenda",
        include_body: bool = False,
        download_attachments: bool = False,
        save_email: bool = False
    ) -> str:
        """
        메일 조회 결과를 mail_query 스타일로 포맷팅

        Args:
            mails: 메일 딕셔너리 리스트
            user_id: 사용자 ID
            panel_name: 패널 이름
            chair_address: 의장 주소
            start_date: 시작 날짜
            end_date: 종료 날짜
            mail_type: 메일 타입 ("agenda" 또는 "responses")
            include_body: 본문 포함 여부
            download_attachments: 첨부파일 다운로드 여부
            save_email: 메일 저장 여부

        Returns:
            포맷팅된 결과 문자열
        """
        result_text = f"📧 메일 조회 결과 - {user_id} ({panel_name})\n"
        result_text += f"{'='*60}\n"

        # 날짜 범위 표시 (UTC -> KST 변환)
        if start_date and end_date:
            # datetime 객체인 경우 timezone 처리
            if isinstance(start_date, datetime):
                if start_date.tzinfo is None:
                    start_kst = start_date.replace(tzinfo=timezone.utc).astimezone(self.KST)
                else:
                    start_kst = start_date.astimezone(self.KST)
            else:
                start_kst = datetime.fromisoformat(str(start_date)).replace(tzinfo=timezone.utc).astimezone(self.KST)

            if isinstance(end_date, datetime):
                if end_date.tzinfo is None:
                    end_kst = end_date.replace(tzinfo=timezone.utc).astimezone(self.KST)
                else:
                    end_kst = end_date.astimezone(self.KST)
            else:
                end_kst = datetime.fromisoformat(str(end_date)).replace(tzinfo=timezone.utc).astimezone(self.KST)

            days_back = (end_date - start_date).days
            result_text += f"조회 기간: {start_kst.strftime('%Y-%m-%d %H:%M')} ~ "
            result_text += f"{end_kst.strftime('%Y-%m-%d %H:%M')} KST ({days_back}일간)\n"

        # 필터 정보 표시
        if mail_type == "agenda":
            result_text += f"발신자 필터: {chair_address}\n"
            result_text += f"메일 타입: 아젠다 (의장 → 멤버)\n"
        else:
            result_text += f"메일 타입: 응답 (멤버 → 의장)\n"

        # 조회 옵션 표시
        result_text += f"조회된 메일: {len(mails)}개"
        query_details = []
        if include_body:
            query_details.append("본문 포함")
        else:
            query_details.append("제목만")
        if download_attachments:
            query_details.append("첨부파일 다운로드")
        if save_email:
            query_details.append("메일 저장")

        if query_details:
            result_text += f" ({', '.join(query_details)})"
        result_text += "\n\n"

        # 각 메일 표시
        for i, mail in enumerate(mails, 1):
            result_text += self._format_single_mail(mail, i, include_body, user_id)

        # 요약
        result_text += f"\n✅ 총 {len(mails)}개의 이메일이 처리되었습니다.\n"

        # 옵션 안내
        result_text += self._get_query_options_summary(
            include_body, download_attachments, save_email, panel_name
        )

        return result_text

    def _format_single_mail(
        self,
        mail: Dict[str, Any],
        index: int,
        include_body: bool = False,
        user_id: str = ""
    ) -> str:
        """
        개별 메일 포맷팅

        Args:
            mail: 메일 딕셔너리
            index: 메일 인덱스
            include_body: 본문 포함 여부
            user_id: 사용자 ID (첨부파일 다운로드 URL 생성용)

        Returns:
            포맷팅된 메일 문자열
        """
        text = f"\n[{index}] {mail.get('subject', '(제목 없음)')}\n"

        # 발신자 정보
        sender = self._extract_sender_info(mail)
        text += f"   발신자: {sender}\n"

        # 수신일 (UTC -> KST 변환)
        received_date = self._format_received_date(mail)
        text += f"   수신일: {received_date} KST\n"

        # 읽음 상태
        is_read = mail.get('is_read', False)
        text += f"   읽음: {'✓' if is_read else '✗'}\n"

        # 첨부파일 유무
        has_attachments = mail.get('has_attachments', False)
        text += f"   첨부: {'📎' if has_attachments else '-'}\n"

        # 저장 경로
        if mail.get('saved_email_path'):
            text += f"   💾 저장됨: {mail['saved_email_path']}\n"

        # 본문 표시
        if include_body:
            body_text = self._extract_body_text(mail)
            if body_text:
                text += f"   내용: {body_text}\n"

        # 첨부파일 정보 (has_attachments flag 또는 실제 attachments 데이터가 있는 경우)
        if has_attachments or mail.get('attachments'):
            text += self._format_attachments(mail, user_id)

        return text

    def _extract_sender_info(self, mail: Dict[str, Any]) -> str:
        """발신자 정보 추출"""
        from_address = mail.get('from_address', {})

        if isinstance(from_address, dict):
            email_addr = from_address.get('emailAddress', {})
            if isinstance(email_addr, dict):
                sender_email = email_addr.get('address', 'unknown@email.com')
                sender_name = email_addr.get('name', '')
                if sender_name:
                    return f"{sender_name} <{sender_email}>"
                return sender_email

        return "Unknown"

    def _format_received_date(self, mail: Dict[str, Any]) -> str:
        """수신일 포맷팅 (UTC -> KST)"""
        received_datetime = mail.get('received_date_time')

        if not received_datetime:
            return "Unknown"

        try:
            # datetime 객체인 경우
            if isinstance(received_datetime, datetime):
                if received_datetime.tzinfo is None:
                    dt_utc = received_datetime.replace(tzinfo=timezone.utc)
                else:
                    dt_utc = received_datetime
            # 문자열인 경우
            else:
                dt_utc = datetime.fromisoformat(str(received_datetime).replace('Z', '+00:00'))

            # KST로 변환
            dt_kst = dt_utc.astimezone(self.KST)
            return dt_kst.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return str(received_datetime)

    def _extract_body_text(self, mail: Dict[str, Any]) -> Optional[str]:
        """본문 텍스트 추출 및 HTML 태그 제거"""
        body = mail.get('body')

        if not body:
            return mail.get('body_preview')

        # dict 형태의 body (Graph API 형식)
        if isinstance(body, dict):
            content_type = body.get('contentType', 'text')
            content = body.get('content', '')

            if content_type.lower() == 'html':
                # HTML 태그 제거
                text_content = re.sub('<[^<]+?>', '', content)
                # HTML 엔티티 변환
                text_content = text_content.replace('&nbsp;', ' ')
                text_content = text_content.replace('&lt;', '<')
                text_content = text_content.replace('&gt;', '>')
                text_content = text_content.replace('&amp;', '&')
                return text_content.strip()
            return content

        # 문자열 형태의 body
        return str(body)

    def _format_attachments(self, mail: Dict[str, Any], user_id: str = "") -> str:
        """
        첨부파일 정보 포맷팅 (다운로드 링크 포함)

        ⚠️ IMPORTANT: 첨부파일 이름을 클릭 가능한 링크로 만드세요!
        - 첨부파일 이름을 markdown link 형식으로 포맷팅: [파일명](다운로드URL)
        - 사용자가 첨부파일 이름을 클릭하면 바로 다운로드할 수 있도록 처리
        - 별도로 "🔗 다운로드:" 라인을 추가하지 말고, 파일명 자체를 링크로 만들기

        Args:
            mail: 메일 딕셔너리
            user_id: 사용자 ID (Graph API URL 생성용)

        Returns:
            포맷팅된 첨부파일 정보 (첨부파일 이름이 클릭 가능한 링크로 표시됨)
        """
        text = ""
        mail_id = mail.get('id', '')

        # downloaded_attachments (다운로드된 첨부파일)
        downloaded = mail.get('downloaded_attachments', [])
        if downloaded:
            text += f"   첨부파일 ({len(downloaded)}개):\n"
            for att in downloaded:
                name = att.get('name', 'unknown')
                size = att.get('size', 0)
                text += f"     - {name} ({size:,} bytes)\n"

                if att.get('file_path'):
                    text += f"       💾 저장됨: {att['file_path']}\n"

                if att.get('text_content'):
                    text += f"       📄 변환됨\n"

        # attachments (첨부파일 메타데이터만 - 다운로드 링크 생성)
        elif mail.get('attachments'):
            attachments = mail['attachments']
            if isinstance(attachments, list) and attachments:
                text += f"   첨부파일 ({len(attachments)}개):\n"
                for att in attachments:
                    if isinstance(att, dict):
                        name = att.get('name', 'unknown')
                        size = att.get('size', 0)
                        att_id = att.get('id', '')

                        # Graph API 다운로드 링크 생성 - 첨부파일 이름을 클릭 가능한 링크로 만들기
                        if user_id and mail_id and att_id:
                            download_url = f"https://graph.microsoft.com/v1.0/users/{user_id}/messages/{mail_id}/attachments/{att_id}"
                            # 마크다운 링크 형식: [파일명](URL)
                            text += f"     - [{name}]({download_url}) ({size:,} bytes)\n"
                        else:
                            # 링크 생성 불가 시 일반 텍스트로 표시
                            text += f"     - {name} ({size:,} bytes)\n"

        return text

    def _get_query_options_summary(
        self,
        include_body: bool,
        download_attachments: bool,
        save_email: bool,
        panel_name: str
    ) -> str:
        """조회 옵션 상태 및 안내"""
        summary = f"\n{'='*80}\n"
        summary += "📌 **조회 옵션 상태**\n"
        summary += f"{'='*80}\n"

        summary += "\n**현재 활성화된 옵션:**\n"
        active_options = []

        if include_body:
            active_options.append("✅ 본문 포함")
        else:
            active_options.append("❌ 제목만 조회 (본문 미포함)")

        if download_attachments:
            active_options.append("✅ 첨부파일 다운로드")
        else:
            active_options.append("❌ 첨부파일 미다운로드")

        if save_email:
            active_options.append("✅ 메일 저장")
        else:
            active_options.append("❌ 메일 미저장")

        for option in active_options:
            summary += f"- {option}\n"

        # 사용 가능한 조회 방법
        summary += "\n**📢 사용 가능한 조회 방법:**\n"
        summary += f"- **아젠다 조회**: \"sdtp 패널의 최근 2개월 아젠다 조회해줘\"\n"
        summary += f"- **첨부파일 다운로드**: \"download_attachments: true\"\n"
        summary += f"- **메일 저장**: \"save_email: true\"\n"

        summary += "\n💡 위 옵션을 사용하여 더 자세한 정보를 조회할 수 있습니다.\n"

        # 포맷팅 지침 추가
        summary += self._get_formatting_instructions(panel_name)

        return summary

    def _get_formatting_instructions(self, panel_name: str) -> str:
        """Claude를 위한 포맷팅 지침"""
        instructions = f"\n{'='*80}\n"
        instructions += "📋 **결과 포맷팅 요청**\n"
        instructions += f"{'='*80}\n\n"

        instructions += "📧 이메일 조회 결과 포맷팅 지침\n\n"
        instructions += f"포맷 스타일: table\n"
        instructions += f"첨부파일 포함: True\n"
        instructions += f"패널: {panel_name}\n\n"

        instructions += "다음 순서와 형식으로 테이블을 작성하세요:\n"
        instructions += "** 모든 메일 리스트에 대해서 작성해 주세요 **\n\n"

        instructions += "**📊 표 구성 (필수 열)**:\n"
        instructions += "| 유형 | 날짜 | 발신자/수신자 | 제목 | 주요내용 | 응답필요성 | 응답기한 | 첨부 |\n\n"

        instructions += "**각 열 작성 지침**:\n"
        instructions += "1. **유형**: \n"
        instructions += "   - 아젠다: 의장이 멤버에게 보낸 메일\n"
        instructions += "   - 응답: 멤버가 의장에게 보낸 메일\n"
        instructions += "2. **날짜**: YYYY-MM-DD HH:MM 형식\n"
        instructions += "3. **발신자/수신자**: \n"
        instructions += "   - 아젠다: 의장 이름 (이메일)\n"
        instructions += "   - 응답: → 멤버 이름 (이메일)\n"
        instructions += "4. **제목**: 전체 제목 (너무 길면 ... 사용)\n"
        instructions += "5. **주요내용**: 핵심 내용 1-2줄 요약\n"
        instructions += "6. **응답필요성**: \n"
        instructions += "   - 아젠다: 🔴 응답필요 / 🟢 참고용\n"
        instructions += "   - 응답: ✅ 응답완료 / ⏳ 검토중\n"
        instructions += "7. **응답기한**: 구체적 날짜 또는 \"즉시\", \"3일 내\", \"없음\" 등\n"
        instructions += "8. **첨부**: 파일명 (파일형식) 또는 \"없음\"\n\n"

        instructions += "**응답 필요성 판단 기준**:\n"
        instructions += "- 투표 요청이 포함된 경우\n"
        instructions += "- \"회신 요청\", \"답변 부탁\" 등의 표현\n"
        instructions += "- 마감일이 명시된 경우\n"
        instructions += "- 승인/검토 요청이 있는 경우\n\n"

        instructions += "**예시**:\n"
        instructions += "| 📥 아젠다 | 2024-01-15 09:30 | Chair (chair@eagle.org) | PL25032-01 Vote Request | 새로운 규칙 승인 요청 | 🔴 응답필요 | 1/20까지 | Proposal.pdf |\n"
        instructions += "| 📨 응답 | 2024-01-16 11:20 | → KR Member (kr@krs.co.kr) | Re: PL25032-01 Vote | 찬성 의견 회신 | ✅ 응답완료 | - | - |\n\n"

        instructions += "이메일 내용과 첨부파일을 분석하여 응답 필요성과 기한을 정확히 판단하세요.\n"

        return instructions
