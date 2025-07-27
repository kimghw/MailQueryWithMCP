#!/usr/bin/env python3
"""Upload templates to both SQL and Vector databases"""

import argparse
import logging
from pathlib import Path
from uploaders import TemplateUploader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Upload templates to databases')
    parser.add_argument(
        '--file', 
        type=str,
        default='data/unified/query_templates_unified.json',
        help='Template file path'
    )
    parser.add_argument(
        '--recreate-vector', 
        action='store_true',
        help='Recreate vector collection'
    )
    parser.add_argument(
        '--vector-only',
        action='store_true',
        help='Upload to vector database only'
    )
    parser.add_argument(
        '--sql-only',
        action='store_true',
        help='Upload to SQL database only'
    )
    args = parser.parse_args()
    
    # Convert relative path to absolute
    file_path = Path(args.file)
    if not file_path.is_absolute():
        file_path = Path(__file__).parent / file_path
    
    if not file_path.exists():
        logger.error(f"Template file not found: {file_path}")
        return 1
    
    # Initialize uploader
    uploader = TemplateUploader()
    
    try:
        if args.vector_only:
            # Upload to vector DB only
            templates = uploader.load_templates_from_file(file_path)
            count = uploader.upload_to_vector_db(templates, recreate=args.recreate_vector)
            logger.info(f"Uploaded {count} vectors to vector database")
            
        elif args.sql_only:
            # Upload to SQL only
            templates = uploader.load_templates_from_file(file_path)
            count = uploader.upload_to_sql(templates)
            logger.info(f"Uploaded {count} templates to SQL database")
            
        else:
            # Upload to both
            results = uploader.upload_all(
                file_path,
                recreate_qdrant=args.recreate_vector
            )
            
            logger.info("Upload Summary:")
            logger.info(f"  SQL templates: {results['sql_total']}")
            logger.info(f"  Vector DB points: {results['vector_db_total']}")
            logger.info(f"  Avg vectors per template: {results['vector_db_total'] / results['sql_total']:.1f}")
        
        # Verify sync
        sync_info = uploader.verify_sync()
        logger.info("\nDatabase Status:")
        logger.info(f"  SQL templates: {sync_info['sql_count']}")
        logger.info(f"  Vector DB points: {sync_info['vector_count']}")
        logger.info(f"  Avg vectors per template: {sync_info['avg_vectors_per_template']:.1f}")
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())