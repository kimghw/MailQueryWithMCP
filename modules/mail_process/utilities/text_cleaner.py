"""텍스트 정제 유틸리티"""

import re
from typing import Dict, Optional, Tuple
from infra.core.logger import get_logger


class TextCleaner:
    """텍스트 정제 유틸리티 - 순수 함수 기반"""

    def __init__(self):
        self.logger = get_logger(__name__)

    def clean_text(self, text: str) -> str:
        """
        텍스트 정제 (순수 함수)
        
        Args:
            text: 원본 텍스트
            
        Returns:
            정제된 텍스트
        """
        if not text:
            return ""

        # 1. 모든 종류의 줄바꿈을 일반 줄바꿈으로 통일
        clean = text.replace("\r\n", "\n").replace("\r", "\n")
        
        # 2. HTML 태그 제거
        clean = re.sub(r'<[^>]+>', '', clean)
        
        # 3. 이메일 주소를 공백으로 변환
        clean = re.sub(r'<[^>]+@[^>]+>', ' ', clean)
        clean = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', ' ', clean)
        
        # 4. URL 제거
        clean = re.sub(r'https?://[^\s]+', ' ', clean)
        clean = re.sub(r'www\.[^\s]+', ' ', clean)
        
        # 5. 연속된 줄바꿈을 하나의 공백으로 변환
        clean = re.sub(r"\n+", " ", clean)
        
        # 6. 탭 문자를 공백으로 변환
        clean = clean.replace('\t', ' ')
        
        # 7. 특수문자 정리 (한글, 영문, 숫자, 기본 구두점만 유지)
        clean = re.sub(r'[^\w\s가-힣.,!?():;-]', ' ', clean)
        
        # 8. 불필요한 구분선 제거
        clean = re.sub(r'[-=]{5,}', ' ', clean)
        
        # 9. 의미없는 단일 문자 제거 (단, 숫자는 유지)
        clean = re.sub(r'\b[a-zA-Z]\b', '', clean)
        
        # 10. 과도한 공백 정리
        clean = re.sub(r'\s+', ' ', clean)
        
        # 11. 양쪽 공백 제거
        clean = clean.strip()
        
        return clean

    def prepare_mail_content(self, mail: Dict) -> Tuple[Dict, str]:
        """
        메일 내용 준비 - 원본 메일을 정제하여 새로운 메일 객체와 전체 정제 내용 반환
        
        Args:
            mail: 원본 메일 딕셔너리
            
        Returns:
            (정제된 메일 딕셔너리, 키워드 추출용 전체 정제 내용)
        """
        # 원본 메일 복사
        refined_mail = mail.copy()
        
        # 1. subject 정제
        if mail.get('subject'):
            refined_mail['subject'] = self.clean_text(mail['subject'])
        
        # 2. bodyPreview 정제
        if mail.get('bodyPreview'):
            refined_mail['bodyPreview'] = self.clean_text(mail['bodyPreview'])
        elif mail.get('body_preview'):
            refined_mail['body_preview'] = self.clean_text(mail['body_preview'])
        
        # 3. body.content 정제
        if mail.get('body') and isinstance(mail['body'], dict):
            refined_body = mail['body'].copy()
            if refined_body.get('content'):
                refined_body['content'] = self.clean_text(refined_body['content'])
            refined_mail['body'] = refined_body
        
        # 4. 키워드 추출용 전체 내용 생성
        # 본문 내용 추출 우선순위: body.content > bodyPreview > subject
        content_for_keywords = ""
        
        # body.content 확인
        if refined_mail.get('body') and isinstance(refined_mail['body'], dict):
            content_for_keywords = refined_mail['body'].get('content', '')
        
        # bodyPreview 확인
        if not content_for_keywords:
            content_for_keywords = refined_mail.get('bodyPreview', refined_mail.get('body_preview', ''))
        
        # subject도 포함 (중요한 정보가 있을 수 있음)
        subject = refined_mail.get('subject', '')
        if subject and subject not in content_for_keywords:
            content_for_keywords = f"{subject} {content_for_keywords}"
        
        return refined_mail, content_for_keywords

    def is_content_too_short(self, content: str, min_length: int = 10) -> bool:
        """
        내용이 너무 짧은지 확인
        
        Args:
            content: 확인할 내용
            min_length: 최소 길이 (기본값: 10)
            
        Returns:
            너무 짧으면 True
        """
        return len(content.strip()) < min_length