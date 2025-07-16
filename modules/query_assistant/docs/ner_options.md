# 한국어 NER (Named Entity Recognition) 라이브러리 옵션

## 1. KoNLPy 기반 솔루션

### Komoran
```python
from konlpy.tag import Komoran
komoran = Komoran()
pos_tags = komoran.pos("KR 기관의 최근 응답률 보여줘")
# NNP (고유명사) 태그 추출
```

### Mecab-ko
```python
from konlpy.tag import Mecab
mecab = Mecab()
pos_tags = mecab.pos("한국선급의 응답률은?")
```

**장점**: 가볍고 빠름
**단점**: 단순 품사 태깅, 도메인 특화 엔티티 인식 한계

## 2. 딥러닝 기반 NER

### KoELECTRA + NER
```python
from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch

model_name = "monologg/koelectra-base-v3-naver-ner"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForTokenClassification.from_pretrained(model_name)

def extract_entities(text):
    inputs = tokenizer(text, return_tensors="pt")
    outputs = model(**inputs)
    predictions = torch.argmax(outputs.logits, dim=-1)
    
    # 토큰별 엔티티 태그 추출
    tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
    tags = [model.config.id2label[p.item()] for p in predictions[0]]
    
    return list(zip(tokens, tags))
```

**엔티티 타입**: PER(인물), LOC(위치), ORG(조직), DAT(날짜), TIM(시간) 등

### Pororo NER
```python
from pororo import Pororo

ner = Pororo(task="ner", lang="ko")
entities = ner("KR 기관의 최근 30일간 응답률")
# [('KR', 'ORGANIZATION'), ('최근', 'DATE'), ('30일간', 'DATE')]
```

**장점**: 사용하기 쉬움, 한국어 특화
**단점**: 모델 크기가 큼

## 3. spaCy 한국어 모델

```python
import spacy

# 한국어 모델 설치: python -m spacy download ko_core_news_sm
nlp = spacy.load("ko_core_news_sm")
doc = nlp("한국선급에서 3개월 전 제출한 아젠다")

for ent in doc.ents:
    print(ent.text, ent.label_)
```

## 4. 도메인 특화 NER 구현 (추천)

질의 처리에 최적화된 커스텀 NER 구현:

```python
import re
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum

class EntityType(Enum):
    ORGANIZATION = "ORG"      # 기관명
    TIME_PERIOD = "TIME"      # 시간 표현
    STATUS = "STATUS"         # 상태값
    QUANTITY = "QUANTITY"     # 수량
    KEYWORD = "KEYWORD"       # 검색 키워드
    AGENDA_ID = "AGENDA_ID"   # 아젠다 ID

@dataclass
class NamedEntity:
    text: str
    entity_type: EntityType
    normalized_value: Any
    start_pos: int
    end_pos: int
    confidence: float = 1.0

class DomainNER:
    """질의 처리 도메인에 특화된 NER"""
    
    def __init__(self, preprocessing_repo=None):
        self.preprocessing_repo = preprocessing_repo
        
        # 도메인 특화 패턴
        self.patterns = {
            EntityType.ORGANIZATION: [
                (r'\b(KR|BV|CCS|DNV|LR|ABS|RINA|NK|PRS|IRS|CRS)\b', 1.0),
                (r'(한국선급|뷰로베리타스|중국선급)', 0.9),
            ],
            EntityType.TIME_PERIOD: [
                (r'(\d+)\s*(일|주|개월|달|년|년간)\s*(전|동안|간)?', 0.95),
                (r'(오늘|어제|최근|이번주|지난주|이번달|지난달|올해|작년)', 0.9),
                (r'(\d{4}[-./]\d{1,2}[-./]\d{1,2})', 1.0),  # 날짜
            ],
            EntityType.STATUS: [
                (r'(승인|허가|반려|거부|거절|미결정|대기|보류)', 0.95),
            ],
            EntityType.QUANTITY: [
                (r'(\d+)\s*개', 0.9),
                (r'(전체|모든|일부)', 0.8),
            ],
            EntityType.AGENDA_ID: [
                (r'(PL\d{5})', 1.0),  # PL12345 형식
            ]
        }
        
    def extract_entities(self, text: str) -> List[NamedEntity]:
        """텍스트에서 엔티티 추출"""
        entities = []
        
        # 1. 패턴 기반 추출
        for entity_type, patterns in self.patterns.items():
            for pattern, confidence in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entity = NamedEntity(
                        text=match.group(0),
                        entity_type=entity_type,
                        normalized_value=self._normalize_entity(
                            match.group(0), entity_type
                        ),
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=confidence
                    )
                    entities.append(entity)
        
        # 2. 전처리 데이터셋 활용 (동의어 매핑)
        if self.preprocessing_repo:
            entities.extend(self._extract_from_preprocessing(text))
        
        # 3. 중복 제거 및 정렬
        entities = self._resolve_overlaps(entities)
        
        return sorted(entities, key=lambda e: e.start_pos)
    
    def _normalize_entity(self, text: str, entity_type: EntityType) -> Any:
        """엔티티 정규화"""
        if entity_type == EntityType.ORGANIZATION:
            # 조직명 매핑
            org_map = {
                "한국선급": "KR",
                "뷰로베리타스": "BV",
                "중국선급": "CCS",
            }
            return org_map.get(text, text.upper())
            
        elif entity_type == EntityType.TIME_PERIOD:
            # 시간 표현을 일수로 변환
            time_match = re.search(r'(\d+)\s*(일|주|개월|달|년)', text)
            if time_match:
                value = int(time_match.group(1))
                unit = time_match.group(2)
                
                if unit in ["주"]:
                    return value * 7
                elif unit in ["개월", "달"]:
                    return value * 30
                elif unit in ["년", "년간"]:
                    return value * 365
                else:
                    return value
            
            # 상대 시간 표현
            relative_map = {
                "오늘": 0,
                "어제": 1,
                "최근": 7,
                "이번주": 7,
                "지난주": 14,
                "이번달": 30,
                "지난달": 60,
                "올해": 365,
                "작년": 730
            }
            return relative_map.get(text, text)
            
        elif entity_type == EntityType.STATUS:
            # 상태값 정규화
            status_map = {
                "승인": "approved",
                "허가": "approved",
                "반려": "rejected",
                "거부": "rejected",
                "거절": "rejected",
                "미결정": "pending",
                "대기": "pending",
                "보류": "pending"
            }
            return status_map.get(text, text)
            
        return text
    
    def _extract_from_preprocessing(self, text: str) -> List[NamedEntity]:
        """전처리 데이터셋을 활용한 엔티티 추출"""
        entities = []
        
        # preprocessing_dataset에서 패턴 매칭
        terms = self.preprocessing_repo.get_all_active_terms()
        
        for term in terms:
            if term.is_pattern:
                # 패턴 매칭
                pattern = re.compile(term.pattern_regex, re.IGNORECASE)
                for match in pattern.finditer(text):
                    entity_type = self._map_term_type_to_entity(term.term_type)
                    if entity_type:
                        entities.append(NamedEntity(
                            text=match.group(0),
                            entity_type=entity_type,
                            normalized_value=term.normalized_term,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            confidence=0.85
                        ))
            else:
                # 정확한 매칭
                if term.original_term.lower() in text.lower():
                    start = text.lower().find(term.original_term.lower())
                    entity_type = self._map_term_type_to_entity(term.term_type)
                    if entity_type:
                        entities.append(NamedEntity(
                            text=term.original_term,
                            entity_type=entity_type,
                            normalized_value=term.normalized_term,
                            start_pos=start,
                            end_pos=start + len(term.original_term),
                            confidence=0.9
                        ))
        
        return entities
    
    def _map_term_type_to_entity(self, term_type: str) -> Optional[EntityType]:
        """전처리 term_type을 EntityType으로 매핑"""
        mapping = {
            "organization": EntityType.ORGANIZATION,
            "time_expression": EntityType.TIME_PERIOD,
            "status": EntityType.STATUS,
        }
        return mapping.get(term_type)
    
    def _resolve_overlaps(self, entities: List[NamedEntity]) -> List[NamedEntity]:
        """중복되는 엔티티 해결 (높은 신뢰도 우선)"""
        if not entities:
            return entities
            
        # 신뢰도 순으로 정렬
        entities.sort(key=lambda e: e.confidence, reverse=True)
        
        resolved = []
        used_positions = set()
        
        for entity in entities:
            # 위치가 겹치는지 확인
            positions = set(range(entity.start_pos, entity.end_pos))
            if not positions & used_positions:
                resolved.append(entity)
                used_positions.update(positions)
        
        return resolved

# 사용 예시
def demonstrate_ner():
    ner = DomainNER()
    
    test_queries = [
        "KR 기관의 최근 30일간 응답률 보여줘",
        "지난달 한국선급에서 승인된 아젠다 목록",
        "PL12345 아젠다의 상태는?",
        "3개월 전부터 현재까지 반려된 건수"
    ]
    
    for query in test_queries:
        print(f"\n질의: {query}")
        entities = ner.extract_entities(query)
        for entity in entities:
            print(f"  - {entity.text} ({entity.entity_type.value}): {entity.normalized_value}")
```

## 5. 하이브리드 접근법 (추천)

```python
class HybridNER:
    """규칙 기반 + ML 기반 하이브리드 NER"""
    
    def __init__(self):
        # 도메인 특화 NER
        self.domain_ner = DomainNER()
        
        # ML 기반 NER (선택적)
        try:
            from pororo import Pororo
            self.ml_ner = Pororo(task="ner", lang="ko")
        except:
            self.ml_ner = None
    
    def extract_entities(self, text: str) -> List[NamedEntity]:
        # 1. 도메인 특화 추출 (우선순위 높음)
        domain_entities = self.domain_ner.extract_entities(text)
        
        # 2. ML 기반 추출 (보완용)
        if self.ml_ner:
            ml_entities = self._convert_ml_entities(
                self.ml_ner(text), text
            )
            
            # 도메인 엔티티로 커버되지 않은 부분만 추가
            for ml_entity in ml_entities:
                if not self._is_covered(ml_entity, domain_entities):
                    domain_entities.append(ml_entity)
        
        return sorted(domain_entities, key=lambda e: e.start_pos)
```

## 권장 사항

1. **초기 단계**: 도메인 특화 규칙 기반 NER 구현
   - 빠르고 정확한 도메인 엔티티 인식
   - preprocessing_dataset 테이블 활용

2. **고도화 단계**: 하이브리드 접근
   - 규칙 기반 + ML 모델 조합
   - 새로운 패턴 학습 및 추가

3. **성능 고려사항**:
   - 규칙 기반: 빠름, 도메인 특화
   - ML 기반: 느림, 일반화 능력