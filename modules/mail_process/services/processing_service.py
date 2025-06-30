"""처리 서비스 - 메일 정제 및 키워드 추출"""

from typing import List, Dict, Optional
from infra.core import get_logger, get_config
from ..utilities import TextCleaner, MailParser
from .keyword_service import MailKeywordService

logger = get_logger(__name__)


class ProcessingService:
    """메일 처리 서비스"""
    
    def __init__(self):
        self.text_cleaner = TextCleaner()
        self.mail_parser = MailParser()
        self.keyword_service = MailKeywordService()
        self.config = get_config()
        self.logger = get_logger(__name__)
        
        # 설정값 로드
        self.min_content_length = int(
            self.config.get_setting("MIN_MAIL_CONTENT_LENGTH", "10")
        )
    
    async def process_mails(self, mails: List[Dict]) -> List[Dict]:
        """메일 정제 및 키워드 추출"""
        processed_mails = []
        process_stats = {
            'total': len(mails),
            'processed': 0,
            'too_short': 0,
            'keyword_extracted': 0,
            'processing_errors': 0
        }
        
        async with self.keyword_service:
            for mail in mails:
                try:
                    processed_mail = await self._process_single_mail(mail)
                    if processed_mail:
                        processed_mails.append(processed_mail)
                        process_stats['processed'] += 1
                        
                        if processed_mail.get('_processed', {}).get('keywords'):
                            process_stats['keyword_extracted'] += 1
                    else:
                        process_stats['too_short'] += 1
                        
                except Exception as e:
                    process_stats['processing_errors'] += 1
                    self.logger.error(f"메일 처리 중 오류: {str(e)}", exc_info=True)
                    continue
        
        self._log_process_summary(process_stats)
        return processed_mails
    
    async def _process_single_mail(self, mail: Dict) -> Optional[Dict]:
        """개별 메일 처리"""
        # 메일 정보 추출
        mail_id = self.mail_parser.extract_mail_id(mail)
        sent_time = self.mail_parser.extract_sent_time(mail)
        
        # 텍스트 정제
        refined_mail = self.text_cleaner.prepare_mail_content(mail)
        
        # 내용 추출 및 결합
        subject = refined_mail.get('subject', '')
        body_content = refined_mail.get('body', {}).get('content', '')
        clean_content = f"{subject} {body_content}".strip()
        
        # 내용 검증
        if self.text_cleaner.is_content_too_short(
            clean_content, 
            min_length=self.min_content_length
        ):
            self.logger.debug(f"내용 부족: {mail_id}")
            return None
        
        # 키워드 추출
        keywords = await self.keyword_service.extract_keywords(clean_content)
        
        # 처리된 메일 데이터 구성
        mail['_processed'] = {
            'mail_id': mail_id,
            'sent_time': sent_time,
            'clean_content': clean_content,
            'keywords': keywords,
            'refined_mail': refined_mail
        }
        
        return mail
    
    def _log_process_summary(self, stats: Dict):
        """처리 요약 로깅"""
        self.logger.info(
            f"처리 완료: {stats['processed']}/{stats['total']} "
            f"(내용부족={stats['too_short']}, "
            f"키워드추출={stats['keyword_extracted']}, "
            f"오류={stats['processing_errors']})"
        )
    
    async def close(self):
        """리소스 정리"""
        try:
            await self.keyword_service.close()
        except Exception as e:
            self.logger.warning(f"키워드 서비스 정리 중 오류: {str(e)}")
