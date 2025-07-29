"""Template structure and content validator"""

import re
import json
import logging
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class TemplateValidator:
    """Validate template structure and content"""
    
    # Required fields for each template
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
    SQL_TEMPLATE_REQUIRED = ['query']
    
    # Valid categories
    VALID_CATEGORIES = [
        'agenda_status', 'time_based_query', 'organization_response',
        'agenda_statistics', 'agenda_analysis', 'keyword_analysis',
        'agenda_search', 'system_config', 'data_quality',
        'organization_analysis', 'meeting_info', 'project_team',
        'panel_specific', 'keyword_search', 'chair_communication',
        'panel_statistics', 'llm_direct_response', 'vectordb_search',
        'response_analysis', 'deadline_analysis', 'organization_info',
        'mail_content', 'statistics', 'response_tracking', 'mail_type'
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
        
        # Skip config templates
        template_id = template.get('template_id', '')
        if template_id.startswith('_config'):
            return True, [], []
            
        # Check required fields
        self._check_required_fields(template)
        
        # Validate template_id
        self._validate_template_id(template_id)
        
        # Validate category
        self._validate_category(template.get('template_category'))
        
        # Validate query_info
        self._validate_query_info(template.get('query_info', {}))
        
        # Validate sql_template
        self._validate_sql_template(template.get('sql_template', {}))
        
        # Validate parameters
        self._validate_parameters(
            template.get('parameters', []),
            template.get('sql_template', {}).get('query', '')
        )
        
        # Validate additional required fields
        self._validate_template_version(template.get('template_version'))
        self._validate_target_scope(template.get('target_scope'))
        self._validate_related_db(template.get('related_db'))
        self._validate_related_tables(template.get('related_tables'))
        self._validate_routing_type(template.get('routing_type'))
        self._validate_to_agent(template.get('to_agent'))
        
        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings
        
    def validate_file(self, file_path: Path) -> Tuple[bool, Dict[str, Any]]:
        """Validate all templates in a file
        
        Returns:
            Tuple of (is_valid, report)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            return False, {
                'error': f'Failed to load file: {e}',
                'valid_count': 0,
                'invalid_count': 0
            }
            
        # Extract templates
        if isinstance(data, list):
            templates = data
        elif isinstance(data, dict) and 'templates' in data:
            templates = data['templates']
        else:
            return False, {
                'error': 'Unknown file format',
                'valid_count': 0,
                'invalid_count': 0
            }
            
        # Validate each template
        valid_count = 0
        invalid_count = 0
        all_errors = []
        all_warnings = []
        invalid_templates = []
        
        for i, template in enumerate(templates):
            is_valid, errors, warnings = self.validate_template(template)
            
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                invalid_templates.append({
                    'index': i,
                    'template_id': template.get('template_id', 'unknown'),
                    'errors': errors
                })
                
            all_errors.extend(errors)
            all_warnings.extend(warnings)
            
        return invalid_count == 0, {
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'total_count': len(templates),
            'errors': all_errors,
            'warnings': all_warnings,
            'invalid_templates': invalid_templates
        }
        
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
            
        # Should end with _v2
        if not template_id.endswith('_v2'):
            self.warnings.append(f"Template ID should end with '_v2': {template_id}")
            
        # Should be lowercase with underscores
        if not re.match(r'^[a-z0-9_]+$', template_id):
            self.errors.append(f"Template ID should only contain lowercase letters, numbers, and underscores: {template_id}")
            
    def _validate_category(self, category: Optional[str]):
        """Validate template category"""
        if not category:
            self.errors.append("Template category is empty")
            return
            
        if category not in self.VALID_CATEGORIES:
            self.errors.append(f"Invalid category '{category}'. Valid categories: {', '.join(self.VALID_CATEGORIES)}")
            
    def _validate_query_info(self, query_info: Dict[str, Any]):
        """Validate query_info structure"""
        if not query_info:
            self.errors.append("query_info is empty")
            return
            
        # Check required fields
        for field in self.QUERY_INFO_REQUIRED:
            if field not in query_info:
                self.errors.append(f"Missing required field in query_info: {field}")
                
        # Validate natural_questions
        questions = query_info.get('natural_questions', [])
        if not questions:
            self.errors.append("natural_questions is empty")
        elif len(questions) < 3:
            self.warnings.append(f"Should have at least 3 natural questions (found {len(questions)})")
            
        # Validate keywords
        keywords = query_info.get('keywords', [])
        if not keywords:
            self.errors.append("keywords is empty")
            
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
            # Basic SQL validation
            if not any(keyword in query.upper() for keyword in ['SELECT', '--']):
                self.errors.append("SQL query should start with SELECT or be a comment")
                
    def _validate_parameters(self, parameters: List[Dict[str, Any]], sql_query: str):
        """Validate parameters and their usage in SQL"""
        if not parameters:
            # Check if SQL has placeholders
            if '{' in sql_query and '}' in sql_query:
                self.warnings.append("SQL contains placeholders but no parameters are defined")
            return
            
        # Extract placeholders from SQL
        placeholders = re.findall(r'\{(\w+)\}', sql_query)
        param_names = [p.get('name', '') for p in parameters]
        
        # Check if all placeholders have corresponding parameters
        for placeholder in placeholders:
            if placeholder not in param_names and placeholder not in ['date_condition', 'deadline_filter', 'no_deadline_filter']:
                self.errors.append(f"SQL placeholder '{{{placeholder}}}' has no corresponding parameter")
                
        # Check if all parameters are used
        for param_name in param_names:
            if param_name and f'{{{param_name}}}' not in sql_query:
                self.warnings.append(f"Parameter '{param_name}' is defined but not used in SQL")
    
    def _validate_template_version(self, version: Optional[str]):
        """Validate template version format"""
        if not version:
            self.errors.append("template_version is missing")
            return
        
        # Check version format (e.g., "1.0.0")
        if not re.match(r'^\d+\.\d+\.\d+$', version):
            self.errors.append(f"Invalid version format '{version}'. Expected format: X.Y.Z")
    
    def _validate_target_scope(self, target_scope: Optional[Dict[str, Any]]):
        """Validate target_scope structure"""
        if not target_scope:
            self.errors.append("target_scope is missing")
            return
        
        # Check required fields in target_scope
        required_scope_fields = ['scope_type', 'target_organizations', 'target_panels']
        for field in required_scope_fields:
            if field not in target_scope:
                self.errors.append(f"Missing required field in target_scope: {field}")
        
        # Validate scope_type
        scope_type = target_scope.get('scope_type')
        if scope_type and scope_type not in ['all', 'organization', 'panel']:
            self.errors.append(f"Invalid scope_type '{scope_type}'. Valid values: all, organization, panel")
        
        # Validate target_organizations is a list
        target_orgs = target_scope.get('target_organizations')
        if target_orgs is not None and not isinstance(target_orgs, list):
            self.errors.append("target_organizations must be a list")
        
        # Validate target_panels
        target_panels = target_scope.get('target_panels')
        if target_panels is not None:
            if not isinstance(target_panels, (str, list)):
                self.errors.append("target_panels must be a string or list")
    
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
            self.warnings.append("related_tables is empty")
    
    def _validate_routing_type(self, routing_type: Optional[str]):
        """Validate routing_type field"""
        if not routing_type:
            self.errors.append("routing_type is missing")
            return
        
        valid_routing_types = ['sql', 'llm_direct', 'llm_direct_response', 'vectordb', 'vectordb_search']
        if routing_type not in valid_routing_types:
            self.errors.append(f"Invalid routing_type '{routing_type}'. Valid values: {', '.join(valid_routing_types)}")
    
    def _validate_to_agent(self, to_agent: Optional[str]):
        """Validate to_agent field"""
        if not to_agent:
            self.errors.append("to_agent is missing")
        elif not isinstance(to_agent, str):
            self.errors.append("to_agent must be a string")
        elif len(to_agent.strip()) == 0:
            self.warnings.append("to_agent is empty")