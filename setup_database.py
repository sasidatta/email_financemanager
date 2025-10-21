#!/usr/bin/env python3
"""
Database setup script for Email Finance Manager
Run this script to initialize the database schema and run migrations.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Create database connection using environment variables."""
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            dbname=os.getenv('POSTGRES_DB', 'emaildb'),
            user=os.getenv('POSTGRES_USER', 'bankuser'),
            password=os.getenv('POSTGRES_PASSWORD', 'bankpass')
        )
        return conn
    except psycopg2.Error as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)

def run_sql_file(conn, file_path):
    """Execute SQL commands from a file."""
    try:
        with open(file_path, 'r') as f:
            sql_content = f.read()
        
        with conn.cursor() as cursor:
            cursor.execute(sql_content)
            conn.commit()
            logger.info(f"Successfully executed {file_path}")
            
    except FileNotFoundError:
        logger.error(f"SQL file not found: {file_path}")
        sys.exit(1)
    except psycopg2.Error as e:
        logger.error(f"Error executing {file_path}: {e}")
        conn.rollback()
        sys.exit(1)

def check_database_exists(conn, dbname):
    """Check if database exists."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
        return cursor.fetchone() is not None

def create_database_if_not_exists(host, port, user, password, dbname):
    """Create database if it doesn't exist."""
    try:
        # Connect to postgres database to create new database
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname='postgres',
            user=user,
            password=password
        )
        conn.autocommit = True
        
        if not check_database_exists(conn, dbname):
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE {dbname}")
                logger.info(f"Created database: {dbname}")
        else:
            logger.info(f"Database {dbname} already exists")
            
        conn.close()
        
    except psycopg2.Error as e:
        logger.error(f"Failed to create database: {e}")
        sys.exit(1)

def main():
    """Main setup function."""
    logger.info("Starting database setup...")
    
    # Get database configuration from environment
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = os.getenv('POSTGRES_PORT', '5432')
    user = os.getenv('POSTGRES_USER', 'bankuser')
    password = os.getenv('POSTGRES_PASSWORD', 'bankpass')
    dbname = os.getenv('POSTGRES_DB', 'emaildb')
    
    # Create database if it doesn't exist
    create_database_if_not_exists(host, port, user, password, dbname)
    
    # Connect to the target database
    conn = get_db_connection()
    
    # Run migrations in order
    migrations = [
        'migrations/001_initial_schema.sql',
        'migrations/002_migrate_existing_data.sql'
    ]
    
    for migration in migrations:
        if os.path.exists(migration):
            logger.info(f"Running migration: {migration}")
            run_sql_file(conn, migration)
        else:
            logger.warning(f"Migration file not found: {migration}")
    
    # Verify setup
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT COUNT(*) as count FROM categories")
        categories_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM transactions")
        transactions_count = cursor.fetchone()['count']
        
        logger.info(f"Setup complete! Categories: {categories_count}, Transactions: {transactions_count}")
    
    conn.close()
    logger.info("Database setup completed successfully!")

if __name__ == "__main__":
    main()
