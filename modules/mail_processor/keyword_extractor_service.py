"""OpenRouter를 활용한 키워드 추출 서비스"""
import re
import time
import json
import aiohttp
from collections import Counter
from typing import List, Optional

from infra.core.config import get_config
from infra.core.logger import get_logger
from .mail_processor_schema import KeywordExtractionRequest, KeywordExtractionResponse


class MailProcessorKeywordExtractorService:
    """OpenRouter를 활용한 키워드 추출 서비스"""
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)
        
        # OpenRouter 설정
        self.api_key = getattr(self.config, 'openrouter_api_key', None)
        self.model = getattr(self.config, 'openrouter_model', "openai/o3-mini")
        self.base_url = "https://openrouter.ai/api/v1"
        
    async def extract_keywords(self, text: str, max_keywords: int = 5) -> KeywordExtractionResponse:
        """메일 본문에서 키워드 추출"""
        start_time = time.time()
        
        try:
            # 텍스트 정제
            clean_text = self._clean_text(text)
            
            # 너무 짧은 텍스트는 빈 리스트 반환
            if len(clean_text.strip()) < 10:
                return KeywordExtractionResponse(
                    keywords=[],
                    method="empty_text",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            
            # OpenRouter API 호출
            if self.api_key:
                keywords = await self._call_openrouter_api(clean_text, max_keywords)
                if keywords:
                    self.logger.debug(f"키워드 추출 성공: {keywords}")
                    return KeywordExtractionResponse(
                        keywords=keywords,
                        method="openrouter",
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )
            
            # Fallback 키워드 추출
            keywords = self._fallback_keyword_extraction(clean_text, max_keywords)
            return KeywordExtractionResponse(
                keywords=keywords,
                method="fallback",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
                
        except Exception as e:
            self.logger.warning(f"키워드 추출 실패, fallback 사용: {str(e)}")
            keywords = self._fallback_keyword_extraction(text, max_keywords)
            return KeywordExtractionResponse(
                keywords=keywords,
                method="fallback_error",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
    
    async def _call_openrouter_api(self, text: str, max_keywords: int) -> List[str]:
        """OpenRouter API 호출"""
        # 텍스트 길이 제한 (2000자)
        limited_text = text[:2000] if len(text) > 2000 else text
        
        prompt = f"""다음 이메일 본문에서 가장 중요한 키워드 {max_keywords}개를 한국어로 추출해주세요.
키워드는 명사 위주로 추출하고, 콤마로 구분하여 나열해주세요. 제목에나 기본적으로 메일 번호가 숫자와 문자로 식별됩니다. 그 식별번호는 키워드에 포함되어야 합니다. 메일 내용을 보면 어떤 기관, 어떤 종류의 문서 작업, 다음 회의일정, 주요 기술 내용, 향후 작업 계획 등이 있으며 이것들도 키워드에 속합니다. 

이메일 본문: {limited_text}

형식: 키워드1(문서번호), 키워드2, 키워드3, 키워드4, 키워드5"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://iacsgraph.local",
            "X-Title": "IACSGRAPH Mail Processor"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 100,
            "temperature": 0.3,
            "top_p": 1.0
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data['choices'][0]['message']['content'].strip()
                        
                        # 키워드 파싱
                        keywords = [kw.strip() for kw in content.split(',')]
                        keywords = [kw for kw in keywords if kw and len(kw) >= 2]
                        
                        return keywords[:max_keywords]
                        
                    elif response.status == 429:
                        # Rate limit - 잠시 대기 후 fallback
                        self.logger.warning("OpenRouter API rate limit, fallback 사용")
                        return []
                        
                    else:
                        error_text = await response.text()
                        self.logger.error(f"OpenRouter API 오류: {response.status} - {error_text}")
                        return []
        except Exception as e:
            self.logger.error(f"OpenRouter API 호출 실패: {str(e)}")
            return []
    
    def _fallback_keyword_extraction(self, text: str, max_keywords: int) -> List[str]:
        """OpenRouter 실패 시 간단한 fallback 키워드 추출"""
        # 간단한 한국어 단어 추출
        clean_text = self._clean_text(text)
        
        # 한국어 단어 추출 (2글자 이상)
        korean_words = re.findall(r'[가-힣]{2,}', clean_text)
        
        # 영문 단어 추출 (3글자 이상)
        english_words = re.findall(r'[A-Za-z]{3,}', clean_text)
        
        # 숫자 포함 식별자 추출 (예: EA004, REQ-123)
        identifiers = re.findall(r'[A-Z]{2,}\d+|[A-Z]+-\d+|\d{3,}', clean_text)
        
        # 모든 단어 합치기
        all_words = korean_words + english_words + identifiers
        
        # 빈도수 기반 상위 키워드 선택
        word_counts = Counter(all_words)
        top_keywords = [word for word, count in word_counts.most_common(max_keywords)]
        
        return top_keywords
    
    def _clean_text(self, text: str) -> str:
        """텍스트 정제"""
        if not text:
            return ""
        
        # HTML 태그 제거
        clean = re.sub(r'<[^>]+>', '', text)
        
        # 과도한 공백 정리
        clean = re.sub(r'\s+', ' ', clean)
        
        # 특수문자 정리 (한글, 영문, 숫자, 기본 구두점만 유지)
        clean = re.sub(r'[^\w\s가-힣.,!?()-]', ' ', clean)
        
        return clean.strip()
