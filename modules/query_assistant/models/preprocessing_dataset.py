"""
Preprocessing Dataset Model
동의어 사전 및 정규화 패턴 관리
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import re
from dataclasses import dataclass, field, asdict


@dataclass
class PreprocessingTerm:
    """전처리 용어 데이터 모델"""
    
    # 기본 식별자
    id: Optional[int] = None
    
    # 용어 분류
    term_type: str = ""  # 'synonym', 'organization', 'time_expression', 'status', 'keyword'
    category: Optional[str] = None  # 세부 카테고리
    
    # 용어 매핑
    original_term: str = ""
    normalized_term: str = ""
    language: str = "ko"
    
    # 패턴 정보
    is_pattern: bool = False
    pattern_regex: Optional[str] = None
    pattern_priority: int = 100
    
    # 컨텍스트 정보
    context_clues: List[str] = field(default_factory=list)
    domain_specific: bool = True
    
    # 사용 통계
    usage_count: int = 0
    last_used_at: Optional[datetime] = None
    match_accuracy: float = 1.0
    
    # 관계 정보
    related_terms: List[str] = field(default_factory=list)
    parent_term_id: Optional[int] = None
    
    # 메타데이터
    source: str = "manual"  # 'manual', 'auto_extracted', 'llm_suggested'
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True
    
    def __post_init__(self):
        """초기화 후 처리"""
        # 시간 필드 초기화
        if not self.created_at:
            self.created_at = datetime.now()
        if not self.updated_at:
            self.updated_at = datetime.now()
        
        # 패턴 컴파일 (유효성 검사)
        if self.is_pattern and self.pattern_regex:
            try:
                re.compile(self.pattern_regex)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {self.pattern_regex} - {e}")
    
    def match(self, text: str) -> Optional[str]:
        """텍스트와 매칭 시도"""
        if self.is_pattern and self.pattern_regex:
            # 패턴 매칭
            pattern = re.compile(self.pattern_regex, re.IGNORECASE)
            match = pattern.search(text)
            if match:
                # 캡처 그룹이 있으면 normalized_term에 치환
                if match.groups():
                    result = self.normalized_term
                    for i, group in enumerate(match.groups(), 1):
                        result = result.replace(f'{{{i}}}', group)
                    return result
                return self.normalized_term
        else:
            # 정확한 매칭
            if self.original_term.lower() in text.lower():
                return self.normalized_term
        
        return None
    
    def record_usage(self, accuracy: float = 1.0):
        """사용 기록 업데이트"""
        self.usage_count += 1
        self.last_used_at = datetime.now()
        
        # 가중 평균으로 정확도 업데이트
        total_weight = self.usage_count - 1 + 1
        self.match_accuracy = (
            (self.match_accuracy * (self.usage_count - 1) + accuracy) / total_weight
        )
        
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        data = asdict(self)
        
        # JSON 필드 직렬화
        if self.context_clues:
            data['context_clues'] = json.dumps(self.context_clues, ensure_ascii=False)
        if self.related_terms:
            data['related_terms'] = json.dumps(self.related_terms, ensure_ascii=False)
        
        # datetime 필드 직렬화
        for field_name in ['last_used_at', 'created_at', 'updated_at']:
            if data.get(field_name):
                data[field_name] = data[field_name].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PreprocessingTerm':
        """딕셔너리에서 객체 생성"""
        # JSON 필드 역직렬화
        if isinstance(data.get('context_clues'), str):
            data['context_clues'] = json.loads(data['context_clues'])
        if isinstance(data.get('related_terms'), str):
            data['related_terms'] = json.loads(data['related_terms'])
        
        # datetime 필드 역직렬화
        for field_name in ['last_used_at', 'created_at', 'updated_at']:
            if data.get(field_name):
                if isinstance(data[field_name], str):
                    data[field_name] = datetime.fromisoformat(data[field_name])
        
        return cls(**data)
    
    def deactivate(self):
        """용어 비활성화"""
        self.is_active = False
        self.updated_at = datetime.now()
    
    def add_related_term(self, term: str):
        """관련 용어 추가"""
        if term not in self.related_terms:
            self.related_terms.append(term)
            self.updated_at = datetime.now()
    
    def set_context_clues(self, clues: List[str]):
        """문맥 단서 설정"""
        self.context_clues = clues
        self.updated_at = datetime.now()


class PreprocessingDataset:
    """전처리 데이터셋 관리 클래스"""
    
    def __init__(self, terms: List[PreprocessingTerm]):
        self.terms = sorted(terms, key=lambda t: t.pattern_priority)
        self._build_indices()
    
    def _build_indices(self):
        """검색 성능을 위한 인덱스 구축"""
        self.by_type = {}
        self.by_category = {}
        self.patterns = []
        self.exact_matches = {}
        
        for term in self.terms:
            if not term.is_active:
                continue
            
            # 타입별 인덱싱
            if term.term_type not in self.by_type:
                self.by_type[term.term_type] = []
            self.by_type[term.term_type].append(term)
            
            # 카테고리별 인덱싱
            if term.category:
                if term.category not in self.by_category:
                    self.by_category[term.category] = []
                self.by_category[term.category].append(term)
            
            # 패턴과 정확한 매칭 분리
            if term.is_pattern:
                self.patterns.append(term)
            else:
                key = term.original_term.lower()
                if key not in self.exact_matches:
                    self.exact_matches[key] = []
                self.exact_matches[key].append(term)
    
    def preprocess(self, text: str) -> str:
        """텍스트 전처리"""
        processed_text = text
        
        # 1. 정확한 매칭부터 처리 (빠름)
        text_lower = text.lower()
        for key, terms in self.exact_matches.items():
            if key in text_lower:
                for term in terms:
                    processed_text = re.sub(
                        rf'\b{re.escape(term.original_term)}\b',
                        term.normalized_term,
                        processed_text,
                        flags=re.IGNORECASE
                    )
        
        # 2. 패턴 매칭 처리 (우선순위 순)
        for term in self.patterns:
            match_result = term.match(processed_text)
            if match_result:
                # 패턴에 의한 치환
                pattern = re.compile(term.pattern_regex, re.IGNORECASE)
                processed_text = pattern.sub(match_result, processed_text)
        
        return processed_text
    
    def find_terms_by_type(self, term_type: str) -> List[PreprocessingTerm]:
        """특정 타입의 용어 검색"""
        return self.by_type.get(term_type, [])
    
    def find_terms_by_category(self, category: str) -> List[PreprocessingTerm]:
        """특정 카테고리의 용어 검색"""
        return self.by_category.get(category, [])
    
    def add_term(self, term: PreprocessingTerm):
        """새 용어 추가"""
        self.terms.append(term)
        self._build_indices()  # 인덱스 재구축
    
    def get_statistics(self) -> Dict[str, Any]:
        """데이터셋 통계"""
        active_terms = [t for t in self.terms if t.is_active]
        
        return {
            "total_terms": len(self.terms),
            "active_terms": len(active_terms),
            "inactive_terms": len(self.terms) - len(active_terms),
            "pattern_terms": len(self.patterns),
            "exact_match_terms": sum(len(terms) for terms in self.exact_matches.values()),
            "types": list(self.by_type.keys()),
            "categories": list(self.by_category.keys()),
            "most_used_terms": sorted(
                active_terms,
                key=lambda t: t.usage_count,
                reverse=True
            )[:10]
        }