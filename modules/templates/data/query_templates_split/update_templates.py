#!/usr/bin/env python3
import json
import os

def create_sql_prompt(natural_questions, template_id):
    """natural_questions 기반으로 간결한 sql_prompt 생성"""
    # 첫 번째 natural question을 기반으로 작성
    if not natural_questions:
        return "데이터베이스에서 관련 정보를 조회합니다."
    
    first_question = natural_questions[0]
    
    # 템플릿별 맞춤 sql_prompt 생성
    prompt_map = {
        "monthly_agenda_response_status": "월별 의제 발송 및 응답 현황을 집계하기 위해 agenda_all과 agenda_responses_content를 조인합니다. 월별로 그룹화하여 총 의제 수와 응답 받은 의제 수를 계산하고, 응답률 추이를 파악할 수 있도록 합니다.",
        "pending_agenda_error_reasons": "자동 분류되지 못한 메일의 오류 원인을 파악하기 위해 agenda_pending 테이블을 조회합니다. error_reason별로 그룹화하여 각 오류 유형의 발생 빈도를 분석하고, 시스템 개선이 필요한 부분을 식별합니다.",
        "incomplete_agendas_last_30days": "최근 30일간 마감일이 남아있는 미완료 의제를 조회하기 위해 agenda_chair 테이블에서 진행중인 REQUEST 타입 의제를 필터링합니다. 마감일과 응답 상태를 확인하여 긴급 처리가 필요한 의제를 파악합니다."
    }
    
    # 기본 패턴 적용
    if "월별" in first_question or "monthly" in template_id:
        return f"월별 {first_question.split('월별')[1] if '월별' in first_question else '통계'}를 집계하기 위해 관련 테이블을 조회하고 월별로 그룹화합니다."
    elif "미완료" in first_question or "incomplete" in template_id:
        return f"아직 완료되지 않은 의제들을 찾기 위해 진행 상태와 마감일을 기준으로 필터링합니다. {first_question}를 위한 조회를 수행합니다."
    elif "응답" in first_question and "필요" in first_question:
        return f"특정 조직이 응답해야 하는 의제를 찾기 위해 response_org 조건과 응답 상태를 확인합니다. {first_question}를 위한 데이터를 추출합니다."
    elif "통계" in first_question or "집계" in first_question:
        return f"{first_question}를 위해 관련 데이터를 집계하고 그룹화합니다."
    elif "검색" in first_question or "찾" in first_question:
        return f"{first_question}를 위해 키워드나 조건을 기반으로 데이터를 검색합니다."
    else:
        return f"{first_question}를 위해 필요한 데이터를 조회하고 정렬합니다."

def create_to_agent(natural_questions, template_category):
    """natural_questions와 category 기반으로 구조화된 to_agent 생성"""
    
    # 카테고리별 기본 분석 구조
    if template_category == "agenda_statistics":
        return """통계 데이터를 다음과 같이 분석해주세요:
1. 전체 통계 수치와 주요 지표 요약
2. 시간대별/기간별 추이 분석
3. 상위/하위 그룹 식별 및 특징
4. 전년 대비 또는 전월 대비 변화율
5. 특이사항 및 개선 제안"""
    
    elif template_category == "organization_response":
        return """조직의 응답 현황을 다음과 같이 분석해주세요:
1. 응답 필요 의제 수와 응답률
2. 마감일별 긴급도 분류
3. 주요 미응답 의제 내용 요약
4. 타 조직 대비 응답 성과
5. 우선 처리 필요 의제 추천"""
    
    elif template_category == "agenda_analysis":
        return """의제 분석 결과를 다음과 같이 정리해주세요:
1. 주요 의제별 핵심 내용 요약
2. 이해관계자별 입장 정리
3. 쟁점 사항 및 리스크 분석
4. 예상되는 영향 및 파급효과
5. 대응 전략 및 권고사항"""
    
    elif template_category == "keyword_analysis":
        return """키워드 분석 결과를 다음과 같이 정리해주세요:
1. 상위 빈출 키워드와 출현 횟수
2. 키워드 클러스터 및 주제 그룹
3. 시간대별 키워드 트렌드
4. 신규 출현 키워드 식별
5. 키워드 기반 이슈 예측"""
    
    elif template_category == "agenda_search":
        return """검색 결과를 다음과 같이 정리해주세요:
1. 검색된 의제 수와 분포
2. 관련도 높은 상위 의제 요약
3. 시간순/중요도순 정렬 결과
4. 검색 키워드별 매칭 현황
5. 추가 검색 키워드 제안"""
    
    elif template_category == "agenda_status":
        return """의제 상태를 다음과 같이 분석해주세요:
1. 상태별 의제 분포 현황
2. 진행 지연 의제 식별
3. 완료 예정 의제 현황
4. 병목 구간 분석
5. 프로세스 개선 제안"""
    
    else:
        # 기본 구조
        return """조회 결과를 다음과 같이 분석해주세요:
1. 전체 데이터 요약 및 주요 수치
2. 중요 항목 우선순위 정렬
3. 패턴 및 트렌드 분석
4. 이상 징후 또는 특이사항
5. 후속 조치 권고사항"""

def update_template_file(filepath):
    """템플릿 파일 업데이트"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        updated = False
        for template in data.get('templates', []):
            # natural_questions 가져오기
            natural_questions = template.get('query_info', {}).get('natural_questions', [])
            template_id = template.get('template_id', '')
            template_category = template.get('template_category', '')
            
            # sql_prompt 업데이트
            if 'sql_template' in template:
                new_sql_prompt = create_sql_prompt(natural_questions, template_id)
                template['sql_template']['sql_prompt'] = new_sql_prompt
                updated = True
            
            # to_agent 업데이트
            new_to_agent = create_to_agent(natural_questions, template_category)
            template['to_agent'] = new_to_agent
            updated = True
        
        if updated:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Updated: {filepath}")
        
        return updated
    
    except Exception as e:
        print(f"Error updating {filepath}: {e}")
        return False

def main():
    """모든 템플릿 파일 업데이트"""
    template_dir = "/home/kimghw/IACSGRAPH/modules/templates/data/query_templates_split"
    
    for i in range(1, 10):
        filename = f"query_templates_part_{i:03d}.json"
        filepath = os.path.join(template_dir, filename)
        
        if os.path.exists(filepath):
            update_template_file(filepath)
        else:
            print(f"File not found: {filepath}")

if __name__ == "__main__":
    main()