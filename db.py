from contextlib import contextmanager
from psycopg2.extras import RealDictCursor
import psycopg2
from psycopg2 import pool
from config_loader import Config
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

def get_db_config():
    """Get database configuration from environment variables or config file."""
    config = Config()
    db_conf = config.database
    
    return {
        'host': os.getenv('POSTGRES_HOST', db_conf.get('host', 'localhost')),
        'port': int(os.getenv('POSTGRES_PORT', db_conf.get('port', 5432))),
        'dbname': os.getenv('POSTGRES_DB', db_conf.get('dbname', 'emaildb')),
        'user': os.getenv('POSTGRES_USER', db_conf.get('user', 'bankuser')),
        'password': os.getenv('POSTGRES_PASSWORD', db_conf.get('password', 'bankpass'))
    }

# Global connection pool (initialized lazily)
db_pool = None
db_config = None

def initialize_pool():
    """Initialize the connection pool if not already done."""
    global db_pool, db_config
    
    if db_pool is None:
        db_config = get_db_config()
        try:
            db_pool = psycopg2.pool.SimpleConnectionPool(
                1, 20,
                host=db_config['host'],
                port=db_config['port'],
                dbname=db_config['dbname'],
                user=db_config['user'],
                password=db_config['password']
            )
            logger.info(f"Database connection pool initialized for {db_config['host']}:{db_config['port']}")
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise e

def get_conn():
    # Initialize pool if not already done
    initialize_pool()
    
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT 1')
    except Exception:
        logger.warning("Database connection lost. Attempting to reconnect...")
        # Try to reconnect if the connection is broken
        try:
            db_pool.putconn(conn, close=True)
        except Exception:
            # If putconn fails, close connection directly
            try:
                conn.close()
            except Exception:
                pass
        try:
            conn = psycopg2.connect(**db_config)
            logger.info("Database reconnection successful.")
        except Exception as e:
            logger.critical("Failed to reconnect to the database.", exc_info=True)
            raise e
    return conn

def put_conn(conn):
    db_pool.putconn(conn) 


# Context manager for getting a cursor and ensuring cleanup
@contextmanager
def get_cursor():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield cur, conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        put_conn(conn)

def get_connection():
    return get_conn()

def get_all_accounts():
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM accounts ORDER BY id DESC")
            accounts = cur.fetchall()
        conn.commit()
        return accounts
    except Exception as e:
        logger.exception("Error fetching accounts")
        raise
    finally:
        put_conn(conn)

def add_account(data):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO accounts (account_name, account_type, bank_name, account_number, credit_limit, current_balance)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                data['account_name'],
                data['account_type'],
                data['bank_name'],
                data['account_number'],
                data.get('credit_limit'),
                data.get('current_balance')
            ))
        conn.commit()
    except Exception as e:
        logger.exception("Error adding account")
        raise
    finally:
        put_conn(conn)

def update_account(account_id, data):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE accounts SET
                    account_name=%s,
                    account_type=%s,
                    bank_name=%s,
                    account_number=%s,
                    credit_limit=%s,
                    current_balance=%s,
                    updated_at=NOW()
                WHERE id=%s
            """, (
                data['account_name'],
                data['account_type'],
                data['bank_name'],
                data['account_number'],
                data.get('credit_limit'),
                data.get('current_balance'),
                account_id
            ))
        conn.commit()
    except Exception as e:
        logger.exception("Error updating account")
        raise
    finally:
        put_conn(conn)

def delete_account(account_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM accounts WHERE id=%s", (account_id,))
        conn.commit()
    except Exception as e:
        logger.exception("Error deleting account")
        raise
    finally:
        put_conn(conn)