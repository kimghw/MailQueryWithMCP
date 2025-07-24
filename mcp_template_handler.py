"""MCP Server Template Handler with Parameter Validation"""

import json
from typing import Dict, Any, Optional
from template_parameter_validator import TemplateParameterValidator

class MCPTemplateHandler:
    """MCP 서버용 템플릿 핸들러"""
    
    def __init__(self):
        self.templates = {}
        self._load_templates()
    
    def _load_templates(self):
        """템플릿 파일 로드"""
        # 실제로는 데이터베이스나 파일에서 로드
        try:
            with open("agenda_query_templates_v2_examples.json", "r", encoding="utf-8") as f:
                templates_list = json.load(f)
                for template in templates_list:
                    self.templates[template["template_id"]] = template
        except Exception as e:
            print(f"템플릿 로드 실패: {e}")
    
    def process_query(self, template_id: str, user_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        템플릿 ID와 사용자 파라미터로 쿼리 처리
        
        Returns:
            성공 시: {
                "status": "success",
                "template_id": "...",
                "sql_query": "...",
                "parameters": {...}
            }
            실패 시: {
                "status": "error", 
                "error": "에러 메시지",
                "missing_params": [...]
            }
        """
        # 템플릿 찾기
        if template_id not in self.templates:
            return {
                "status": "error",
                "error": f"템플릿을 찾을 수 없습니다: {template_id}"
            }
        
        template = self.templates[template_id]
        validator = TemplateParameterValidator(template)
        
        # 파라미터 검증
        validation_result = validator.validate_and_process(user_params)
        
        if not validation_result.is_valid:
            return {
                "status": "error",
                "error": validation_result.error_message,
                "missing_params": validation_result.missing_params,
                "template_id": template_id,
                "required_params": validator.required_params
            }
        
        # SQL 쿼리 생성
        try:
            formatted_query = validator.format_sql_query(validation_result.processed_params)
            
            return {
                "status": "success",
                "template_id": template_id,
                "sql_query": formatted_query,
                "parameters": validation_result.processed_params,
                "category": template.get("template_category", "unknown")
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"쿼리 생성 중 오류 발생: {str(e)}",
                "template_id": template_id
            }
    
    def get_template_info(self, template_id: str) -> Optional[Dict[str, Any]]:
        """템플릿 정보 반환"""
        if template_id not in self.templates:
            return None
        
        template = self.templates[template_id]
        validator = TemplateParameterValidator(template)
        
        return {
            "template_id": template_id,
            "category": template.get("template_category"),
            "natural_questions": template.get("query_info", {}).get("natural_questions", []),
            "required_params": validator.required_params,
            "optional_params": validator.optional_params,
            "default_params": validator.default_params
        }


# 사용 예시
def demo_mcp_handler():
    """MCP 핸들러 데모"""
    handler = MCPTemplateHandler()
    
    print("=== MCP 템플릿 핸들러 데모 ===\n")
    
    # 예시 1: 필수 파라미터 누락
    print("1. 필수 파라미터 누락 시나리오:")
    result1 = handler.process_query("kr_response_required_agendas_v2", {})
    print(json.dumps(result1, ensure_ascii=False, indent=2))
    
    print("\n2. 올바른 파라미터 제공:")
    result2 = handler.process_query("kr_response_required_agendas_v2", {
        "organization_code": "KR"
    })
    if result2["status"] == "success":
        print(f"생성된 SQL: {result2['sql_query']}")
    
    print("\n3. 템플릿 정보 조회:")
    info = handler.get_template_info("kr_response_required_agendas_v2")
    print(json.dumps(info, ensure_ascii=False, indent=2))
    
    print("\n4. 키워드 검색 템플릿 (필수 파라미터 있음):")
    result3 = handler.process_query("keyword_based_agenda_search_v2", {
        "keywords": "보안"
    })
    if result3["status"] == "success":
        print(f"생성된 SQL: {result3['sql_query']}")
    else:
        print(f"에러: {result3['error']}")


if __name__ == "__main__":
    demo_mcp_handler()