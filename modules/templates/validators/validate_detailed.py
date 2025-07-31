#!/usr/bin/env python3
"""Generate detailed validation report with specific examples"""

import json
import re
from pathlib import Path
from datetime import datetime
from template_validator import TemplateValidator
from parameter_validator import ParameterValidator


def find_issue_in_sql(sql_query, issue_type):
    """Find specific issue in SQL query and return context"""
    if not sql_query:
        return None
        
    lines = sql_query.split('\n') if '\n' in sql_query else [sql_query]
    
    for i, line in enumerate(lines):
        if issue_type == "lowercase_request":
            if "'request'" in line.lower() and "'REQUEST'" not in line:
                # Find the position
                pos = line.lower().find("'request'")
                start = max(0, pos - 20)
                end = min(len(line), pos + 30)
                return f"...{line[start:end]}..."
        elif issue_type == "old_params":
            matches = re.findall(r'\{(\w+)\}', line)
            if matches:
                return f"Found {{{{matches[0]}}}} in: ...{line[:60]}..."
        elif issue_type == "dynamic_ref":
            if "r.:" in line:
                pos = line.find("r.:")
                start = max(0, pos - 20)
                end = min(len(line), pos + 30)
                return f"...{line[start:end]}..."
    
    return None


def main():
    template_dir = Path('/home/kimghw/IACSGRAPH/modules/templates/data/query_templates_split')
    
    print("=" * 80)
    print("IACSGRAPH Detailed Validation Report")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    validator = TemplateValidator()
    
    # Focus on specific issues
    lowercase_issues = []
    old_param_issues = []
    empty_sql_issues = []
    missing_field_issues = []
    
    for file_path in sorted(template_dir.glob('query_templates_group_*.json')):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        templates = data.get('templates', [])
        
        for template in templates:
            template_id = template.get('template_id', 'unknown')
            sql_query = template.get('sql_template', {}).get('query', '')
            
            # Check for lowercase 'request'
            if sql_query and "'request'" in sql_query.lower() and "'REQUEST'" not in sql_query:
                context = find_issue_in_sql(sql_query, "lowercase_request")
                lowercase_issues.append({
                    'file': file_path.name,
                    'template': template_id,
                    'context': context
                })
            
            # Check for old parameter format
            if sql_query and re.search(r'\{(\w+)\}', sql_query):
                context = find_issue_in_sql(sql_query, "old_params")
                old_param_issues.append({
                    'file': file_path.name,
                    'template': template_id,
                    'context': context
                })
            
            # Check for empty SQL
            if not sql_query:
                empty_sql_issues.append({
                    'file': file_path.name,
                    'template': template_id,
                    'routing_type': template.get('routing_type', 'unknown')
                })
            
            # Check for missing to_agent
            if not template.get('to_agent'):
                missing_field_issues.append({
                    'file': file_path.name,
                    'template': template_id,
                    'field': 'to_agent'
                })
    
    # Print detailed findings
    print("\n1. LOWERCASE 'request' ISSUES")
    print("-" * 80)
    if lowercase_issues:
        for issue in lowercase_issues[:5]:
            print(f"\nFile: {issue['file']}")
            print(f"Template: {issue['template']}")
            print(f"Context: {issue['context']}")
        if len(lowercase_issues) > 5:
            print(f"\n... and {len(lowercase_issues) - 5} more")
    else:
        print("No lowercase 'request' issues found!")
    
    print("\n\n2. OLD PARAMETER FORMAT ISSUES")
    print("-" * 80)
    if old_param_issues:
        for issue in old_param_issues[:5]:
            print(f"\nFile: {issue['file']}")
            print(f"Template: {issue['template']}")
            print(f"Context: {issue['context']}")
    else:
        print("No old parameter format issues found!")
    
    print("\n\n3. EMPTY SQL QUERY ISSUES")
    print("-" * 80)
    if empty_sql_issues:
        for issue in empty_sql_issues[:10]:
            print(f"File: {issue['file']}, Template: {issue['template']}, Type: {issue['routing_type']}")
    else:
        print("No empty SQL issues found!")
    
    print("\n\n4. MISSING FIELD ISSUES")
    print("-" * 80)
    if missing_field_issues:
        for issue in missing_field_issues[:5]:
            print(f"File: {issue['file']}, Template: {issue['template']}, Missing: {issue['field']}")
    else:
        print("No missing field issues found!")
    
    # Let's also check actual SQL content for a few templates
    print("\n\n5. SAMPLE SQL QUERIES")
    print("-" * 80)
    
    # Check kr_no_response_ongoing_agendas specifically
    test_templates = ['kr_no_response_ongoing_agendas', 'kr_response_required_agendas', 'pending_agenda_count']
    
    for file_path in sorted(template_dir.glob('query_templates_group_001.json')):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        templates = data.get('templates', [])
        
        for template in templates:
            template_id = template.get('template_id')
            if template_id in test_templates:
                sql_query = template.get('sql_template', {}).get('query', '')
                print(f"\n{template_id}:")
                print(f"SQL (first 200 chars): {sql_query[:200]}...")
                
                # Check for mail_type patterns
                mail_type_matches = re.findall(r"mail_type\s*=\s*'(\w+)'", sql_query, re.IGNORECASE)
                if mail_type_matches:
                    print(f"Found mail_type values: {mail_type_matches}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()