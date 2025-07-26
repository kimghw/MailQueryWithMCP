"""
SQL Generator for Query Assistant
Handles parameter merging and SQL placeholder replacement
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, date
import re

logger = logging.getLogger(__name__)


class SQLGenerator:
    """Generates SQL queries from templates with proper parameter handling"""
    
    def __init__(self):
        """Initialize SQL Generator"""
        pass
    
    def generate_sql(
        self,
        sql_template: str,
        template_params: List[Dict[str, Any]],
        mcp_params: Dict[str, Any],
        synonym_params: Dict[str, Any],
        template_defaults: Dict[str, Any] = None
    ) -> tuple[str, Dict[str, Any]]:
        """
        Generate SQL query with merged parameters
        
        Args:
            sql_template: SQL template with placeholders
            template_params: Parameter definitions from template
            mcp_params: Parameters from MCP call (extracted_period, etc.)
            synonym_params: Parameters from synonym processing
            template_defaults: Default parameters from template
            
        Returns:
            tuple: (generated_sql, merged_parameters)
        """
        # 1. Merge parameters with priority: MCP > Synonym > Template defaults
        merged_params = self._merge_parameters(
            template_defaults or {},
            synonym_params,
            mcp_params,
            template_params
        )
        
        # 2. Build SQL conditions based on sql_builder configurations
        sql_with_conditions = self._build_sql_conditions(
            sql_template,
            template_params,
            merged_params
        )
        
        # 3. Replace remaining placeholders
        final_sql = self._replace_placeholders(sql_with_conditions, merged_params)
        
        logger.info(f"Generated SQL with parameters: {merged_params}")
        
        return final_sql, merged_params
    
    def _merge_parameters(
        self,
        template_defaults: Dict[str, Any],
        synonym_params: Dict[str, Any],
        mcp_params: Dict[str, Any],
        template_param_defs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Merge parameters from different sources with priority
        Priority: MCP > Synonym > Template defaults
        """
        merged = {}
        
        # Start with template defaults
        merged.update(template_defaults)
        
        # Apply template parameter defaults
        for param_def in template_param_defs:
            param_name = param_def.get('name')
            if param_name and 'default' in param_def:
                default_value = param_def['default']
                
                # Handle different default types
                if isinstance(default_value, dict):
                    if default_value.get('type') == 'relative' and 'days' in default_value:
                        merged[param_name] = default_value['days']
                    else:
                        merged[param_name] = default_value
                else:
                    merged[param_name] = default_value
        
        # Override with synonym parameters
        for key, value in synonym_params.items():
            if value is not None:
                merged[key] = value
        
        # Override with MCP parameters (highest priority)
        # Map MCP format to internal format
        if 'extracted_period' in mcp_params and mcp_params['extracted_period']:
            period_data = mcp_params['extracted_period']
            if isinstance(period_data, dict) and 'start' in period_data and 'end' in period_data:
                merged['period_start'] = period_data['start']
                merged['period_end'] = period_data['end']
                merged['date_range'] = {
                    'type': 'range',
                    'from': period_data['start'],
                    'to': period_data['end']
                }
        
        if 'extracted_keywords' in mcp_params and mcp_params['extracted_keywords']:
            merged['keywords'] = mcp_params['extracted_keywords']
            # Also set as keyword for single keyword templates
            if len(mcp_params['extracted_keywords']) > 0:
                merged['keyword'] = mcp_params['extracted_keywords'][0]
        
        if 'extracted_organization' in mcp_params and mcp_params['extracted_organization']:
            merged['organization'] = mcp_params['extracted_organization']
            merged['organization_code'] = mcp_params['extracted_organization']
        
        # Copy other direct parameters
        direct_params = ['limit', 'status', 'agenda_code', 'agenda_base', 'agenda_base_version']
        for param in direct_params:
            if param in mcp_params and mcp_params[param] is not None:
                merged[param] = mcp_params[param]
            elif param in synonym_params and synonym_params[param] is not None:
                merged[param] = synonym_params[param]
        
        return merged
    
    def _build_sql_conditions(
        self,
        sql_template: str,
        template_params: List[Dict[str, Any]],
        merged_params: Dict[str, Any]
    ) -> str:
        """Build SQL conditions based on sql_builder configurations"""
        sql = sql_template
        
        for param_def in template_params:
            sql_builder = param_def.get('sql_builder', {})
            builder_type = sql_builder.get('type')
            placeholder = sql_builder.get('placeholder')
            
            if not placeholder:
                continue
            
            if (builder_type in ['period', 'date_range']) and placeholder in sql:
                # Build period/date_range condition
                field = sql_builder.get('field', 'sent_time')
                
                # Check if placeholder already has table alias prefix
                # e.g., "r.{date_condition}" should not add another "r." to field
                placeholder_pattern = rf'(\w+\.)?{re.escape(placeholder)}'
                match = re.search(placeholder_pattern, sql)
                if match and match.group(1):  # Has table alias before placeholder
                    # Remove table alias from field if it matches
                    table_alias = match.group(1).rstrip('.')
                    if field.startswith(f'{table_alias}.'):
                        field = field[len(table_alias)+1:]  # Remove redundant alias
                
                condition = self._build_period_condition(field, merged_params)
                sql = sql.replace(placeholder, condition)
                
            elif builder_type == 'keywords' and placeholder in sql:
                # Build keywords condition
                field = sql_builder.get('field', 'title')
                operator = sql_builder.get('operator', 'LIKE')
                condition = self._build_keywords_condition(field, operator, merged_params)
                sql = sql.replace(placeholder, condition)
                
            elif builder_type == 'direct_replace' and 'placeholders' in sql_builder:
                # Direct replacement for multiple placeholders from single parameter
                if param_def.get('name') == 'period' and 'period_start' in merged_params:
                    sql = sql.replace('{period_start}', f"'{merged_params['period_start']}'")
                    sql = sql.replace('{period_end}', f"'{merged_params['period_end']}'")
                
            elif builder_type == 'string' and placeholder in sql:
                # Direct string replacement
                param_name = param_def.get('name')
                if param_name in merged_params:
                    value = merged_params[param_name]
                    # Check if the value needs quotes
                    if self._needs_quotes(sql, placeholder):
                        sql = sql.replace(placeholder, f"'{value}'")
                    else:
                        sql = sql.replace(placeholder, str(value))
                        
            elif builder_type == 'number' and placeholder in sql:
                # Direct number replacement
                param_name = param_def.get('name')
                if param_name in merged_params:
                    value = merged_params[param_name]
                    sql = sql.replace(placeholder, str(value))
        
        return sql
    
    def _build_period_condition(self, field: str, params: Dict[str, Any]) -> str:
        """Build SQL period condition"""
        # Check for date range
        if 'date_range' in params and params['date_range']:
            date_range = params['date_range']
            if isinstance(date_range, dict):
                start = date_range.get('from') or date_range.get('start')
                end = date_range.get('to') or date_range.get('end')
                if start and end:
                    return f"{field} BETWEEN '{start}' AND '{end}'"
        
        # Check for period_start and period_end
        if 'period_start' in params and 'period_end' in params:
            return f"{field} BETWEEN '{params['period_start']}' AND '{params['period_end']}'"
        
        # Check for days parameter
        if 'days' in params and params['days']:
            days = params['days']
            return f"{field} >= DATE('now', '-{days} days')"
        
        # Default to last 30 days
        return f"{field} >= DATE('now', '-30 days')"
    
    def _build_keywords_condition(self, field: str, operator: str, params: Dict[str, Any]) -> str:
        """Build SQL keywords condition"""
        keywords = params.get('keywords', [])
        
        if not keywords:
            # Check for single keyword
            if 'keyword' in params and params['keyword']:
                keywords = [params['keyword']]
            else:
                return "1=1"  # Always true condition
        
        if operator.upper() == 'LIKE':
            conditions = [f"{field} LIKE '%{keyword}%'" for keyword in keywords]
        elif operator.upper() == 'CONTAINS':
            conditions = [f"CONTAINS({field}, '{keyword}')" for keyword in keywords]
        else:
            conditions = [f"{field} = '{keyword}'" for keyword in keywords]
        
        return f"({' OR '.join(conditions)})"
    
    def _needs_quotes(self, sql: str, placeholder: str) -> bool:
        """Check if a placeholder needs quotes based on SQL context"""
        # Find the placeholder position
        pos = sql.find(placeholder)
        if pos == -1:
            return False
        
        # Check if placeholder is inside a string literal (e.g., '%{keyword}%')
        # Count quotes before the placeholder
        before_sql = sql[:pos]
        single_quotes_before = before_sql.count("'") - before_sql.count("\\'")
        
        # If odd number of quotes before, we're inside a string literal
        if single_quotes_before % 2 == 1:
            return False
        
        # Check if already quoted
        if pos > 0 and sql[pos-1] in ["'", '"']:
            return False
        
        # Check context - common patterns that need quotes
        before = sql[max(0, pos-10):pos].strip().lower()
        if any(op in before for op in ['=', '!=', '<>', 'like', 'in', 'between']):
            return True
        
        # Check for BETWEEN ... AND pattern
        after = sql[pos+len(placeholder):pos+len(placeholder)+10].strip().lower()
        if 'and' in after or 'and' in before:
            return True
        
        return False
    
    def _replace_placeholders(self, sql: str, params: Dict[str, Any]) -> str:
        """Replace remaining placeholders in SQL"""
        # Replace {param} style placeholders
        for param_name, value in params.items():
            placeholder = f"{{{param_name}}}"
            if placeholder in sql:
                if isinstance(value, str):
                    # Check if already quoted
                    if not self._needs_quotes(sql, placeholder):
                        sql = sql.replace(placeholder, value)
                    else:
                        sql = sql.replace(placeholder, f"'{value}'")
                elif isinstance(value, (int, float)):
                    sql = sql.replace(placeholder, str(value))
                elif isinstance(value, (datetime, date)):
                    if self._needs_quotes(sql, placeholder):
                        sql = sql.replace(placeholder, f"'{value.strftime('%Y-%m-%d')}'")
                    else:
                        sql = sql.replace(placeholder, value.strftime('%Y-%m-%d'))
                elif value is None:
                    sql = sql.replace(placeholder, "NULL")
                else:
                    sql = sql.replace(placeholder, str(value))
        
        # Replace :param style placeholders
        for param_name, value in params.items():
            placeholder = f":{param_name}"
            if placeholder in sql:
                if isinstance(value, str):
                    sql = sql.replace(placeholder, f"'{value}'")
                elif isinstance(value, (int, float)):
                    sql = sql.replace(placeholder, str(value))
                elif isinstance(value, (datetime, date)):
                    if self._needs_quotes(sql, placeholder):
                        sql = sql.replace(placeholder, f"'{value.strftime('%Y-%m-%d')}'")
                    else:
                        sql = sql.replace(placeholder, value.strftime('%Y-%m-%d'))
                elif value is None:
                    sql = sql.replace(placeholder, "NULL")
                else:
                    sql = sql.replace(placeholder, str(value))
        
        # Clean up any remaining empty conditions
        sql = re.sub(r'AND\s+\(\s*\)', '', sql)
        sql = re.sub(r'WHERE\s+\(\s*\)', 'WHERE 1=1', sql)
        sql = re.sub(r'AND\s+AND', 'AND', sql)
        sql = re.sub(r'WHERE\s+AND', 'WHERE', sql)
        
        # Clean up excessive whitespace and newlines
        sql = ' '.join(sql.split())
        
        return sql.strip()