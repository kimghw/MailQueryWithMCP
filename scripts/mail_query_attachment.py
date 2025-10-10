"""
통합 메일 조회 스크립트
본문과 첨부파일을 함께 처리하며, 명령줄 인자로 다양한 옵션 제공
"""
import argparse
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path
import re
import csv
import sys
sys.path.append(str(Path(__file__).parent.parent))

from infra.core.database import get_database_manager
from infra.core.logger import get_logger
from modules.mail_query import (
    MailQueryFilters,
    MailQueryOrchestrator,
    MailQueryRequest,
    PaginationOptions,
)
from modules.mail_query_without_db import AttachmentDownloader, FileConverter, EmailSaver
from modules.mail_query_without_db.onedrive_wrapper import OneDriveWrapper

logger = get_logger(__name__)


class UnifiedMailQuery:
    """통합 메일 조회 클래스"""

    def __init__(self, output_dir: str = "./attachments", enable_onedrive: bool = False):
        self.mail_query = MailQueryOrchestrator()
        self.db = get_database_manager()
        self.enable_onedrive = enable_onedrive
        self.attachment_downloader = AttachmentDownloader(output_dir, enable_onedrive=enable_onedrive)
        self.file_converter = FileConverter()
        self.email_saver = EmailSaver(output_dir, enable_onedrive=enable_onedrive)

    async def get_all_active_accounts(self) -> List[Dict[str, Any]]:
        """활성화된 모든 계정 조회"""
        query = """
            SELECT 
                user_id, 
                user_name, 
                email,
                is_active,
                status,
                last_sync_time
            FROM accounts 
            WHERE is_active = 1
            ORDER BY user_id
        """
        accounts = self.db.fetch_all(query)
        return [dict(account) for account in accounts]

    async def query_mails(
        self,
        user_id: str,
        days_back: int = 30,
        max_mails: int = 10,
        include_body: bool = False,
        download_attachments: bool = False,
        save_emails: bool = False,
        save_csv: bool = True,
        upload_to_onedrive: bool = False,
        has_attachments_filter: Optional[bool] = None,
        show_details: bool = True,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """메일 조회 (옵션 설정 가능)"""
        
        start_time = datetime.now()
        
        try:
            # 필터 설정
            if start_date and end_date:
                # 날짜 범위가 지정된 경우
                filters = MailQueryFilters(
                    date_from=start_date,
                    date_to=end_date
                )
            else:
                # days_back만 지정된 경우
                filters = MailQueryFilters(
                    date_from=datetime.now() - timedelta(days=days_back)
                )
            if has_attachments_filter is not None:
                filters.has_attachments = has_attachments_filter

            # 선택 필드 설정
            select_fields = [
                "id",
                "subject",
                "from",
                "sender",
                "receivedDateTime",
                "bodyPreview",
                "hasAttachments",
                "importance",
                "isRead",
                "webLink",
            ]
            
            if include_body:
                select_fields.append("body")
            
            if download_attachments or has_attachments_filter:
                select_fields.append("attachments")
            
            # 디버그: select_fields 확인
            print(f"DEBUG: select_fields = {select_fields}")

            # 메일 조회 요청
            request = MailQueryRequest(
                user_id=user_id,
                filters=filters,
                pagination=PaginationOptions(top=max_mails, skip=0, max_pages=1),
                select_fields=select_fields,
            )

            # 메일 조회
            async with self.mail_query as orchestrator:
                response = await orchestrator.mail_query_user_emails(request)
                # graph_client는 OneDrive 업로드나 첨부파일 다운로드시 필요
                graph_client = orchestrator.graph_client if (download_attachments or upload_to_onedrive) else None
                # OneDrive 업로드시 access_token도 필요
                access_token = None
                if upload_to_onedrive:
                    access_token = await orchestrator.token_service.get_valid_access_token(user_id)

            # 결과 처리
            result = {
                "user_id": user_id,
                "success": True,
                "total_mails": response.total_fetched,
                "execution_time_ms": response.execution_time_ms,
                "has_more": response.has_more,
                "messages": [],
                "attachments_downloaded": 0,
                "emails_saved": 0,
                "onedrive_uploads": 0,
                "error": None,
            }

            # 각 메일 처리
            blocked_senders = ['block@krs.co.kr']  # 차단할 발신자 목록
            
            for mail in response.messages:
                # 발신자 이메일 추출 및 필터링
                sender_email = None
                if mail.from_address and isinstance(mail.from_address, dict):
                    sender_email = mail.from_address.get("emailAddress", {}).get("address", "")
                
                # 차단된 발신자인 경우 스킵
                if sender_email and sender_email.lower() in [s.lower() for s in blocked_senders]:
                    if show_details:
                        print(f"\n  🚫 차단된 발신자: {sender_email} - 메일 '{mail.subject}' 스킵")
                    continue
                
                mail_info = self._process_mail_info(mail, include_body, show_details)
                
                # 이메일 내용 저장
                if save_emails:
                    if show_details:
                        print(f"\n  💾 메일 '{mail.subject}' 저장 중...")
                    
                    # 메일 데이터를 딕셔너리로 변환
                    mail_dict = mail.model_dump() if hasattr(mail, 'model_dump') else mail.__dict__
                    
                    # 필드 이름 매핑 (Graph API -> email_saver 형식)
                    if 'receivedDateTime' in mail_dict:
                        mail_dict['received_date_time'] = mail_dict.get('receivedDateTime')
                    if 'from' in mail_dict:
                        mail_dict['from_address'] = mail_dict.get('from')
                    if 'toRecipients' in mail_dict:
                        mail_dict['to_recipients'] = mail_dict.get('toRecipients')
                    if 'isRead' in mail_dict:
                        mail_dict['is_read'] = mail_dict.get('isRead')
                    if 'hasAttachments' in mail_dict:
                        mail_dict['has_attachments'] = mail_dict.get('hasAttachments')
                    if 'bodyPreview' in mail_dict:
                        mail_dict['body_preview'] = mail_dict.get('bodyPreview')
                    if 'webLink' in mail_dict:
                        mail_dict['web_link'] = mail_dict.get('webLink')
                    
                    try:
                        # 서드파티 업로드는 비활성화
                        saved_result = await self.email_saver.save_email_as_text(
                            mail_dict,
                            user_id,
                            include_headers=True,
                            save_html=include_body,
                            upload_to_onedrive=False,  # 임시 비활성화
                            graph_client=None
                        )
                        mail_info["saved_path"] = str(saved_result["text_file"])
                        result["emails_saved"] += 1
                        
                        if show_details:
                            print(f"    ✅ 저장됨: {saved_result['text_file']}")
                        
                        # OneDrive 업로드 (wrapper 사용)
                        if upload_to_onedrive and access_token:
                            async with OneDriveWrapper(access_token) as wrapper:
                                # 날짜와 발신자 정보 추출
                                email_date = mail.received_date_time
                                sender_email = None
                                if mail.from_address and isinstance(mail.from_address, dict):
                                    sender_email = mail.from_address.get("emailAddress", {}).get("address", "unknown")
                                
                                # 폴더명 생성
                                date_str = email_date.strftime("%Y%m%d")
                                safe_sender = self._sanitize_for_path(sender_email)
                                safe_subject = self._sanitize_for_path(mail.subject or "NoSubject")[:50]
                                
                                folder_name = f"{safe_subject}_{date_str}_{safe_sender}"
                                folder_path = f"/EmailAttachments/{user_id}/{folder_name}"
                                
                                # 폴더 생성
                                await wrapper.create_folder(f"/EmailAttachments/{user_id}")
                                await wrapper.create_folder(folder_path)
                                
                                # 파일 업로드
                                onedrive_path = f"{folder_path}/email_content.txt"
                                upload_result = await wrapper.upload_small_file(
                                    saved_result["text_file"],
                                    onedrive_path
                                )
                                
                                if upload_result:
                                    mail_info["onedrive_url"] = upload_result.get("webUrl")
                                    result["onedrive_uploads"] += 1
                                    if show_details:
                                        print(f"    ☁️  OneDrive: {onedrive_path}")
                                        
                    except Exception as e:
                        logger.error(f"메일 저장 실패: {str(e)}")
                        if show_details:
                            print(f"    ❌ 저장 실패: {str(e)}")
                
                # 첨부파일 다운로드
                if download_attachments and mail.has_attachments:
                    if show_details:
                        print(f"\n  📎 메일 '{mail.subject}'의 첨부파일 처리 중...")
                    
                    # 첨부파일 데이터 확인
                    if not hasattr(mail, 'attachments') or not mail.attachments:
                        print(f"    ⚠️  첨부파일 데이터가 없습니다.")
                        print(f"    has_attachments: {mail.has_attachments}")
                        print(f"    attachments 속성 존재: {hasattr(mail, 'attachments')}")
                        if hasattr(mail, 'attachments'):
                            print(f"    attachments 내용: {mail.attachments}")
                        continue
                    
                    # 메일 정보 추출 (폴더 구조용)
                    email_date = mail.received_date_time
                    sender_email = None
                    if mail.from_address and isinstance(mail.from_address, dict):
                        sender_email = mail.from_address.get("emailAddress", {}).get("address")
                    
                    for attachment in mail.attachments:
                        attachment_info = await self._process_attachment(
                            graph_client, 
                            mail.id, 
                            attachment, 
                            user_id,
                            mail.subject,  # 메일 제목 추가
                            email_date,    # 메일 날짜 추가
                            sender_email,  # 발신자 이메일 추가
                            False,  # OneDrive 업로드는 wrapper로 처리
                            show_details,
                            None
                        )
                        if attachment_info:
                            mail_info["attachments"].append(attachment_info)
                            result["attachments_downloaded"] += 1
                            
                            # OneDrive 업로드 (wrapper 사용)
                            if upload_to_onedrive and access_token and attachment_info.get("file_path"):
                                try:
                                    async with OneDriveWrapper(access_token) as wrapper:
                                        # 폴더명 생성
                                        date_str = email_date.strftime("%Y%m%d")
                                        safe_sender = self._sanitize_for_path(sender_email)
                                        safe_subject = self._sanitize_for_path(mail.subject or "NoSubject")[:50]
                                        
                                        folder_name = f"{safe_subject}_{date_str}_{safe_sender}"
                                        folder_path = f"/EmailAttachments/{user_id}/{folder_name}"
                                        
                                        # 폴더 생성
                                        await wrapper.create_folder(f"/EmailAttachments/{user_id}")
                                        await wrapper.create_folder(folder_path)
                                        
                                        # 파일 업로드
                                        file_path = Path(attachment_info["file_path"])
                                        onedrive_path = f"{folder_path}/{file_path.name}"
                                        upload_result = await wrapper.upload_small_file(
                                            file_path,
                                            onedrive_path
                                        )
                                        
                                        if upload_result:
                                            attachment_info["onedrive_url"] = upload_result.get("webUrl")
                                            attachment_info["onedrive_path"] = onedrive_path
                                            result["onedrive_uploads"] += 1
                                            if show_details:
                                                print(f"      ☁️  OneDrive: {onedrive_path}")
                                except Exception as e:
                                    logger.error(f"OneDrive upload failed for attachment: {str(e)}")

                result["messages"].append(mail_info)

            # CSV로 메일 메타데이터 저장
            if save_csv and result["messages"]:
                try:
                    print(f"\n📊 CSV 저장할 메일 수: {len(result['messages'])} 개")
                    csv_file = self.save_emails_to_csv(result["messages"], user_id)
                    result["csv_file"] = str(csv_file)
                    if show_details:
                        print(f"📊 메일 메타데이터 CSV 저장 완료: {csv_file}")
                except Exception as e:
                    logger.error(f"CSV 저장 실패: {str(e)}")
                    print(f"❌ CSV 저장 중 오류 발생: {str(e)}")

            return result

        except Exception as e:
            logger.error(f"계정 {user_id} 메일 조회 실패: {str(e)}")
            return {
                "user_id": user_id,
                "success": False,
                "total_mails": 0,
                "execution_time_ms": int(
                    (datetime.now() - start_time).total_seconds() * 1000
                ),
                "error": str(e),
            }

    def _process_mail_info(self, mail, include_body: bool, show_details: bool) -> Dict[str, Any]:
        """메일 정보 처리"""
        sender = "Unknown"
        sender_email = "unknown@email.com"
        if mail.from_address and isinstance(mail.from_address, dict):
            email_addr = mail.from_address.get("emailAddress", {})
            sender_email = email_addr.get("address", "unknown@email.com")
            sender = sender_email
            sender_name = email_addr.get("name", "")
            if sender_name and show_details:
                sender = f"{sender_name} <{sender_email}>"

        mail_info = {
            "id": mail.id,
            "subject": mail.subject,
            "sender": sender,
            "sender_email": sender_email,
            "received_date": mail.received_date_time.strftime("%Y-%m-%d %H:%M"),
            "received_date_time": mail.received_date_time,  # datetime 객체도 추가
            "has_attachments": mail.has_attachments,
            "is_read": mail.is_read,
            "importance": mail.importance,
            "attachments": []
        }

        # 본문 처리
        if include_body and mail.body:
            content_type = mail.body.get("contentType", "text")
            content = mail.body.get("content", "")
            
            if content_type == "html":
                # HTML 태그 제거
                text_content = re.sub('<[^<]+?>', '', content)
                text_content = text_content.replace('&nbsp;', ' ')
                text_content = text_content.replace('&lt;', '<')
                text_content = text_content.replace('&gt;', '>')
                text_content = text_content.replace('&amp;', '&')
                mail_info["body"] = text_content
            else:
                mail_info["body"] = content
        elif mail.body_preview:
            mail_info["body_preview"] = mail.body_preview

        return mail_info

    async def _process_attachment(
        self, 
        graph_client, 
        message_id: str, 
        attachment: Dict[str, Any], 
        user_id: str,
        email_subject: Optional[str] = None,
        email_date: Optional[Any] = None,
        sender_email: Optional[str] = None,
        upload_to_onedrive: bool = False,
        show_details: bool = True,
        access_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """첨부파일 다운로드 및 텍스트 변환"""
        try:
            attachment_name = attachment.get('name', 'unknown')
            attachment_size = attachment.get('size', 0)
            
            print(f"    - {attachment_name} ({attachment_size:,} bytes)")
            print(f"      attachment data: {attachment}")  # 디버그용
            
            # 첨부파일 다운로드 및 저장
            if show_details:
                print(f"      📥 다운로드 중...")
            
            result = await self.attachment_downloader.download_and_save(
                graph_client,
                message_id,
                attachment,
                user_id,
                upload_to_onedrive=upload_to_onedrive,
                email_date=email_date,
                sender_email=sender_email,
                email_subject=email_subject,
                access_token=access_token
            )
            
            if result and result.get("file_path"):
                file_path = Path(result["file_path"])
                print(f"      ✅ 저장됨: {file_path}")
                
                # 지원되는 형식인지 확인
                if self.file_converter.is_supported(file_path):
                    # 텍스트로 변환
                    text_content = self.file_converter.convert_to_text(file_path)
                    
                    # 텍스트 파일로 저장
                    text_file_path = self.file_converter.save_as_text(
                        file_path,
                        text_content,
                        attachment_name
                    )
                    
                    print(f"      📄 텍스트 변환 완료: {text_file_path}")
                    
                    att_info = {
                        "name": attachment_name,
                        "size": attachment_size,
                        "file_path": str(file_path),
                        "text_path": str(text_file_path),
                        "text_preview": text_content[:200] + "..." if len(text_content) > 200 else text_content
                    }
                    
                    # OneDrive 업로드 정보 추가
                    if upload_to_onedrive and result.get("onedrive"):
                        att_info["onedrive_url"] = result["onedrive"].get("webUrl")
                        att_info["onedrive_path"] = result["onedrive"].get("path")
                        if show_details:
                            print(f"      ☁️  OneDrive: {result['onedrive']['path']}")
                    
                    return att_info
                else:
                    print(f"      ⚠️  지원하지 않는 파일 형식: {file_path.suffix}")
                    return {
                        "name": attachment_name,
                        "size": attachment_size,
                        "file_path": str(file_path),
                        "text_path": None,
                        "text_preview": f"Unsupported format: {file_path.suffix}"
                    }
            
        except Exception as e:
            logger.error(f"첨부파일 처리 실패: {str(e)}")
            return None
    
    def _sanitize_for_path(self, text: str) -> str:
        """경로에 안전한 문자열로 변환"""
        if not text:
            return "unknown"
            
        # 이메일에서 도메인 제거
        if '@' in text:
            text = text.split('@')[0]
        
        # 한글 처리를 위해 특수문자만 제거
        # 위험한 문자들
        dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\n', '\r', '\t']
        for char in dangerous_chars:
            text = text.replace(char, '_')
        
        # 연속된 공백을 하나로
        text = ' '.join(text.split())
        
        # 공백을 언더스코어로
        text = text.replace(' ', '_')
        
        # 연속된 언더스코어 정리
        while '__' in text:
            text = text.replace('__', '_')
        
        # 양 끝 언더스코어 제거
        text = text.strip('_')
        
        return text or "unknown"

    def save_emails_to_csv(self, emails: List[Dict[str, Any]], user_id: str) -> Path:
        """이메일 메타데이터를 CSV 파일로 저장"""
        # CSV 파일 경로 설정
        csv_dir = Path(self.attachment_downloader.output_dir) / user_id
        csv_dir.mkdir(parents=True, exist_ok=True)
        
        # 파일명에 현재 시간 포함
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = csv_dir / f"email_metadata_{timestamp}.csv"
        
        # CSV 작성
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            # UTF-8 BOM을 추가하여 한글이 Excel에서 깨지지 않도록 함
            fieldnames = [
                '번호',
                '제목',
                '발신자',
                '발신자_이메일',
                '수신일시',
                '읽음상태',
                '중요도',
                '첨부파일',
                '첨부파일_개수',
                '첨부파일_목록',
                '본문_미리보기',
                '폴더명',
                'message_id'
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for idx, email in enumerate(emails, 1):
                # 첨부파일 정보 처리
                attachment_names = []
                attachment_count = 0
                if email.get('attachments'):
                    attachment_names = [att['name'] for att in email['attachments']]
                    attachment_count = len(attachment_names)
                
                # 폴더명 생성 (실제 저장되는 폴더명과 동일하게)
                safe_subject = self.attachment_downloader._sanitize_filename(email.get('subject', 'NoSubject')[:50])
                received_datetime = email.get('received_date_time', datetime.now())
                date_str = received_datetime.strftime('%Y%m%d') if isinstance(received_datetime, datetime) else datetime.now().strftime('%Y%m%d')
                safe_sender = self.attachment_downloader._sanitize_filename(email.get('sender_email', 'unknown').split('@')[0][:30])
                folder_name = f"{safe_subject}_{date_str}_{safe_sender}"
                
                row = {
                    '번호': idx,
                    '제목': email.get('subject', ''),
                    '발신자': email.get('sender', ''),
                    '발신자_이메일': email.get('sender_email', ''),
                    '수신일시': email.get('received_date', ''),
                    '읽음상태': '읽음' if email.get('is_read', False) else '안읽음',
                    '중요도': email.get('importance', 'normal'),
                    '첨부파일': '있음' if email.get('has_attachments', False) else '없음',
                    '첨부파일_개수': attachment_count,
                    '첨부파일_목록': '; '.join(attachment_names) if attachment_names else '',
                    '본문_미리보기': (email.get('body_preview', '') or '')[:100].replace('\n', ' ').replace('\r', ' '),
                    '폴더명': folder_name,
                    'message_id': email.get('id', '')
                }
                
                writer.writerow(row)
        
        logger.info(f"이메일 메타데이터 CSV 저장 완료: {csv_file}")
        return csv_file
    
    def print_mail_details(self, mail_info: Dict[str, Any], index: int, show_body: bool = False):
        """메일 상세 정보 출력"""
        print(f"\n[{index}] {mail_info['subject']}")
        print(f"    발신자: {mail_info['sender']}")
        print(f"    수신일: {mail_info['received_date']}")
        print(f"    읽음: {'✓' if mail_info['is_read'] else '✗'}")
        print(f"    첨부: {'📎' if mail_info['has_attachments'] else '-'}")
        
        if show_body:
            if 'body' in mail_info:
                body_preview = mail_info['body'][:500]
                print(f"    본문: {body_preview}...")
            elif 'body_preview' in mail_info:
                print(f"    미리보기: {mail_info['body_preview'][:100]}...")
        
        if mail_info.get('attachments'):
            print("    첨부파일:")
            for att in mail_info['attachments']:
                print(f"      - {att['name']} ({att['size']:,} bytes)")

    async def run_query(
        self,
        user_ids: Optional[List[str]] = None,
        days_back: int = 30,
        max_mails: int = 10,
        include_body: bool = False,
        download_attachments: bool = False,
        save_emails: bool = False,
        save_csv: bool = True,
        upload_to_onedrive: bool = False,
        has_attachments_filter: Optional[bool] = None,
        show_summary_only: bool = False,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ):
        """메일 조회 실행"""
        
        print("📧 메일 조회 시작")
        print("=" * 80)
        if start_date and end_date:
            print(f"설정: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}, 계정당 최대 {max_mails}개 메일")
        else:
            print(f"설정: 최근 {days_back}일, 계정당 최대 {max_mails}개 메일")
        print(f"본문 포함: {'예' if include_body else '아니오'}")
        print(f"첨부파일 다운로드: {'예' if download_attachments else '아니오'}")
        print(f"메일 저장: {'예' if save_emails else '아니오'}")
        print(f"CSV 메타데이터 저장: {'예' if save_csv else '아니오'}")
        if upload_to_onedrive:
            print(f"OneDrive 업로드: 예")
        if has_attachments_filter is not None:
            print(f"첨부파일 필터: {'있는 메일만' if has_attachments_filter else '없는 메일만'}")
        print("=" * 80)

        # 계정 목록 가져오기
        if user_ids:
            accounts = [{"user_id": uid, "user_name": uid} for uid in user_ids]
        else:
            accounts = await self.get_all_active_accounts()
            print(f"\n📋 활성 계정 수: {len(accounts)}개")

        # 각 계정별 메일 조회
        all_results = []
        total_mails = 0
        total_attachments = 0
        total_emails_saved = 0
        total_onedrive_uploads = 0
        success_count = 0

        for i, account in enumerate(accounts, 1):
            user_id = account["user_id"]
            user_name = account.get("user_name", user_id)
            
            if not show_summary_only:
                print(f"\n[{i}/{len(accounts)}] {user_id} ({user_name}) 조회 중...")

            result = await self.query_mails(
                user_id=user_id,
                days_back=days_back,
                max_mails=max_mails,
                include_body=include_body,
                download_attachments=download_attachments,
                save_emails=save_emails,
                save_csv=save_csv,
                upload_to_onedrive=upload_to_onedrive,
                has_attachments_filter=has_attachments_filter,
                show_details=not show_summary_only,
                start_date=start_date,
                end_date=end_date
            )

            all_results.append(result)

            if result["success"]:
                success_count += 1
                total_mails += result["total_mails"]
                total_attachments += result["attachments_downloaded"]
                total_emails_saved += result.get("emails_saved", 0)
                total_onedrive_uploads += result.get("onedrive_uploads", 0)

                if not show_summary_only:
                    print(f"  ✅ 성공: {result['total_mails']}개 메일")
                    
                    # 메일 상세 출력
                    for j, msg in enumerate(result["messages"], 1):
                        self.print_mail_details(msg, j, show_body=include_body)
            else:
                if not show_summary_only:
                    print(f"  ❌ 실패: {result['error']}")

        # 전체 결과 요약
        print("\n" + "=" * 80)
        print("📊 전체 결과 요약")
        print("=" * 80)
        print(f"\n✅ 성공: {success_count}/{len(accounts)} 계정")
        print(f"📧 총 메일 수: {total_mails}개")
        if save_emails:
            print(f"💾 저장된 메일: {total_emails_saved}개")
        if download_attachments:
            print(f"📎 다운로드된 첨부파일: {total_attachments}개")
        if upload_to_onedrive and total_onedrive_uploads > 0:
            print(f"☁️  OneDrive 업로드: {total_onedrive_uploads}개")
        if save_emails or download_attachments:
            print(f"📁 로컬 저장 위치: {self.attachment_downloader.output_dir}")

        print(f"\n✅ 조회 완료!")
        print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return {
            "total_accounts": len(accounts),
            "success_count": success_count,
            "total_mails": total_mails,
            "total_attachments": total_attachments,
            "total_emails_saved": total_emails_saved,
            "total_onedrive_uploads": total_onedrive_uploads,
            "results": all_results,
        }

    async def close(self):
        """리소스 정리"""
        await self.mail_query.close()


async def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="통합 메일 조회 도구")
    
    # 계정 옵션
    parser.add_argument(
        "-u", "--user",
        nargs="+",
        help="조회할 사용자 ID - 이메일의 @ 앞부분만 입력 (예: kimghw@krs.co.kr → kimghw)"
    )
    
    # 조회 옵션
    parser.add_argument(
        "-d", "--days",
        type=int,
        default=30,
        help="조회할 기간 (일 단위, 기본값: 30)"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="시작 날짜 (YYYY-MM-DD 형식)"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="종료 날짜 (YYYY-MM-DD 형식)"
    )
    parser.add_argument(
        "-n", "--number",
        type=int,
        default=10,
        help="계정당 최대 메일 수 (기본값: 10)"
    )
    
    # 내용 옵션
    parser.add_argument(
        "-b", "--body",
        action="store_true",
        help="메일 본문 포함"
    )
    parser.add_argument(
        "-a", "--attachments",
        action="store_true",
        help="첨부파일 다운로드"
    )
    parser.add_argument(
        "--has-attachments",
        action="store_true",
        help="첨부파일이 있는 메일만 조회"
    )
    parser.add_argument(
        "--no-attachments",
        action="store_true",
        help="첨부파일이 없는 메일만 조회"
    )
    parser.add_argument(
        "-e", "--save-emails",
        action="store_true",
        help="메일 내용을 텍스트 파일로 저장"
    )
    parser.add_argument(
        "--onedrive",
        action="store_true",
        help="OneDrive에 파일 업로드 (메일 및 첨부파일)"
    )
    
    # 출력 옵션
    parser.add_argument(
        "-s", "--summary",
        action="store_true",
        help="요약만 표시 (상세 내용 생략)"
    )
    parser.add_argument(
        "-o", "--output",
        default="./attachments",
        help="첨부파일 저장 디렉토리 (기본값: ./attachments)"
    )
    
    args = parser.parse_args()
    
    # 날짜 범위 계산 - 우선순위: 날짜 범위 > days_back
    days_back = args.days
    start_date = None
    end_date = None
    
    # 날짜 파라미터가 제공된 경우
    if args.start_date or args.end_date:
        try:
            # 시작날짜와 종료날짜 모두 지정된 경우
            if args.start_date and args.end_date:
                start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
                end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
                
                if start_date > end_date:
                    print("❌ 오류: 시작 날짜가 종료 날짜보다 늦습니다.")
                    return
                
                # days_back은 무시됨
                days_back = (end_date - start_date).days + 1
            
            # 시작날짜만 지정된 경우
            elif args.start_date:
                start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
                end_date = datetime.now()
                days_back = (end_date - start_date).days + 1
            
            # 종료날짜만 지정된 경우
            elif args.end_date:
                end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
                start_date = end_date - timedelta(days=days_back - 1)
                
        except ValueError as e:
            print(f"❌ 오류: 잘못된 날짜 형식입니다. YYYY-MM-DD 형식을 사용하세요. {e}")
            return
    
    # 첨부파일 필터 설정
    has_attachments_filter = None
    if args.has_attachments:
        has_attachments_filter = True
    elif args.no_attachments:
        has_attachments_filter = False
    
    # 메일 조회 실행
    query = UnifiedMailQuery(output_dir=args.output, enable_onedrive=args.onedrive)
    
    try:
        await query.run_query(
            user_ids=args.user,
            days_back=days_back,
            max_mails=args.number,
            include_body=args.body,
            download_attachments=args.attachments,
            save_emails=args.save_emails,
            upload_to_onedrive=args.onedrive,
            has_attachments_filter=has_attachments_filter,
            show_summary_only=args.summary,
            start_date=start_date,
            end_date=end_date
        )
    finally:
        await query.close()


if __name__ == "__main__":
    # 도움말 출력
    print("\n사용 예시:")
    print("  python -m scripts.mail_query_attachment                     # 기본 조회")
    print("  python -m scripts.mail_query_attachment -u kimghw           # 특정 사용자")
    print("  python -m scripts.mail_query_attachment -d 7 -n 20         # 최근 7일, 20개")
    print("  python -m scripts.mail_query_attachment -b                  # 본문 포함")
    print("  python -m scripts.mail_query_attachment -a                  # 첨부파일 다운로드")
    print("  python -m scripts.mail_query_attachment -e                  # 메일을 텍스트로 저장")
    print("  python -m scripts.mail_query_attachment --onedrive          # OneDrive에 업로드")
    print("  python -m scripts.mail_query_attachment --has-attachments   # 첨부파일 있는 메일만")
    print("  python -m scripts.mail_query_attachment --start-date 2025-01-01 --end-date 2025-01-31  # 날짜 범위 지정")
    print("  python -m scripts.mail_query_attachment -u kimghw -b -a -e --onedrive # 모든 옵션")
    print()
    
    asyncio.run(main())