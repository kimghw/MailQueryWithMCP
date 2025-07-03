"""키워드 추출 서비스 - mail_process의 keyword_service.py 기반"""

import re
import time
import json
import asyncio
import aiohttp
from collections import Counter
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from pathlib import Path

from infra.core.config import get_config
from infra.core.logger import get_logger
from modules.keyword_extractor.keyword_extractor_schema import KeywordExtractionResponse, ExtractionMethod



class ExtractionService:
    """키워드 추출 서비스 (기존 MailKeywordService 기반)"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)

        # OpenRouter 설정
        self.api_key = getattr(self.config, "openrouter_api_key", None)
        self.model = getattr(self.config, "openrouter_model", "openai/gpt-3.5-turbo")
        self.base_url = "https://openrouter.ai/api/v1"
        
        # 기존 배치 처리 설정 사용 (이미 존재함)
        self.batch_size = int(self.config.get_setting("KEYWORD_EXTRACTION_BATCH_SIZE", "50"))
        self.concurrent_requests = int(self.config.get_setting("KEYWORD_EXTRACTION_CONCURRENT_REQUESTS", "5"))
        self.batch_timeout = int(self.config.get_setting("KEYWORD_EXTRACTION_BATCH_TIMEOUT", "60"))
        
        # 구조화된 응답 사용 여부 - 기존 설정 사용
        self.use_structured_response = self.config.get_setting(
            "ENABLE_STRUCTURED_EXTRACTION", "true"
        ).lower() == "true"
        
        # 재사용 가능한 세션
        self._session: Optional[aiohttp.ClientSession] = None
        
        self.logger.info(f"추출 서비스 초기화: model={self.model}")

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self.logger.debug("추출 서비스 세션 생성됨")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self.close()

    def _save_structured_response(self, text: str, subject: str, sent_time: Optional[datetime], result: Dict[str, Any]) -> None:
        """구조화된 응답을 파일로 저장"""
        try:
            # 메서드 호출 확인용 로그 추가
            self.logger.info(f"구조화된 응답 저장 시작 - subject: {subject}")
            
            # 저장 디렉토리 설정
            base_dir = Path("/home/kimghw/IACSGRAPH/data/mail_analysis_results")
            base_dir.mkdir(parents=True, exist_ok=True)
            
            # 디렉토리 생성 확인
            self.logger.info(f"저장 디렉토리 존재 여부: {base_dir.exists()}")
            
            # 파일명 생성 (날짜 기반)
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"mail_analysis_results_{date_str}.jsonl"
            filepath = base_dir / filename
            
            # 저장할 데이터 구성
            analysis_data = {
                "timestamp": datetime.now().isoformat(),
                "subject": subject,
                "sent_time": sent_time.isoformat() if sent_time and hasattr(sent_time, 'isoformat') else str(sent_time),
                "body_content": text[:2000],  # 처음 2000자만
                "model": self.model,
                "analysis_result": result
            }
            
            # 저장 직전 로그
            self.logger.info(f"파일 저장 시도: {filepath}")
            
            # JSONL 파일에 추가 모드로 저장
            with open(filepath, 'a', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False)
                f.write('\n')
            
            # 저장 성공 로그
            self.logger.info(f"구조화된 응답 저장 완료: {filepath}")
            
        except Exception as e:
            self.logger.error(f"구조화된 응답 저장 실패: {str(e)}", exc_info=True)

    async def close(self):
        """세션 정리"""
        if self._session and not self._session.closed:
            await self._session.close()
            self.logger.debug("추출 서비스 세션 정리됨")
            self._session = None

    async def extract(
        self,
        text: str,
        subject: str = "",
        sent_time: Optional[datetime] = None,
        max_keywords: int = 5,
        prompt_data: Dict[str, Any] = None,
        use_structured_response: bool = True
    ) -> KeywordExtractionResponse:
        """
        키워드 추출 실행
        
        Args:
            text: 추출할 텍스트
            subject: 제목 (선택사항)
            sent_time: 발송 시간 (선택사항)
            max_keywords: 최대 키워드 수
            prompt_data: 프롬프트 데이터
            use_structured_response: 구조화된 응답 사용 여부
            
        Returns:
            키워드 추출 응답
        """
        start_time = time.time()

        try:
            # 구조화된 응답 사용
            if use_structured_response and self.api_key and prompt_data:
                result = await self._call_openrouter_structured_api(
                    text, subject, sent_time, max_keywords, prompt_data
                )
                if result:
                    return self._create_response_from_result(result, start_time)

            # 기본 API 호출
            if self.api_key:
                keywords, token_info = await self._call_openrouter_api(text, max_keywords)
                if keywords:
                    return KeywordExtractionResponse(
                        keywords=keywords,
                        method=ExtractionMethod.OPENROUTER,
                        model=self.model,
                        execution_time_ms=int((time.time() - start_time) * 1000),
                        token_info=token_info
                    )

            # Fallback
            keywords = self._fallback_keyword_extraction(text, max_keywords)
            return KeywordExtractionResponse(
                keywords=keywords,
                method=ExtractionMethod.FALLBACK,
                model="rule_based",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as e:
            self.logger.warning(f"키워드 추출 실패, fallback 사용: {str(e)}")
            keywords = self._fallback_keyword_extraction(text, max_keywords)
            return KeywordExtractionResponse(
                keywords=keywords,
                method=ExtractionMethod.FALLBACK_ERROR,
                model="rule_based",
                execution_time_ms=int((time.time() - start_time) * 1000),
                token_info={"error": str(e)}
            )

    async def extract_batch(
        self,
        items: List[Dict[str, Any]],
        batch_size: int = 50,
        concurrent_requests: int = 5,
        prompt_data: Dict[str, Any] = None
    ) -> List[List[str]]:
        """
        배치 키워드 추출
        
        Args:
            items: 추출할 아이템 리스트
            batch_size: 배치 크기
            concurrent_requests: 동시 요청 수
            prompt_data: 프롬프트 데이터 (구조화된 응답용)
            
        Returns:
            각 아이템의 키워드 리스트
        """
        results = []
        
        # 청크로 나누어 처리
        for chunk_start in range(0, len(items), batch_size):
            chunk_end = min(chunk_start + batch_size, len(items))
            chunk_items = items[chunk_start:chunk_end]
            
            # 동시 처리
            chunk_results = await self._process_chunk_concurrent(
                chunk_items, concurrent_requests, prompt_data
            )
            results.extend(chunk_results)
            
            # API 속도 제한 고려
            if chunk_end < len(items):
                await asyncio.sleep(0.5)
        
        return results

    async def _process_chunk_concurrent(
        self, 
        items: List[Dict[str, Any]],
        concurrent_requests: int,
        prompt_data: Dict[str, Any] = None
    ) -> List[List[str]]:
        """청크를 동시에 처리"""
        semaphore = asyncio.Semaphore(concurrent_requests)
        
        async def process_with_semaphore(item: Dict[str, Any]) -> List[str]:
            async with semaphore:
                try:
                    content = item.get('content', '') if isinstance(item, dict) else str(item)
                    subject = item.get('subject', '') if isinstance(item, dict) else ""
                    sent_time = item.get('sent_time') if isinstance(item, dict) else None
                    
                    # 구조화된 응답 사용 시도
                    if self.api_key and prompt_data and self.use_structured_response:
                        result = await self._call_openrouter_structured_api(
                            content, subject, sent_time, 5, prompt_data
                        )
                        if result and 'keywords' in result:
                            return result['keywords']
                    
                    # 기본 API 호출
                    if self.api_key:
                        keywords, _ = await self._call_openrouter_api(content, 5)
                        if keywords:
                            return keywords
                    
                    return self._fallback_keyword_extraction(content, 5)
                except Exception as e:
                    self.logger.warning(f"개별 API 호출 실패: {str(e)}")
                    content = item.get('content', '') if isinstance(item, dict) else str(item)
                    return self._fallback_keyword_extraction(content, 5)
        
        # 모든 태스크를 동시에 실행
        tasks = [process_with_semaphore(item) for item in items]
        
        # 타임아웃 설정
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.batch_timeout
            )
        except asyncio.TimeoutError:
            self.logger.error(f"배치 처리 타임아웃 ({self.batch_timeout}초)")
            results = []
            for item in items:
                content = item.get('content', '') if isinstance(item, dict) else str(item)
                results.append(self._fallback_keyword_extraction(content, 5))
        
        # 예외 처리
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.warning(f"태스크 {i} 실패: {str(result)}")
                content = items[i].get('content', '') if isinstance(items[i], dict) else str(items[i])
                processed_results.append(self._fallback_keyword_extraction(content, 5))
            else:
                processed_results.append(result)
        
        return processed_results

    async def _get_session(self) -> aiohttp.ClientSession:
        """세션 가져오기 (필요시 생성)"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self.logger.debug("새로운 추출 서비스 세션 생성")
        return self._session

    async def _call_openrouter_structured_api(
        self, 
        content: str, 
        subject: str,
        sent_time: Optional[datetime],
        max_keywords: int,
        prompt_data: Dict[str, Any]
    ) -> Optional[Dict]:
        """OpenRouter API 호출 (구조화된 응답)"""
        if not self.api_key:
            return None

        # 텍스트 길이 제한
        limited_content = content[:2000] if len(content) > 2000 else content
        
        # 발송 시간 포맷팅
        sent_time_str = sent_time.isoformat() if sent_time else "Unknown"
        
        # 프롬프트 준비
        try:
            system_prompt = prompt_data.get('system_prompt', '')
            user_prompt_template = prompt_data.get('user_prompt_template', '')
            
            user_prompt = user_prompt_template
            user_prompt = user_prompt.replace('{subject}', subject if subject else "No subject")
            user_prompt = user_prompt.replace('{content}', limited_content)
            user_prompt = user_prompt.replace('{sent_time}', sent_time_str)
        except Exception as e:
            self.logger.error(f"프롬프트 템플릿 처리 오류: {str(e)}")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.1,
        }

        # response_format이 지원되는 모델인 경우 추가
        if "gpt-4" in self.model or "gpt-3.5-turbo" in self.model:
            payload["response_format"] = {"type": "json_object"}

        try:
            session = await self._get_session()
            
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:

                if response.status != 200:
                    response_text = await response.text()
                    self.logger.error(f"API 오류: Status {response.status}, Response: {response_text}")
                    return None

                data = await response.json()
                
                # 응답에서 컨텐츠 추출
                if "choices" in data and data["choices"]:
                    choice = data["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        content_response = choice["message"]["content"]
                        
                        if not content_response:
                            return None
                        
                        # JSON 파싱 시도
                        try:
                            result = self._parse_json_response(content_response)
                            
                            # 디버깅 로그 추가
                            self.logger.debug(f"Parsed result: {result}")
                            self.logger.debug(f"Has mail_type: {'mail_type' in result if result else False}")
                            
                            # 토큰 사용량 정보 추가
                            if "usage" in data:
                                result['token_usage'] = data["usage"]
                            
                            # 구조화된 응답 저장 (API 응답이 있으면 항상 저장)
                            if result:
                                self._save_structured_response(limited_content, subject, sent_time, result)
                            else:
                                self.logger.warning(f"Not saving: result={bool(result)}, has_mail_type={'mail_type' in result if result else False}")
                            
                            return result
                            
                        except json.JSONDecodeError:
                            # JSON 파싱 실패 시 기존 방식으로 파싱
                            keywords = self._parse_keywords(content_response)
                            return {
                                'keywords': keywords[:max_keywords],
                                'token_usage': data.get("usage", {})
                            }

                return None

        except Exception as e:
            self.logger.error(f"OpenRouter 구조화된 API 호출 실패: {str(e)}")
            return None

    async def _call_openrouter_api(self, text: str, max_keywords: int) -> Tuple[List[str], dict]:
        """OpenRouter API 호출 (기본)"""
        if not self.api_key:
            return [], {}

        # 텍스트 길이 제한
        limited_text = text[:1000] if len(text) > 1000 else text

        # 간단한 프롬프트
        prompt = f"Extract {max_keywords} keywords from this text: {limited_text}\n\nKeywords:"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 100,
            "temperature": 0.3,
        }

        token_info = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

        try:
            session = await self._get_session()

            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:

                if response.status != 200:
                    return [], token_info

                data = await response.json()

                # 토큰 사용량 정보 추출
                if "usage" in data:
                    usage = data["usage"]
                    token_info.update({
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    })

                # 응답에서 컨텐츠 추출
                if "choices" in data and data["choices"]:
                    choice = data["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        content = choice["message"]["content"]
                        if content and content.strip():
                            keywords = self._parse_keywords(content)
                            return keywords[:max_keywords], token_info

                return [], token_info

        except Exception as e:
            self.logger.error(f"OpenRouter API 호출 실패: {str(e)}")
            return [], token_info

    def _fallback_keyword_extraction(self, text: str, max_keywords: int) -> List[str]:
        """Fallback 키워드 추출"""
        # 한국어 단어 추출 (2글자 이상)
        korean_words = re.findall(r"[가-힣]{2,}", text)

        # 영문 단어 추출 (3글자 이상)
        english_words = re.findall(r"[A-Za-z]{3,}", text)

        # 숫자 포함 식별자 추출
        identifiers = re.findall(r"[A-Z]{2,}\d+|[A-Z]+-\d+|\d{3,}", text)

        # 모든 단어 합치기
        all_words = korean_words + english_words + identifiers

        # 빈도수 기반 상위 키워드 선택
        word_counts = Counter(all_words)
        top_keywords = [word for word, count in word_counts.most_common(max_keywords)]

        return top_keywords

    def _parse_keywords(self, content: str) -> List[str]:
        """키워드 응답 파싱"""
        keywords = []

        # 1. 번호 매김 형식
        if re.search(r"\d+\.\s*", content):
            lines = content.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                match = re.match(r"\d+\.\s*(.+)", line)
                if match:
                    keyword = match.group(1).strip()
                    if keyword:
                        keywords.append(keyword)

        # 2. 콤마로 구분된 형식
        elif "," in content:
            keywords = [kw.strip() for kw in content.split(",") if kw.strip()]

        # 3. 줄바꿈으로 구분된 형식
        elif "\n" in content:
            keywords = [line.strip() for line in content.split("\n") if line.strip()]

        # 4. 공백으로 구분된 형식
        else:
            keywords = content.split()

        # 키워드 정제
        cleaned_keywords = []
        for kw in keywords:
            kw = re.sub(r"^[^\w가-힣]+|[^\w가-힣]+$", "", kw)
            if kw and len(kw) >= 2:
                cleaned_keywords.append(kw)

        return cleaned_keywords

    def _parse_json_response(self, content_response: str) -> Dict:
        """JSON 응답 파싱 (코드 블록 처리 포함)"""
        if not content_response:
            raise json.JSONDecodeError("Empty response", "", 0)
        
        # 첫 번째 시도: 직접 파싱
        try:
            return json.loads(content_response)
        except json.JSONDecodeError:
            pass
        
        # 두 번째 시도: 코드 블록 제거
        if content_response.strip().startswith('```'):
            lines = content_response.strip().split('\n')
            if lines[0].strip() in ['```json', '```']:
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            clean_json = '\n'.join(lines)
            
            if clean_json.strip():
                return json.loads(clean_json)
        
        raise json.JSONDecodeError("Failed to parse JSON", content_response, 0)

    def _create_response_from_result(
        self, 
        result: Dict[str, Any], 
        start_time: float
    ) -> KeywordExtractionResponse:
        """API 결과를 응답 객체로 변환"""
        # 키워드 검증 및 정제
        keywords = result.get('keywords', [])
        if isinstance(keywords, list):
            keywords = [k.strip() for k in keywords if k and k.strip()]
        else:
            keywords = []
        
        # 응답 생성
        response = KeywordExtractionResponse(
            keywords=keywords,
            method=ExtractionMethod.OPENROUTER,
            model=self.model,
            execution_time_ms=int((time.time() - start_time) * 1000),
            token_info=result.get('token_usage', {})
        )
        
        # 구조화된 응답 필드 추가
        if 'summary' in result:
            response.summary = result['summary']
        if 'deadline' in result:
            response.deadline = result['deadline']
        if 'has_deadline' in result:
            response.has_deadline = result['has_deadline']
        if 'mail_type' in result:
            response.mail_type = result['mail_type']
        if 'decision_status' in result:
            response.decision_status = result['decision_status']
        if 'sender_type' in result:
            response.sender_type = result['sender_type']
        if 'sender_organization' in result:
            response.sender_organization = result['sender_organization']
        if 'agenda_no' in result:
            response.agenda_no = result['agenda_no']
        if 'agenda_info' in result:
            response.agenda_info = result['agenda_info']
        
        return response
