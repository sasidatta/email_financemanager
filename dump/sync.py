import os
import sqlite3
import psycopg2

def get_db_config():
    return {
        "host": "192.168.0.174",
        "port": "5432",
        "dbname": "emaildb",
        "user": "bankuser",
        "password": "bankpass",
    }

def sync_transactions(sqlite_db_path, pg_conn_params):
    # Connect to SQLite .mmbak database
    sqlite_conn = sqlite3.connect(sqlite_db_path)
    sqlite_conn.row_factory = sqlite3.Row  # Enable named access
    sqlite_cursor = sqlite_conn.cursor()

    # Connect to Postgres database
    pg_conn = psycopg2.connect(**pg_conn_params)
    pg_cursor = pg_conn.cursor()

    # Read transactions from ZINOUTCOME table in SQLite
    sqlite_cursor.execute("SELECT * FROM ZINOUTCOME")
    transactions = sqlite_cursor.fetchall()

    from datetime import datetime, timezone, timedelta

    # Insert transactions into Postgres external_transactions table
    for transaction in transactions:
        # Map SQLite columns to external_transactions table columns:
        # ZDATE (int) -> email_timestamp (as datetime with tz)
        # ZAMOUNT -> amount
        # ZASSET_NAME -> merchant_name
        # ZDO_TYPE -> transaction_type
        # ZCARDDIVIDID -> card_number
        # ZCATEGORY_NAME -> category
        # ZCONTENT -> notes
        zdate_int = transaction["ZDATE"]
        # ZDATE is in seconds since 2001-01-01 00:00:00 UTC (Apple epoch)
        apple_epoch = datetime(2001, 1, 1, tzinfo=timezone.utc)
        if zdate_int is not None:
            email_timestamp = apple_epoch + timedelta(seconds=zdate_int)
        else:
            email_timestamp = datetime.utcnow()
        amount = transaction["ZAMOUNT"]
        merchant_name = transaction["ZASSET_NAME"]
        if merchant_name is None or merchant_name.strip() == "":
            merchant_name = "unknown merchant"
        zdo_type = transaction["ZDO_TYPE"]
        if zdo_type == 1:
            transaction_type = "debit"
        elif zdo_type == 2:
            transaction_type = "credit"
        elif zdo_type == 3:
            transaction_type = "upi"
        else:
            transaction_type = ""
        card_number = transaction["ZCARDDIVIDID"]
        if card_number is None or card_number.strip() == "":
            card_number = None
        category = transaction["ZCATEGORY_NAME"] if transaction["ZCATEGORY_NAME"] is not None else ""
        notes = transaction["ZCONTENT"] if transaction["ZCONTENT"] is not None else ""
        pg_cursor.execute("""
            INSERT INTO external_transactions (email_timestamp, amount, merchant_name, transaction_type, card_number, category, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            email_timestamp,
            amount,
            merchant_name,
            transaction_type,
            card_number,
            category,
            notes,
        ))

    # Commit and close connections
    pg_conn.commit()
    print("All transactions have been successfully committed to Postgres.")
    pg_cursor.close()
    pg_conn.close()
    sqlite_cursor.close()
    sqlite_conn.close()

if __name__ == "__main__":
    sqlite_db_path = "20250908_014447.mmbak"
    pg_conn_params = get_db_config()
    sync_transactions(sqlite_db_path, pg_conn_params)
