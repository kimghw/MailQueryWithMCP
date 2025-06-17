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
                    model=self.model,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    token_info={}
                )
            
            # OpenRouter API 호출
            if self.api_key:
                keywords, token_info = await self._call_openrouter_api(clean_text, max_keywords)
                if keywords:
                    self.logger.debug(f"키워드 추출 성공: {keywords}")
                    return KeywordExtractionResponse(
                        keywords=keywords,
                        method="openrouter",
                        model=self.model,
                        execution_time_ms=int((time.time() - start_time) * 1000),
                        token_info=token_info
                    )
            
            # Fallback 키워드 추출
            keywords = self._fallback_keyword_extraction(clean_text, max_keywords)
            return KeywordExtractionResponse(
                keywords=keywords,
                method="fallback",
                model="rule_based",
                execution_time_ms=int((time.time() - start_time) * 1000),
                token_info={}
            )
                
        except Exception as e:
            self.logger.warning(f"키워드 추출 실패, fallback 사용: {str(e)}")
            keywords = self._fallback_keyword_extraction(text, max_keywords)
            return KeywordExtractionResponse(
                keywords=keywords,
                method="fallback_error",
                model="rule_based",
                execution_time_ms=int((time.time() - start_time) * 1000),
                token_info={}
            )
    
    async def _call_openrouter_api(self, text: str, max_keywords: int) -> tuple[List[str], dict]:
        """OpenRouter API 호출"""
        
        # API 키 확인
        if not self.api_key:
            self.logger.warning("OpenRouter API 키가 설정되지 않음")
            return [], {}
        
        # 텍스트 길이 제한 (2000자)
        limited_text = text[:2000] if len(text) > 2000 else text
        
        prompt = f"""다음 이메일 본문에서 가장 중요한 키워드 {max_keywords}개를 추출해주세요.
키워드는 콤마로 구분하여 나열해주세요. 번호나 기호 없이 키워드만 작성해주세요.

이메일 본문: {limited_text}

키워드:"""  # 응답 형식 단순화

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://iacsgraph.local",
            "X-Title": "IACSGRAPH Mail Processor"
        }
        
        payload = {
            "model": self.model,  # 설정에서 가져온 모델명 사용
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that extracts keywords from emails."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 100,
            "temperature": 0.3,
            "top_p": 1.0
        }
        
        # 토큰 정보 초기화
        token_info = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"OpenRouter API 오류 ({response.status}): {error_text}")
                        return [], token_info
                    
                    data = await response.json()
                    
                    # 토큰 사용량 정보 추출
                    if 'usage' in data:
                        usage = data['usage']
                        token_info.update({
                            "prompt_tokens": usage.get('prompt_tokens', 0),
                            "completion_tokens": usage.get('completion_tokens', 0),
                            "total_tokens": usage.get('total_tokens', 0)
                        })
                        
                        # 비용 계산 (gpt-3.5-turbo 기준: $0.0015/1K input, $0.002/1K output)
                        input_cost = (token_info["prompt_tokens"] / 1000) * 0.0015
                        output_cost = (token_info["completion_tokens"] / 1000) * 0.002
                        token_info["cost_usd"] = round(input_cost + output_cost, 6)
                    
                    # 응답 구조 확인
                    if 'choices' not in data or not data['choices']:
                        self.logger.error(f"OpenRouter API 응답 형식 오류: {data}")
                        return [], token_info
                    
                    choice = data['choices'][0]
                    if 'message' not in choice or 'content' not in choice['message']:
                        self.logger.error(f"메시지 내용 없음: {choice}")
                        return [], token_info
                    
                    content = choice['message']['content'].strip()
                    
                    if not content:
                        self.logger.warning("OpenRouter API 응답이 비어있음")
                        return [], token_info
                    
                    # 키워드 파싱
                    keywords = self._parse_keywords(content)
                    
                    self.logger.info(f"OpenRouter 키워드 추출 성공: {keywords}")
                    self.logger.info(f"토큰 사용량: {token_info['total_tokens']}토큰, 비용: ${token_info['cost_usd']}")
                    
                    return keywords[:max_keywords], token_info
                    
        except Exception as e:
            self.logger.error(f"OpenRouter API 호출 실패: {str(e)}", exc_info=True)
            return [], token_info

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
    
    def _parse_keywords(self, content: str) -> List[str]:
        """다양한 형식의 키워드 응답을 파싱"""
        keywords = []
        
        # 1. 콤마로 구분된 형식: "키워드1, 키워드2, 키워드3"
        if ',' in content:
            keywords = [kw.strip() for kw in content.split(',')]
        
        # 2. 번호 매김 형식: "1. 키워드1\n2. 키워드2\n3. 키워드3"
        elif re.search(r'\d+\.\s*', content):
            # 번호와 점을 제거하고 키워드만 추출
            lines = content.split('\n')
            for line in lines:
                # "1. 키워드" 형식에서 키워드만 추출
                match = re.match(r'\d+\.\s*(.+)', line.strip())
                if match:
                    keywords.append(match.group(1).strip())
        
        # 3. 줄바꿈으로 구분된 형식: "키워드1\n키워드2\n키워드3"
        elif '\n' in content:
            keywords = [line.strip() for line in content.split('\n') if line.strip()]
        
        # 4. 공백으로 구분된 형식: "키워드1 키워드2 키워드3"
        else:
            keywords = content.split()
        
        # 키워드 정제
        cleaned_keywords = []
        for kw in keywords:
            # 불필요한 문자 제거
            kw = re.sub(r'^[^\w가-힣]+|[^\w가-힣]+$', '', kw)
            # 최소 길이 확인
            if kw and len(kw) >= 2:
                cleaned_keywords.append(kw)
        
        return cleaned_keywords
