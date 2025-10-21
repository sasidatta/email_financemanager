#!/usr/bin/env python3
"""
Simple migration runner for Email Finance Manager
Run this when your database is accessible to migrate existing data.
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the data migration manually."""
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', '192.168.0.174'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            dbname=os.getenv('POSTGRES_DB', 'emaildb'),
            user=os.getenv('POSTGRES_USER', 'bankuser'),
            password=os.getenv('POSTGRES_PASSWORD', 'bankpass')
        )
        
        # Read and execute migration
        with open('migrate_data.sql', 'r') as f:
            migration_sql = f.read()
        
        with conn.cursor() as cursor:
            cursor.execute(migration_sql)
            conn.commit()
            
        logger.info("Migration completed successfully!")
        conn.close()
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    logger.info("Starting manual migration...")
    run_migration()
