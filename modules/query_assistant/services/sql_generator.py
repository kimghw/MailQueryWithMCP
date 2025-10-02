"""
Simplified SQL Generator v3 - Cleaner interface with query list
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)


class SQLGenerator:
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
        logger.debug("=== generate_sql called ===")
        logger.debug(f"Template params: {template_params}")
        logger.debug(f"MCP params: {mcp_params}")
        logger.debug(f"Synonym params: {synonym_params}")
        logger.debug(f"Template defaults: {template_defaults}")
        
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
        logger.debug(f"After template defaults: {merged}")
        
        # Apply template parameter defaults
        for param_def in template_param_defs:
            param_name = param_def.get('name')
            if param_name and 'default' in param_def:
                default_value = param_def['default']
                logger.debug(f"Processing param '{param_name}' with type '{param_def.get('type')}' and default '{default_value}'")
                
                # Handle datetime defaults
                if param_def.get('type') == 'datetime' and isinstance(default_value, str):
                    logger.debug(f"Datetime parameter detected: '{param_name}' = '{default_value}'")
                    if default_value.startswith("datetime("):
                        logger.debug(f"Calling _calculate_datetime with: '{default_value}'")
                        calculated_value = self._calculate_datetime(default_value)
                        logger.debug(f"_calculate_datetime returned: '{calculated_value}'")
                        if calculated_value:
                            merged[param_name] = calculated_value
                            logger.debug(f"Set '{param_name}' to calculated value: '{calculated_value}'")
                        else:
                            logger.warning(f"Failed to calculate datetime for '{default_value}'")
                    else:
                        merged[param_name] = default_value
                        logger.debug(f"Using datetime string as-is: '{default_value}'")
                else:
                    merged[param_name] = default_value
                    logger.debug(f"Set '{param_name}' to default: '{default_value}'")
        
        # Override with synonym parameters
        merged.update({k: v for k, v in synonym_params.items() if v is not None})
        logger.debug(f"After synonym parameters: {merged}")
        
        # Override with MCP parameters (highest priority)
        if 'extracted_period' in mcp_params and mcp_params['extracted_period']:
            period_data = mcp_params['extracted_period']
            if isinstance(period_data, dict):
                merged['period_start'] = period_data.get('start')
                merged['period_end'] = period_data.get('end')
                logger.debug(f"Applied period from MCP: start={period_data.get('start')}, end={period_data.get('end')}")
        
        if 'extracted_keywords' in mcp_params and mcp_params['extracted_keywords']:
            merged['keyword'] = mcp_params['extracted_keywords']
            merged['keywords'] = mcp_params['extracted_keywords']  # Legacy
            logger.debug(f"Applied keywords from MCP: {mcp_params['extracted_keywords']}")
        
        if 'extracted_organization' in mcp_params:
            merged['organization'] = mcp_params['extracted_organization']
            logger.debug(f"Applied organization from MCP: {mcp_params['extracted_organization']}")
        
        if 'extracted_intent' in mcp_params:
            merged['intent'] = mcp_params['extracted_intent']
            logger.debug(f"Applied intent from MCP: {mcp_params['extracted_intent']}")
        
        # Copy other parameters
        for param in ['limit', 'status', 'agenda', 'panel', 'intent']:
            if param in mcp_params:
                merged[param] = mcp_params[param]
                logger.debug(f"Applied {param} from MCP: {mcp_params[param]}")
        
        logger.debug(f"Final merged parameters: {merged}")
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
        logger.debug(f"Starting parameter substitution with params: {params}")
        
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
            
            logger.debug(f"Substituting {placeholder} with value: {value} (type: {type(value).__name__})")
            
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
                formatted = value.strftime('%Y-%m-%d %H:%M:%S')
                sql = sql.replace(placeholder, f"'{formatted}'")
                logger.debug(f"Datetime {param_name} formatted as: {formatted}")
            elif isinstance(value, list):
                # Use first value for non-array context
                first_val = value[0] if value else None
                if isinstance(first_val, str):
                    sql = sql.replace(placeholder, f"'{first_val}'")
                else:
                    sql = sql.replace(placeholder, str(first_val))
        
        logger.debug(f"SQL after substitution: {sql[:200]}...")  # Log first 200 chars
        return sql.strip()
    
    def _calculate_datetime(self, datetime_expr: str) -> Optional[str]:
        """Calculate datetime from SQLite expression"""
        logger.debug(f"_calculate_datetime called with: '{datetime_expr}'")
        
        match = re.match(r"datetime\('now',\s*'([+-]\d+)\s+days?'\)", datetime_expr)
        if match:
            days = int(match.group(1))
            logger.debug(f"Matched relative datetime pattern with {days} days")
            calculated = datetime.now() + timedelta(days=days)
            result = calculated.strftime('%Y-%m-%d %H:%M:%S')
            logger.debug(f"Calculated datetime: {result}")
            return result
        
        if datetime_expr == "datetime('now')":
            logger.debug("Matched 'datetime(now)' pattern")
            result = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.debug(f"Current datetime: {result}")
            return result
        
        logger.debug(f"No matching datetime pattern for: '{datetime_expr}'")
        return None