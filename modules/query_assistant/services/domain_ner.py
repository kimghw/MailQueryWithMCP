"""Domain-specific Named Entity Recognition for query processing"""

import re
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

from ..models.preprocessing_dataset import PreprocessingTerm
from ..repositories.preprocessing_repository import PreprocessingRepository

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """엔티티 타입 정의"""
    ORGANIZATION = "ORG"      # 기관명
    TIME_PERIOD = "TIME"      # 시간 표현
    STATUS = "STATUS"         # 상태값
    QUANTITY = "QUANTITY"     # 수량
    KEYWORD = "KEYWORD"       # 검색 키워드
    AGENDA_ID = "AGENDA_ID"   # 아젠다 ID
    PERSON = "PERSON"         # 인물명
    DECISION = "DECISION"     # 결정 유형


@dataclass
class NamedEntity:
    """인식된 개체 정보"""
    text: str                    # 원본 텍스트
    entity_type: EntityType      # 엔티티 타입
    normalized_value: Any        # 정규화된 값
    start_pos: int              # 시작 위치
    end_pos: int                # 종료 위치
    confidence: float = 1.0     # 신뢰도
    metadata: Dict[str, Any] = None  # 추가 메타데이터


class DomainNER:
    """IACSGRAPH 도메인에 특화된 Named Entity Recognition"""
    
    def __init__(self, preprocessing_repo: Optional[PreprocessingRepository] = None):
        """
        Args:
            preprocessing_repo: 전처리 데이터셋 저장소
        """
        self.preprocessing_repo = preprocessing_repo
        
        # 도메인 특화 패턴 정의
        self.patterns = {
            EntityType.ORGANIZATION: [
                # 선급 코드 (대문자) - 단어 경계가 아닌 경우도 포함
                (r'(KR|BV|CCS|DNV|LR|ABS|RINA|NK|PRS|IRS|CRS)(?=\s|와|과|의|,|$)', 1.0),
                # 한글 선급명
                (r'(한국선급|뷰로베리타스|중국선급|로이드|아메리칸뷰로)', 0.9),
                # 영문 선급명
                (r'(Korean Register|Bureau Veritas|Lloyd\'s Register)', 0.9),
                # DTP 기관
                (r'\b(KRSDTP|KOMDTP|KMDTP|GMDTP|BMDTP|PLDTP)\b', 1.0),
            ],
            
            EntityType.TIME_PERIOD: [
                # 숫자 + 단위
                (r'(\d+)\s*(일|주|개월|달|년|년간)\s*(전|동안|간)?', 0.95),
                # 상대 시간
                (r'(오늘|어제|그제|최근|이번\s*주|지난\s*주|이번\s*달|지난\s*달|올해|작년)', 0.9),
                # 날짜 형식
                (r'(\d{4}[-./]\d{1,2}[-./]\d{1,2})', 1.0),
                # 분기
                (r'(\d+)\s*분기', 0.9),
            ],
            
            EntityType.STATUS: [
                # 승인 상태
                (r'(승인|허가|통과|approve)', 0.95),
                # 반려 상태
                (r'(반려|거부|거절|기각|reject)', 0.95),
                # 대기 상태
                (r'(미결정|대기|보류|검토중|pending)', 0.95),
            ],
            
            EntityType.QUANTITY: [
                # 숫자 + 개
                (r'(\d+)\s*개', 0.9),
                # 숫자 + 건
                (r'(\d+)\s*건', 0.9),
                # 범위 표현
                (r'(전체|모든|일부|몇개|여러)', 0.8),
                # 퍼센트
                (r'(\d+)\s*(%|퍼센트|프로)', 0.9),
            ],
            
            EntityType.AGENDA_ID: [
                # PL + 5자리 숫자
                (r'PL\d{5}', 1.0),
                # 변형 패턴
                (r'PL[-\s]?\d{5}', 0.9),
            ],
            
            EntityType.DECISION: [
                # 결정 유형
                (r'(전원일치|다수결|과반수)', 0.9),
                # 투표 관련
                (r'(찬성|반대|기권)', 0.9),
            ],
        }
        
        # 정규화 매핑
        self.normalization_maps = {
            EntityType.ORGANIZATION: {
                # 한글 -> 코드
                "한국선급": "KR",
                "뷰로베리타스": "BV", 
                "중국선급": "CCS",
                "로이드": "LR",
                "아메리칸뷰로": "ABS",
                # 영문 -> 코드
                "korean register": "KR",
                "bureau veritas": "BV",
                "lloyd's register": "LR",
                # DTP 기관
                "한국연구재단": "KRSDTP",
                "해양수산부": "KOMDTP",
                "기상청": "KMDTP",
            },
            
            EntityType.STATUS: {
                # 한글 -> 영문
                "승인": "approved",
                "허가": "approved",
                "통과": "approved",
                "반려": "rejected",
                "거부": "rejected",
                "거절": "rejected",
                "기각": "rejected",
                "미결정": "pending",
                "대기": "pending",
                "보류": "pending",
                "검토중": "pending",
            },
            
            EntityType.TIME_PERIOD: {
                # 상대 시간 -> 일수
                "오늘": 0,
                "어제": 1,
                "그제": 2,
                "최근": 7,
                "이번주": 7,
                "지난주": 14,
                "이번달": 30,
                "지난달": 60,
                "올해": 365,
                "작년": 730,
            },
        }
    
    def extract_entities(self, text: str) -> List[NamedEntity]:
        """텍스트에서 엔티티 추출
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            추출된 엔티티 리스트 (위치 순 정렬)
        """
        entities = []
        
        # 1. 패턴 기반 추출
        for entity_type, patterns in self.patterns.items():
            for pattern, confidence in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entity = NamedEntity(
                        text=match.group(0),
                        entity_type=entity_type,
                        normalized_value=self._normalize_entity(
                            match.group(0), entity_type, match
                        ),
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=confidence
                    )
                    entities.append(entity)
        
        # 2. 전처리 데이터셋 활용
        if self.preprocessing_repo:
            entities.extend(self._extract_from_preprocessing(text))
        
        # 3. 중복 제거 및 정렬
        entities = self._resolve_overlaps(entities)
        
        # 4. 후처리 (컨텍스트 기반 보정)
        entities = self._post_process_entities(entities, text)
        
        return sorted(entities, key=lambda e: e.start_pos)
    
    def _normalize_entity(self, text: str, entity_type: EntityType, match: re.Match = None) -> Any:
        """엔티티 정규화
        
        Args:
            text: 엔티티 텍스트
            entity_type: 엔티티 타입
            match: 정규식 매치 객체
            
        Returns:
            정규화된 값
        """
        # 대소문자 정규화
        normalized_text = text.strip().lower()
        
        # 타입별 매핑 확인
        if entity_type in self.normalization_maps:
            mapping = self.normalization_maps[entity_type]
            if normalized_text in mapping:
                return mapping[normalized_text]
        
        # 특수 처리
        if entity_type == EntityType.TIME_PERIOD and match:
            return self._normalize_time_period(text, match)
        elif entity_type == EntityType.QUANTITY and match:
            return self._normalize_quantity(text, match)
        
        # 기본값: 원본 텍스트 (대문자 처리)
        if entity_type == EntityType.ORGANIZATION:
            return text.upper()
        
        return text
    
    def _normalize_time_period(self, text: str, match: re.Match) -> Dict[str, Any]:
        """시간 표현 정규화
        
        Returns:
            {"days": 일수, "unit": 단위, "text": 원본}
        """
        # 숫자 + 단위 패턴
        time_match = re.search(r'(\d+)\s*(일|주|개월|달|년|년간)', text)
        if time_match:
            value = int(time_match.group(1))
            unit = time_match.group(2)
            
            days = value
            if unit in ["주"]:
                days = value * 7
            elif unit in ["개월", "달"]:
                days = value * 30
            elif unit in ["년", "년간"]:
                days = value * 365
            
            return {
                "days": days,
                "value": value,
                "unit": unit,
                "text": text
            }
        
        # 상대 시간 표현
        if text.strip() in self.normalization_maps[EntityType.TIME_PERIOD]:
            days = self.normalization_maps[EntityType.TIME_PERIOD][text.strip()]
            return {
                "days": days,
                "relative": True,
                "text": text
            }
        
        return {"text": text}
    
    def _normalize_quantity(self, text: str, match: re.Match) -> Dict[str, Any]:
        """수량 표현 정규화"""
        # 숫자 추출
        num_match = re.search(r'(\d+)', text)
        if num_match:
            value = int(num_match.group(1))
            
            # 단위 확인
            if "%" in text or "퍼센트" in text or "프로" in text:
                return {"value": value, "unit": "percent", "text": text}
            elif "개" in text:
                return {"value": value, "unit": "count", "text": text}
            elif "건" in text:
                return {"value": value, "unit": "case", "text": text}
            
            return {"value": value, "text": text}
        
        # 범위 표현
        if text in ["전체", "모든"]:
            return {"value": "all", "text": text}
        elif text in ["일부", "몇개", "여러"]:
            return {"value": "some", "text": text}
        
        return {"text": text}
    
    def _extract_from_preprocessing(self, text: str) -> List[NamedEntity]:
        """전처리 데이터셋을 활용한 엔티티 추출"""
        entities = []
        
        try:
            # 활성 용어 가져오기
            dataset = self.preprocessing_repo.load_dataset()
            processed_text = text.lower()
            
            # 각 용어에 대해 매칭 시도
            for term in dataset.terms:
                if not term.is_active:
                    continue
                
                entity_type = self._map_term_type_to_entity(term.term_type)
                if not entity_type:
                    continue
                
                # 매칭 시도
                match_result = term.match(text)
                if match_result:
                    # 위치 찾기
                    pattern = re.escape(term.original_term)
                    for match in re.finditer(pattern, text, re.IGNORECASE):
                        entities.append(NamedEntity(
                            text=match.group(0),
                            entity_type=entity_type,
                            normalized_value=match_result,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            confidence=0.85,
                            metadata={"source": "preprocessing", "term_id": term.id}
                        ))
                    
                    # 사용 기록
                    self.preprocessing_repo.record_usage(term.id)
                    
        except Exception as e:
            logger.warning(f"Error extracting from preprocessing: {e}")
        
        return entities
    
    def _map_term_type_to_entity(self, term_type: str) -> Optional[EntityType]:
        """전처리 term_type을 EntityType으로 매핑"""
        mapping = {
            "organization": EntityType.ORGANIZATION,
            "time_expression": EntityType.TIME_PERIOD,
            "status": EntityType.STATUS,
            "keyword": EntityType.KEYWORD,
        }
        return mapping.get(term_type)
    
    def _resolve_overlaps(self, entities: List[NamedEntity]) -> List[NamedEntity]:
        """중복되는 엔티티 해결"""
        if not entities:
            return entities
        
        # 신뢰도와 길이 기준으로 정렬
        entities.sort(key=lambda e: (e.confidence, e.end_pos - e.start_pos), reverse=True)
        
        resolved = []
        used_positions = set()
        
        for entity in entities:
            # 위치가 겹치는지 확인
            positions = set(range(entity.start_pos, entity.end_pos))
            if not positions & used_positions:
                resolved.append(entity)
                used_positions.update(positions)
        
        return resolved
    
    def _post_process_entities(self, entities: List[NamedEntity], text: str) -> List[NamedEntity]:
        """엔티티 후처리 (컨텍스트 기반 보정)"""
        # 예: "KR의 응답률" -> KR을 ORGANIZATION으로 확정
        for entity in entities:
            if entity.entity_type == EntityType.ORGANIZATION:
                # 주변 컨텍스트 확인
                context_start = max(0, entity.start_pos - 10)
                context_end = min(len(text), entity.end_pos + 10)
                context = text[context_start:context_end]
                
                # 컨텍스트 단서 추가
                if any(word in context for word in ["기관", "선급", "응답", "제출"]):
                    entity.confidence = min(1.0, entity.confidence + 0.1)
        
        return entities
    
    def get_entity_summary(self, entities: List[NamedEntity]) -> Dict[str, List[Any]]:
        """엔티티를 타입별로 정리"""
        summary = {}
        
        for entity in entities:
            entity_type = entity.entity_type.value
            if entity_type not in summary:
                summary[entity_type] = []
            
            summary[entity_type].append({
                "text": entity.text,
                "normalized": entity.normalized_value,
                "confidence": entity.confidence
            })
        
        return summary