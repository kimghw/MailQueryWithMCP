"""Parameter validator for v2.0.0 templates based on creation_guidelines.md"""

import re
import json
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from pathlib import Path


class ParameterValidator:
    """Validate template parameters based on creation_guidelines.md"""
    
    # Valid parameter types (simplified in v2.0.0)
    VALID_TYPES = ['string', 'datetime', 'array']
    
    # Known MCP formats
    MCP_FORMATS = {
        'period': 'extracted_period',
        'organization': 'extracted_organization',
        'keyword': 'extracted_keywords',
        'keywords': 'extracted_keywords',
        'panel': 'extracted_panel',
        'agenda': 'extracted_agenda'
    }
    
    # Valid organizations
    VALID_ORGANIZATIONS = [
        'ABS', 'BV', 'CCS', 'CRS', 'DNV', 'IRS', 
        'KR', 'NK', 'PRS', 'RINA', 'IL', 'TL', 'LR'
    ]
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_parameters(self, parameters: List[Dict[str, Any]], sql_query: str) -> Tuple[bool, List[str], List[str]]:
        """Validate parameters list and their usage in SQL
        
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        if not isinstance(parameters, list):
            self.errors.append("Parameters must be a list")
            return False, self.errors, self.warnings
        
        # Extract parameters from SQL (v2.0.0 uses :param_name format)
        sql_params = self._extract_sql_parameters(sql_query)
        defined_params = []
        
        for i, param in enumerate(parameters):
            param_name = param.get('name', f'param_{i}')
            defined_params.append(param_name)
            
            # Validate individual parameter
            self._validate_parameter(param, i)
        
        # Check SQL parameter usage
        self._check_parameter_usage(sql_params, defined_params)
        
        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings
    
    def _extract_sql_parameters(self, sql_query: str) -> List[str]:
        """Extract :param_name style parameters from SQL"""
        if not sql_query:
            return []
            
        # Find all :param_name patterns
        params = re.findall(r':(\w+)', sql_query)
        # Remove SQLite datetime function parameters
        params = [p for p in params if p not in ['period_start', 'period_end', 'organization', 'keyword', 'agenda', 'panel']
                  or p in params]  # Keep if actually used as parameter
        return list(set(params))
    
    def _validate_parameter(self, param: Dict[str, Any], index: int):
        """Validate individual parameter structure"""
        # Check required fields
        if 'name' not in param:
            self.errors.append(f"Parameter {index}: missing 'name' field")
            return
        
        name = param['name']
        
        # Check type
        if 'type' not in param:
            self.errors.append(f"Parameter '{name}': missing 'type' field")
        else:
            param_type = param['type']
            if param_type not in self.VALID_TYPES:
                self.errors.append(f"Parameter '{name}': invalid type '{param_type}'. Valid types: {', '.join(self.VALID_TYPES)}")
        
        # Check required field
        if 'required' not in param:
            self.warnings.append(f"Parameter '{name}': missing 'required' field (should be true/false)")
        
        # Validate based on type
        param_type = param.get('type')
        if param_type == 'datetime':
            self._validate_datetime_parameter(param)
        elif param_type == 'string':
            self._validate_string_parameter(param)
        elif param_type == 'array':
            self._validate_array_parameter(param)
        
        # Check mcp_format
        if 'mcp_format' not in param:
            # Suggest mcp_format based on name
            suggested_format = self._suggest_mcp_format(name)
            if suggested_format:
                self.warnings.append(f"Parameter '{name}': missing 'mcp_format'. Suggested: '{suggested_format}'")
            else:
                self.warnings.append(f"Parameter '{name}': missing 'mcp_format'")
        else:
            # Validate mcp_format matches expected pattern
            mcp_format = param['mcp_format']
            expected_format = self._suggest_mcp_format(name)
            if expected_format and mcp_format != expected_format:
                self.warnings.append(f"Parameter '{name}': mcp_format '{mcp_format}' might be incorrect. Expected: '{expected_format}'")
        
        # Check description
        if 'description' not in param:
            self.warnings.append(f"Parameter '{name}': missing 'description'")
    
    def _validate_datetime_parameter(self, param: Dict[str, Any]):
        """Validate datetime parameter"""
        name = param['name']
        
        # Check default value format
        if 'default' in param:
            default = param['default']
            if not isinstance(default, str):
                self.errors.append(f"Parameter '{name}': datetime default must be a string")
            elif not default.startswith('datetime('):
                self.errors.append(f"Parameter '{name}': datetime default should use datetime() function, e.g., \"datetime('now', '-30 days')\"")
            else:
                # Validate datetime expression
                valid_patterns = [
                    r"datetime\('now'\)",
                    r"datetime\('now', '[+-]\d+ days?'\)",
                    r"datetime\('now', '[+-]\d+ months?'\)",
                    r"datetime\('now', '[+-]\d+ years?'\)"
                ]
                if not any(re.match(pattern + r'$', default) for pattern in valid_patterns):
                    self.warnings.append(f"Parameter '{name}': unusual datetime default format: {default}")
    
    def _validate_array_parameter(self, param: Dict[str, Any]):
        """Validate array parameter"""
        name = param['name']
        
        # Check default value
        if 'default' in param:
            default = param['default']
            # Currently, default is stored as string, not array
            if isinstance(default, list):
                self.warnings.append(f"Parameter '{name}': default should be a string, not an array (current implementation)")
        
        # Check common array parameter names
        if name == 'keyword':
            if 'mcp_format' in param and param['mcp_format'] != 'extracted_keywords':
                self.warnings.append(f"Parameter '{name}': array type 'keyword' should use mcp_format='extracted_keywords'")
        elif name == 'organization':
            if 'mcp_format' in param and param['mcp_format'] != 'extracted_organizations':
                self.warnings.append(f"Parameter '{name}': array type 'organization' should use mcp_format='extracted_organizations'")
    
    def _validate_string_parameter(self, param: Dict[str, Any]):
        """Validate string parameter"""
        name = param['name']
        
        # Check for organization parameter
        if name == 'organization' and 'default' in param:
            default = param['default']
            if default not in self.VALID_ORGANIZATIONS:
                self.warnings.append(f"Parameter '{name}': unknown organization code '{default}'")
        
        # Check for old multi_query flag (deprecated)
        if 'multi_query' in param:
            self.errors.append(f"Parameter '{name}': multi_query is deprecated. Use type='array' instead")
    
    def _suggest_mcp_format(self, param_name: str) -> Optional[str]:
        """Suggest mcp_format based on parameter name"""
        # Direct matches
        if param_name in self.MCP_FORMATS:
            return self.MCP_FORMATS[param_name]
        
        # Pattern matches
        if 'period' in param_name or param_name.endswith('_start') or param_name.endswith('_end'):
            return 'extracted_period'
        elif 'org' in param_name or param_name == 'organization':
            return 'extracted_organization'
        elif 'keyword' in param_name:
            return 'extracted_keywords'
        elif 'panel' in param_name:
            return 'extracted_panel'
        elif 'agenda' in param_name:
            return 'extracted_agenda'
        
        return None
    
    def _check_parameter_usage(self, sql_params: List[str], defined_params: List[str]):
        """Check if SQL parameters match defined parameters"""
        # Check for undefined parameters in SQL
        for sql_param in sql_params:
            if sql_param not in defined_params:
                self.errors.append(f"SQL uses parameter :{sql_param} which is not defined")
        
        # Check for unused defined parameters
        for defined_param in defined_params:
            if defined_param and f':{defined_param}' not in str(sql_params):
                # Check if it's actually in the SQL (might be missed by regex)
                # This is a warning, not an error, as some parameters might be optional
                self.warnings.append(f"Parameter '{defined_param}' is defined but might not be used in SQL")
    
    def validate_file(self, file_path: Path) -> Tuple[bool, Dict[str, Any]]:
        """Validate parameters in all templates in a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            return False, {'error': f"Failed to load file: {e}"}
        
        templates = data.get('templates', [])
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
            parameters = template.get('parameters', [])
            sql_query = template.get('sql_template', {}).get('query', '')
            
            is_valid, errors, warnings = self.validate_parameters(parameters, sql_query)
            
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
    """Validate parameters in all template files"""
    import sys
    
    if len(sys.argv) < 2:
        template_dir = Path('/home/kimghw/IACSGRAPH/modules/templates/data/query_templates_split')
    else:
        template_dir = Path(sys.argv[1])
    
    validator = ParameterValidator()
    
    print("=" * 80)
    print("Parameter Validation Report (v2.0.0)")
    print("=" * 80)
    
    all_valid = True
    total_errors = 0
    total_warnings = 0
    
    for file_path in sorted(template_dir.glob('query_templates_group_*.json')):
        print(f"\nValidating {file_path.name}...")
        is_valid, results = validator.validate_file(file_path)
        
        if not is_valid:
            all_valid = False
        
        error_count = len(results.get('errors', []))
        warning_count = len(results.get('warnings', []))
        total_errors += error_count
        total_warnings += warning_count
        
        print(f"  Templates: {results['total']}")
        print(f"  Errors: {error_count}")
        print(f"  Warnings: {warning_count}")
        
        if results.get('errors'):
            print("\n  Errors:")
            for error_info in results['errors'][:3]:  # Show first 3
                print(f"    [{error_info['template_id']}]")
                for error in error_info['errors'][:2]:  # Show first 2 errors
                    print(f"      - {error}")
            if len(results['errors']) > 3:
                print(f"    ... and {len(results['errors']) - 3} more templates with errors")
        
        if results.get('warnings'):
            print("\n  Sample Warnings:")
            shown = 0
            for warning_info in results['warnings']:
                if shown >= 2:  # Show only 2 templates with warnings
                    remaining = len(results['warnings']) - shown
                    if remaining > 0:
                        print(f"    ... and {remaining} more templates with warnings")
                    break
                print(f"    [{warning_info['template_id']}]")
                for warning in warning_info['warnings'][:1]:  # Show first warning only
                    print(f"      - {warning}")
                shown += 1
    
    print("\n" + "=" * 80)
    print(f"Summary:")
    print(f"  Total Errors: {total_errors}")
    print(f"  Total Warnings: {total_warnings}")
    if all_valid:
        print("\n✓ All parameters are structurally valid!")
    else:
        print("\n✗ Some parameters have validation errors")
    print("=" * 80)


if __name__ == "__main__":
    main()