#!/usr/bin/env python3
"""Analyze and classify template parameters"""

import json
import glob
from collections import defaultdict
from typing import Dict, List, Any

def analyze_template_parameters():
    """Extract and analyze all parameters from template files"""
    
    # Store all parameters
    all_parameters = defaultdict(lambda: {
        'type': set(),
        'required_count': 0,
        'optional_count': 0,
        'default_values': set(),
        'templates': [],
        'types_by_template': {}
    })
    
    # Process all template files
    template_files = glob.glob('/home/kimghw/IACSGRAPH/modules/templates/data/query_templates_split/*.json')
    
    total_templates = 0
    
    for file_path in template_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for template in data.get('templates', []):
            total_templates += 1
            template_id = template.get('template_id', 'unknown')
            
            for param in template.get('parameters', []):
                param_name = param.get('name', '')
                param_type = param.get('type', 'unknown')
                is_required = param.get('required', True)
                default_value = param.get('default')
                
                # Update parameter info
                param_info = all_parameters[param_name]
                param_info['type'].add(param_type)
                param_info['templates'].append(template_id)
                param_info['types_by_template'][template_id] = {
                    'type': param_type,
                    'required': is_required
                }
                
                if is_required:
                    param_info['required_count'] += 1
                else:
                    param_info['optional_count'] += 1
                    
                if default_value:
                    param_info['default_values'].add(str(default_value))
    
    # Generate report
    print("=== 템플릿 파라미터 분석 보고서 ===\n")
    print(f"총 템플릿 수: {total_templates}")
    print(f"고유 파라미터 수: {len(all_parameters)}\n")
    
    # Classify parameters
    required_params = []
    optional_params = []
    mixed_params = []
    
    for param_name, info in all_parameters.items():
        total_usage = info['required_count'] + info['optional_count']
        
        if info['required_count'] > 0 and info['optional_count'] == 0:
            required_params.append((param_name, info, total_usage))
        elif info['required_count'] == 0 and info['optional_count'] > 0:
            optional_params.append((param_name, info, total_usage))
        else:
            mixed_params.append((param_name, info, total_usage))
    
    # Sort by usage frequency
    required_params.sort(key=lambda x: x[2], reverse=True)
    optional_params.sort(key=lambda x: x[2], reverse=True)
    mixed_params.sort(key=lambda x: x[2], reverse=True)
    
    # Print classification
    print("=== 필수 파라미터 (항상 required=true) ===")
    for param_name, info, usage in required_params:
        types = ', '.join(sorted(info['type']))
        print(f"- {param_name}")
        print(f"  타입: {types}")
        print(f"  사용 횟수: {usage}개 템플릿")
        print(f"  사용 템플릿 수: {len(info['templates'])}개")
        print()
    
    print("\n=== 선택적 파라미터 (항상 required=false) ===")
    for param_name, info, usage in optional_params:
        types = ', '.join(sorted(info['type']))
        defaults = ', '.join(sorted(info['default_values'])) if info['default_values'] else 'None'
        print(f"- {param_name}")
        print(f"  타입: {types}")
        print(f"  사용 횟수: {usage}개 템플릿")
        print(f"  기본값: {defaults}")
        print(f"  사용 템플릿 수: {len(info['templates'])}개")
        print()
    
    print("\n=== 혼합 파라미터 (템플릿에 따라 필수/선택) ===")
    for param_name, info, usage in mixed_params:
        types = ', '.join(sorted(info['type']))
        print(f"- {param_name}")
        print(f"  타입: {types}")
        print(f"  필수로 사용: {info['required_count']}회")
        print(f"  선택으로 사용: {info['optional_count']}회")
        print(f"  사용 템플릿 수: {len(info['templates'])}개")
        print()
    
    # Summary statistics
    print("\n=== 요약 통계 ===")
    print(f"필수 파라미터: {len(required_params)}개")
    print(f"선택적 파라미터: {len(optional_params)}개")
    print(f"혼합 파라미터: {len(mixed_params)}개")
    
    # Parameter types distribution
    type_count = defaultdict(int)
    for param_name, info in all_parameters.items():
        for ptype in info['type']:
            type_count[ptype] += 1
    
    print("\n=== 파라미터 타입 분포 ===")
    for ptype, count in sorted(type_count.items(), key=lambda x: x[1], reverse=True):
        print(f"- {ptype}: {count}개")
    
    return all_parameters

if __name__ == "__main__":
    analyze_template_parameters()