"""
Simplified SQL Generator v3 - Cleaner interface with query list
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)


class SQLGeneratorV3:
    """SQL generator that returns list of queries for array parameters"""
    
    def __init__(self):
        """Initialize SQL Generator V3"""
        pass
    
    def generate_sql(
        self,
        sql_template: str,
        template_params: List[Dict[str, Any]],
        mcp_params: Dict[str, Any],
        synonym_params: Dict[str, Any],
        template_defaults: Dict[str, Any] = None
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Generate SQL queries with simplified parameter handling
        
        Args:
            sql_template: SQL template with :param_name placeholders
            template_params: Parameter definitions from template
            mcp_params: Parameters from MCP call
            synonym_params: Parameters from synonym processing
            template_defaults: Default parameters from template
            
        Returns:
            tuple: (queries, merged_parameters)
                - queries: List of SQL queries (1 or more)
                - merged_parameters: All parameters merged
        """
        # 1. Merge parameters
        merged_params = self._merge_parameters(
            template_defaults or {},
            synonym_params,
            mcp_params,
            template_params
        )
        
        # 2. Identify array parameters that need multi-query
        array_params = self._get_array_params(template_params, merged_params)
        
        # 3. Generate queries
        if array_params:
            # Generate multiple queries for array parameters
            queries = self._generate_queries_for_arrays(
                sql_template, 
                merged_params, 
                array_params
            )
        else:
            # Single query
            query = self._substitute_parameters(sql_template, merged_params)
            queries = [query]
        
        logger.info(f"Generated {len(queries)} queries")
        
        return queries, merged_params
    
    def _merge_parameters(
        self,
        template_defaults: Dict[str, Any],
        synonym_params: Dict[str, Any],
        mcp_params: Dict[str, Any],
        template_param_defs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge parameters from different sources"""
        merged = {}
        
        # Start with template defaults
        merged.update(template_defaults)
        
        # Apply template parameter defaults
        for param_def in template_param_defs:
            param_name = param_def.get('name')
            if param_name and 'default' in param_def:
                default_value = param_def['default']
                
                # Handle datetime defaults
                if param_def.get('type') == 'datetime' and isinstance(default_value, str):
                    if default_value.startswith("datetime("):
                        calculated_value = self._calculate_datetime(default_value)
                        if calculated_value:
                            merged[param_name] = calculated_value
                    else:
                        merged[param_name] = default_value
                else:
                    merged[param_name] = default_value
        
        # Override with synonym parameters
        merged.update({k: v for k, v in synonym_params.items() if v is not None})
        
        # Override with MCP parameters (highest priority)
        if 'extracted_period' in mcp_params and mcp_params['extracted_period']:
            period_data = mcp_params['extracted_period']
            if isinstance(period_data, dict):
                merged['period_start'] = period_data.get('start')
                merged['period_end'] = period_data.get('end')
        
        if 'extracted_keywords' in mcp_params and mcp_params['extracted_keywords']:
            merged['keyword'] = mcp_params['extracted_keywords']
            merged['keywords'] = mcp_params['extracted_keywords']  # Legacy
        
        if 'extracted_organization' in mcp_params:
            merged['organization'] = mcp_params['extracted_organization']
        
        # Copy other parameters
        for param in ['limit', 'status', 'agenda', 'panel']:
            if param in mcp_params:
                merged[param] = mcp_params[param]
        
        return merged
    
    def _get_array_params(
        self,
        template_params: List[Dict[str, Any]],
        merged_params: Dict[str, Any]
    ) -> Dict[str, List[Any]]:
        """Get array parameters that have multiple values"""
        array_params = {}
        
        for param_def in template_params:
            param_name = param_def.get('name')
            param_type = param_def.get('type')
            
            if param_type == 'array' and param_name in merged_params:
                value = merged_params[param_name]
                if isinstance(value, list) and len(value) > 1:
                    array_params[param_name] = value
        
        return array_params
    
    def _generate_queries_for_arrays(
        self,
        sql_template: str,
        params: Dict[str, Any],
        array_params: Dict[str, List[Any]]
    ) -> List[str]:
        """Generate queries for each combination of array values"""
        queries = []
        
        # For now, handle single array parameter
        if len(array_params) == 1:
            param_name, values = list(array_params.items())[0]
            
            for value in values:
                # Create params with single value
                query_params = params.copy()
                query_params[param_name] = value
                
                query = self._substitute_parameters(sql_template, query_params)
                queries.append(query)
        else:
            # Multiple arrays - for now just use first value of each
            # TODO: Implement cartesian product if needed
            query_params = params.copy()
            for param_name, values in array_params.items():
                query_params[param_name] = values[0] if values else None
            
            query = self._substitute_parameters(sql_template, query_params)
            queries.append(query)
        
        return queries
    
    def _substitute_parameters(self, sql_template: str, params: Dict[str, Any]) -> str:
        """Simple parameter substitution using :param_name syntax"""
        sql = sql_template
        
        # Handle CASE statements for dynamic columns
        case_pattern = r'CASE\s+:(\w+)\s+(.+?)\s+END'
        sql = re.sub(
            case_pattern,
            lambda m: f"CASE '{params.get(m.group(1), '')}' {m.group(2)} END",
            sql,
            flags=re.IGNORECASE | re.DOTALL
        )
        
        # Replace :param_name placeholders
        for param_name, value in params.items():
            placeholder = f":{param_name}"
            
            if placeholder not in sql:
                continue
                
            if value is None:
                sql = sql.replace(placeholder, "NULL")
            elif isinstance(value, str):
                # Handle LIKE patterns
                if re.search(rf"LIKE\s*'%'\s*\|\|\s*{re.escape(placeholder)}\s*\|\|\s*'%'", sql):
                    sql = re.sub(
                        rf"LIKE\s*'%'\s*\|\|\s*{re.escape(placeholder)}\s*\|\|\s*'%'",
                        f"LIKE '%' || '{value}' || '%'",
                        sql
                    )
                else:
                    sql = sql.replace(placeholder, f"'{value}'")
            elif isinstance(value, (int, float)):
                sql = sql.replace(placeholder, str(value))
            elif isinstance(value, datetime):
                sql = sql.replace(placeholder, f"'{value.strftime('%Y-%m-%d %H:%M:%S')}'")
            elif isinstance(value, list):
                # Use first value for non-array context
                first_val = value[0] if value else None
                if isinstance(first_val, str):
                    sql = sql.replace(placeholder, f"'{first_val}'")
                else:
                    sql = sql.replace(placeholder, str(first_val))
        
        return sql.strip()
    
    def _calculate_datetime(self, datetime_expr: str) -> Optional[str]:
        """Calculate datetime from SQLite expression"""
        match = re.match(r"datetime\('now',\s*'([+-]\d+)\s+days?'\)", datetime_expr)
        if match:
            days = int(match.group(1))
            calculated = datetime.now() + timedelta(days=days)
            return calculated.strftime('%Y-%m-%d %H:%M:%S')
        
        if datetime_expr == "datetime('now')":
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return None