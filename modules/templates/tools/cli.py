#!/usr/bin/env python3
"""CLI tool for template management"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.templates import UNIFIED_TEMPLATES_PATH
from modules.templates.uploaders import TemplateUploader
from modules.templates.validators import TemplateValidator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cmd_validate(args):
    """Validate template file"""
    file_path = Path(args.file) if args.file else UNIFIED_TEMPLATES_PATH
    
    validator = TemplateValidator()
    is_valid, report = validator.validate_file(file_path)
    
    print(f"\n{'='*60}")
    print(f"Template Validation Report")
    print(f"{'='*60}")
    print(f"File: {file_path}")
    print(f"Total templates: {report['total_count']}")
    print(f"Valid: {report['valid_count']}")
    print(f"Invalid: {report['invalid_count']}")
    
    if report.get('errors'):
        print(f"\n❌ Errors ({len(report['errors'])}):")
        for error in report['errors'][:10]:
            print(f"  - {error}")
        if len(report['errors']) > 10:
            print(f"  ... and {len(report['errors']) - 10} more")
            
    if report.get('warnings'):
        print(f"\n⚠️  Warnings ({len(report['warnings'])}):")
        for warning in report['warnings'][:10]:
            print(f"  - {warning}")
            
    if report.get('invalid_templates'):
        print(f"\n❌ Invalid templates:")
        for invalid in report['invalid_templates'][:5]:
            print(f"  - {invalid['template_id']} (index {invalid['index']})")
            for error in invalid['errors'][:2]:
                print(f"    • {error}")
                
    print(f"\n{'✅ All templates are valid!' if is_valid else '❌ Validation failed!'}")
    
    return 0 if is_valid else 1


def cmd_upload(args):
    """Upload templates to databases"""
    file_path = Path(args.file) if args.file else UNIFIED_TEMPLATES_PATH
    
    # Validate first
    validator = TemplateValidator()
    is_valid, report = validator.validate_file(file_path)
    
    if not is_valid and not args.force:
        print("❌ Validation failed! Use --force to upload anyway.")
        return 1
        
    # Upload
    uploader = TemplateUploader(
        db_path=args.db_path,
        qdrant_url=args.qdrant_url,
        qdrant_port=args.qdrant_port
    )
    
    target = args.target.lower()
    
    try:
        if target == 'all':
            results = uploader.upload_all(file_path, recreate_qdrant=args.recreate)
            print(f"\n✅ Upload complete!")
            print(f"  SQL: {results['sql']} uploaded, {results['sql_total']} total")
            print(f"  Qdrant: {results['qdrant']} uploaded, {results['qdrant_total']} total")
            
        elif target == 'sql':
            templates = uploader.load_templates_from_file(file_path)
            count = uploader.upload_to_sql(templates)
            print(f"\n✅ Uploaded {count} templates to SQL database")
            
        elif target == 'qdrant':
            templates = uploader.load_templates_from_file(file_path)
            count = uploader.upload_to_qdrant(templates, recreate=args.recreate)
            print(f"\n✅ Uploaded {count} templates to Qdrant")
            
        else:
            print(f"❌ Unknown target: {target}")
            return 1
            
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        print(f"❌ Upload failed: {e}")
        return 1
        
    return 0


def cmd_sync(args):
    """Check sync status between SQL and Qdrant"""
    uploader = TemplateUploader(
        db_path=args.db_path,
        qdrant_url=args.qdrant_url,
        qdrant_port=args.qdrant_port
    )
    
    status = uploader.verify_sync()
    
    print(f"\n{'='*40}")
    print(f"Sync Status")
    print(f"{'='*40}")
    print(f"SQL templates: {status['sql_count']}")
    print(f"Qdrant templates: {status['qdrant_count']}")
    print(f"Difference: {status['difference']}")
    print(f"Status: {'✅ In sync' if status['in_sync'] else '❌ Out of sync'}")
    
    return 0 if status['in_sync'] else 1


def cmd_search(args):
    """Search templates using Qdrant"""
    from modules.templates.uploaders import QdrantTemplateUploader
    
    uploader = QdrantTemplateUploader(
        qdrant_url=args.qdrant_url,
        qdrant_port=args.qdrant_port
    )
    
    results = uploader.search_templates(args.query, limit=args.limit)
    
    print(f"\n🔍 Search results for: '{args.query}'")
    print(f"{'='*60}")
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['template_id']} (score: {result['score']:.3f})")
        print(f"   Category: {result['category']}")
        if result['questions']:
            print(f"   Example: {result['questions'][0]}")
            
    if not results:
        print("No matching templates found.")
        
    return 0


def main():
    parser = argparse.ArgumentParser(description='Template management CLI')
    
    # Global options
    parser.add_argument('--db-path', default='data/iacsgraph.db', help='Path to SQL database')
    parser.add_argument('--qdrant-url', default='localhost', help='Qdrant server URL')
    parser.add_argument('--qdrant-port', type=int, default=6333, help='Qdrant server port')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate template file')
    validate_parser.add_argument('--file', help='Template file to validate')
    validate_parser.set_defaults(func=cmd_validate)
    
    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload templates to databases')
    upload_parser.add_argument('--file', help='Template file to upload')
    upload_parser.add_argument('--target', choices=['all', 'sql', 'qdrant'], default='all',
                              help='Upload target')
    upload_parser.add_argument('--recreate', action='store_true',
                              help='Recreate Qdrant collection')
    upload_parser.add_argument('--force', action='store_true',
                              help='Force upload even with validation errors')
    upload_parser.set_defaults(func=cmd_upload)
    
    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Check sync status')
    sync_parser.set_defaults(func=cmd_sync)
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search templates')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', type=int, default=5, help='Number of results')
    search_parser.set_defaults(func=cmd_search)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
        
    # Execute command
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())