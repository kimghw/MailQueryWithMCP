"""키워드 추출 서비스 - SAVE_STRUCTURED_DATA 설정 적용"""

import re
import time
import json
import asyncio
import aiohttp
from collections import Counter
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime

from infra.core.config import get_config
from infra.core.logger import get_logger
from modules.keyword_extractor.keyword_extractor_schema import KeywordExtractionResponse, ExtractionMethod


class ExtractionService:
    """키워드 추출 서비스"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)

        # OpenRouter 설정
        self.api_key = getattr(self.config, "openrouter_api_key", None)
        self.model = getattr(self.config, "openrouter_model", "openai/gpt-3.5-turbo")
        self.base_url = "https://openrouter.ai/api/v1"
        
        # 배치 처리 설정
        self.batch_size = int(self.config.get_setting("KEYWORD_EXTRACTION_BATCH_SIZE", "50"))
        self.concurrent_requests = int(self.config.get_setting("KEYWORD_EXTRACTION_CONCURRENT_REQUESTS", "5"))
        self.batch_timeout = int(self.config.get_setting("KEYWORD_EXTRACTION_BATCH_TIMEOUT", "60"))
        
        # 구조화된 응답 사용 여부
        self.use_structured_response = self.config.get_setting(
            "ENABLE_STRUCTURED_EXTRACTION", "true"
        ).lower() == "true"
        
        # 구조화된 데이터 저장 여부 (새로 추가)
        self.save_structured_data = self.config.get_setting(
            "SAVE_STRUCTURED_DATA", "true"
        ).lower() == "true"
        
        # 재사용 가능한 세션
        self._session: Optional[aiohttp.ClientSession] = None
        
        self.logger.info(
            f"추출 서비스 초기화: "
            f"model={self.model}, "
            f"save_structured_data={self.save_structured_data}"
        )

    # ... 기존 메서드들 유지 (__aenter__, __aexit__, close 등)

    async def _call_openrouter_structured_api(
        self, 
        content: str, 
        subject: str,
        sent_time: Optional[datetime],
        max_keywords: int,
        prompt_data: Dict[str, Any]
    ) -> Optional[Dict]:
        """OpenRouter API 호출 (구조화된 응답) - 저장 설정 적용"""
        
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
            
            # 플레이스홀더 치환
            user_prompt = user_prompt_template.replace('{subject}', subject if subject else "No subject")
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
        if ("gpt-4" in self.model or "gpt-3.5-turbo" in self.model) and "anthropic" not in self.model:
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
                            self.logger.warning("응답 컨텐츠가 비어있음")
                            return None
                        
                        # JSON 파싱 시도
                        try:
                            result = self._parse_json_response(content_response)
                            
                            if result:
                                # 토큰 사용량 정보 추가
                                if "usage" in data:
                                    result['token_usage'] = data["usage"]
                                
                                # SAVE_STRUCTURED_DATA 설정에 따라 저장 여부 결정
                                if self.save_structured_data:
                                    self._save_structured_response(content, subject, sent_time, result)
                                    self.logger.debug("구조화된 응답 저장 완료")
                                else:
                                    self.logger.debug("구조화된 응답 저장 스킵 (SAVE_STRUCTURED_DATA=false)")
                                
                            return result
                            
                        except json.JSONDecodeError as e:
                            self.logger.error(f"JSON 파싱 실패: {str(e)}")
                            # JSON 파싱 실패 시 기존 방식으로 파싱
                            keywords = self._parse_keywords(content_response)
                            return {
                                'keywords': keywords[:max_keywords],
                                'token_usage': data.get("usage", {})
                            }
                else:
                    self.logger.warning("API 응답에 choices가 없음")

                return None

        except Exception as e:
            self.logger.error(f"OpenRouter 구조화된 API 호출 실패: {str(e)}", exc_info=True)
            return None

    def _save_structured_response(self, text: str, subject: str, sent_time: Optional[datetime], result: Dict[str, Any]) -> None:
        """구조화된 응답을 파일로 저장 (설정에 따라 호출됨)"""
        try:
            self.logger.info(f"구조화된 응답 저장 시작 - subject: {subject}")
            
            # 프로젝트 루트 기준 상대 경로 사용
            from pathlib import Path
            
            # config에서 DATABASE_PATH를 참고하여 data 디렉토리 찾기
            db_path = self.config.database_path  # ./data/iacsgraph.db
            data_dir = Path(db_path).parent  # ./data
            base_dir = data_dir / "mail_analysis_results"
            
            base_dir.mkdir(parents=True, exist_ok=True)
            
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
            
            # JSONL 파일에 추가 모드로 저장
            with open(filepath, 'a', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False)
                f.write('\n')
            
            self.logger.info(f"구조화된 응답 저장 완료: {filepath.absolute()}")
            
        except Exception as e:
            self.logger.error(f"구조화된 응답 저장 실패: {str(e)}", exc_info=True)

    # ... 나머지 메서드들은 동일