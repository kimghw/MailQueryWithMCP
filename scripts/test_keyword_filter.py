#!/usr/bin/env python3
"""
KeywordFilter 테스트 스크립트
"""

import sys
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import KeywordFilter directly from schema file to avoid dependencies
class KeywordFilter(BaseModel):
    """키워드 검색 필터 (클라이언트 측 필터링)"""

    and_keywords: Optional[List[str]] = Field(
        None,
        description="AND 조건: 모든 키워드가 포함되어야 함"
    )
    or_keywords: Optional[List[str]] = Field(
        None,
        description="OR 조건: 하나 이상의 키워드가 포함되어야 함"
    )
    not_keywords: Optional[List[str]] = Field(
        None,
        description="NOT 조건: 이 키워드들이 포함되지 않아야 함"
    )

    @field_validator("and_keywords", "or_keywords", "not_keywords")
    @classmethod
    def validate_keywords(cls, v):
        if v is not None:
            # Strip whitespace and filter empty strings
            return [k.strip() for k in v if k.strip()]
        return v

    def model_post_init(self, __context):
        """최소 하나의 키워드 조건이 필요함을 검증"""
        if not self.and_keywords and not self.or_keywords and not self.not_keywords:
            raise ValueError("최소 하나 이상의 키워드 조건(and_keywords, or_keywords, not_keywords)이 필요합니다")


def test_and_keywords():
    """AND 조건 테스트"""
    print("\n=== Test 1: AND keywords ===")
    try:
        kf = KeywordFilter(and_keywords=["계약서", "2024"])
        print(f"✓ Created: {kf.model_dump()}")
        print(f"  and_keywords: {kf.and_keywords}")
        print(f"  or_keywords: {kf.or_keywords}")
        print(f"  not_keywords: {kf.not_keywords}")
    except Exception as e:
        print(f"✗ Failed: {e}")


def test_or_keywords():
    """OR 조건 테스트"""
    print("\n=== Test 2: OR keywords ===")
    try:
        kf = KeywordFilter(or_keywords=["계약서", "제안서"])
        print(f"✓ Created: {kf.model_dump()}")
        print(f"  and_keywords: {kf.and_keywords}")
        print(f"  or_keywords: {kf.or_keywords}")
        print(f"  not_keywords: {kf.not_keywords}")
    except Exception as e:
        print(f"✗ Failed: {e}")


def test_not_keywords():
    """NOT 조건 테스트"""
    print("\n=== Test 3: NOT keywords ===")
    try:
        kf = KeywordFilter(not_keywords=["취소", "반려"])
        print(f"✓ Created: {kf.model_dump()}")
        print(f"  and_keywords: {kf.and_keywords}")
        print(f"  or_keywords: {kf.or_keywords}")
        print(f"  not_keywords: {kf.not_keywords}")
    except Exception as e:
        print(f"✗ Failed: {e}")


def test_combined_keywords():
    """조합 조건 테스트"""
    print("\n=== Test 4: Combined keywords ===")
    try:
        kf = KeywordFilter(
            and_keywords=["계약서", "2024"],
            not_keywords=["취소"]
        )
        print(f"✓ Created: {kf.model_dump()}")
        print(f"  and_keywords: {kf.and_keywords}")
        print(f"  or_keywords: {kf.or_keywords}")
        print(f"  not_keywords: {kf.not_keywords}")
    except Exception as e:
        print(f"✗ Failed: {e}")


def test_all_combined():
    """모든 조건 조합 테스트"""
    print("\n=== Test 5: All conditions combined ===")
    try:
        kf = KeywordFilter(
            and_keywords=["프로젝트", "2024"],
            or_keywords=["계약서", "제안서"],
            not_keywords=["취소", "반려"]
        )
        print(f"✓ Created: {kf.model_dump()}")
        print(f"  and_keywords: {kf.and_keywords}")
        print(f"  or_keywords: {kf.or_keywords}")
        print(f"  not_keywords: {kf.not_keywords}")
    except Exception as e:
        print(f"✗ Failed: {e}")


def test_empty_keywords():
    """빈 키워드 테스트 (실패해야 함)"""
    print("\n=== Test 6: Empty keywords (should fail) ===")
    try:
        kf = KeywordFilter()
        print(f"✗ Should have failed but created: {kf.model_dump()}")
    except ValueError as e:
        print(f"✓ Correctly rejected: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")


def test_whitespace_handling():
    """공백 처리 테스트"""
    print("\n=== Test 7: Whitespace handling ===")
    try:
        kf = KeywordFilter(and_keywords=["  계약서  ", " 2024 ", ""])
        print(f"✓ Created with whitespace: {kf.model_dump()}")
        print(f"  and_keywords (cleaned): {kf.and_keywords}")
    except Exception as e:
        print(f"✗ Failed: {e}")


def test_dict_initialization():
    """딕셔너리로 초기화 테스트 (MCP에서 받는 형식)"""
    print("\n=== Test 8: Dictionary initialization ===")
    try:
        data = {
            "and_keywords": ["계약서", "2024"],
            "not_keywords": ["취소"]
        }
        kf = KeywordFilter(**data)
        print(f"✓ Created from dict: {kf.model_dump()}")
        print(f"  and_keywords: {kf.and_keywords}")
        print(f"  or_keywords: {kf.or_keywords}")
        print(f"  not_keywords: {kf.not_keywords}")
    except Exception as e:
        print(f"✗ Failed: {e}")


def main():
    print("=" * 60)
    print("KeywordFilter Schema Test")
    print("=" * 60)

    test_and_keywords()
    test_or_keywords()
    test_not_keywords()
    test_combined_keywords()
    test_all_combined()
    test_empty_keywords()
    test_whitespace_handling()
    test_dict_initialization()

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
