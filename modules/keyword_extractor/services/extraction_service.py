# modules/keyword_extractor/services/extraction_service.py
"""키워드 추출 서비스 - 간소화 버전 (subject와 content만 사용)"""

import asyncio
import json
import re
import time
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from infra.core.config import get_config
from infra.core.logger import get_logger
from modules.keyword_extractor.keyword_extractor_schema import (
    ExtractionMethod,
    KeywordExtractionResponse,
)


class ExtractionService:
    """키워드 추출 서비스 - 간소화 버전"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)

        # OpenRouter 설정
        self.api_key = getattr(self.config, "openrouter_api_key", None)
        self.model = getattr(self.config, "openrouter_model", "openai/gpt-3.5-turbo")
        self.base_url = "https://openrouter.ai/api/v1"

        # 배치 처리 설정
        self.batch_size = int(
            self.config.get_setting("KEYWORD_EXTRACTION_BATCH_SIZE", "50")
        )
        self.concurrent_requests = int(
            self.config.get_setting("KEYWORD_EXTRACTION_CONCURRENT_REQUESTS", "5")
        )

        # 구조화된 응답 사용 여부
        self.use_structured_response = (
            self.config.get_setting("ENABLE_STRUCTURED_EXTRACTION", "true").lower()
            == "true"
        )

        # 재사용 가능한 세션
        self._session: Optional[aiohttp.ClientSession] = None

        self.logger.info(
            f"추출 서비스 초기화: model={self.model}, "
            f"structured_response={self.use_structured_response}"
        )

    async def __aenter__(self):
        """컨텍스트 매니저 진입"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        await self.close()

    async def extract(
        self,
        text: str,
        subject: str = "",
        max_keywords: int = 5,
        prompt_data: Optional[Dict[str, Any]] = None,
        use_structured_response: bool = True,
    ) -> KeywordExtractionResponse:
        """
        텍스트에서 키워드 추출 (간소화 버전)

        Args:
            text: 추출할 텍스트 (content)
            subject: 제목
            max_keywords: 최대 키워드 수
            prompt_data: 프롬프트 데이터
            use_structured_response: 구조화된 응답 사용 여부

        Returns:
            키워드 추출 응답
        """
        start_time = time.time()

        try:
            if use_structured_response and self.use_structured_response:
                # 구조화된 응답 API 호출
                result = await self._call_openrouter_api(
                    content=text,
                    subject=subject,
                    max_keywords=max_keywords,
                    prompt_data=prompt_data or {},
                )

                if result:
                    execution_time = int((time.time() - start_time) * 1000)
                    return KeywordExtractionResponse(
                        keywords=result.get("keywords", [])[:max_keywords],
                        method=ExtractionMethod.OPENROUTER,
                        model=self.model,
                        execution_time_ms=execution_time,
                        token_info=result.get("token_usage", {}),
                        # 구조화된 응답 필드들
                        deadline=result.get("deadline"),
                        has_deadline=result.get("has_deadline"),
                        mail_type=result.get("mail_type"),
                        decision_status=result.get("decision_status"),
                    )

            # 폴백: 기본 키워드 추출
            keywords = self._extract_keywords_fallback(text, max_keywords)
            execution_time = int((time.time() - start_time) * 1000)

            return KeywordExtractionResponse(
                keywords=keywords,
                method=ExtractionMethod.FALLBACK,
                model="rule_based",
                execution_time_ms=execution_time,
            )

        except Exception as e:
            self.logger.error(f"키워드 추출 실패: {str(e)}")
            execution_time = int((time.time() - start_time) * 1000)

            return KeywordExtractionResponse(
                keywords=[],
                method=ExtractionMethod.FALLBACK_ERROR,
                model="error",
                execution_time_ms=execution_time,
                token_info={"error": str(e)},
            )

    async def extract_batch(
        self,
        items: List[Dict[str, Any]],
        batch_size: int,
        concurrent_requests: int,
        prompt_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """배치 키워드 추출 - 전체 결과 반환"""
        results = []

        for i in range(0, len(items), batch_size):
            batch_items = items[i : i + batch_size]
            batch_results = await self._process_batch_chunk(batch_items, prompt_data)
            results.extend(batch_results)

        return results

    async def _process_batch_chunk(
        self, batch_items: List[Dict], prompt_data: Dict
    ) -> List[Dict[str, Any]]:
        """배치 청크 처리"""
        tasks = []

        for item in batch_items:
            task = self._process_single_item(item, prompt_data)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 예외가 발생한 경우 빈 결과로 처리
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"배치 아이템 처리 중 예외: {result}")
                processed_results.append({
                    "keywords": [],
                    "deadline": None,
                    "has_deadline": False,
                    "mail_type": "OTHER",
                    "decision_status": None,
                })
            else:
                processed_results.append(result)

        return processed_results

    async def _process_single_item(
        self, item: Dict, prompt_data: Dict
    ) -> Dict[str, Any]:
        """단일 아이템 처리"""
        try:
            content = item.get("content", "")
            subject = item.get("subject", "")

            # API 호출
            result = await self._call_openrouter_api(
                content=content,
                subject=subject,
                max_keywords=5,
                prompt_data=prompt_data,
            )

            if result:
                return result
            else:
                return {
                    "keywords": [],
                    "deadline": None,
                    "has_deadline": False,
                    "mail_type": "OTHER",
                    "decision_status": None,
                }

        except Exception as e:
            self.logger.error(f"아이템 처리 실패: {str(e)}")
            return {
                "keywords": [],
                "deadline": None,
                "has_deadline": False,
                "mail_type": "OTHER",
                "decision_status": None,
            }

    async def _call_openrouter_api(
        self,
        content: str,
        subject: str,
        max_keywords: int,
        prompt_data: Dict[str, Any],
    ) -> Optional[Dict]:
        """OpenRouter API 호출 (간소화 버전)"""
        if not self.api_key:
            return None

        # 텍스트 길이 제한
        max_content_length = 4000 if "claude" in self.model.lower() else 2000
        limited_content = (
            content[:max_content_length]
            if len(content) > max_content_length
            else content
        )

        # 프롬프트 준비
        try:
            system_prompt = prompt_data.get("system_prompt", "")
            user_prompt_template = prompt_data.get("user_prompt_template", "")

            # 플레이스홀더 치환 - subject와 content만
            user_prompt = user_prompt_template.replace(
                "{subject}", subject or "No subject"
            )
            user_prompt = user_prompt.replace("{content}", limited_content)

            self.logger.debug(f"프롬프트 준비 완료 - subject: {subject[:50]}...")

        except Exception as e:
            self.logger.error(f"프롬프트 템플릿 처리 오류: {str(e)}")
            return None

        # API 요청 준비
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 400,  # 필요한 필드만 받으므로 토큰 수 감소
            "temperature": 0.0,
        }

        # GPT 모델용 response_format
        if "gpt" in self.model.lower():
            payload["response_format"] = {"type": "json_object"}

        start_time = time.time()

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
                    self.logger.error(
                        f"API 오류: Status {response.status}, Response: {response_text}"
                    )
                    return None

                data = await response.json()

                # 응답에서 컨텐츠 추출
                if "choices" in data and data["choices"]:
                    choice = data["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        content_response = choice["message"]["content"]

                        if not content_response:
                            self.logger.warning("응답 컨텐츠가 비어있음")
                            return None

                        # JSON 파싱
                        try:
                            result = self._parse_json_response(content_response)
                            
                            if result:
                                # 토큰 사용량 정보 추가
                                if "usage" in data:
                                    result["token_usage"] = data["usage"]
                                
                                # 필수 필드 검증
                                required_fields = [
                                    "keywords",
                                    "deadline",
                                    "has_deadline",
                                    "mail_type",
                                    "decision_status",
                                ]
                                
                                if all(field in result for field in required_fields):
                                    self.logger.debug(
                                        f"API 응답 파싱 완료 - "
                                        f"keywords: {len(result.get('keywords', []))}, "
                                        f"mail_type: {result.get('mail_type')}"
                                    )
                                    return result
                                else:
                                    missing = [f for f in required_fields if f not in result]
                                    self.logger.warning(f"필수 필드 누락: {missing}")

                        except json.JSONDecodeError as e:
                            self.logger.error(f"JSON 파싱 실패: {str(e)}")

                return None

        except Exception as e:
            self.logger.error(f"OpenRouter API 호출 실패: {str(e)}")
            return None

    async def _get_session(self) -> aiohttp.ClientSession:
        """HTTP 세션 반환"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.http_timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"User-Agent": "IACSGraph/1.0", "Accept": "application/json"},
            )
        return self._session

    def _parse_json_response(self, content_response: str) -> Optional[Dict]:
        """JSON 응답 파싱"""
        try:
            # JSON 블록 추출
            json_match = re.search(
                r"```json\s*(\{.*?\})\s*```", content_response, re.DOTALL
            )
            if json_match:
                json_str = json_match.group(1)
            else:
                # 중괄호로 둘러싸인 JSON 찾기
                brace_match = re.search(r"\{.*\}", content_response, re.DOTALL)
                if brace_match:
                    json_str = brace_match.group(0)
                else:
                    json_str = content_response

            # JSON 파싱
            parsed = json.loads(json_str)
            return parsed if isinstance(parsed, dict) else None

        except json.JSONDecodeError:
            return None

    def _extract_keywords_fallback(self, text: str, max_keywords: int) -> List[str]:
        """폴백 키워드 추출"""
        words = re.findall(r"\b[가-힣a-zA-Z]{3,}\b", text)
        word_counts = Counter(words)
        return [word for word, _ in word_counts.most_common(max_keywords)]

    async def close(self):
        """리소스 정리"""
        try:
            if self._session and not self._session.closed:
                await self._session.close()
                self.logger.debug("HTTP 세션 종료됨")
        except Exception as e:
            self.logger.error(f"리소스 정리 중 오류: {str(e)}")