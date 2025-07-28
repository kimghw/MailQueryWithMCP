#!/usr/bin/env python3
"""
Script to update sql_prompt and to_agent fields in all query template files
"""

import json
import os

def generate_concise_sql_prompt(template):
    """Generate a concise sql_prompt based on the template"""
    natural_questions = template.get('query_info', {}).get('natural_questions', [])
    query = template.get('sql_template', {}).get('query', '')
    
    # Extract key information from the query
    if 'agenda_chair' in query:
        table = "agenda_chair"
    elif 'agenda_responses_content' in query:
        table = "agenda_responses_content"
    elif 'agenda_responses_receivedtime' in query:
        table = "agenda_responses_receivedtime"
    else:
        table = "agenda"
    
    # Analyze query conditions
    conditions = []
    if 'mail_type' in query:
        if "'REQUEST'" in query:
            conditions.append("REQUEST 타입")
        elif "'NOTIFICATION'" in query:
            conditions.append("NOTIFICATION 타입")
    
    if 'has_deadline' in query and 'has_deadline = 1' in query:
        conditions.append("마감일 있는")
    
    if 'deadline > DATE' in query:
        conditions.append("진행중인")
    elif 'deadline < DATE' in query:
        conditions.append("마감 지난")
    
    if 'response_completed = 0' in query:
        conditions.append("미응답")
    elif 'response_completed = 1' in query:
        conditions.append("응답완료")
    
    if natural_questions:
        main_question = natural_questions[0]
        if "3개월" in main_question:
            time_context = "최근 3개월간"
        elif "6개월" in main_question:
            time_context = "최근 6개월간"
        elif "1년" in main_question or "12개월" in main_question:
            time_context = "최근 1년간"
        elif "최근" in main_question:
            time_context = "최근"
        else:
            time_context = ""
    else:
        time_context = ""
    
    # Build concise prompt
    prompt_parts = []
    if time_context:
        prompt_parts.append(time_context)
    
    if conditions:
        prompt_parts.append(" ".join(conditions))
    
    if "의제" in str(natural_questions):
        prompt_parts.append("의제")
    elif "응답" in str(natural_questions):
        prompt_parts.append("응답")
    
    prompt_parts.append("조회")
    
    if 'ORDER BY' in query:
        if 'DESC' in query:
            prompt_parts.append("(최신순)")
        else:
            prompt_parts.append("(오래된순)")
    
    return f"{table} 테이블에서 {' '.join(prompt_parts)}."

def generate_structured_to_agent(template):
    """Generate structured to_agent instructions based on the template"""
    natural_questions = template.get('query_info', {}).get('natural_questions', [])
    category = template.get('template_category', '')
    
    # Determine the type of analysis needed
    if 'agenda_status' in category or '미완료' in str(natural_questions) or '완료되지' in str(natural_questions):
        return """조회된 결과를 다음과 같이 분석해주세요:
1. 전체 미완료 의제 수와 마감일별 분포
2. 우선순위가 높은 긴급 의제 (마감 7일 이내)
3. 응답 대상 조직별 미완료 현황
4. 주요 키워드 및 주제별 분류
5. 처리 지연 리스크가 있는 의제 식별"""
    
    elif 'time_based' in category or '최근' in str(natural_questions) or '개월' in str(natural_questions):
        return """조회된 결과를 다음과 같이 분석해주세요:
1. 기간별 의제 발생 추이 분석
2. 주요 의제 유형 및 빈도
3. 핵심 키워드 및 트렌드 변화
4. 응답 요청 대상별 분포
5. 전체적인 업무 패턴 및 인사이트"""
    
    elif 'organization_response' in category or '응답' in str(natural_questions):
        return """조회된 결과를 다음과 같이 분석해주세요:
1. 조직별 응답 현황 요약
2. 미응답 의제의 긴급도 평가
3. 응답 지연 사유 분석 (가능한 경우)
4. 주요 미응답 의제의 내용 정리
5. 후속 조치 필요 사항"""
    
    elif 'deadline' in category or '마감' in str(natural_questions):
        return """조회된 결과를 다음과 같이 분석해주세요:
1. 마감일별 의제 분포 현황
2. 긴급 처리 필요 의제 (D-3 이내)
3. 마감 임박 의제의 주요 내용
4. 응답 대상별 마감 현황
5. 리스크 관리 필요 사항"""
    
    elif 'completed' in category or '완료' in str(natural_questions):
        return """조회된 결과를 다음과 같이 분석해주세요:
1. 완료된 의제의 전체 통계
2. 의제 유형별 완료 현황
3. 주요 완료 의제의 결과 요약
4. 처리 기간 분석
5. 향후 참고할 만한 인사이트"""
    
    else:
        # Default structured analysis
        return """조회된 결과를 다음과 같이 분석해주세요:
1. 전체 데이터 개요 및 주요 통계
2. 핵심 항목별 분류 및 정리
3. 주요 패턴 및 트렌드 분석
4. 특이사항 및 주목할 점
5. 실행 가능한 인사이트 도출"""

def update_template_file(file_path):
    """Update sql_prompt and to_agent fields in a template file"""
    print(f"Processing {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    updated_count = 0
    
    for template in data.get('templates', []):
        # Update sql_prompt
        if 'sql_template' in template and 'sql_prompt' in template['sql_template']:
            old_prompt = template['sql_template']['sql_prompt']
            new_prompt = generate_concise_sql_prompt(template)
            template['sql_template']['sql_prompt'] = new_prompt
            updated_count += 1
            print(f"  Updated sql_prompt for {template.get('template_id', 'unknown')}")
        
        # Update to_agent
        if 'to_agent' in template:
            old_agent = template['to_agent']
            new_agent = generate_structured_to_agent(template)
            template['to_agent'] = new_agent
            print(f"  Updated to_agent for {template.get('template_id', 'unknown')}")
    
    # Write updated data back to file
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"  Total templates updated: {updated_count}\n")
    return updated_count

def main():
    """Main function to update all template files"""
    base_path = "/home/kimghw/IACSGRAPH/modules/templates/data/query_templates_split"
    total_updated = 0
    
    for i in range(1, 10):
        file_name = f"query_templates_part_{i:03d}.json"
        file_path = os.path.join(base_path, file_name)
        
        if os.path.exists(file_path):
            updated = update_template_file(file_path)
            total_updated += updated
        else:
            print(f"File not found: {file_path}")
    
    print(f"\nTotal templates updated across all files: {total_updated}")

if __name__ == "__main__":
    main()