"""Parameter validation and suggestion service"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re

from ..schema import QueryTemplate
from ..services.db_connector import DBConnector

logger = logging.getLogger(__name__)


class ParameterValidator:
    """Validates required parameters and suggests examples from database"""
    
    def __init__(self, db_connector: DBConnector):
        self.db_connector = db_connector
        
    def validate_and_suggest(
        self, 
        template: QueryTemplate,
        extracted_params: Dict[str, Any],
        user_query: str
    ) -> Dict[str, Any]:
        """Validate parameters and provide suggestions if missing
        
        Returns:
            Dict with:
                - is_valid: bool
                - missing_params: List[str]
                - suggestions: Dict[param_name, List[examples]]
                - clarification_message: str
        """
        missing_params = []
        suggestions = {}
        
        # Check for missing required parameters
        for param in template.required_params:
            if param not in extracted_params:
                missing_params.append(param)
                # Get suggestions for this parameter
                suggestions[param] = self._get_parameter_suggestions(param, template)
        
        # Build clarification message
        clarification_message = ""
        if missing_params:
            clarification_message = self._build_clarification_message(
                missing_params, 
                suggestions,
                template
            )
        
        return {
            "is_valid": len(missing_params) == 0,
            "missing_params": missing_params,
            "suggestions": suggestions,
            "clarification_message": clarification_message,
            "template_info": {
                "id": template.id,
                "natural_query": template.natural_query,
                "category": template.category
            }
        }
    
    def _get_parameter_suggestions(self, param_name: str, template: QueryTemplate) -> List[Any]:
        """Get example values for a parameter from the database"""
        suggestions = []
        
        try:
            if param_name == "organization":
                # Get list of organizations from database
                # Get available organizations
                sql = """
                    WITH org_list AS (
                        SELECT 'ABS' as org WHERE EXISTS (SELECT 1 FROM agenda_responses_content WHERE ABS IS NOT NULL LIMIT 1)
                        UNION ALL
                        SELECT 'BV' WHERE EXISTS (SELECT 1 FROM agenda_responses_content WHERE BV IS NOT NULL LIMIT 1)
                        UNION ALL
                        SELECT 'CCS' WHERE EXISTS (SELECT 1 FROM agenda_responses_content WHERE CCS IS NOT NULL LIMIT 1)
                        UNION ALL
                        SELECT 'CRS' WHERE EXISTS (SELECT 1 FROM agenda_responses_content WHERE CRS IS NOT NULL LIMIT 1)
                        UNION ALL
                        SELECT 'DNV' WHERE EXISTS (SELECT 1 FROM agenda_responses_content WHERE DNV IS NOT NULL LIMIT 1)
                        UNION ALL
                        SELECT 'IRS' WHERE EXISTS (SELECT 1 FROM agenda_responses_content WHERE IRS IS NOT NULL LIMIT 1)
                        UNION ALL
                        SELECT 'KR' WHERE EXISTS (SELECT 1 FROM agenda_responses_content WHERE KR IS NOT NULL LIMIT 1)
                        UNION ALL
                        SELECT 'NK' WHERE EXISTS (SELECT 1 FROM agenda_responses_content WHERE NK IS NOT NULL LIMIT 1)
                        UNION ALL
                        SELECT 'PRS' WHERE EXISTS (SELECT 1 FROM agenda_responses_content WHERE PRS IS NOT NULL LIMIT 1)
                        UNION ALL
                        SELECT 'RINA' WHERE EXISTS (SELECT 1 FROM agenda_responses_content WHERE RINA IS NOT NULL LIMIT 1)
                        UNION ALL
                        SELECT 'LR' WHERE EXISTS (SELECT 1 FROM agenda_responses_content WHERE LR IS NOT NULL LIMIT 1)
                    )
                    SELECT org FROM org_list ORDER BY org
                """
                results = self.db_connector.execute_query(sql)
                suggestions = [row['org'] for row in results if row['org']]
                
            elif param_name == "status":
                # Get available statuses
                sql = """
                    SELECT DISTINCT decision_status 
                    FROM agenda_chair 
                    WHERE decision_status IS NOT NULL
                    ORDER BY decision_status
                """
                results = self.db_connector.execute_query(sql)
                suggestions = [row['decision_status'] for row in results]
                
            elif param_name == "period":
                # Suggest common periods
                suggestions = ["7일", "30일", "90일", "1년", "전체"]
                
            elif param_name == "keyword":
                # Get recent keywords from subjects
                sql = """
                    SELECT DISTINCT subject
                    FROM agenda_chair
                    WHERE sent_time >= datetime('now', '-30 days')
                    ORDER BY sent_time DESC
                    LIMIT 5
                """
                results = self.db_connector.execute_query(sql)
                # Extract key terms from subjects
                for row in results:
                    subject = row['subject']
                    # Extract meaningful keywords
                    keywords = re.findall(r'[A-Z]{2,}|MSC|IMO|IACS|\w{4,}', subject)
                    suggestions.extend(keywords[:2])
                suggestions = list(set(suggestions))[:10]
                
            elif param_name == "priority":
                # Get priority values
                suggestions = ["high", "medium", "low", "urgent", "높음", "중간", "낮음", "긴급"]
                
        except Exception as e:
            logger.error(f"Error getting suggestions for {param_name}: {e}")
            
        return suggestions
    
    def _build_clarification_message(
        self, 
        missing_params: List[str],
        suggestions: Dict[str, List[Any]],
        template: QueryTemplate
    ) -> str:
        """Build a user-friendly clarification message"""
        
        messages = []
        messages.append("🔍 추가 정보가 필요합니다:")
        messages.append("")
        
        # Show the template pattern
        messages.append(f"선택된 쿼리 패턴: '{template.natural_questions}'")
        messages.append("")
        
        # Explain each missing parameter
        param_descriptions = {
            "organization": "기관 코드",
            "status": "결정 상태",
            "period": "조회 기간",
            "keyword": "검색 키워드",
            "priority": "우선순위"
        }
        
        for param in missing_params:
            desc = param_descriptions.get(param, param)
            messages.append(f"❓ **{desc}** ({param})가 필요합니다.")
            
            if param in suggestions and suggestions[param]:
                messages.append(f"   예시: {', '.join(str(s) for s in suggestions[param][:5])}")
                if len(suggestions[param]) > 5:
                    messages.append(f"   ... 외 {len(suggestions[param]) - 5}개")
            messages.append("")
        
        # Provide example queries
        messages.append("💡 다음과 같이 질문해주세요:")
        
        # Generate example based on template
        if "organization" in missing_params:
            orgs = suggestions.get("organization", ["KR"])[:3]
            for org in orgs:
                example = template.natural_questions.replace("{organization}", org)
                messages.append(f"   - {example}")
                
        elif "period" in missing_params:
            periods = suggestions.get("period", ["30일"])[:2]
            for period in periods:
                example = template.natural_questions.replace("{period}", period)
                messages.append(f"   - {example}")
                
        elif "status" in missing_params:
            statuses = suggestions.get("status", ["created"])[:2]
            for status in statuses:
                example = template.natural_questions.replace("{status}", status)
                messages.append(f"   - {example}")
        
        return "\n".join(messages)
    
    def extract_parameters_with_context(
        self,
        query: str,
        template: QueryTemplate,
        previous_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract parameters considering previous context"""
        
        params = {}
        
        # If we have previous context, use it as defaults
        if previous_context:
            params.update(previous_context)
        
        # Extract new parameters from current query
        # This would be enhanced with more sophisticated NLP
        
        # Organization extraction
        if "organization" in template.required_params:
            orgs = self._get_parameter_suggestions("organization", template)
            for org in orgs:
                if org.lower() in query.lower():
                    params["organization"] = org
                    break
        
        # Period extraction
        if "period" in template.required_params:
            period_patterns = [
                (r'(\d+)\s*일', lambda m: (f"{m.group(1)}일", int(m.group(1)))),
                (r'(\d+)\s*주', lambda m: (f"{m.group(1)}주", int(m.group(1)) * 7)),
                (r'(\d+)\s*개월', lambda m: (f"{m.group(1)}개월", int(m.group(1)) * 30)),
                (r'(\d+)\s*년', lambda m: (f"{m.group(1)}년", int(m.group(1)) * 365)),
            ]
            
            for pattern, extractor in period_patterns:
                match = re.search(pattern, query)
                if match:
                    period_str, days = extractor(match)
                    params["period"] = period_str
                    params["days"] = days
                    break
        
        return params