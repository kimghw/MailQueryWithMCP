#!/usr/bin/env python3
"""
Merge split query template files back into a unified file
"""
import json
from pathlib import Path

def merge_templates(input_dir='query_templates_split', output_file='query_templates_unified.json'):
    """Merge split template files back into unified format"""
    
    input_path = Path(input_dir)
    
    # Read metadata
    metadata_file = input_path / 'metadata.json'
    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # Read index
    index_file = input_path / 'index.json'
    with open(index_file, 'r', encoding='utf-8') as f:
        index = json.load(f)
    
    # Initialize unified data structure
    unified_data = {
        "version": metadata.get("version", "10.0.0"),
        "description": metadata.get("description", "IACSGRAPH Query Templates with MCP Integration"),
        "last_updated": metadata.get("last_updated", "2025-01-26"),
        "total_templates": metadata.get("total_templates", 0),
        "metadata": metadata.get("metadata", {}),
        "database_schema": metadata.get("database_schema", {}),
        "query_guidelines": metadata.get("query_guidelines", {}),
        "templates": []
    }
    
    # Read and merge all template files in order
    for file_info in index['files']:
        template_file = input_path / file_info['filename']
        print(f"Reading {template_file}...")
        
        with open(template_file, 'r', encoding='utf-8') as f:
            part_data = json.load(f)
        
        # Add templates from this part
        templates = part_data.get('templates', [])
        unified_data['templates'].extend(templates)
        print(f"  Added {len(templates)} templates")
    
    # Verify template count
    actual_count = len(unified_data['templates'])
    expected_count = unified_data['total_templates']
    
    if actual_count != expected_count:
        print(f"WARNING: Template count mismatch! Expected {expected_count}, got {actual_count}")
        unified_data['total_templates'] = actual_count
    
    print(f"\nTotal templates merged: {actual_count}")
    
    # Write unified file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unified_data, f, ensure_ascii=False, indent=2)
    
    print(f"Created unified file: {output_file}")
    
    return output_file

if __name__ == "__main__":
    merge_templates()