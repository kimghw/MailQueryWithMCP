"""Template structure and content validator - Updated for v2.0.0 guidelines"""

import re
import json
import logging
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class TemplateValidator:
    """Validate template structure and content based on creation_guidelines.md"""
    
    # Required fields for each template (v2.0.0)
    REQUIRED_FIELDS = [
        'template_id',
        'template_version',
        'template_category',
        'query_info',
        'target_scope',
        'sql_template',
        'parameters',
        'related_db',
        'related_tables',
        'routing_type',
        'to_agent'
    ]
    
    # Required fields in query_info
    QUERY_INFO_REQUIRED = ['natural_questions', 'keywords']
    
    # Required fields in sql_template
    SQL_TEMPLATE_REQUIRED = ['query', 'system', 'sql_prompt']
    
    # Required fields in target_scope
    TARGET_SCOPE_REQUIRED = ['scope_type', 'target_organizations', 'target_panels']
    
    # Valid categories from creation_guidelines.md
    VALID_CATEGORIES = [
        'agenda_status',       # 의제 상태 관련
        'response_tracking',   # 응답 추적
        'keyword_analysis',    # 키워드 분석
        'statistics',          # 통계
        'mail_type',          # 메일 유형별 조회
        'keyword_search',      # 키워드 검색
        # Additional categories from templates
        'specific_agenda',     # 특정 의제 조회
        'organization_info',   # 조직 정보
        'meeting',            # 회의 관련
        'deadline_tracking',   # 마감일 추적
        'attachment_analysis', # 첨부파일 분석
        'opinion_analysis',    # 의견 분석
        'related_analysis',    # 관련 분석
        'meeting_attendance',  # 회의 참석
        'project_team'        # 프로젝트 팀
    ]
    
    # Valid scope types
    VALID_SCOPE_TYPES = ['all', 'organization', 'panel', 'panel_org', 'agenda']
    
    # Valid parameter types
    VALID_PARAM_TYPES = ['string', 'datetime', 'array']
    
    # Valid organizations
    VALID_ORGANIZATIONS = [
        'ABS', 'BV', 'CCS', 'CRS', 'DNV', 'IRS', 
        'KR', 'NK', 'PRS', 'RINA', 'IL', 'TL', 'LR'
    ]
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        
    def validate_template(self, template: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """Validate a single template
        
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        template_id = template.get('template_id', '')
        
        # Check required fields
        self._check_required_fields(template)
        
        # Validate template_id naming convention
        self._validate_template_id(template_id)
        
        # Validate template version
        self._validate_template_version(template.get('template_version'))
        
        # Validate category
        self._validate_category(template.get('template_category'))
        
        # Validate query_info
        self._validate_query_info(template.get('query_info', {}))
        
        # Validate target_scope
        self._validate_target_scope(template.get('target_scope', {}))
        
        # Validate sql_template
        self._validate_sql_template(template.get('sql_template', {}))
        
        # Validate parameters
        self._validate_parameters(
            template.get('parameters', []),
            template.get('sql_template', {}).get('query', '')
        )
        
        # Validate other fields
        self._validate_related_db(template.get('related_db'))
        self._validate_related_tables(template.get('related_tables'))
        self._validate_routing_type(template.get('routing_type'))
        self._validate_to_agent(template.get('to_agent'))
        
        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings
    
    def _check_required_fields(self, template: Dict[str, Any]):
        """Check if all required fields are present"""
        for field in self.REQUIRED_FIELDS:
            if field not in template:
                self.errors.append(f"Missing required field: {field}")
    
    def _validate_template_id(self, template_id: str):
        """Validate template ID format"""
        if not template_id:
            self.errors.append("Template ID is empty")
            return
        
        # Should follow naming convention: {domain}_{action}_{target}
        if not re.match(r'^[a-z0-9_]+$', template_id):
            self.errors.append(f"Template ID should only contain lowercase letters, numbers, and underscores: {template_id}")
    
    def _validate_template_version(self, version: Optional[str]):
        """Validate template version format"""
        if not version:
            self.errors.append("template_version is missing")
            return
        
        # Should be 2.0.0 for updated templates
        if version != "2.0.0":
            self.warnings.append(f"Template version should be '2.0.0' for updated templates, found: {version}")
    
    def _validate_category(self, category: Optional[str]):
        """Validate template category"""
        if not category:
            self.errors.append("Template category is empty")
            return
            
        if category not in self.VALID_CATEGORIES:
            self.warnings.append(f"Unknown category '{category}'. Known categories: {', '.join(self.VALID_CATEGORIES[:6])}")
    
    def _validate_query_info(self, query_info: Dict[str, Any]):
        """Validate query_info structure"""
        if not query_info:
            self.errors.append("query_info is empty")
            return
            
        # Check required fields
        for field in self.QUERY_INFO_REQUIRED:
            if field not in query_info:
                self.errors.append(f"Missing required field in query_info: {field}")
        
        # Validate natural_questions format
        questions = query_info.get('natural_questions', [])
        if not questions:
            self.errors.append("natural_questions is empty")
        else:
            # Check for proper format: (original), (similar1-N), (ext)
            has_original = False
            has_ext = False
            similar_count = 0
            
            for q in questions:
                if '(original)' in q:
                    has_original = True
                elif '(ext)' in q:
                    has_ext = True
                elif re.search(r'\(similar\d+\)', q):
                    similar_count += 1
            
            if not has_original:
                self.errors.append("Missing (original) question in natural_questions")
            if not has_ext:
                self.errors.append("Missing (ext) question in natural_questions")
            if similar_count < 3:
                self.warnings.append(f"Should have at least 3 similar questions, found {similar_count}")
        
        # Validate keywords
        keywords = query_info.get('keywords', [])
        if not keywords:
            self.errors.append("keywords is empty")
    
    def _validate_target_scope(self, target_scope: Dict[str, Any]):
        """Validate target_scope structure"""
        if not target_scope:
            self.errors.append("target_scope is missing")
            return
        
        # Check required fields
        for field in self.TARGET_SCOPE_REQUIRED:
            if field not in target_scope:
                self.errors.append(f"Missing required field in target_scope: {field}")
        
        # Validate scope_type
        scope_type = target_scope.get('scope_type')
        if scope_type and scope_type not in self.VALID_SCOPE_TYPES:
            self.warnings.append(f"Unknown scope_type '{scope_type}'. Known types: {', '.join(self.VALID_SCOPE_TYPES)}")
        
        # Validate target_organizations
        target_orgs = target_scope.get('target_organizations')
        if target_orgs is not None:
            if not isinstance(target_orgs, list):
                self.errors.append("target_organizations must be a list")
            else:
                for org in target_orgs:
                    if org not in self.VALID_ORGANIZATIONS:
                        self.warnings.append(f"Unknown organization code: {org}")
        
        # Validate target_panels
        target_panels = target_scope.get('target_panels')
        if target_panels is not None:
            if not isinstance(target_panels, (str, list)):
                self.errors.append("target_panels must be a string ('all') or list")
    
    def _validate_sql_template(self, sql_template: Dict[str, Any]):
        """Validate sql_template structure"""
        if not sql_template:
            self.errors.append("sql_template is empty")
            return
            
        # Check required fields
        for field in self.SQL_TEMPLATE_REQUIRED:
            if field not in sql_template:
                self.errors.append(f"Missing required field in sql_template: {field}")
        
        # Validate SQL query
        query = sql_template.get('query', '')
        if not query:
            self.errors.append("SQL query is empty")
        else:
            # Check for proper parameter format (v2.0.0 uses :param_name)
            old_style_params = re.findall(r'\{(\w+)\}', query)
            if old_style_params:
                self.errors.append(f"SQL uses old-style parameters {{{old_style_params}}}. Use :param_name format")
            
            # Check for proper case in SQL keywords
            # Look for lowercase 'request' (not 'REQUEST')
            if re.search(r"'request'", query, re.IGNORECASE) and not re.search(r"'REQUEST'", query):
                self.errors.append("Use uppercase for mail_type values: 'REQUEST' not 'request'")
            
            # Check for dynamic column references
            if 'r.:' in query:
                self.errors.append("SQL contains dynamic column reference (r.:). Use CASE statements instead")
    
    def _validate_parameters(self, parameters: List[Dict[str, Any]], sql_query: str):
        """Validate parameters and their usage in SQL"""
        if not sql_query:
            return
            
        # Extract :param_name style parameters from SQL
        sql_params = re.findall(r':(\w+)', sql_query)
        param_names = [p.get('name', '') for p in parameters]
        
        # Check parameter structure
        for param in parameters:
            if 'name' not in param:
                self.errors.append("Parameter missing 'name' field")
                continue
                
            if 'type' not in param:
                self.errors.append(f"Parameter '{param['name']}' missing 'type' field")
            elif param['type'] not in self.VALID_PARAM_TYPES:
                self.errors.append(f"Invalid parameter type '{param['type']}' for '{param['name']}'")
            
            # Check datetime parameters have proper defaults
            if param.get('type') == 'datetime' and param.get('default'):
                default = param['default']
                if not default.startswith('datetime('):
                    self.warnings.append(f"Datetime parameter '{param['name']}' should use datetime() function in default")
            
            # Check for mcp_format
            if 'mcp_format' not in param:
                self.warnings.append(f"Parameter '{param['name']}' missing 'mcp_format' field")
        
        # Check if all SQL parameters have definitions
        for sql_param in sql_params:
            if sql_param not in param_names:
                self.errors.append(f"SQL parameter :{sql_param} has no definition in parameters")
        
        # Check if all defined parameters are used
        for param_name in param_names:
            if param_name and f':{param_name}' not in sql_query:
                self.warnings.append(f"Parameter '{param_name}' is defined but not used in SQL")
    
    def _validate_related_db(self, related_db: Optional[str]):
        """Validate related_db field"""
        if not related_db:
            self.errors.append("related_db is missing")
        elif related_db != "iacsgraph.db":
            self.warnings.append(f"Unexpected database name: {related_db}")
    
    def _validate_related_tables(self, related_tables: Optional[List[str]]):
        """Validate related_tables field"""
        if related_tables is None:
            self.errors.append("related_tables is missing")
        elif not isinstance(related_tables, list):
            self.errors.append("related_tables must be a list")
        elif len(related_tables) == 0:
            self.errors.append("related_tables is empty")
    
    def _validate_routing_type(self, routing_type: Optional[str]):
        """Validate routing_type field"""
        if not routing_type:
            self.errors.append("routing_type is missing")
        elif routing_type != "sql":
            self.warnings.append(f"Unexpected routing_type: {routing_type}")
    
    def _validate_to_agent(self, to_agent: Optional[str]):
        """Validate to_agent field"""
        if not to_agent:
            self.errors.append("to_agent is missing")
        elif len(to_agent) < 10:
            self.warnings.append("to_agent prompt seems too short")
    
    def validate_file(self, file_path: Path) -> Tuple[bool, Dict[str, Any]]:
        """Validate all templates in a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            return False, {'error': f"Failed to load file: {e}"}
        
        templates = data.get('templates', [])
        if not templates:
            return False, {'error': "No templates found in file"}
        
        results = {
            'file': file_path.name,
            'total': len(templates),
            'valid': 0,
            'invalid': 0,
            'errors': [],
            'warnings': []
        }
        
        for template in templates:
            template_id = template.get('template_id', 'unknown')
            is_valid, errors, warnings = self.validate_template(template)
            
            if is_valid:
                results['valid'] += 1
            else:
                results['invalid'] += 1
                results['errors'].append({
                    'template_id': template_id,
                    'errors': errors
                })
            
            if warnings:
                results['warnings'].append({
                    'template_id': template_id,
                    'warnings': warnings
                })
        
        return results['invalid'] == 0, results


def main():
    """Validate all template files"""
    import sys
    
    if len(sys.argv) < 2:
        template_dir = Path('/home/kimghw/IACSGRAPH/modules/templates/data/query_templates_split')
    else:
        template_dir = Path(sys.argv[1])
    
    validator = TemplateValidator()
    
    print("=" * 80)
    print("Template Validation Report (v2.0.0)")
    print("=" * 80)
    
    all_valid = True
    
    for file_path in sorted(template_dir.glob('query_templates_group_*.json')):
        print(f"\nValidating {file_path.name}...")
        is_valid, results = validator.validate_file(file_path)
        
        if not is_valid:
            all_valid = False
            
        print(f"  Total: {results['total']}")
        print(f"  Valid: {results['valid']}")
        print(f"  Invalid: {results['invalid']}")
        
        if results.get('errors'):
            print("\n  Errors:")
            for error_info in results['errors'][:3]:  # Show first 3
                print(f"    [{error_info['template_id']}]")
                for error in error_info['errors'][:2]:  # Show first 2 errors
                    print(f"      - {error}")
        
        if results.get('warnings'):
            print("\n  Warnings:")
            for warning_info in results['warnings'][:3]:  # Show first 3
                print(f"    [{warning_info['template_id']}]")
                for warning in warning_info['warnings'][:2]:  # Show first 2 warnings
                    print(f"      - {warning}")
    
    print("\n" + "=" * 80)
    if all_valid:
        print("✓ All templates are valid!")
    else:
        print("✗ Some templates have validation errors")
    print("=" * 80)


if __name__ == "__main__":
    main()