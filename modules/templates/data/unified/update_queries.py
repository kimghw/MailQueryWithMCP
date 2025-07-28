#!/usr/bin/env python3
"""
Update SQL queries in query_templates_unified.json based on database schema requirements.

Key Rules:
1. For response-required: Use agenda_chair with mail_type='REQUEST' AND has_deadline=1
2. For incomplete/ongoing: deadline > DATE('now')
3. For completed: deadline <= DATE('now')
4. Organization responses: Use CASE statements for dynamic column access
5. If user wants deadline info, must use agenda_chair table
6. If querying responses, must JOIN with agenda_responses_content
7. Always use proper table aliases (ac for agenda_chair, a for agenda_all, arc for responses)
"""

import json
import re
from typing import Dict, List, Any
import copy

def load_json(file_path: str) -> Dict:
    """Load JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data: Dict, file_path: str):
    """Save JSON file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def needs_deadline_info(query: str, natural_questions: List[str], keywords: List[str]) -> bool:
    """Check if query needs deadline information."""
    deadline_indicators = [
        'deadline', '마감', '기한', '응답요청', '응답 요청', '미완료', '완료되지',
        '진행중', '대기중', 'ongoing', 'incomplete', 'pending', 'response required'
    ]
    
    # Check in query
    query_lower = query.lower()
    for indicator in deadline_indicators:
        if indicator in query_lower:
            return True
    
    # Check in natural questions and keywords
    all_text = ' '.join(natural_questions + keywords).lower()
    for indicator in deadline_indicators:
        if indicator in all_text:
            return True
    
    return False

def needs_response_info(query: str, natural_questions: List[str], keywords: List[str]) -> bool:
    """Check if query needs response information."""
    response_indicators = [
        'response', '응답', '회신', '답변', 'agenda_responses', 'arc.',
        '조직별', '기관별', 'organization response'
    ]
    
    # Check in query
    query_lower = query.lower()
    for indicator in response_indicators:
        if indicator in query_lower:
            return True
    
    # Check in natural questions and keywords
    all_text = ' '.join(natural_questions + keywords).lower()
    for indicator in response_indicators:
        if indicator in all_text:
            return True
    
    return False

def fix_table_references(query: str) -> str:
    """Fix table references to use proper aliases."""
    # Determine which table is being used
    main_table = None
    if 'FROM agenda_chair ac' in query:
        main_table = 'agenda_chair'
        alias = 'ac'
    elif 'FROM agenda_all a' in query:
        main_table = 'agenda_all'
        alias = 'a'
    else:
        return query  # Don't modify if table pattern not recognized
    
    # Fields that need aliasing
    fields = [
        'agenda_base_version', 'agenda_code', 'subject', 'sender_organization',
        'sent_time', 'decision_status', 'response_org', 'keywords', 'created_at',
        'sender_type', 'mail_type', 'has_deadline', 'deadline'
    ]
    
    # Add alias to unaliased fields
    for field in fields:
        # Skip if field is already aliased
        pattern = rf'\b(?<![.\w]){field}\b(?!\s*\()'
        
        # Check if this field should use a different alias
        if field in ['deadline', 'has_deadline', 'mail_type'] and main_table == 'agenda_all':
            # These fields only exist in agenda_chair
            continue
        
        query = re.sub(pattern, f'{alias}.{field}', query)
    
    # Fix any remaining unaliased table references
    query = re.sub(r'\bagenda_all\.', 'a.', query)
    query = re.sub(r'\bagenda_chair\.', 'ac.', query)
    query = re.sub(r'\bagenda_responses_content\.', 'arc.', query)
    
    return query

def update_query_for_deadline_requirements(template: Dict) -> Dict:
    """Update query to use agenda_chair when deadline information is needed."""
    query = template['sql_template']['query']
    natural_questions = template['query_info']['natural_questions']
    keywords = template['query_info']['keywords']
    
    if needs_deadline_info(query, natural_questions, keywords):
        # Check if query already uses agenda_chair
        if 'FROM agenda_all' in query and 'deadline' in query.lower():
            # Need to switch to agenda_chair
            new_query = query.replace('FROM agenda_all a', 'FROM agenda_chair ac')
            new_query = new_query.replace('FROM agenda_all', 'FROM agenda_chair ac')
            
            # Add required conditions for response-required queries
            if 'WHERE' in new_query:
                if 'mail_type' not in new_query:
                    new_query = new_query.replace('WHERE', "WHERE ac.mail_type = 'REQUEST' AND ac.has_deadline = 1 AND")
            else:
                new_query = new_query.replace('FROM agenda_chair ac', "FROM agenda_chair ac WHERE ac.mail_type = 'REQUEST' AND ac.has_deadline = 1")
            
            # Fix table aliases
            new_query = new_query.replace('a.', 'ac.')
            
            # Update for incomplete/ongoing
            if '미완료' in ' '.join(natural_questions) or 'incomplete' in ' '.join(natural_questions).lower():
                new_query = re.sub(r"ac\.deadline\s*[<>]=?\s*DATE\('now'\)", "ac.deadline > DATE('now')", new_query)
            
            # Update for completed
            elif '완료' in ' '.join(natural_questions) and '미완료' not in ' '.join(natural_questions):
                new_query = re.sub(r"ac\.deadline\s*[<>]=?\s*DATE\('now'\)", "ac.deadline <= DATE('now')", new_query)
            
            template['sql_template']['query'] = new_query
            
            # Update related_tables
            if 'related_tables' in template:
                if 'agenda_all' in template['related_tables']:
                    template['related_tables'].remove('agenda_all')
                if 'agenda_chair' not in template['related_tables']:
                    template['related_tables'].append('agenda_chair')
    
    return template

def update_query_for_response_requirements(template: Dict) -> Dict:
    """Update query to properly handle response information."""
    query = template['sql_template']['query']
    natural_questions = template['query_info']['natural_questions']
    keywords = template['query_info']['keywords']
    
    if needs_response_info(query, natural_questions, keywords):
        # Check if query needs to JOIN with agenda_responses_content
        if 'agenda_responses_content' not in query:
            # Check if we need to add JOIN
            needs_join = False
            if 'arc.' in query:
                needs_join = True
            for text in natural_questions + keywords:
                if any(word in text.lower() for word in ['응답', 'response', '답변', '회신']):
                    needs_join = True
                    break
            
            if needs_join:
                # Add JOIN if not present
                if 'FROM agenda_all a' in query and '\n' not in query:
                    query = query.replace(
                        'FROM agenda_all a',
                        'FROM agenda_all a\n                LEFT JOIN agenda_responses_content arc ON a.agenda_base_version = arc.agenda_base_version'
                    )
                elif 'FROM agenda_chair ac' in query and '\n' not in query:
                    query = query.replace(
                        'FROM agenda_chair ac',
                        'FROM agenda_chair ac\n                LEFT JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version'
                    )
        
        # Fix dynamic column references to use CASE statements
        org_columns = ['ABS', 'BV', 'CCS', 'CRS', 'DNV', 'IRS', 'KR', 'NK', 'PRS', 'RINA', 'IL', 'TL', 'LR']
        
        # Pattern for dynamic column reference like arc.{organization}
        dynamic_pattern = r'arc\.\{(\w+)\}'
        matches = re.findall(dynamic_pattern, query)
        
        for match in matches:
            param_name = match
            case_statement = f"CASE {{{param_name}}} "
            for org in org_columns:
                case_statement += f"WHEN '{org}' THEN arc.{org} "
            case_statement += "END"
            
            query = query.replace(f'arc.{{{param_name}}}', case_statement)
        
        # Also handle patterns like arc.{param} in WHERE clauses
        # Example: WHERE arc.{organization} IS NOT NULL
        where_pattern = r'WHERE.*arc\.\{(\w+)\}'
        if re.search(where_pattern, query):
            # Need to handle WHERE clause differently
            for match in matches:
                param_name = match
                # For WHERE clauses, we need to check all organizations
                case_conditions = []
                for org in org_columns:
                    case_conditions.append(f"({{{param_name}}} = '{org}' AND arc.{org} IS NOT NULL)")
                
                where_condition = f"({' OR '.join(case_conditions)})"
                query = re.sub(rf'arc\.\{{{param_name}\}}\s+IS\s+NOT\s+NULL', where_condition, query)
                query = re.sub(rf'arc\.\{{{param_name}\}}\s+IS\s+NULL', f"NOT {where_condition}", query)
        
        template['sql_template']['query'] = query
        
        # Update related_tables
        if 'related_tables' in template:
            if 'agenda_responses_content' not in template['related_tables']:
                template['related_tables'].append('agenda_responses_content')
    
    return template

def fix_specific_query_patterns(template: Dict) -> Dict:
    """Fix specific query patterns based on requirements."""
    query = template['sql_template']['query']
    
    # Fix sender_type references (should be sender_organization for agenda_all)
    if 'sender_type' in query and 'agenda_all' in query:
        query = query.replace("sender_type = 'CHAIR'", "sender_organization = 'Chair'")
    
    # Fix mail_type references for agenda_all (this field doesn't exist in agenda_all)
    if 'FROM agenda_all' in query and 'mail_type' in query:
        # This indicates the query should probably use agenda_chair instead
        template['sql_template']['query'] = query
        template = update_query_for_deadline_requirements(template)
        query = template['sql_template']['query']
    
    # Ensure proper table aliases are used
    query = fix_table_references(query)
    
    template['sql_template']['query'] = query
    return template

def update_parameters(template: Dict) -> Dict:
    """Update parameter field references to match table aliases."""
    if 'parameters' in template:
        for param in template['parameters']:
            if 'sql_builder' in param and 'field' in param['sql_builder']:
                field = param['sql_builder']['field']
                # Update field references based on the query's main table
                query = template['sql_template']['query']
                if 'FROM agenda_chair ac' in query:
                    param['sql_builder']['field'] = f'ac.{field}' if not field.startswith('ac.') else field
                elif 'FROM agenda_all a' in query:
                    param['sql_builder']['field'] = f'a.{field}' if not field.startswith('a.') else field
    
    return template

def process_templates(file_path: str):
    """Process all templates in the JSON file."""
    print("Loading query templates...")
    data = load_json(file_path)
    
    # Create backup
    backup_path = file_path.replace('.json', '_backup_before_update.json')
    save_json(data, backup_path)
    print(f"Created backup at: {backup_path}")
    
    # Process each template
    updated_count = 0
    sql_template_count = 0
    for i, template in enumerate(data['templates']):
        # Skip templates without sql_template (e.g., vectordb or llm_direct)
        if 'sql_template' not in template or 'query' not in template.get('sql_template', {}):
            continue
        
        sql_template_count += 1
        original_query = template['sql_template']['query']
        
        # Apply updates
        template = update_query_for_deadline_requirements(template)
        template = update_query_for_response_requirements(template)
        template = fix_specific_query_patterns(template)
        template = update_parameters(template)
        
        # Check if query was updated
        if template['sql_template']['query'] != original_query:
            updated_count += 1
            print(f"\nUpdated template {i+1}: {template['template_id']}")
            print(f"Original: {original_query[:100]}...")
            print(f"Updated: {template['sql_template']['query'][:100]}...")
    
    # Save updated file
    save_json(data, file_path)
    print(f"\nCompleted! Updated {updated_count} out of {sql_template_count} SQL templates.")
    print(f"Total templates in file: {len(data['templates'])}")
    print(f"Updated file saved to: {file_path}")

def main():
    """Main function."""
    file_path = "/home/kimghw/IACSGRAPH/modules/templates/data/unified/query_templates_unified.json"
    process_templates(file_path)

if __name__ == "__main__":
    main()