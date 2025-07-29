"""
Parameter builder for SQL query generation with multiple value support
"""
from typing import Any, Dict, List, Union

class ParameterBuilder:
    """Build SQL conditions from parameters"""
    
    @staticmethod
    def build_or_like_condition(values: List[str], fields: List[str]) -> str:
        """
        Build OR LIKE condition for multiple values and fields
        
        Example:
        values = ["IMO", "해사"]
        fields = ["keywords", "subject"]
        Returns: "(keywords LIKE '%IMO%' OR subject LIKE '%IMO%' OR keywords LIKE '%해사%' OR subject LIKE '%해사%')"
        """
        if not values or not fields:
            return "1=1"
        
        conditions = []
        for value in values:
            for field in fields:
                conditions.append(f"{field} LIKE '%{value}%'")
        
        return f"({' OR '.join(conditions)})"
    
    @staticmethod
    def build_in_condition(values: List[str], field: str) -> str:
        """
        Build IN condition for multiple exact values
        
        Example:
        values = ["KR", "JP", "US"]
        field = "organization_code"
        Returns: "organization_code IN ('KR', 'JP', 'US')"
        """
        if not values:
            return "1=1"
        
        quoted_values = [f"'{v}'" for v in values]
        return f"{field} IN ({', '.join(quoted_values)})"
    
    @staticmethod
    def build_between_dates(date_from: str, date_to: str, field: str = "sent_time") -> str:
        """
        Build BETWEEN condition for date range
        
        Example:
        date_from = "2024-01-01"
        date_to = "2024-12-31"
        Returns: "sent_time BETWEEN '2024-01-01' AND '2024-12-31'"
        """
        return f"{field} BETWEEN '{date_from}' AND '{date_to}'"
    
    @staticmethod
    def build_date_condition(date_param: Union[Dict, int], field: str = "sent_time") -> str:
        """
        Build date condition from various formats
        
        Supports:
        - Relative days: {"type": "relative", "days": 30}
        - Date range: {"type": "range", "from": "2024-01-01", "to": "2024-12-31"}
        - Single integer (backward compatibility): 30
        
        Returns appropriate SQL condition
        """
        if isinstance(date_param, int):
            # Backward compatibility: single days parameter
            return f"{field} >= DATE('now', '-{date_param} days')"
        
        elif isinstance(date_param, dict):
            date_type = date_param.get('type', 'relative')
            
            if date_type == 'relative':
                # Support both 'days' and 'amount' for period type
                days = date_param.get('days', date_param.get('amount', 30))
                return f"{field} >= DATE('now', '-{days} days')"
                
            elif date_type in ['range', 'absolute']:
                # Support both 'from/to' and 'start/end' for consistency
                date_from = date_param.get('from', date_param.get('start'))
                date_to = date_param.get('to', date_param.get('end'))
                if date_from and date_to:
                    return ParameterBuilder.build_between_dates(date_from, date_to, field)
                elif date_from:
                    return f"{field} >= '{date_from}'"
                elif date_to:
                    return f"{field} <= '{date_to}'"
                    
        # Default fallback
        return f"{field} >= DATE('now', '-30 days')"
    
    @staticmethod
    def process_parameters(sql_template: str, parameters: List[Dict], user_params: Dict[str, Any]) -> str:
        """
        Process parameters and build final SQL query
        
        Args:
            sql_template: SQL template with placeholders
            parameters: Parameter definitions from template
            user_params: User-provided parameter values
            
        Returns:
            Final SQL query with all placeholders replaced
        """
        final_sql = sql_template
        
        for param_def in parameters:
            param_name = param_def['name']
            param_type = param_def['type']
            default_value = param_def.get('default')
            sql_builder = param_def.get('sql_builder')
            
            # Get value from user params or use default
            value = user_params.get(param_name, default_value)
            
            # Skip if no value and no default
            if value is None:
                if param_def.get('required', False):
                    raise ValueError(f"Required parameter '{param_name}' not provided")
                continue
            
            # Handle different parameter types
            if sql_builder:
                # Complex parameter with SQL builder
                builder_type = sql_builder['type']
                
                if builder_type == 'or_like':
                    # Handle array of keywords with OR LIKE
                    if not isinstance(value, list):
                        value = [value]
                    fields = sql_builder['fields']
                    placeholder = sql_builder['placeholder']
                    condition = ParameterBuilder.build_or_like_condition(value, fields)
                    final_sql = final_sql.replace(placeholder, condition)
                    
                elif builder_type == 'in':
                    # Handle array with IN clause
                    if not isinstance(value, list):
                        value = [value]
                    field = sql_builder['field']
                    placeholder = sql_builder['placeholder']
                    condition = ParameterBuilder.build_in_condition(value, field)
                    final_sql = final_sql.replace(placeholder, condition)
                    
                elif builder_type in ['date_range', 'period']:
                    # Handle date range/period parameter
                    field = sql_builder.get('field', 'sent_time')
                    placeholder = sql_builder['placeholder']
                    condition = ParameterBuilder.build_date_condition(value, field)
                    final_sql = final_sql.replace(placeholder, condition)
                    
                elif builder_type == 'keywords':
                    # Handle keywords parameter (similar to or_like)
                    if not isinstance(value, list):
                        value = [value]
                    fields = sql_builder.get('fields', ['keywords', 'subject'])
                    placeholder = sql_builder['placeholder']
                    condition = ParameterBuilder.build_or_like_condition(value, fields)
                    final_sql = final_sql.replace(placeholder, condition)
                    
                elif builder_type == 'string':
                    # Handle simple string replacement
                    placeholder = sql_builder['placeholder']
                    # Check if it's a column name replacement (no quotes)
                    if sql_builder.get('as_column', False) or f"r.{placeholder}" in final_sql or f"c.{placeholder}" in final_sql:
                        final_sql = final_sql.replace(placeholder, value)
                    else:
                        final_sql = final_sql.replace(placeholder, f"'{value}'")
                    
            else:
                # Simple parameter replacement
                placeholder = f"{{{param_name}}}"
                
                # Special handling for backward compatibility
                if param_name == 'days' and 'date_range' not in [p['name'] for p in parameters]:
                    # Legacy days parameter - convert to date condition
                    date_condition = f"sent_time >= DATE('now', '-{value} days')"
                    final_sql = final_sql.replace(f"sent_time >= DATE('now', '-{{{param_name}}} days')", date_condition)
                    final_sql = final_sql.replace(f"a.sent_time >= DATE('now', '-{{{param_name}}} days')", f"a.{date_condition}")
                    final_sql = final_sql.replace(f"r.sent_time >= DATE('now', '-{{{param_name}}} days')", f"r.{date_condition}")
                else:
                    if param_type == 'array':
                        # Convert array to comma-separated string for simple cases
                        if isinstance(value, list):
                            value = ','.join(str(v) for v in value)
                    final_sql = final_sql.replace(placeholder, str(value))
        
        return final_sql


# Example usage
if __name__ == "__main__":
    # Test with multiple keywords
    template = {
        "sql_template": {
            "query": "SELECT * FROM agenda_all WHERE {keywords_condition} AND sent_time >= DATE('now', '-{days} days')"
        },
        "parameters": [
            {
                "name": "keywords",
                "type": "array",
                "required": false,
                "default": [],
                "sql_builder": {
                    "type": "or_like",
                    "fields": ["keywords", "subject", "body"],
                    "placeholder": "{keywords_condition}"
                }
            },
            {
                "name": "days",
                "type": "integer",
                "required": false,
                "default": 30
            }
        ]
    }
    
    user_params = {
        "keywords": ["IMO", "해사", "안전"],
        "days": 60
    }
    
    builder = ParameterBuilder()
    final_sql = builder.process_parameters(
        template["sql_template"]["query"],
        template["parameters"],
        user_params
    )
    print(final_sql)