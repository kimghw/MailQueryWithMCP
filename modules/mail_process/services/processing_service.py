"""처리 서비스 - 메일 정제 및 키워드 추출 (배치 처리 지원)"""

from typing import List, Dict, Optional
from infra.core import get_logger, get_config
from ..utilities import TextCleaner, MailParser
from .keyword_service import MailKeywordService

logger = get_logger(__name__)


class ProcessingService:
    """메일 처리 서비스 (배치 키워드 추출)"""
    
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
        
        # 배치 처리 활성화 여부
        self.batch_keyword_extraction = self.config.get_setting(
            "ENABLE_BATCH_KEYWORD_EXTRACTION", "true"
        ).lower() == "true"
        
        self.logger.info(f"처리 서비스 초기화: batch_keyword_extraction={self.batch_keyword_extraction}")
    
    async def process_mails(self, mails: List[Dict]) -> List[Dict]:
        """메일 정제 및 키워드 추출 (배치 처리)"""
        if not mails:
            return []
        
        process_stats = {
            'total': len(mails),
            'processed': 0,
            'too_short': 0,
            'keyword_extracted': 0,
            'processing_errors': 0
        }
        
        self.logger.info(f"메일 처리 시작: {len(mails)}개")
        
        # 배치 처리 활성화된 경우
        if self.batch_keyword_extraction:
            processed_mails = await self._process_mails_batch(mails, process_stats)
        else:
            # 기존 개별 처리 방식
            processed_mails = await self._process_mails_individual(mails, process_stats)
        
        self._log_process_summary(process_stats)
        return processed_mails
    
    async def _process_mails_batch(self, mails: List[Dict], stats: Dict) -> List[Dict]:
        """배치 방식으로 메일 처리"""
        # 1단계: 모든 메일 정제 및 준비
        prepared_mails = []
        
        for i, mail in enumerate(mails):
            try:
                prepared_mail = self._prepare_mail_for_processing(mail)
                if prepared_mail:
                    prepared_mails.append(prepared_mail)
                else:
                    stats['too_short'] += 1
            except Exception as e:
                stats['processing_errors'] += 1
                self.logger.error(f"메일 준비 중 오류: {str(e)}")
                continue
        
        # 2단계: 배치 키워드 추출을 위한 데이터 준비
        mail_data_for_keywords = []
        for prepared_mail in prepared_mails:
            mail_data_for_keywords.append({
                'content': prepared_mail['_processed']['clean_content'],
                'subject': prepared_mail['_processed']['refined_mail'].get('subject', ''),
                'sent_time': prepared_mail['_processed']['sent_time']
            })
        
        # 3단계: 키워드 배치 추출
        if mail_data_for_keywords:
            async with self.keyword_service:
                try:
                    all_keywords = await self.keyword_service.extract_keywords_batch(mail_data_for_keywords)
                    
                    # 4단계: 결과 병합
                    for i, prepared_mail in enumerate(prepared_mails):
                        if i < len(all_keywords):
                            keywords = all_keywords[i]
                            prepared_mail['_processed']['keywords'] = keywords
                            if keywords:
                                stats['keyword_extracted'] += 1
                        else:
                            prepared_mail['_processed']['keywords'] = []
                        
                        stats['processed'] += 1
                        
                except Exception as e:
                    self.logger.error(f"배치 키워드 추출 실패: {str(e)}")
                    # 실패 시 모든 메일에 빈 키워드 할당
                    for prepared_mail in prepared_mails:
                        prepared_mail['_processed']['keywords'] = []
                        stats['processed'] += 1
        
        return prepared_mails
    
    async def _process_mails_individual(self, mails: List[Dict], stats: Dict) -> List[Dict]:
        """개별 방식으로 메일 처리 (기존 방식)"""
        processed_mails = []
        
        async with self.keyword_service:
            for mail in mails:
                try:
                    processed_mail = await self._process_single_mail(mail)
                    if processed_mail:
                        processed_mails.append(processed_mail)
                        stats['processed'] += 1
                        
                        if processed_mail.get('_processed', {}).get('keywords'):
                            stats['keyword_extracted'] += 1
                    else:
                        stats['too_short'] += 1
                        
                except Exception as e:
                    stats['processing_errors'] += 1
                    self.logger.error(f"메일 처리 중 오류: {str(e)}", exc_info=True)
                    continue
        
        return processed_mails
    
    def _prepare_mail_for_processing(self, mail: Dict) -> Optional[Dict]:
        """메일 처리 준비 (키워드 추출 제외)"""
        # 메일 정보 추출
        mail_id = self.mail_parser.extract_mail_id(mail)
        sent_time = self.mail_parser.extract_sent_time(mail)
        
        # 발신자 정보 추출 추가
        sender_address = self.mail_parser.extract_sender_address(mail)
        sender_name = self.mail_parser.extract_sender_name(mail)
        
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
        
        # 처리된 메일 데이터 구성
        mail['_processed'] = {
            'mail_id': mail_id,
            'sent_time': sent_time,
            'sender_address': sender_address,
            'sender_name': sender_name,
            'clean_content': clean_content,
            'refined_mail': refined_mail,
            'keywords': []  # 나중에 채워질 예정
        }
        
        # 최상위 레벨에도 저장 (호환성을 위해)
        mail['sender_address'] = sender_address
        mail['sender_name'] = sender_name
        
        return mail
    
    async def _process_single_mail(self, mail: Dict) -> Optional[Dict]:
        """개별 메일 처리 (기존 방식 유지)"""
        # 메일 준비
        prepared_mail = self._prepare_mail_for_processing(mail)
        if not prepared_mail:
            return None
        
        # 키워드 추출
        clean_content = prepared_mail['_processed']['clean_content']
        sent_time = prepared_mail['_processed']['sent_time']
        subject = prepared_mail['_processed']['refined_mail'].get('subject', '')
        
        keywords = await self.keyword_service.extract_keywords(
            clean_content,
            subject,
            sent_time  
        )
        prepared_mail['_processed']['keywords'] = keywords
        
        return prepared_mail
    
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
