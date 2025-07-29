"""Parameter validator for template SQL queries"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ParameterValidator:
    """Validate and process template parameters"""
    
    def __init__(self):
        self.errors = []
        
    def validate_parameters(
        self,
        parameters: List[Dict[str, Any]],
        provided_values: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any], List[str]]:
        """Validate provided parameters against template requirements
        
        Args:
            parameters: Template parameter definitions
            provided_values: Values provided by user/system
            
        Returns:
            Tuple of (is_valid, processed_values, errors)
        """
        self.errors = []
        processed = {}
        
        for param_def in parameters:
            param_name = param_def.get('name', '')
            param_type = param_def.get('type', 'string')
            is_required = param_def.get('required', True)
            default_value = param_def.get('default')
            
            # Get provided value
            value = provided_values.get(param_name)
            
            # Check required parameter
            if is_required and value is None:
                if default_value is not None:
                    value = default_value
                else:
                    self.errors.append(f"Required parameter '{param_name}' is missing")
                    continue
                    
            # Skip optional parameters without value
            if not is_required and value is None:
                if default_value is not None:
                    value = default_value
                else:
                    continue
                    
            # Validate and process by type
            if param_type == 'string':
                processed[param_name] = self._validate_string(param_name, value)
            elif param_type in ['date_range', 'period']:
                processed[param_name] = self._validate_date_range(param_name, value, param_def)
            elif param_type == 'integer':
                processed[param_name] = self._validate_integer(param_name, value)
            elif param_type == 'array':
                processed[param_name] = self._validate_array(param_name, value)
            else:
                self.errors.append(f"Unknown parameter type '{param_type}' for '{param_name}'")
                
        is_valid = len(self.errors) == 0
        return is_valid, processed, self.errors
        
    def build_sql_with_parameters(
        self,
        sql_template: str,
        parameters: Dict[str, Any],
        param_definitions: List[Dict[str, Any]]
    ) -> str:
        """Build SQL query with parameter values
        
        Args:
            sql_template: SQL template with placeholders
            parameters: Parameter values
            param_definitions: Parameter definitions from template
            
        Returns:
            SQL query with parameters replaced
        """
        sql = sql_template
        
        # Process each parameter
        for param_name, param_value in parameters.items():
            placeholder = f'{{{param_name}}}'
            
            # Find parameter definition
            param_def = next((p for p in param_definitions if p['name'] == param_name), None)
            if not param_def:
                continue
                
            # Build SQL based on parameter type
            sql_builder = param_def.get('sql_builder', {})
            
            # Check if placeholder is defined in sql_builder
            if sql_builder.get('placeholder'):
                placeholder = sql_builder['placeholder']
            
            if sql_builder:
                sql_value = self._build_sql_value(param_value, sql_builder, param_def)
            else:
                # Simple string replacement
                if isinstance(param_value, str):
                    sql_value = f"'{param_value}'"
                else:
                    sql_value = str(param_value)
                    
            sql = sql.replace(placeholder, sql_value)
            
        # Handle special placeholders
        sql = self._handle_special_placeholders(sql, parameters)
        
        return sql
        
    def _validate_string(self, name: str, value: Any) -> str:
        """Validate string parameter"""
        if not isinstance(value, str):
            self.errors.append(f"Parameter '{name}' should be a string, got {type(value).__name__}")
            return str(value)
        return value
        
    def _validate_integer(self, name: str, value: Any) -> int:
        """Validate integer parameter"""
        try:
            return int(value)
        except (TypeError, ValueError):
            self.errors.append(f"Parameter '{name}' should be an integer, got {type(value).__name__}")
            return 0
            
    def _validate_array(self, name: str, value: Any) -> List[Any]:
        """Validate array parameter"""
        if isinstance(value, list):
            return value
        elif isinstance(value, str):
            # Try to parse JSON array
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except:
                pass
        self.errors.append(f"Parameter '{name}' should be an array")
        return []
        
    def _validate_date_range(self, name: str, value: Any, param_def: Dict[str, Any]) -> Dict[str, Any]:
        """Validate date range parameter"""
        if isinstance(value, dict):
            return value
            
        # Parse string representations
        if isinstance(value, str):
            # Handle relative dates like "30 days", "3 months"
            match = re.match(r'(\d+)\s*(day|week|month|year)s?', value.lower())
            if match:
                amount = int(match.group(1))
                unit = match.group(2)
                return {
                    'type': 'relative',
                    'amount': amount,
                    'unit': unit,
                    'days': amount if unit == 'day' else amount * (7 if unit == 'week' else 30 if unit == 'month' else 365)
                }
                
        # Use default if available
        default = param_def.get('default', {})
        if default:
            return default
            
        self.errors.append(f"Invalid date range format for '{name}'")
        return {'type': 'relative', 'days': 30}
        
    def _build_sql_value(self, value: Any, sql_builder: Dict[str, Any], param_def: Dict[str, Any] = None) -> str:
        """Build SQL value based on builder configuration"""
        builder_type = sql_builder.get('type', 'string')
        
        if builder_type in ['date_range', 'period']:
            return self._build_date_range_sql(value, sql_builder)
        elif builder_type == 'in_list':
            return self._build_in_list_sql(value)
        elif builder_type == 'keywords':
            return self._build_keywords_sql(value, sql_builder)
        elif builder_type == 'string':
            # For simple string replacement, don't add quotes if it's a column name
            if sql_builder.get('as_column', False):
                return value
            return f"'{value}'" if isinstance(value, str) else str(value)
        else:
            return f"'{value}'" if isinstance(value, str) else str(value)
            
    def _build_date_range_sql(self, date_value: Dict[str, Any], sql_builder: Dict[str, Any]) -> str:
        """Build SQL for date range"""
        field = sql_builder.get('field', 'sent_time')
        
        if date_value.get('type') == 'relative':
            days = date_value.get('days', date_value.get('amount', 30))
            return f"{field} >= DATE('now', '-{days} days')"
        elif date_value.get('type') == 'absolute':
            start = date_value.get('start')
            end = date_value.get('end')
            if start and end:
                return f"{field} BETWEEN '{start}' AND '{end}'"
            elif start:
                return f"{field} >= '{start}'"
            elif end:
                return f"{field} <= '{end}'"
                
        return "1=1"  # No date filter
        
    def _build_in_list_sql(self, values: List[str]) -> str:
        """Build SQL for IN clause"""
        if not values:
            return "1=0"  # No matches
            
        quoted = [f"'{v}'" for v in values]
        return f"({', '.join(quoted)})"
        
    def _build_keywords_sql(self, keywords: List[str], sql_builder: Dict[str, Any]) -> str:
        """Build SQL for keywords search"""
        fields = sql_builder.get('fields', ['keywords'])
        if not keywords:
            return "1=0"
        
        conditions = []
        for keyword in keywords:
            field_conditions = []
            for field in fields:
                field_conditions.append(f"{field} LIKE '%{keyword}%'")
            conditions.append(f"({' OR '.join(field_conditions)})")
        
        return f"({' OR '.join(conditions)})"
    
    def _handle_special_placeholders(self, sql: str, parameters: Dict[str, Any]) -> str:
        """Handle special placeholders like {date_condition}"""
        # Handle {date_condition}
        if '{date_condition}' in sql:
            date_param = parameters.get('date_range', parameters.get('date_info', parameters.get('period')))
            if date_param:
                date_sql = self._build_date_range_sql(date_param, {'field': 'sent_time'})
                sql = sql.replace('{date_condition}', date_sql)
            else:
                sql = sql.replace('{date_condition}', '1=1')
        
        # Handle {period_condition}
        if '{period_condition}' in sql:
            period_param = parameters.get('period', parameters.get('date_range'))
            if period_param:
                # Find the field from SQL context
                field = 'sent_time'
                if 'c.sent_time' in sql:
                    field = 'c.sent_time'
                period_sql = self._build_date_range_sql(period_param, {'field': field})
                sql = sql.replace('{period_condition}', period_sql)
            else:
                sql = sql.replace('{period_condition}', '1=1')
        
        # Handle {keywords_condition}
        if '{keywords_condition}' in sql:
            keywords = parameters.get('keywords', [])
            if keywords:
                # Default fields for keyword search
                keyword_sql = self._build_keywords_sql(keywords, {'fields': ['keywords', 'subject']})
                sql = sql.replace('{keywords_condition}', keyword_sql)
            else:
                sql = sql.replace('{keywords_condition}', '1=0')
                
        # Handle other special placeholders
        special_placeholders = {
            '{deadline_filter}': 'deadline IS NOT NULL AND deadline >= DATE("now")',
            '{no_deadline_filter}': 'deadline IS NULL'
        }
        
        for placeholder, replacement in special_placeholders.items():
            if placeholder in sql:
                sql = sql.replace(placeholder, replacement)
                
        return sql