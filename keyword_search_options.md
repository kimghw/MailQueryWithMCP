# Keyword Search Implementation Options

## 현재 문제
현재 구현은 if-elif로 체크하기 때문에:
- `"계약서 AND 2024"` ✅ 작동
- `"계약서 OR 제안서"` ✅ 작동
- `"(계약서 OR 제안서) AND 2024"` ❌ AND만 체크되고 OR 무시됨

## 해결 방안

### 옵션 1: 복합 쿼리 파서 구현
**장점**: 복잡한 쿼리 지원, 괄호 지원
**단점**: 구현 복잡, 유지보수 어려움

```python
# 예: "(계약서 OR 제안서) AND 2024 NOT 초안"
# - 괄호 파싱
# - 연산자 우선순위 (NOT > AND > OR)
# - AST 빌드 필요
```

**구현 시간**: 2-3시간

---

### 옵션 2: 간단한 순차 파싱 (추천)
**장점**: 구현 간단, 대부분 케이스 커버
**단점**: 괄호 미지원

```python
# 파싱 순서:
# 1. 먼저 OR로 분리 → ["계약서 AND 2024", "제안서 AND 2024"]
# 2. 각 부분을 AND로 분리 → [["계약서", "2024"], ["제안서", "2024"]]
# 3. NOT 처리
# 4. 평가: (계약서 AND 2024) OR (제안서 AND 2024)

def parse_keyword(keyword: str):
    # Split by OR first (lowest priority)
    or_parts = keyword.split(" OR ")

    for or_part in or_parts:
        # Split by AND (higher priority)
        and_parts = or_part.split(" AND ")

        # Check if all AND parts match
        if all(part in text for part in and_parts):
            return True

    return False
```

**지원 쿼리**:
- ✅ `"계약서 AND 2024"`
- ✅ `"계약서 OR 제안서"`
- ✅ `"계약서 AND 2024 OR 제안서 AND 김철수"`
- ✅ `"프로젝트 NOT 취소"`
- ❌ `"(계약서 OR 제안서) AND 2024"` (괄호 없이 동일한 효과)

**구현 시간**: 30분

---

### 옵션 3: 구조화된 스키마 (가장 명확)
**장점**: 명확한 의도, 타입 안전
**단점**: 사용자가 구조 이해해야 함

```python
# mail_query_schema.py
class KeywordFilter(BaseModel):
    """키워드 검색 필터"""
    operator: str = Field("AND", description="연산자: AND, OR, NOT")
    keywords: List[str] = Field(..., description="검색 키워드 리스트")

class MailQueryFilters(BaseModel):
    keyword_filter: Optional[KeywordFilter] = None
```

**사용 예시**:
```python
# 계약서 AND 2024
keyword_filter = KeywordFilter(
    operator="AND",
    keywords=["계약서", "2024"]
)

# 계약서 OR 제안서
keyword_filter = KeywordFilter(
    operator="OR",
    keywords=["계약서", "제안서"]
)
```

**구현 시간**: 1시간

---

## 추천 방향

### 단기 (지금 바로): 옵션 2
- 빠르게 구현 가능
- 대부분의 사용 케이스 커버
- 직관적인 문자열 쿼리

### 장기 (나중에): 옵션 3
- 더 명확한 의도
- 타입 안전성
- 확장 가능

## 구현 예시 (옵션 2)

```python
def filter_by_keyword(self, messages: List, keyword: str) -> List:
    """키워드로 메시지 필터링 - 개선된 파서"""
    if not keyword:
        return messages

    filtered = []
    keyword = keyword.strip()

    # OR 우선 분리 (가장 낮은 우선순위)
    or_groups = self._split_by_operator(keyword, " OR ")

    for mail in messages:
        mail_text = self._get_searchable_text(mail).lower()

        # 하나의 OR 그룹이라도 매치되면 포함
        for or_group in or_groups:
            if self._match_and_group(mail_text, or_group):
                filtered.append(mail)
                break

    return filtered

def _match_and_group(self, text: str, group: str) -> bool:
    """AND 그룹 매칭"""
    # NOT 처리
    if " NOT " in group.upper():
        parts = group.split(" NOT ", 1)
        include = parts[0].strip()
        exclude = parts[1].strip() if len(parts) > 1 else ""

        # AND 처리
        and_parts = include.split(" AND ")
        include_match = all(p.strip().lower() in text for p in and_parts)
        exclude_match = exclude.lower() in text if exclude else False

        return include_match and not exclude_match

    # AND만 있는 경우
    and_parts = group.split(" AND ")
    return all(p.strip().lower() in text for p in and_parts)
```
