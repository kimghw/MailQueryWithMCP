"""Template Parameter Validator for Query Templates v2"""

import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """파라미터 검증 결과"""
    is_valid: bool
    missing_params: List[str]
    error_message: Optional[str]
    processed_params: Dict[str, Any]

class TemplateParameterValidator:
    """템플릿 파라미터 검증 및 처리 클래스"""
    
    def __init__(self, template: Dict[str, Any]):
        self.template = template
        self.required_params = self._get_param_names(template.get("parameters", {}).get("required_params", []))
        self.optional_params = self._get_param_names(template.get("parameters", {}).get("optional_params", []))
        self.default_params = template.get("parameters", {}).get("default_params", {})
    
    def _get_param_names(self, params: List[Dict[str, Any]]) -> List[str]:
        """파라미터 리스트에서 이름만 추출"""
        return [p["name"] for p in params if isinstance(p, dict) and "name" in p]
    
    def validate_and_process(self, provided_params: Dict[str, Any]) -> ValidationResult:
        """
        제공된 파라미터를 검증하고 처리
        
        Args:
            provided_params: 사용자가 제공한 파라미터
            
        Returns:
            ValidationResult: 검증 결과 및 처리된 파라미터
        """
        # 1. 필수 파라미터 확인
        missing_required = []
        for required_param in self.required_params:
            if required_param not in provided_params or provided_params[required_param] is None:
                missing_required.append(required_param)
        
        # 필수 파라미터가 누락된 경우
        if missing_required:
            error_msg = self._generate_error_message(missing_required)
            return ValidationResult(
                is_valid=False,
                missing_params=missing_required,
                error_message=error_msg,
                processed_params={}
            )
        
        # 2. 파라미터 병합 (제공된 값 + 기본값)
        processed_params = self.default_params.copy()
        
        # 제공된 파라미터로 업데이트
        for param_name, param_value in provided_params.items():
            if param_value is not None:  # None이 아닌 값만 업데이트
                processed_params[param_name] = param_value
        
        # 3. 유효한 파라미터만 필터링 (required + optional에 있는 것만)
        valid_param_names = set(self.required_params + self.optional_params)
        filtered_params = {k: v for k, v in processed_params.items() 
                          if k in valid_param_names and v is not None}
        
        return ValidationResult(
            is_valid=True,
            missing_params=[],
            error_message=None,
            processed_params=filtered_params
        )
    
    def _generate_error_message(self, missing_params: List[str]) -> str:
        """누락된 필수 파라미터에 대한 에러 메시지 생성"""
        param_descriptions = self._get_param_descriptions()
        
        if len(missing_params) == 1:
            param = missing_params[0]
            desc = param_descriptions.get(param, "")
            return f"필수 파라미터가 누락되었습니다: '{param}' - {desc}"
        else:
            param_list = []
            for param in missing_params:
                desc = param_descriptions.get(param, "")
                param_list.append(f"  - '{param}': {desc}")
            
            return f"다음 필수 파라미터들이 누락되었습니다:\n" + "\n".join(param_list)
    
    def _get_param_descriptions(self) -> Dict[str, str]:
        """파라미터 설명 추출"""
        descriptions = {}
        
        # required_params에서 설명 추출
        for param in self.template.get("parameters", {}).get("required_params", []):
            if isinstance(param, dict):
                descriptions[param["name"]] = param.get("description", "설명 없음")
        
        # optional_params에서 설명 추출
        for param in self.template.get("parameters", {}).get("optional_params", []):
            if isinstance(param, dict):
                descriptions[param["name"]] = param.get("description", "설명 없음")
        
        return descriptions
    
    def format_sql_query(self, params: Dict[str, Any]) -> str:
        """파라미터를 사용하여 SQL 쿼리 포맷팅"""
        query_template = self.template.get("sql_template", {}).get("query", "")
        
        try:
            # 문자열 포맷팅
            formatted_query = query_template.format(**params)
            return formatted_query
        except KeyError as e:
            return f"쿼리 포맷팅 오류: 파라미터 {e}가 쿼리에 필요하지만 제공되지 않았습니다"


# 사용 예시
def process_template_query(template: Dict[str, Any], user_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    템플릿과 사용자 파라미터를 처리하여 쿼리 실행 준비
    
    Returns:
        Dict containing:
        - success: bool
        - query: formatted SQL query (if success)
        - error: error message (if failed)
        - params: processed parameters (if success)
    """
    validator = TemplateParameterValidator(template)
    validation_result = validator.validate_and_process(user_params)
    
    if not validation_result.is_valid:
        return {
            "success": False,
            "error": validation_result.error_message,
            "missing_params": validation_result.missing_params
        }
    
    # SQL 쿼리 포맷팅
    formatted_query = validator.format_sql_query(validation_result.processed_params)
    
    return {
        "success": True,
        "query": formatted_query,
        "params": validation_result.processed_params
    }


# 테스트 코드
if __name__ == "__main__":
    # 템플릿 로드
    with open("template_v2_format.json", "r", encoding="utf-8") as f:
        template = json.load(f)
    
    print("=== 템플릿 파라미터 검증 테스트 ===\n")
    
    # 테스트 1: 필수 파라미터 누락
    print("테스트 1: 필수 파라미터 누락")
    result1 = process_template_query(template, {})
    print(f"결과: {json.dumps(result1, ensure_ascii=False, indent=2)}\n")
    
    # 테스트 2: 필수 파라미터만 제공
    print("테스트 2: 필수 파라미터만 제공")
    result2 = process_template_query(template, {"organization_code": "KR"})
    print(f"결과: {json.dumps(result2, ensure_ascii=False, indent=2)}\n")
    
    # 테스트 3: 일부 선택 파라미터 제공
    print("테스트 3: 필수 + 일부 선택 파라미터 제공")
    result3 = process_template_query(template, {
        "organization_code": "US",
        "dates": 60,
        "status": "ongoing"
    })
    print(f"결과: {json.dumps(result3, ensure_ascii=False, indent=2)}\n")
    
    # 테스트 4: 모든 파라미터 제공
    print("테스트 4: 모든 파라미터 제공")
    result4 = process_template_query(template, {
        "organization_code": "JP",
        "dates": 90,
        "keywords": "security",
        "status": "completed",
        "response_required": False,
        "response_status": "responded"
    })
    print(f"결과: {json.dumps(result4, ensure_ascii=False, indent=2)}")