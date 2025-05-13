import psycopg2
from psycopg2 import pool
from config_loader import Config

config = Config()
db_conf = config.database

db_pool = psycopg2.pool.SimpleConnectionPool(
    1, 20,
    host=db_conf.get('host', 'localhost'),
    port=db_conf.get('port', 5432),
    dbname=db_conf.get('dbname', 'emaildb'),
    user=db_conf.get('user', 'bankuser'),
    password=db_conf.get('password', 'bankpass')
)

def get_conn():
    return db_pool.getconn()

def put_conn(conn):
    db_pool.putconn(conn) 