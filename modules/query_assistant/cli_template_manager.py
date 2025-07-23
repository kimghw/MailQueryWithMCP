#!/usr/bin/env python3
"""CLI tool for managing Query Assistant templates"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

from database.template_manager import TemplateManager
from database.migrate_jsonl import JSONLMigrator
from services.vector_store_http import VectorStoreHTTP


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Query Assistant Template Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate JSONL files to database
  python cli_template_manager.py migrate --folder ./templates/data
  
  # Sync templates to VectorDB
  python cli_template_manager.py sync
  
  # Show statistics
  python cli_template_manager.py stats
  
  # List templates
  python cli_template_manager.py list --category agenda_summary
  
  # Create a new template
  python cli_template_manager.py create --file new_template.json
  
  # Export templates to JSON
  python cli_template_manager.py export --output templates_backup.json
        """
    )
    
    parser.add_argument(
        '--db-url',
        default='sqlite:///templates.db',
        help='Database URL (default: sqlite:///templates.db)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Migrate JSONL files to database')
    migrate_parser.add_argument(
        '--folder',
        default='modules/query_assistant/templates/data',
        help='Folder containing JSONL files'
    )
    migrate_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test migration without writing to database'
    )
    
    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Sync templates to VectorDB')
    sync_parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Batch size for indexing (default: 50)'
    )
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show template statistics')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List templates')
    list_parser.add_argument(
        '--category',
        help='Filter by category'
    )
    list_parser.add_argument(
        '--limit',
        type=int,
        default=20,
        help='Maximum number of templates to show (default: 20)'
    )
    list_parser.add_argument(
        '--format',
        choices=['table', 'json', 'csv'],
        default='table',
        help='Output format'
    )
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new template')
    create_parser.add_argument(
        '--file',
        required=True,
        help='JSON file containing template data'
    )
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update an existing template')
    update_parser.add_argument(
        '--template-id',
        required=True,
        help='Template ID to update'
    )
    update_parser.add_argument(
        '--file',
        required=True,
        help='JSON file containing updates'
    )
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a template')
    delete_parser.add_argument(
        '--template-id',
        required=True,
        help='Template ID to delete'
    )
    delete_parser.add_argument(
        '--hard',
        action='store_true',
        help='Permanently delete (default: soft delete)'
    )
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export templates to JSON')
    export_parser.add_argument(
        '--output',
        required=True,
        help='Output file path'
    )
    export_parser.add_argument(
        '--category',
        help='Export only specific category'
    )
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search templates')
    search_parser.add_argument(
        'query',
        help='Search query'
    )
    search_parser.add_argument(
        '--limit',
        type=int,
        default=5,
        help='Maximum results (default: 5)'
    )
    
    return parser


async def handle_migrate(args, manager: TemplateManager):
    """Handle migrate command"""
    migrator = JSONLMigrator(db_url=args.db_url)
    
    if args.dry_run:
        print(f"🔍 Dry run - scanning {args.folder}")
        data_path = Path(args.folder)
        jsonl_files = list(data_path.glob("*.jsonl"))
        
        total_templates = 0
        for jsonl_file in jsonl_files:
            templates = migrator.read_jsonl_file(jsonl_file)
            total_templates += len(templates)
            
            print(f"\n📄 {jsonl_file.name}: {len(templates)} templates")
            for template in templates[:3]:
                converted = migrator.convert_template_format(template)
                print(f"  - {converted['template_id']}: {converted['natural_questions'][:60]}...")
        
        print(f"\n✅ Total templates found: {total_templates}")
    else:
        print(f"🚀 Starting migration from {args.folder}")
        result = await migrator.migrate_and_sync(args.folder)
        
        print("\n📊 Migration Results:")
        print(f"  ✅ Templates migrated: {result['migrated_count']}")
        
        if result['migration_errors']:
            print(f"  ❌ Migration errors: {len(result['migration_errors'])}")
            for error in result['migration_errors'][:5]:
                print(f"     - {error}")
        
        if 'sync_result' in result:
            sync = result['sync_result']
            print(f"\n🔄 VectorDB sync:")
            print(f"  - Previously indexed: {sync.get('previously_indexed', 0)}")
            print(f"  - Newly indexed: {sync.get('newly_indexed', 0)}")
            print(f"  - Total active: {sync.get('total_templates', 0)}")


async def handle_sync(args, manager: TemplateManager):
    """Handle sync command"""
    print("🔄 Starting template synchronization...")
    result = await manager.full_sync()
    
    print(f"\n✅ Sync complete:")
    print(f"  - Total templates: {result['total_templates']}")
    print(f"  - Previously indexed: {result['previously_indexed']}")
    print(f"  - Newly indexed: {result['newly_indexed']}")
    
    if result['errors']:
        print(f"  ❌ Errors: {len(result['errors'])}")
        for error in result['errors'][:5]:
            print(f"     - {error}")


def handle_stats(args, manager: TemplateManager):
    """Handle stats command"""
    stats = manager.get_statistics()
    
    print("📊 Template Statistics:\n")
    print(f"  Total templates: {stats['total_templates']}")
    print(f"  Active templates: {stats['active_templates']}")
    print(f"  Indexed templates: {stats['indexed_templates']}")
    
    print(f"\n📂 Categories:")
    for category, count in stats['categories']:
        print(f"  - {category}: {count}")
    
    if stats['most_used']:
        print(f"\n🔥 Most used templates:")
        for template in stats['most_used'][:5]:
            print(f"  - {template.template_id}: {template.usage_count} uses")


def handle_list(args, manager: TemplateManager):
    """Handle list command"""
    templates = manager.list_templates(category=args.category, limit=args.limit)
    
    if args.format == 'json':
        data = [t.to_dict() for t in templates]
        print(json.dumps(data, indent=2, ensure_ascii=False))
    
    elif args.format == 'csv':
        if templates:
            # Print CSV header
            print("template_id,category,natural_questions,usage_count,is_active")
            for t in templates:
                print(f'"{t.template_id}","{t.category}","{t.natural_questions}",{t.usage_count},{t.is_active}')
    
    else:  # table format
        print(f"\n📋 Templates" + (f" in category '{args.category}'" if args.category else ""))
        print("=" * 80)
        
        for template in templates:
            print(f"\n🆔 {template.template_id}")
            print(f"   Category: {template.category}")
            print(f"   Question: {template.natural_questions[:60]}...")
            print(f"   Usage: {template.usage_count} | Active: {template.is_active}")


def handle_create(args, manager: TemplateManager):
    """Handle create command"""
    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        
        template = manager.create_template(template_data)
        print(f"✅ Template created: {template.template_id}")
        
    except FileNotFoundError:
        print(f"❌ File not found: {args.file}")
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
    except Exception as e:
        print(f"❌ Error creating template: {e}")


def handle_update(args, manager: TemplateManager):
    """Handle update command"""
    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            updates = json.load(f)
        
        template = manager.update_template(args.template_id, updates)
        print(f"✅ Template updated: {template.template_id}")
        
    except FileNotFoundError:
        print(f"❌ File not found: {args.file}")
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
    except Exception as e:
        print(f"❌ Error updating template: {e}")


def handle_delete(args, manager: TemplateManager):
    """Handle delete command"""
    try:
        manager.delete_template(args.template_id, hard_delete=args.hard)
        action = "deleted" if args.hard else "deactivated"
        print(f"✅ Template {action}: {args.template_id}")
        
    except Exception as e:
        print(f"❌ Error deleting template: {e}")


def handle_export(args, manager: TemplateManager):
    """Handle export command"""
    templates = manager.list_templates(category=args.category, active_only=False)
    
    data = [t.to_dict() for t in templates]
    
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Exported {len(data)} templates to {args.output}")
        
    except Exception as e:
        print(f"❌ Error exporting templates: {e}")


async def handle_search(args, manager: TemplateManager):
    """Handle search command"""
    # This would need integration with vector store
    print(f"🔍 Searching for: {args.query}")
    print("⚠️  Search functionality requires vector store integration")


async def main():
    """Main function"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Create manager
    manager = TemplateManager(db_url=args.db_url)
    
    # Handle commands
    if args.command == 'migrate':
        await handle_migrate(args, manager)
    
    elif args.command == 'sync':
        await handle_sync(args, manager)
    
    elif args.command == 'stats':
        handle_stats(args, manager)
    
    elif args.command == 'list':
        handle_list(args, manager)
    
    elif args.command == 'create':
        handle_create(args, manager)
    
    elif args.command == 'update':
        handle_update(args, manager)
    
    elif args.command == 'delete':
        handle_delete(args, manager)
    
    elif args.command == 'export':
        handle_export(args, manager)
    
    elif args.command == 'search':
        await handle_search(args, manager)


if __name__ == "__main__":
    asyncio.run(main())