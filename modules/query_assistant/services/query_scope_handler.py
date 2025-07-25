"""
Query Scope Handler for determining query coverage
Handles 'all', 'one', 'more' scope extraction and processing
"""
from typing import Dict, Any, Optional, List, Tuple
import re
import logging

logger = logging.getLogger(__name__)


class QueryScopeHandler:
    """Handle query scope determination and processing"""
    
    # Scope types
    SCOPE_ALL = "all"    # 모든 패널/기관
    SCOPE_ONE = "one"    # 단일 패널/기관
    SCOPE_MORE = "more"  # 2개 이상의 패널/기관
    
    # Keywords indicating scope
    ALL_KEYWORDS = {
        'korean': ['모든', '전체', '전부', '각', '모두', '전', '다'],
        'english': ['all', 'every', 'each', 'entire', 'whole', 'total']
    }
    
    MULTI_KEYWORDS = {
        'korean': ['여러', '다수', '복수', '몇몇', '일부'],
        'english': ['multiple', 'several', 'various', 'many', 'some']
    }
    
    @staticmethod
    def extract_scope_from_query(query: str) -> Tuple[str, List[str]]:
        """
        Extract scope from query text using rule-based approach
        
        Returns:
            Tuple of (scope, detected_keywords)
        """
        query_lower = query.lower()
        detected_keywords = []
        
        # Check for ALL scope keywords
        for lang_keywords in QueryScopeHandler.ALL_KEYWORDS.values():
            for keyword in lang_keywords:
                if keyword in query_lower:
                    detected_keywords.append(keyword)
        
        if detected_keywords:
            return QueryScopeHandler.SCOPE_ALL, detected_keywords
        
        # Check for MULTI scope keywords
        for lang_keywords in QueryScopeHandler.MULTI_KEYWORDS.values():
            for keyword in lang_keywords:
                if keyword in query_lower:
                    detected_keywords.append(keyword)
        
        if detected_keywords:
            return QueryScopeHandler.SCOPE_MORE, detected_keywords
        
        # Count mentioned organizations
        organizations = QueryScopeHandler._extract_organizations(query)
        panels = QueryScopeHandler._extract_panels(query)
        
        total_entities = len(organizations) + len(panels)
        
        if total_entities == 0:
            # No specific entity mentioned, could be all or context-dependent
            return QueryScopeHandler.SCOPE_ALL, []
        elif total_entities == 1:
            return QueryScopeHandler.SCOPE_ONE, organizations + panels
        else:
            return QueryScopeHandler.SCOPE_MORE, organizations + panels
    
    @staticmethod
    def _extract_organizations(query: str) -> List[str]:
        """Extract organization codes from query"""
        org_patterns = {
            'KR': r'\b(kr|한국선급|korean\s+register|한국)\b',
            'BV': r'\b(bv|bureau\s+veritas|뷰로베리타스)\b',
            'CCS': r'\b(ccs|중국선급|china\s+classification)\b',
            'ABS': r'\b(abs|american\s+bureau)\b',
            'DNV': r'\b(dnv|dnv\s+gl)\b',
            'LR': r'\b(lr|lloyd|로이드)\b',
            'US': r'\b(us|미국|united\s+states)\b',
            'JP': r'\b(jp|일본|japan)\b',
            'CN': r'\b(cn|중국|china)\b'
        }
        
        found_orgs = []
        query_lower = query.lower()
        
        for org_code, pattern in org_patterns.items():
            if re.search(pattern, query_lower, re.IGNORECASE):
                found_orgs.append(org_code)
        
        return found_orgs
    
    @staticmethod
    def _extract_panels(query: str) -> List[str]:
        """Extract panel codes from query"""
        panel_patterns = {
            'PL': r'\b(pl|panel|패널)\b',
            'UR': r'\b(ur|uniform\s+requirement)\b',
            'PR': r'\b(pr|procedural\s+requirement)\b',
            'SC': r'\b(sc|small\s+craft)\b',
            'PT': r'\b(pt|panel\s+technical)\b',
            'GPG': r'\b(gpg|general\s+policy\s+group)\b',
            'EG': r'\b(eg|expert\s+group)\b'
        }
        
        found_panels = []
        query_lower = query.lower()
        
        for panel_code, pattern in panel_patterns.items():
            if re.search(pattern, query_lower, re.IGNORECASE):
                found_panels.append(panel_code)
        
        return found_panels
    
    @staticmethod
    def process_scope_parameter(
        llm_scope: Optional[str],
        query: str,
        extracted_orgs: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Process scope parameter from LLM and query
        
        Args:
            llm_scope: Scope extracted by LLM ('all', 'one', 'more')
            query: Original query text
            extracted_orgs: Organizations extracted from query
            
        Returns:
            Dictionary with processed scope information
        """
        # Use LLM scope if provided, otherwise extract from query
        if llm_scope and llm_scope in [QueryScopeHandler.SCOPE_ALL, 
                                       QueryScopeHandler.SCOPE_ONE, 
                                       QueryScopeHandler.SCOPE_MORE]:
            scope = llm_scope
            logger.info(f"Using LLM-provided scope: {scope}")
        else:
            scope, keywords = QueryScopeHandler.extract_scope_from_query(query)
            logger.info(f"Extracted scope from query: {scope} (keywords: {keywords})")
        
        # Build scope information
        scope_info = {
            'scope': scope,
            'organizations': extracted_orgs or [],
            'filter_type': None,
            'sql_condition': None
        }
        
        # Determine filter type and SQL condition based on scope
        if scope == QueryScopeHandler.SCOPE_ALL:
            scope_info['filter_type'] = 'none'  # No filtering needed
            scope_info['sql_condition'] = '1=1'  # Always true
            
        elif scope == QueryScopeHandler.SCOPE_ONE:
            if extracted_orgs and len(extracted_orgs) == 1:
                scope_info['filter_type'] = 'single'
                scope_info['sql_condition'] = f"organization = '{extracted_orgs[0]}'"
            else:
                # Fallback to KR if no specific org found
                scope_info['filter_type'] = 'single'
                scope_info['sql_condition'] = "organization = 'KR'"
                
        elif scope == QueryScopeHandler.SCOPE_MORE:
            if extracted_orgs and len(extracted_orgs) > 1:
                scope_info['filter_type'] = 'multiple'
                org_list = "', '".join(extracted_orgs)
                scope_info['sql_condition'] = f"organization IN ('{org_list}')"
            else:
                # If scope is 'more' but we don't have multiple orgs, treat as 'all'
                scope_info['filter_type'] = 'none'
                scope_info['sql_condition'] = '1=1'
        
        return scope_info
    
    @staticmethod
    def enhance_template_selection(
        templates: List[Dict[str, Any]],
        scope_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Enhance template selection based on scope
        
        Prioritize templates that match the scope type
        """
        if not templates:
            return templates
        
        scope = scope_info['scope']
        
        # Score templates based on scope match
        scored_templates = []
        for template in templates:
            score_boost = 0
            
            # Check template's target scope
            target_scope = template.get('target_scope', {})
            scope_type = target_scope.get('scope_type', 'all')
            
            # Boost score for matching scope
            if scope == QueryScopeHandler.SCOPE_ALL and scope_type == 'all':
                score_boost = 0.1
            elif scope == QueryScopeHandler.SCOPE_ONE and scope_type == 'specific_organization':
                score_boost = 0.15
            elif scope == QueryScopeHandler.SCOPE_MORE and scope_type == 'multiple_organizations':
                score_boost = 0.1
            
            # Apply boost to template
            if 'score' in template:
                template['score'] += score_boost
            
            scored_templates.append(template)
        
        # Sort by score
        scored_templates.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return scored_templates


# Example usage
if __name__ == "__main__":
    handler = QueryScopeHandler()
    
    test_queries = [
        "모든 패널의 진행중인 의제",  # all
        "KR이 응답하지 않은 의제",    # one
        "KR과 BV의 응답 현황",        # more
        "전체 기관의 평균 응답시간",   # all
        "진행중인 의제 목록",         # all (no specific entity)
        "여러 기관의 승인 현황"       # more
    ]
    
    print("Query Scope Extraction Test")
    print("="*50)
    
    for query in test_queries:
        scope, keywords = handler.extract_scope_from_query(query)
        print(f"\nQuery: {query}")
        print(f"Scope: {scope}")
        print(f"Keywords: {keywords}")
        
        # Process scope
        orgs = handler._extract_organizations(query)
        scope_info = handler.process_scope_parameter(None, query, orgs)
        print(f"SQL Condition: {scope_info['sql_condition']}")