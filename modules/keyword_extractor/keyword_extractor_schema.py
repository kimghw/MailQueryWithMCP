# modules/keyword_extractor/keyword_extractor_schema.py
"""키워드 추출 모듈 스키마 정의 - 간소화 버전"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExtractionMethod(str, Enum):
    """추출 방법"""
    OPENROUTER = "openrouter"
    FALLBACK = "fallback"
    EMPTY_TEXT = "empty_text"
    FALLBACK_ERROR = "fallback_error"


class KeywordExtractionRequest(BaseModel):
    """키워드 추출 요청 - 간소화"""
    text: str = Field(..., description="추출할 텍스트 (content)")
    subject: str = Field(default="", description="제목")
    max_keywords: int = Field(default=5, description="최대 키워드 수")
    use_structured_response: bool = Field(
        default=True, description="구조화된 응답 사용"
    )


class KeywordExtractionResponse(BaseModel):
    """키워드 추출 응답 - 간소화"""
    keywords: List[str] = Field(default_factory=list)
    method: ExtractionMethod
    model: str  # 사용된 모델명
    execution_time_ms: int
    token_info: Dict[str, Any] = Field(
        default_factory=dict, description="토큰 사용량 정보"
    )
    
    # 구조화된 응답 필드 (필요한 것만)
    deadline: Optional[str] = None
    has_deadline: Optional[bool] = None
    mail_type: Optional[str] = None
    decision_status: Optional[str] = None


class BatchExtractionRequest(BaseModel):
    """배치 추출 요청"""
    items: List[Dict[str, Any]] = Field(..., description="추출할 아이템 리스트")
    batch_size: int = Field(default=50, description="배치 크기")
    concurrent_requests: int = Field(default=5, description="동시 요청 수")


class BatchExtractionResponse(BaseModel):
    """배치 추출 응답"""
    results: List[Dict[str, Any]] = Field(
        default_factory=list, description="각 아이템의 추출 결과"
    )
    total_items: int
    successful_items: int
    failed_items: int
    total_execution_time_ms: int