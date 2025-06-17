## 2. utilities/text_cleaner.py

"""텍스트 정제 유틸리티"""

import re
from typing import Dict, Optional
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

    def prepare_mail_content(self, mail: Dict) -> str:
        """
        메일 내용 준비 - 제목과 본문을 합쳐서 정제
        
        Args:
            mail: 메일 딕셔너리
            
        Returns:
            정제된 전체 내용
        """
        # 본문 내용 추출 우선순위: body.content > bodyPreview > subject
        body_content = ""
        
        # 1. body.content 확인
        body = mail.get('body', {})
        if isinstance(body, dict) and body.get('content'):
            body_content = body['content']
        
        # 2. bodyPreview 확인
        elif mail.get('bodyPreview'):
            body_content = mail['bodyPreview']
        
        # 3. subject만 있는 경우
        subject = mail.get('subject', '')
        if not body_content and subject:
            body_content = subject
        
        # 텍스트 정제
        clean_content = self.clean_text(body_content)
        
        # 제목도 포함 (중요한 정보가 있을 수 있음)
        if subject:
            clean_subject = self.clean_text(subject)
            if clean_subject and clean_subject not in clean_content:
                clean_content = f"{clean_subject} {clean_content}"
        
        return clean_content

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


