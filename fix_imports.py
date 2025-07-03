#!/usr/bin/env python3
import os
import re
import sys

def fix_imports_in_file(filepath):
    """파일 내의 잘못된 import 구문을 수정"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # infra.core에서 여러 항목을 import하는 패턴들을 수정
    patterns = [
        # from infra.core.logger import get_logger
from infra.core.config import get_config
        (r'from infra\.core import ([^;\n]+)', fix_core_imports),
        # from infra.core.logger import get_logger
from infra.core.config import get_config
        (r'from infra\.core\.logger import ([^;\n]+)', fix_logger_imports),
        # from infra.core.config import get_config
from infra.core.logger import get_logger
        (r'from infra\.core\.config import ([^;\n]+)', fix_config_imports),
        # from infra.core.database import get_database_manager
from infra.core.logger import get_logger
        (r'from infra\.core\.database import ([^;\n]+)', fix_database_imports),
        # from infra.core.kafka_client import get_kafka_client
from infra.core.logger import get_logger
        (r'from infra\.core\.kafka_client import ([^;\n]+)', fix_kafka_imports),
    ]
    
    for pattern, fix_func in patterns:
        matches = re.finditer(pattern, content)
        for match in reversed(list(matches)):
            imports = match.group(1)
            new_imports = fix_func(imports)
            content = content[:match.start()] + new_imports + content[match.end():]
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed imports in: {filepath}")
        return True
    return False

def fix_core_imports(imports_str):
    """
    items = [item.strip() for item in imports_str.split(',')]
    import_lines = []
    
    for item in items:
        if 'get_logger' in item:
            import_lines.append('from infra.core.logger import get_logger')
        elif 'get_config' in item:
            import_lines.append('from infra.core.config import get_config')
        elif 'get_database_manager' in item:
            import_lines.append('from infra.core.database import get_database_manager')
        elif 'get_kafka_client' in item:
            import_lines.append('from infra.core.kafka_client import get_kafka_client')
    
    return '\n'.join(import_lines)

def fix_logger_imports(imports_str):
    """
    items = [item.strip() for item in imports_str.split(',')]
    logger_items = []
    other_imports = []
    
    for item in items:
        if 'get_logger' in item:
            logger_items.append(item)
        elif 'get_config' in item:
            other_imports.append('from infra.core.config import get_config')
        elif 'get_database_manager' in item:
            other_imports.append('from infra.core.database import get_database_manager')
        elif 'get_kafka_client' in item:
            other_imports.append('from infra.core.kafka_client import get_kafka_client')
    
    result = []
    if logger_items:
        result.append(f"
    result.extend(other_imports)
    
    return '\n'.join(result)

def fix_config_imports(imports_str):
    """
    items = [item.strip() for item in imports_str.split(',')]
    config_items = []
    other_imports = []
    
    for item in items:
        if 'get_config' in item:
            config_items.append(item)
        elif 'get_logger' in item:
            other_imports.append('from infra.core.logger import get_logger')
        elif 'get_database_manager' in item:
            other_imports.append('from infra.core.database import get_database_manager')
        elif 'get_kafka_client' in item:
            other_imports.append('from infra.core.kafka_client import get_kafka_client')
    
    result = []
    if config_items:
        result.append(f"
    result.extend(other_imports)
    
    return '\n'.join(result)

def fix_database_imports(imports_str):
    """
    items = [item.strip() for item in imports_str.split(',')]
    db_items = []
    other_imports = []
    
    for item in items:
        if 'get_database_manager' in item:
            db_items.append(item)
        elif 'get_logger' in item:
            other_imports.append('from infra.core.logger import get_logger')
        elif 'get_config' in item:
            other_imports.append('from infra.core.config import get_config')
        elif 'get_kafka_client' in item:
            other_imports.append('from infra.core.kafka_client import get_kafka_client')
    
    result = []
    if db_items:
        result.append(f"
    result.extend(other_imports)
    
    return '\n'.join(result)

def fix_kafka_imports(imports_str):
    """
    items = [item.strip() for item in imports_str.split(',')]
    kafka_items = []
    other_imports = []
    
    for item in items:
        if 'get_kafka_client' in item:
            kafka_items.append(item)
        elif 'get_logger' in item:
            other_imports.append('from infra.core.logger import get_logger')
        elif 'get_config' in item:
            other_imports.append('from infra.core.config import get_config')
        elif 'get_database_manager' in item:
            other_imports.append('from infra.core.database import get_database_manager')
    
    result = []
    if kafka_items:
        result.append(f"
    result.extend(other_imports)
    
    return '\n'.join(result)

def main():
    root_dir = '/home/kimghw/IACSGRAPH'
    fixed_count = 0
    
    for root, dirs, files in os.walk(root_dir):
        # Skip .venv directory
        if '.venv' in root:
            continue
            
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if fix_imports_in_file(filepath):
                    fixed_count += 1
    
    print(f"\nTotal files fixed: {fixed_count}")

if __name__ == '__main__':
    main()
