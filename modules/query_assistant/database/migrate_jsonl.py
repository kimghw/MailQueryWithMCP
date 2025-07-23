"""Migration script to convert JSONL templates to database format"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import asyncio

from template_manager import TemplateManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JSONLMigrator:
    """Migrate JSONL templates to database"""
    
    def __init__(self, db_url: str = "sqlite:///templates.db"):
        self.template_manager = TemplateManager(db_url=db_url)
        
    def read_jsonl_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Read templates from JSONL file"""
        templates = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        template_data = json.loads(line)
                        templates.append(template_data)
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing line {line_num} in {file_path.name}: {e}")
                        
            logger.info(f"Read {len(templates)} templates from {file_path.name}")
            return templates
            
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return []
    
    def convert_template_format(self, jsonl_template: Dict[str, Any]) -> Dict[str, Any]:
        """Convert JSONL template format to database format"""
        # Map fields from JSONL to DB format
        db_template = {
            'template_id': jsonl_template.get('template_id'),
            'natural_questions': jsonl_template.get('natural_questions'),
            'sql_query': jsonl_template.get('sql_query'),
            'sql_query_with_parameters': jsonl_template.get('sql_query_with_parameters'),
            'keywords': jsonl_template.get('keywords', []),
            'category': jsonl_template.get('category'),
            'required_params': jsonl_template.get('required_params', []),
            'optional_params': jsonl_template.get('optional_params', []),
            'default_params': jsonl_template.get('default_params', {}),
            'examples': jsonl_template.get('examples', []),
            'description': jsonl_template.get('description'),
            'to_agent_prompt': jsonl_template.get('to_agent_prompt'),
            'version': jsonl_template.get('template_version', '1.0.0'),
            'embedding_model': jsonl_template.get('embedding_model', 'text-embedding-3-large'),
            'embedding_dimension': jsonl_template.get('embedding_dimension', 3072),
            'is_active': jsonl_template.get('active', True)
        }
        
        # Handle query_filter -> optional_params mapping if needed
        if 'query_filter' in jsonl_template and 'optional_params' not in jsonl_template:
            db_template['optional_params'] = jsonl_template['query_filter']
        
        # Remove None values
        db_template = {k: v for k, v in db_template.items() if v is not None}
        
        return db_template
    
    def migrate_jsonl_folder(self, folder_path: str) -> Tuple[int, List[str]]:
        """Migrate all JSONL files in a folder"""
        data_path = Path(folder_path)
        if not data_path.exists():
            raise ValueError(f"Folder not found: {folder_path}")
        
        all_templates = []
        errors = []
        
        # Find all JSONL files
        jsonl_files = list(data_path.glob("*.jsonl"))
        logger.info(f"Found {len(jsonl_files)} JSONL files in {folder_path}")
        
        for jsonl_file in jsonl_files:
            # Read templates from file
            file_templates = self.read_jsonl_file(jsonl_file)
            
            # Convert each template
            for template in file_templates:
                try:
                    converted = self.convert_template_format(template)
                    all_templates.append(converted)
                except Exception as e:
                    errors.append(f"Error converting template in {jsonl_file.name}: {e}")
        
        # Bulk create templates
        if all_templates:
            logger.info(f"Migrating {len(all_templates)} templates to database...")
            success_count, create_errors = self.template_manager.bulk_create_templates(all_templates)
            errors.extend(create_errors)
            
            return success_count, errors
        
        return 0, errors
    
    async def migrate_and_sync(self, folder_path: str) -> Dict[str, Any]:
        """Migrate JSONL files and sync to VectorDB"""
        # Step 1: Migrate to database
        success_count, errors = self.migrate_jsonl_folder(folder_path)
        
        result = {
            'migrated_count': success_count,
            'migration_errors': errors
        }
        
        # Step 2: Sync to VectorDB
        if success_count > 0:
            logger.info("Syncing migrated templates to VectorDB...")
            sync_result = await self.template_manager.full_sync()
            result.update({
                'sync_result': sync_result,
                'total_indexed': sync_result.get('newly_indexed', 0)
            })
        
        return result


async def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate JSONL templates to database")
    parser.add_argument(
        '--folder', 
        default='modules/query_assistant/templates/data',
        help='Folder containing JSONL files'
    )
    parser.add_argument(
        '--db-url',
        default='sqlite:///templates.db',
        help='Database URL'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test migration without writing to database'
    )
    
    args = parser.parse_args()
    
    # Create migrator
    migrator = JSONLMigrator(db_url=args.db_url)
    
    if args.dry_run:
        # Dry run - just read and validate
        data_path = Path(args.folder)
        jsonl_files = list(data_path.glob("*.jsonl"))
        
        total_templates = 0
        for jsonl_file in jsonl_files:
            templates = migrator.read_jsonl_file(jsonl_file)
            total_templates += len(templates)
            
            print(f"\n{jsonl_file.name}:")
            for template in templates[:3]:  # Show first 3
                converted = migrator.convert_template_format(template)
                print(f"  - {converted['template_id']}: {converted['natural_questions'][:50]}...")
        
        print(f"\nTotal templates found: {total_templates}")
        
    else:
        # Actual migration
        print(f"Starting migration from {args.folder}")
        result = await migrator.migrate_and_sync(args.folder)
        
        print("\n=== Migration Results ===")
        print(f"Templates migrated: {result['migrated_count']}")
        
        if result['migration_errors']:
            print(f"\nMigration errors: {len(result['migration_errors'])}")
            for error in result['migration_errors'][:5]:
                print(f"  - {error}")
        
        if 'sync_result' in result:
            sync = result['sync_result']
            print(f"\nVectorDB sync:")
            print(f"  - Previously indexed: {sync.get('previously_indexed', 0)}")
            print(f"  - Newly indexed: {sync.get('newly_indexed', 0)}")
            print(f"  - Total active: {sync.get('total_templates', 0)}")
            
            if sync.get('errors'):
                print(f"  - Sync errors: {len(sync['errors'])}")
        
        print("\nMigration complete!")


if __name__ == "__main__":
    asyncio.run(main())