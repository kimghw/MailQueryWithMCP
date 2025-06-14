from pydantic import BaseModel, Field
from typing import List

class KeywordExtractionRequest(BaseModel):
    text: str
    max_keywords: int = Field(5, description="추출할 최대 키워드 수")

class KeywordExtractionResponse(BaseModel):
    keywords: List[str]
