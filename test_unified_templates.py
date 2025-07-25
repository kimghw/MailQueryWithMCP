#!/usr/bin/env python3
import json
import sys
import os
from datetime import datetime

def test_unified_templates():
    """통합 템플릿 파일 테스트"""
    template_path = 'modules/query_assistant/templates_v2/query_templates_unified.json'
    
    print("=" * 80)
    print("🔍 통합 템플릿 테스트")
    print("=" * 80)
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n✅ 템플릿 파일 로드 성공!")
        print(f"📊 파일 버전: {data.get('version', 'N/A')}")
        print(f"📊 전체 템플릿 수: {data.get('total_templates', 0)}")
        
        templates = data.get('templates', [])
        
        # 메타데이터 표시
        metadata = data.get('metadata', {})
        print(f"\n📋 메타데이터:")
        print(f"  - 포함된 버전: {', '.join(metadata.get('includes_versions', []))}")
        print(f"  - 표준화 여부: {metadata.get('standardized', False)}")
        
        # 카테고리별 분석
        categories = metadata.get('categories', {})
        
        print(f"\n📋 카테고리별 템플릿 수:")
        for category, count in sorted(categories.items()):
            print(f"  - {category}: {count}개")
        
        # 라우팅 타입별 분석
        routing_types = metadata.get('routing_types', {})
        print(f"\n📊 라우팅 타입별 분포:")
        for rtype, count in sorted(routing_types.items()):
            print(f"  - {rtype}: {count}개")
        
        # 필수 필드 검증 (새로운 구조에 맞게 수정)
        required_fields = ['template_id', 'template_category', 'query_info', 'sql_template']
        missing_fields = []
        
        for i, template in enumerate(templates):
            for field in required_fields:
                if field not in template:
                    missing_fields.append(f"템플릿 {template.get('template_id', f'인덱스_{i}')}: {field} 누락")
        
        if missing_fields:
            print(f"\n⚠️  필수 필드 누락:")
            for missing in missing_fields[:10]:  # 처음 10개만 표시
                print(f"  - {missing}")
            if len(missing_fields) > 10:
                print(f"  ... 외 {len(missing_fields) - 10}개")
        else:
            print(f"\n✅ 모든 템플릿이 필수 필드를 포함하고 있습니다.")
        
        # 우선순위 분포
        priorities = {}
        for template in templates:
            priority = template.get('priority', 0)
            priorities[priority] = priorities.get(priority, 0) + 1
        
        print(f"\n📊 우선순위 분포:")
        for priority in sorted(priorities.keys(), reverse=True):
            print(f"  - Priority {priority}: {priorities[priority]}개")
        
        # 샘플 템플릿 표시 (새로운 구조에 맞게 수정)
        print(f"\n📝 샘플 템플릿 (첫 3개):")
        for i, template in enumerate(templates[:3]):
            print(f"\n[템플릿 {i+1}]")
            print(f"  ID: {template.get('template_id', 'N/A')}")
            print(f"  카테고리: {template.get('template_category', 'N/A')}")
            print(f"  버전: {template.get('template_version', 'N/A')}")
            
            query_info = template.get('query_info', {})
            keywords = query_info.get('keywords', [])
            questions = query_info.get('natural_questions', [])
            
            print(f"  키워드: {', '.join(keywords[:5])}")
            if len(keywords) > 5:
                print(f"         ... 외 {len(keywords) - 5}개")
            
            if questions:
                print(f"  쿼리 예시: {questions[0]}")
            
            target_scope = template.get('target_scope', {})
            print(f"  대상 범위: {target_scope.get('scope_type', 'N/A')}")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ 템플릿 파일을 찾을 수 없습니다: {template_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {e}")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False

if __name__ == "__main__":
    success = test_unified_templates()
    sys.exit(0 if success else 1)