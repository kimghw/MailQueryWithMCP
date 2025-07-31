#!/usr/bin/env python3
import json
import re
import sys

def update_template_file(filename):
    # Read the file
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Update version
    data['version'] = '2.0.0'
    
    # Process each template
    for template in data['templates']:
        template['template_version'] = '2.0.0'
        
        # Update SQL queries
        if 'sql_template' in template and 'query' in template['sql_template'] and template['sql_template']['query'] is not None:
            query = template['sql_template']['query']
            
            # Replace {period_condition} with sent_time >= :period_start
            query = re.sub(r'\{period_condition\}', 'sent_time >= :period_start', query)
            query = re.sub(r'AND c\.\{period_condition\}', 'AND c.sent_time >= :period_start', query)
            query = re.sub(r'WHERE \{period_condition\}', 'WHERE sent_time >= :period_start', query)
            
            # Replace {keywords_condition} with simple LIKE conditions
            query = re.sub(r'\{keywords_condition\}', "(subject LIKE '%' || :keyword || '%' OR body LIKE '%' || :keyword || '%' OR keywords LIKE '%' || :keyword || '%')", query)
            
            # Replace {organization} with :organization
            query = re.sub(r'\{organization\}', ':organization', query)
            
            # Replace other placeholders
            query = re.sub(r'\{keyword\}', ':keyword', query)
            query = re.sub(r'\{panel\}', ':panel', query)
            query = re.sub(r'\{days_period\}', ':days_period', query)
            query = re.sub(r'\{agenda\}', ':agenda', query)
            
            template['sql_template']['query'] = query
        
        # Update parameters
        if 'parameters' in template:
            new_params = []
            for param in template['parameters']:
                if param['type'] == 'period':
                    # Convert period to datetime parameter
                    days = 90
                    if 'default' in param and isinstance(param['default'], dict) and 'days' in param['default']:
                        days = param['default']['days']
                    new_params.append({
                        'name': 'period_start',
                        'type': 'datetime',
                        'required': False,
                        'default': f"datetime('now', '-{days} days')",
                        'description': '조회 시작 날짜',
                        'mcp_format': param.get('mcp_format', 'extracted_period')
                    })
                elif param['type'] == 'array' and param['name'] == 'keywords':
                    # Convert keywords array to single keyword with multi_query
                    default_val = param.get('default', ['keyword'])[0] if isinstance(param.get('default'), list) else 'keyword'
                    new_params.append({
                        'name': 'keyword',
                        'type': 'string',
                        'required': param.get('required', True),
                        'default': default_val,
                        'multi_query': True,
                        'description': '검색할 키워드',
                        'mcp_format': param.get('mcp_format', 'extracted_keywords')
                    })
                else:
                    # Keep other parameters but remove sql_builder
                    new_param = {k: v for k, v in param.items() if k != 'sql_builder'}
                    new_params.append(new_param)
            template['parameters'] = new_params
    
    # Write back the file
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f'Updated {filename} to v2.0.0')

if __name__ == '__main__':
    if len(sys.argv) > 1:
        update_template_file(sys.argv[1])
    else:
        # Update multiple files
        files_to_update = [
            'query_templates_group_003.json',
            'query_templates_group_004.json',
            'query_templates_group_005.json',
            'query_templates_group_006.json',
            'query_templates_group_007.json',
            'query_templates_group_008.json',
            'query_templates_group_009.json'
        ]
        for filename in files_to_update:
            try:
                update_template_file(filename)
            except Exception as e:
                print(f'Error updating {filename}: {str(e)}')